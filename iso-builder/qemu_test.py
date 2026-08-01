"""Ephemeral QEMU test VM: boots a built ISO in a throwaway UEFI machine.

Everything the VM touches -- the 50GB+ disk, OVMF NVRAM vars, the QEMU
monitor/VNC sockets -- lives in a fresh temp directory created per session
and is deleted completely (shutil.rmtree) the moment the session ends, no
matter how it ends (guest shutdown, Stop button, or the app closing). The
VM display is exposed over a local VNC socket so a GtkVnc.Display widget
can render it embedded in the app instead of QEMU opening its own window.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile

OVMF_CODE_CANDIDATES = [
    "/usr/share/edk2/x64/OVMF_CODE.4m.fd",
    "/usr/share/edk2-ovmf/x64/OVMF_CODE.fd",
    "/usr/share/OVMF/OVMF_CODE.fd",
]
OVMF_VARS_CANDIDATES = [
    "/usr/share/edk2/x64/OVMF_VARS.4m.fd",
    "/usr/share/edk2-ovmf/x64/OVMF_VARS.fd",
    "/usr/share/OVMF/OVMF_VARS.fd",
]

MIN_RAM_MIB = 4096
MIN_CPUS = 2
MIN_DISK_GIB = 50


def _find_first(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def find_ovmf():
    return _find_first(OVMF_CODE_CANDIDATES), _find_first(OVMF_VARS_CANDIDATES)


def _free_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class QemuTestSession:
    """One throwaway VM. Call start(), then stop() exactly once (stop() is
    also safe to call if start() partially failed, to clean up).
    """

    def __init__(self, iso_path, ram_mib=MIN_RAM_MIB, cpus=MIN_CPUS, disk_gib=MIN_DISK_GIB):
        self.iso_path = iso_path
        self.ram_mib = max(ram_mib, MIN_RAM_MIB)
        self.cpus = max(cpus, MIN_CPUS)
        self.disk_gib = max(disk_gib, MIN_DISK_GIB)
        self.process = None
        self.vnc_port = None
        self.tempdir = None

    def start(self):
        ovmf_code, ovmf_vars = find_ovmf()
        if not ovmf_code or not ovmf_vars:
            raise RuntimeError(
                "OVMF (UEFI firmware) not found -- install edk2-ovmf (pacman -S edk2-ovmf)."
            )
        if not shutil.which("qemu-system-x86_64"):
            raise RuntimeError("qemu-system-x86_64 not found -- install qemu-full/qemu-desktop.")
        if not os.path.exists(self.iso_path):
            raise RuntimeError(f"ISO not found: {self.iso_path}")

        self.tempdir = tempfile.mkdtemp(prefix="pearos-qemu-test-")
        disk_path = os.path.join(self.tempdir, "disk.qcow2")
        vars_path = os.path.join(self.tempdir, "OVMF_VARS.fd")
        monitor_socket = os.path.join(self.tempdir, "monitor.sock")

        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", disk_path, f"{self.disk_gib}G"],
            check=True, capture_output=True,
        )
        shutil.copyfile(ovmf_vars, vars_path)

        self.vnc_port = _free_tcp_port()
        vnc_display_index = self.vnc_port - 5900  # QEMU's -vnc :N means TCP port 5900+N

        accel = "kvm" if os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK) else "tcg"

        argv = [
            "qemu-system-x86_64",
            "-name", "pearOS-test (ephemeral)",
            "-machine", f"q35,accel={accel}",
            "-cpu", "host" if accel == "kvm" else "max",
            "-smp", str(self.cpus),
            "-m", str(self.ram_mib),
            "-drive", f"if=pflash,format=raw,readonly=on,file={ovmf_code}",
            "-drive", f"if=pflash,format=raw,file={vars_path}",
            "-drive", f"file={disk_path},if=virtio,format=qcow2",
            "-drive", f"file={self.iso_path},media=cdrom,if=ide,readonly=on",
            "-boot", "order=d,menu=on",
            "-vga", "std",
            "-device", "virtio-net-pci,netdev=net0",
            "-netdev", "user,id=net0",
            "-display", "none",
            "-vnc", f"127.0.0.1:{vnc_display_index}",
            "-monitor", f"unix:{monitor_socket},server,nowait",
            "-no-reboot",
        ]

        self.process = subprocess.Popen(
            argv, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True
        )
        return self

    def is_alive(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            except ProcessLookupError:
                pass
        self.process = None
        if self.tempdir and os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir, ignore_errors=True)
        self.tempdir = None
