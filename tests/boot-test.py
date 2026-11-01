#!/usr/bin/env python3
"""Boot the ISO in QEMU (UEFI), screenshot the screen every INTERVAL seconds
into seq/1.png, seq/2.png, ... and list them in README.md under
"Boot Status sequence".

Exit code 0 if the VM looks booted (screen changed over time and the last
frame is not blank), 1 otherwise. No dependencies besides qemu + OVMF.

Usage: tests/boot-test.py path/to.iso [--duration 180] [--interval 10]
"""
import argparse, hashlib, json, os, re, shutil, socket, struct, subprocess
import sys, tempfile, time, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVMF_CODE = [
    "/usr/share/edk2/x64/OVMF_CODE.4m.fd",
    "/usr/share/OVMF/OVMF_CODE_4M.fd",
    "/usr/share/OVMF/OVMF_CODE.fd",
    "/usr/share/edk2/ovmf/OVMF_CODE.fd",
]
OVMF_VARS = [
    "/usr/share/edk2/x64/OVMF_VARS.4m.fd",
    "/usr/share/OVMF/OVMF_VARS_4M.fd",
    "/usr/share/OVMF/OVMF_VARS.fd",
    "/usr/share/edk2/ovmf/OVMF_VARS.fd",
]
BEGIN, END = "<!-- boot-seq:begin -->", "<!-- boot-seq:end -->"


def first_existing(paths, what):
    for p in paths:
        if os.path.exists(p):
            return p
    sys.exit(f"OVMF {what} not found (install edk2-ovmf / ovmf)")


def read_ppm(path):
    with open(path, "rb") as f:
        data = f.read()
    m = re.match(rb"P6\s+(\d+)\s+(\d+)\s+(\d+)\s", data)
    w, h = int(m[1]), int(m[2])
    return w, h, data[m.end():]


def write_png(path, w, h, rgb):
    raw = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6))
                + chunk(b"IEND", b""))


class QMP:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX)
        for _ in range(50):
            try:
                self.s.connect(path)
                break
            except OSError:
                time.sleep(0.2)
        else:
            sys.exit("cannot connect to QMP socket")
        self.f = self.s.makefile("rw")
        self.f.readline()  # greeting
        self.cmd("qmp_capabilities")

    def cmd(self, name, **args):
        self.f.write(json.dumps({"execute": name, "arguments": args}) + "\n")
        self.f.flush()
        while True:
            r = json.loads(self.f.readline())
            if "return" in r or "error" in r:
                return r


def update_readme(frames, interval, verdict):
    lines = [BEGIN, "", f"Result: **{verdict}**  ", f"One screenshot every {interval}s.", ""]
    for i in range(1, frames + 1):
        lines.append(f"{i}. `{(i - 1) * interval}s` — ![boot {i}](seq/{i}.png)")
    lines += ["", END]
    block = "\n".join(lines)
    path = os.path.join(ROOT, "README.md")
    text = open(path).read()
    if BEGIN in text and END in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        text = text.replace("\n## Star History",
                            f"\n## Boot Status sequence 📌\n{block}\n\n## Star History", 1)
    open(path, "w").write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iso")
    ap.add_argument("--duration", type=int, default=180)
    ap.add_argument("--interval", type=int, default=10)
    ap.add_argument("--memory", default="4G")
    a = ap.parse_args()

    seq = os.path.join(ROOT, "seq")
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)

    tmp = tempfile.mkdtemp()
    vars_copy = os.path.join(tmp, "vars.fd")
    shutil.copy(first_existing(OVMF_VARS, "vars"), vars_copy)
    sock = os.path.join(tmp, "qmp.sock")
    accel = "kvm" if os.access("/dev/kvm", os.W_OK) else "tcg"
    qemu = subprocess.Popen([
        "qemu-system-x86_64", "-machine", f"q35,accel={accel}", "-m", a.memory,
        "-smp", "2", "-display", "none", "-vga", "std",
        "-drive", f"if=pflash,format=raw,readonly=on,file={first_existing(OVMF_CODE, 'code')}",
        "-drive", f"if=pflash,format=raw,file={vars_copy}",
        "-cdrom", a.iso, "-boot", "d", "-qmp", f"unix:{sock},server=on,wait=off",
    ])
    print(f"QEMU started (accel={accel})")

    qmp = QMP(sock)
    hashes, bright, n = [], 0.0, 0
    try:
        for n in range(1, a.duration // a.interval + 1):
            time.sleep(a.interval)
            if qemu.poll() is not None:
                print("QEMU exited early")
                n -= 1
                break
            ppm = os.path.join(tmp, "s.ppm")
            qmp.cmd("screendump", filename=ppm)
            w, h, rgb = read_ppm(ppm)
            write_png(os.path.join(seq, f"{n}.png"), w, h, rgb)
            hashes.append(hashlib.md5(rgb).hexdigest())
            bright = sum(rgb[::97]) / len(rgb[::97])
            print(f"[{n * a.interval:>4}s] seq/{n}.png {w}x{h} brightness={bright:.1f}")
    finally:
        qemu.kill()
        shutil.rmtree(tmp, ignore_errors=True)

    booted = n >= 2 and len(set(hashes)) >= 3 and bright > 20
    verdict = "booted ✅" if booted else "boot FAILED ❌"
    print(verdict)
    if n:
        update_readme(n, a.interval, verdict)
    sys.exit(0 if booted else 1)


main()
