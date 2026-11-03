#!/usr/bin/env python3
"""Boot the ISO in QEMU (UEFI), screenshot the screen every INTERVAL seconds
into seq/1.png, seq/2.png, ... and list them in README.md under
"Boot Status sequence".

Phases:
  1. boot until the desktop is up (Welcome app on screen, picture stable)
  2. click "Install pearOS" in the Welcome app (virtual tablet via QMP)
  3. walk the pearOS installer: pick English -> Next -> "Install pearOS
     NiceC0re" (offline installer) -> Continue; Calamares then opens and the
     last frame should be Calamares

Also runs the UI Sanity Test on the "desktop ready" frame: the top 30 px
(menu bar) and bottom 100 px (dock) are compared with tests/ui-reference/
desktop.png and the % of matching pixels is reported (README: "UI Sanity
Test"). Refresh the reference with --update-reference.

Exit code 0 if the VM booted, the installer opened (screen changed massively
after the click) and the UI sanity test passed; 1 otherwise. No dependencies besides qemu + OVMF.

Usage: tests/boot-test.py path/to.iso [--duration 180] [--install-wait 90]
                          [--interval 10] [--click 575,181]
--click is the "Install pearOS" button in the Welcome app, in pixels of the
1280x800 guest screen.
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
# Calamares pages, in pixels of the 1280x800 guest screen (verified on the
# 2026.11 ISO): Welcome -> Location -> Keyboard -> Partitions -> Summary ->
# Install -> Finish. No users page: the installed system asks on first boot.
CALAMARES_STEPS = [
    ("Welcome, clicked Next", (1133, 654)),
    ("Location, clicked Next", (1133, 654)),
    ("Keyboard, clicked Next", (1133, 654)),
    ("Partitions, selected Erase disk", (19, 107)),
    ("Partitions, clicked Next", (1133, 654)),
    ("Summary, clicked Install", (1120, 654)),
]
# First-boot "hello" assistant of the installed system (same 1280x800 pixels).
# Throwaway account that only exists inside the test VM.
TEST_USER = {"full": "Tester", "name": "tester", "password": "pearos-test-1"}
SETUP_CONTINUE = (983, 682)
APPS = [  # (label, desktop-file id, words the menu bar shows while it has focus)
    ("Seafari", "seafari", ("seafari",)), ("Calculator", "calculator", ("calculator",)),
    ("Notes", "pearos-notes", ("notes",)), ("Finder", "org.gnome.Nautilus", ("files", "finder", "nautilus")),
    ("Kate", "org.kde.kate", ("kate",)),
]
KONSOLE_BOX = (188, 135, 1090, 640)
FINISH_TAB = (1130, 684)  # turns blue when Calamares reaches Finish

# Everything that differs between the pearOS builds. Pixels are for the 1280x800
# guest screen, verified on the 2026.11 (arch) and Goldwing (debian) ISOs.
_C = SETUP_CONTINUE
_C2 = (968, 658)  # "Continue" of the Debian first-boot assistant
PROFILES = {
    "arch": {
        "ref_dir": "",
        # (what the frame shows, click done after it) -- one per --interval tick
        "installer_ticks": [
            ("pearOS installer loading", None, None),
            ("Language screen", "selected English", (657, 385)),
            ("Language screen", "clicked Next", (1022, 704)),
            ("Recovery screen", "selected **Install pearOS NiceC0re** (offline installer)", (655, 353)),
            ("Recovery screen", "clicked **Continue**", (858, 655)),
        ],
        "install_wait": 110,
        "calamares_change": 0.4,
        "calamares_steps": CALAMARES_STEPS,
        "calamares_delay": 4,
        "finish": ("tab", FINISH_TAB),
        "first_boot": [
            ("click", 671, 654),
            ("page", "First boot: language", 5, [("click", 650, 476), ("click", *_C)]),
            ("page", "First boot: keyboard", 5, [("click", 657, 376), ("click", *_C)]),
            ("page", "First boot: time zone", 5, [("click", 650, 396), ("click", *_C)]),
            ("frame", "First boot: create account", 6),
            ("click", 611, 430), ("type", "full"), ("click", 611, 466), ("type", "name"),
            ("click", 567, 586), ("type", "password"), ("click", 800, 586), ("type", "password"),
            ("frame", "First boot: account filled in", 2),
            ("click", *_C),
            ("page", "First boot: look", 8, [("click", *_C)]),
            ("page", "First boot: terms", 8, [("click", *_C)]),
            ("frame", "First boot: applying settings", 10),
        ],
        "identity": ("fastfetch", "fastfetch shows pearOS"),
        "update": {"cmd": "sudo pacman -Syyu --noconfirm", "marker": "PACMAN",
                   "check": "sudo pacman -Syyu --noconfirm", "error": "pacman exited with an error",
                   "label": "pacman -Syyu"},
        "apps": APPS,
    },
    "debian": {
        "ref_dir": "debian",
        "installer_ticks": [
            ("pearOS installer loading", None, None),
            ("pearOS installer loading", None, None),
            ("Language screen", "selected English", (640, 200)),
            ("Language screen", "clicked Next", (992, 582)),
            ("Recovery screen", "selected **Install pearOS Goldwing**", (640, 222)),
            ("Recovery screen", "clicked **Continue**", (875, 537)),
            ("Installer welcome", "clicked **Continue**", (639, 544)),
            ("Terms and Conditions", "clicked **Continue**", (980, 576)),
        ],
        "install_wait": 160,
        "calamares_change": 0.12,
        "calamares_steps": [
            ("Welcome, clicked Next", (1022, 669)),
            ("Location, clicked Next", (1022, 669)),
            ("Keyboard, clicked Next", (1022, 669)),
            ("Partitions, selected Erase disk", (400, 240)),
            ("Partitions, clicked Next", (1022, 669)),
            ("Summary, clicked Install", (1018, 721)),
        ],
        "calamares_delay": 7,
        # Calamares runs in a window here (no step tabs): the Finish page says "All done."
        "finish": ("ocr", (140, 170, 1140, 700), "all done"),
        "first_boot": [
            ("click", 640, 730),
            ("page", "First boot: country", 5, [("click", 968, 627)]),
            ("page", "First boot: transfer", 5, [("click", *_C2)]),
            ("page", "First boot: languages", 5, [("click", *_C2)]),
            ("page", "First boot: accessibility", 5, [("click", *_C2)]),
            ("page", "First boot: data & privacy", 5, [("click", *_C2)]),
            ("page", "First boot: PearID", 5, [("click", 830, 659)]),
            ("frame", "First boot: create account", 5),
            ("click", 640, 330), ("type", "full"), ("click", 640, 368), ("type", "name"),
            ("click", 520, 434), ("type", "password"), ("click", 760, 434), ("type", "password"),
            ("page", "First boot: account filled in", 2, [("click", *_C2)]),
            ("page", "First boot: terms", 6, [("click", *_C2)]),
            ("page", "First boot: location services", 5, [("click", *_C2)]),
            ("page", "First boot: time zone", 5, [("click", *_C2)]),
            ("page", "First boot: analytics", 5, [("click", *_C2)]),
            ("page", "First boot: screen time", 5, [("click", *_C2)]),
            ("page", "First boot: Piri", 5, [("click", *_C2)]),
            ("page", "First boot: look", 5, [("click", *_C2)]),
            ("page", "First boot: updates", 5, [("click", *_C2)]),
            ("page", "First boot: ready", 8, [("click", 640, 730)]),
            ("frame", "First boot: applying settings", 25),
        ],
        "identity": ("cat /etc/os-release", "os-release says pearOS"),
        "update": {"cmd": "sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get -y dist-upgrade",
                   "marker": "APT", "check": "sudo apt-get dist-upgrade",
                   "error": "apt-get exited with an error", "label": "apt-get dist-upgrade"},
        "apps": [("Pafari", "org.gnome.Pafari", ("pafari",)), ("Calculator", "calculator", ("calculator",)),
                 ("Notes", "pearos-notes", ("notes",)),
                 ("Finder", "org.gnome.Nautilus", ("files", "finder", "nautilus"), "nautilus --new-window"),
                 ("Kate", "org.kde.kate", ("kate",))],
    },
}
# Raspberry Pi image (arm64, Debian base): no live ISO and no Calamares. The disk image boots
# straight into the first-boot assistant, which plays the role of the "installation"; every
# check after that (login, UI sanity, os-release, apt, apps, reboot) is the Debian one.
PROFILES["debian-pi"] = dict(PROFILES["debian"], ref_dir="debian-pi", arch="arm64", image=True,
                             install_wait=0)
AAVMF_CODE = [
    "/usr/share/AAVMF/AAVMF_CODE.fd",
    "/usr/share/qemu-efi-aarch64/QEMU_EFI.fd",
    "/usr/share/edk2/aarch64/QEMU_EFI-pflash.raw",
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


def read_png(path):
    """Reads PNGs written by write_png (8-bit RGB, filter 0, one IDAT run)."""
    with open(path, "rb") as f:
        data = f.read()
    pos, idat, w = 8, b"", 0
    while pos < len(data):
        n, t = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if t == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif t == b"IDAT":
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    stride = w * 3 + 1
    return w, h, b"".join(raw[y * stride + 1:(y + 1) * stride] for y in range(h))


def pixel(rgb, w, x, y):
    i = (y * w + x) * 3
    return rgb[i], rgb[i + 1], rgb[i + 2]


def crop_rgb(rgb, w, x0, y0, x1, y1):
    return b"".join(rgb[(y * w + x0) * 3:(y * w + x1) * 3] for y in range(y0, y1))


def ocr(rgb, w, box, scale=2, both=False):
    """Text in a screen region via tesseract, or None when tesseract is not installed.

    Terminal text is light on dark with coloured progress bars, which different
    tesseract versions read very differently, so the region is converted to
    greyscale, inverted when it is mostly dark, and upscaled first.
    """
    if not shutil.which("tesseract"):
        return None
    x0, y0, x1, y1 = box
    cw, ch = x1 - x0, y1 - y0
    crop = crop_rgb(rgb, w, x0, y0, x1, y1)
    gray = [(r + g + b) // 3 for r, g, b in zip(crop[0::3], crop[1::3], crop[2::3])]

    def run(pix, psm):
        out = bytearray()
        for y in range(ch):
            row = bytes(v for v in pix[y * cw:(y + 1) * cw] for _ in range(scale))
            out += row * scale
        d = tempfile.mkdtemp()
        try:
            path = os.path.join(d, "c.pgm")
            with open(path, "wb") as f:
                f.write(b"P5\n%d %d\n255\n" % (cw * scale, ch * scale))
                f.write(bytes(out))
            return subprocess.run(["tesseract", path, "stdout", "--psm", psm],
                                  capture_output=True, text=True, timeout=120).stdout
        finally:
            shutil.rmtree(d, ignore_errors=True)

    if both:
        # one line of text (menu bar), unknown polarity: read it both ways
        return run(gray, "7") + "\n" + run([255 - v for v in gray], "7")
    if sum(gray) / len(gray) < 110:
        gray = [255 - v for v in gray]
    return run(gray, "6")


def key_combo(qmp, combo):
    qmp.cmd("send-key", keys=[{"type": "qcode", "data": k} for k in combo.split("+")])


def strip_similarity(a, b, w, y0, y1, tol=16):
    """% of pixels in rows [y0, y1) whose RGB channels all differ by <= tol."""
    ra, rb = a[y0 * w * 3:y1 * w * 3], b[y0 * w * 3:y1 * w * 3]
    same = sum(1 for i in range(0, len(ra), 3)
               if abs(ra[i] - rb[i]) <= tol and abs(ra[i + 1] - rb[i + 1]) <= tol
               and abs(ra[i + 2] - rb[i + 2]) <= tol)
    return 100.0 * same / (len(ra) // 3)


def changed_fraction(a, b, tol=16):
    """Fraction of (sampled) bytes that differ by more than tol."""
    xs = range(0, min(len(a), len(b)), 97)
    return sum(1 for i in xs if abs(a[i] - b[i]) > tol) / len(xs)



def dock_visible(rgb, w, h):
    """True when the bottom band holds the dock: a modest number of saturated icon pixels.
    (The login/assistant screens have none; a full-screen blue wallpaper has far too many; a
    light wallpaper is not saturated enough to count.) OCR of the white menu bar on a light
    wallpaper is unreliable, so this is the 'is this the desktop' signal on images."""
    y0, y1 = int(h * 0.885), int(h * 0.99)
    x0, x1 = int(w * 0.06), int(w * 0.94)
    sat = total = 0
    for y in range(y0, y1, 2):
        row = (y * w + x0) * 3
        for x in range(x0, x1, 2):
            i = row + (x - x0) * 3
            r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
            total += 1
            if max(r, g, b) - min(r, g, b) >= 70 and max(r, g, b) >= 90:
                sat += 1
    frac = sat / max(1, total)
    return 0.01 <= frac <= 0.25

SERIAL_PATTERNS = [
    r"Kernel panic[^\n]*", r"VFS: Unable to mount root[^\n]*", r"Cannot open root device[^\n]*",
    r"[^\n]*Dependency failed for[^\n]*", r"[^\n]*Failed to start[^\n]*",
    r"[^\n]*Failed to (?:mount|find|load)[^\n]*", r"[^\n]*Welcome to emergency mode[^\n]*",
    r"[^\n]*You are in emergency mode[^\n]*", r"ERROR:[^\n]*", r"[^\n]*Unable to find[^\n]*",
    r"[^\n]*timed out[^\n]*", r"[^\n]*Segmentation fault[^\n]*", r"[^\n]*Out of memory[^\n]*",
    r"[^\n]*Call Trace[^\n]*", r"[^\n]*BUG:[^\n]*", r"[^\n]*not found[^\n]*",
]


def analyze_serial(text, max_evidence=8):
    """Distinctive failure lines from a serial console log (deduplicated)."""
    found = []
    for pat in SERIAL_PATTERNS:
        for m in re.finditer(pat, text):
            line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", m.group(0)).strip()
            if line and line not in found:
                found.append(line[:200])
    return found[:max_evidence]


def diagnose_guest(iso, memory, accel, wait=150):
    """Boots the ISO's kernel + initramfs directly (bypassing the bootloader) with
    the console on a serial port, logs in as root and asks systemd what is going
    on. Returns (boot_log, facts, error); facts has the cause when one is found.
    Explains kernel / early-userspace / session failures, not bootloader ones."""
    import socket
    work = tempfile.mkdtemp()
    qemu = None
    try:
        files = {"vmlinuz": "/arch/boot/x86_64/vmlinuz-linux",
                 "initramfs": "/arch/boot/x86_64/initramfs-linux.img",
                 "intel": "/arch/boot/intel-ucode.img", "amd": "/arch/boot/amd-ucode.img",
                 "entry": "/loader/entries/01-archiso-x86_64-linux.conf"}
        args = ["xorriso", "-osirrox", "on", "-indev", iso]
        for k, v in files.items():
            args += ["-extract", v, os.path.join(work, k)]
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(os.path.join(work, "vmlinuz")):
            return None, {}, "kernel not found in the ISO at /arch/boot/x86_64/vmlinuz-linux"
        entry = open(os.path.join(work, "entry")).read() if os.path.exists(os.path.join(work, "entry")) else ""
        m = re.search(r"^options\s+(.*)$", entry, re.M)
        opts = (m.group(1) if m else "archisobasedir=arch").replace("quiet", "").replace("splash", "")
        with open(os.path.join(work, "initrd"), "wb") as out:
            for k in ("amd", "intel", "initramfs"):
                if os.path.exists(os.path.join(work, k)):
                    out.write(open(os.path.join(work, k), "rb").read())
        vars_copy = os.path.join(work, "vars.fd")
        shutil.copy(first_existing(OVMF_VARS, "vars"), vars_copy)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        qemu = subprocess.Popen([
            "qemu-system-x86_64", "-machine", f"q35,accel={accel}", "-m", memory, "-smp", "2",
            "-display", "none", "-vga", "std", "-nic", "user",
            "-serial", f"tcp:127.0.0.1:{port},server=on,wait=off",
            "-drive", f"if=pflash,format=raw,readonly=on,file={first_existing(OVMF_CODE, 'code')}",
            "-drive", f"if=pflash,format=raw,file={vars_copy}",
            "-kernel", os.path.join(work, "vmlinuz"), "-initrd", os.path.join(work, "initrd"),
            "-append", opts + " console=ttyS0,115200", "-cdrom", iso, "-boot", "d"],
            stderr=subprocess.DEVNULL)
        time.sleep(4)
        sock = socket.create_connection(("127.0.0.1", port))
        sock.settimeout(1)
        ansi = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\\\x07]*(?:\\|\x07)|\(B")

        def read(seconds, until=None):
            end, out = time.time() + seconds, ""
            while time.time() < end:
                try:
                    out += ansi.sub("", sock.recv(65536).decode(errors="replace"))
                except socket.timeout:
                    pass
                if until and until in out:
                    break
            return out

        log = read(120, until="login:")
        if "login:" not in log:
            return log, {}, None  # the kernel never got to a login prompt
        sock.sendall(b"\n"); read(2)
        sock.sendall(b"root\n"); read(4)

        def run(cmd, seconds=10):
            sock.sendall((cmd + "\n").encode())
            return read(seconds)

        # Give the session time to either come up or start crash-looping.
        run("for i in $(seq 1 %d); do systemctl is-active -q graphical.target && break; sleep 2; done; sleep 15" % (wait // 2), wait + 25)
        facts = {}
        facts["active"] = run("systemctl is-active graphical.target sddm", 8)
        facts["jobs"] = run("systemctl list-jobs --no-pager", 8)
        facts["symbols"] = run("journalctl -b --no-pager | grep -aoE '[^ ]+: symbol lookup error: .*' | sort -u | head -3", 10)
        facts["qt"] = run("journalctl -b --no-pager | grep -aoE 'Could not load the Qt platform plugin[^.]*' | sort -u | head -2", 10)
        facts["cores"] = run("coredumpctl list --no-pager 2>/dev/null | awk '{print $(NF-3), $(NF-2)}' | sort | uniq -c | head -6", 10)
        facts["slow"] = run("systemd-analyze blame --no-pager 2>/dev/null | head -3", 10)
        return log, facts, None
    except OSError as e:
        return None, {}, f"could not run the diagnosis: {e}"
    finally:
        if qemu:
            qemu.kill()
        shutil.rmtree(work, ignore_errors=True)


def explain_guest(facts):
    """(cause, evidence lines) from the facts collected by diagnose_guest."""
    def lines(key):
        return [l.strip() for l in facts.get(key, "").splitlines()[1:]
                if l.strip() and not l.strip().startswith(("#", "root@"))]

    symbols = [re.sub(r"^.*?(/\S+: symbol lookup error)", r"\1", l) for l in lines("symbols")
               if "symbol lookup error" in l]
    if symbols:
        return ("the desktop session crashes at startup, a shared library does not match the program "
                "that loads it (typically two packages from different release sets)"), symbols
    qt = [l for l in lines("qt") if "Qt platform plugin" in l]
    jobs = [l.split()[1] for l in lines("jobs") if re.match(r"^\d+\s+\S+\.service\s", l)]
    active = " ".join(lines("active"))
    if jobs and "inactive" in active.split()[:1]:
        return ("the boot is held up: graphical.target waits for services that never finish ("
                + ", ".join(jobs) + ")"), lines("slow")
    cores = lines("cores")
    if cores:
        return "desktop components crashed at startup", cores
    if qt:
        return "an application cannot initialise its Qt platform plugin", qt
    if "inactive" in active or "failed" in active:
        return "the display manager (sddm) is not running", lines("active")
    return None, []


def classify_failure(hashes, frames, n, desktop_at, installer, ui, size):
    """(stage, human reason) for a failed run, judged from the screenshots."""
    if not n:
        return "no-frames", "QEMU produced no screenshots (VM did not start)."
    w, h = size
    last = frames[n]
    nonblack = sum(1 for i in range(0, len(last), 97) if last[i] > 12) / len(range(0, len(last), 97))
    if desktop_at is None:
        if len(set(hashes)) == 1:
            return "bootloader", "Stuck in the bootloader: the screen never changed, the kernel was not started."
        if nonblack < 0.002:
            return "black-screen", ("Black screen after the bootloader: the kernel/initramfs started but nothing "
                                    "graphical ever appeared (hang or crash before Plymouth/SDDM).")
        return "splash", "Boot never reached the desktop: the screen stayed on a boot splash / early UI."
    if not installer:
        return "installer", "Desktop reached, but the pearOS installer / Calamares did not open."
    if ui is not None and not ui["ok"]:
        return "ui", (f"The desktop looks different from the reference: menu bar {ui['top']:.1f}%, "
                      f"dock {ui['dock']:.1f}% similar (needs {ui['threshold']:.0f}%).")
    return "unknown", "Test failed for an unknown reason."


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


def click(qmp, x, y, w, h):
    """Move the virtual tablet to (x, y) of a w x h screen and left-click."""
    ax = {"type": "abs", "data": {"axis": "x", "value": int(x * 32767 / w)}}
    ay = {"type": "abs", "data": {"axis": "y", "value": int(y * 32767 / h)}}
    qmp.cmd("input-send-event", events=[ax, ay])
    time.sleep(1)
    for down in (True, False):
        qmp.cmd("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": "left"}}])
        time.sleep(0.15)


# Characters the guest keyboard can type: char -> QMP qcodes (US layout).
_KEYS = {" ": ["spc"], "-": ["minus"], "_": ["shift", "minus"], ".": ["dot"], "/": ["slash"],
         ",": ["comma"], "=": ["equal"], ":": ["shift", "semicolon"], ";": ["semicolon"],
         "|": ["shift", "backslash"], "\\": ["backslash"], "$": ["shift", "4"], "&": ["shift", "7"],
         ">": ["shift", "dot"], "<": ["shift", "comma"], "'": ["apostrophe"], "*": ["shift", "8"],
         "~": ["shift", "grave_accent"], "@": ["shift", "2"], "!": ["shift", "1"], "+": ["shift", "equal"],
         "(": ["shift", "9"], ")": ["shift", "0"], '"': ["shift", "apostrophe"], "?": ["shift", "slash"],
         "[": ["bracket_left"], "]": ["bracket_right"], "%": ["shift", "5"], "#": ["shift", "3"]}


def type_text(qmp, text, delay=0.12, enter=False):
    """Type text through the guest keyboard (QMP send-key), optionally ending with Enter."""
    for ch in text:
        if ch in _KEYS:
            keys = _KEYS[ch]
        elif ch.isalpha() or ch.isdigit():
            keys = ["shift", ch.lower()] if ch.isupper() else [ch]
        else:
            raise ValueError(f"cannot type {ch!r}")
        qmp.cmd("send-key", keys=[{"type": "qcode", "data": k} for k in keys])
        time.sleep(delay)
    if enter:
        qmp.cmd("send-key", keys=[{"type": "qcode", "data": "ret"}])
        time.sleep(delay)


UI_BEGIN, UI_END = "<!-- ui-sanity:begin -->", "<!-- ui-sanity:end -->"


def replace_block(text, begin, end, body, heading):
    block = "\n".join([begin, "", body, "", end])
    if begin in text and end in text:
        return re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _: block, text, flags=re.S)
    if "\n## Star History" in text:
        return text.replace("\n## Star History", f"\n## {heading} 📌\n{block}\n\n## Star History", 1)
    return text.rstrip("\n") + f"\n\n## {heading} 📌\n{block}\n"


def update_readme(frames, interval, verdict, notes, ui, failure=None, score=None, out_dir=None, ref_rel="tests/ui-reference/"):
    lines = [f"Result: **{verdict}**  "]
    if score:
        lines += ["", f"**Success score: {score['total']}/100**", "",
                  "| Test | Score |", "|---|---|"]
        for name, label in (("boot", "Boot"), ("ui", "UI sanity"), ("install", "Installable"),
                            ("usability", "Usability")):
            if score.get(name) is not None:
                lines.append(f"| {label} | {score[name]}/100 |")
        if score.get("checks"):
            lines += ["", "Usability checks:", "", "| Check | Result |", "|---|---|"]
            for k, v in score["checks"].items():
                lines.append(f"| {k} | {'✅' if v['ok'] else '❌'} {v.get('detail', '')} |")
        lines.append("")
    if failure:
        lines += ["", f"> **Why it failed:** {failure['reason']}", ""]
        if failure.get("evidence"):
            lines += ["Kernel/initramfs log lines that explain it (serial console, direct kernel boot):", "", "```"]
            lines += failure["evidence"] + ["```", ""]
        lines += ["This ISO was **not published**; it was saved as a quarantined `FAIL_TEST` build.", ""]
    lines += [f"One screenshot every {interval}s.", ""]
    for i in range(1, frames + 1):
        note = f" — {notes[i]}" if i in notes else ""
        lines.append(f"{i}. `{i * interval}s`{note} — ![boot {i}](seq/{i}.png)")
    path = os.path.join(out_dir or ROOT, "README.md")
    if not os.path.exists(path):
        open(path, "w").write("")
    text = open(path).read()
    text = replace_block(text, BEGIN, END, "\n".join(lines), "Boot Status sequence")
    if ui:
        u = ["Result: **%s**  " % ui["verdict"],
             f"Compared against the reference `{ref_rel}desktop.png` "
             f"(% of pixels within ±{ui['tol']} per channel; pass ≥ {ui['threshold']:.0f}%).", "",
             "| Area | Similarity |", "|---|---|",
             f"| Top bar (first 30 px) | {ui['top']:.1f}% |",
             f"| Dock (last 100 px) | {ui['dock']:.1f}% |", "",
             f"Current frame: ![desktop](seq/{ui['frame']}.png)"]
        text = replace_block(text, UI_BEGIN, UI_END, "\n".join(u), "UI Sanity Test")
    open(path, "w").write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iso")
    ap.add_argument("--duration", type=int, default=180)
    ap.add_argument("--interval", type=int, default=10)
    ap.add_argument("--memory", default="16G")
    ap.add_argument("--distro", choices=sorted(PROFILES), default="arch",
                    help="which pearOS build is being tested (installer clicks, update command, apps)")
    ap.add_argument("--slow", type=float, default=1.0,
                    help="multiply every wait inside the guest by this (emulated CPU, e.g. the Pi image on a "
                         "runner without KVM: 4)")
    ap.add_argument("--workdir", default=None,
                    help="where seq/ and README.md are written (default: this repo)")
    ap.add_argument("--install-wait", type=int, default=None,
                    help="seconds to keep capturing after clicking Install pearOS (default: per distro)")
    ap.add_argument("--update-reference", action="store_true",
                    help="save the desktop-ready frame as the UI sanity reference")
    ap.add_argument("--ui-threshold", type=float, default=90.0)
    ap.add_argument("--diagnose-seconds", type=int, default=150,
                    help="how long to wait for graphical.target when diagnosing a failure")
    ap.add_argument("--full-install", action="store_true",
                    help="after Calamares opens, click through it, wait for \"installed\", "
                         "then boot the installed disk (a pass then means pearOS really installs)")
    ap.add_argument("--disk-dir", default=None,
                    help="where to keep the 20 GB target disk (must be a real disk, not tmpfs)")
    ap.add_argument("--install-timeout", type=int, default=5400,
                    help="seconds to wait for the installation to finish")
    ap.add_argument("--install-frame-every", type=int, default=120,
                    help="save a frame this often (s) while the installation runs")
    ap.add_argument("--upgrade-reboot", action="store_true",
                    help="after sudo pacman -Syyu, reboot the installed system and check that it still "
                         "reaches the login screen and the desktop (the 'black screen after -Syu' case)")
    ap.add_argument("--canary", action="store_true",
                    help="upgrade canary: install an OLD ISO, update it from the live repo, reboot. "
                         "Passes only if install, login, pacman and the post-update boot all work "
                         "(UI sanity and the other usability checks do not gate)")
    ap.add_argument("--pacman-timeout", type=int, default=900,
                    help="seconds to wait for sudo pacman -Syyu --noconfirm in the installed system")
    ap.add_argument("--reboot-wait", type=int, default=300,
                    help="seconds to wait for the installed system to reach a login/desktop")
    ap.add_argument("--click", default="575,181",
                    help="x,y of the Install pearOS button in the Welcome app")
    a = ap.parse_args()

    P = PROFILES[a.distro]
    if a.install_wait is None:
        a.install_wait = P["install_wait"]
    OUT = os.path.abspath(a.workdir) if a.workdir else ROOT
    REFDIR = os.path.join(ROOT, "tests", "ui-reference", P["ref_dir"])
    seq = os.path.join(OUT, "seq")
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)

    tmp = tempfile.mkdtemp()
    vars_copy = os.path.join(tmp, "vars.fd")
    arm = P.get("arch") == "arm64"
    if not arm:
        shutil.copy(first_existing(OVMF_VARS, "vars"), vars_copy)
    sock = os.path.join(tmp, "qmp.sock")
    disk_dir = a.disk_dir or tmp
    os.makedirs(disk_dir, exist_ok=True)
    disk = os.path.join(disk_dir, "disk.img")
    if P.get("image"):
        # The "ISO" argument is the disk image itself (.img or .img.xz): the guest writes to
        # it (first boot, updates, reboot), so it is a private copy.
        if a.iso.endswith(".xz"):
            with open(disk, "wb") as f:
                subprocess.run(["xz", "-dc", a.iso], stdout=f, check=True)
        else:
            shutil.copyfile(a.iso, disk)
    else:
        with open(disk, "wb") as f:
            f.truncate(20 * 1024 ** 3)  # sparse
    accel = "kvm" if os.access("/dev/kvm", os.W_OK) else "tcg"
    if arm and os.uname().machine not in ("aarch64", "arm64"):
        accel = "tcg"  # KVM only runs guests of the host's own architecture

    def launch(with_iso=True):
        if arm:
            cmd = ["qemu-system-aarch64", "-accel", accel,
                   "-M", "virt,gic-version=host" if accel == "kvm" else "virt",
                   "-cpu", "host" if accel == "kvm" else "max", "-smp", "4", "-m", a.memory,
                   "-bios", first_existing(AAVMF_CODE, "aarch64 firmware"),
                   "-drive", f"if=none,id=hd,format=raw,cache=unsafe,file={disk}",
                   "-device", "virtio-blk-pci,drive=hd", "-device", "virtio-gpu-pci",
                   "-device", "qemu-xhci", "-device", "usb-kbd", "-device", "usb-tablet",
                   "-display", "none", "-serial", f"file:{os.path.join(seq, 'serial.log')}",
                   "-qmp", f"unix:{sock},server=on,wait=off"]
            if os.path.exists(sock):
                os.remove(sock)
            return subprocess.Popen(cmd)
        cmd = [
            "qemu-system-x86_64", "-machine", f"q35,accel={accel}", "-m", a.memory,
            "-smp", "2", "-display", "none", "-vga", "std",
            "-device", "qemu-xhci", "-device", "usb-tablet",
            "-drive", f"if=pflash,format=raw,readonly=on,file={first_existing(OVMF_CODE, 'code')}",
            "-drive", f"if=pflash,format=raw,file={vars_copy}",
            # Blank target disk, otherwise Calamares stops at "no partitions to install on".
            "-drive", f"if=virtio,format=raw,cache=unsafe,file={disk}",
            "-qmp", f"unix:{sock},server=on,wait=off",
        ]
        if with_iso:
            cmd += ["-cdrom", a.iso, "-boot", "d"]
        if os.path.exists(sock):
            os.remove(sock)
        return subprocess.Popen(cmd)

    qemu = launch()
    print(f"QEMU started (accel={accel})")

    qmp = QMP(sock)
    cx, cy = (int(v) for v in a.click.split(","))
    hashes, notes, frames = [], {}, {}
    n, bright, desktop_at, click_at, continue_at, size = 0, 0.0, None, None, None, (1280, 800)
    install = {"ran": False, "finished": False, "booted": False}
    usability = {"ran": False, "checks": {}}
    calamares_open = False

    def peek():
        """Screen contents without saving a frame."""
        ppm = os.path.join(tmp, "p.ppm")
        qmp.cmd("screendump", filename=ppm)
        return read_ppm(ppm)[2]

    def shot():
        nonlocal n, bright, size
        n += 1
        ppm = os.path.join(tmp, "s.ppm")
        qmp.cmd("screendump", filename=ppm)
        w, h, rgb = read_ppm(ppm)
        size = (w, h)
        write_png(os.path.join(seq, f"{n}.png"), w, h, rgb)
        hashes.append(hashlib.md5(rgb).hexdigest())
        frames[n] = rgb
        bright = sum(rgb[::97]) / len(rgb[::97])
        print(f"[{(n - 1) * a.interval + a.interval:>4}s] seq/{n}.png {w}x{h} brightness={bright:.1f}")

    def run_usability():
        """Installed system: first-boot assistant, login, desktop, Konsole, pacman, apps."""
        u = usability
        u["ran"] = True
        w, h = size

        def check(name, ok, detail=""):
            u["checks"][name] = {"ok": bool(ok), "detail": detail}
            print(f"  usability: {name}: {'ok' if ok else 'FAIL'} {detail}")

        def settle(limit=18):
            """Emulated CPUs take many seconds per page transition: wait until the picture
            stops changing (never longer than limit x 10 s) before looking at it or clicking."""
            prev = peek()
            for _ in range(limit):
                time.sleep(10)
                cur = peek()
                if changed_fraction(prev, cur) < 0.005:
                    return
                prev = cur

        def frame(msg, wait=0):
            time.sleep(wait * a.slow)
            if P.get("image"):
                settle()
            shot()
            notes[n] = msg

        def page(msg, wait, *actions):
            frame(msg, wait)
            for a_ in actions:
                a_()

        c = lambda x, y: click(qmp, x, y, w, h)
        t = lambda text: type_text(qmp, text, enter=False)

        # First-boot assistant of the installed system, driven by the distro profile.
        def run_steps(steps):
            for st in steps:
                kind = st[0]
                if kind == "click":
                    if P.get("image"):
                        settle()
                    c(st[1], st[2])
                    if P.get("image"):
                        time.sleep(3 * a.slow)
                elif kind == "type":
                    t(TEST_USER[st[1]])
                elif kind == "frame":
                    frame(st[1], st[2])
                elif kind == "page":
                    frame(st[1], st[2])
                    run_steps(st[3])

        run_steps(P["first_boot"])
        if P.get("image"):
            # The assistant's last screen ("welcome") runs post_setup for a long time (apt, theme,
            # cleanup) and only then returns to the login screen. Its log line sits at the bottom of
            # the screen; wait until that text is gone and the picture is steady.
            stable = 0
            for _ in range(int(90 * a.slow)):
                time.sleep(10)
                key_combo(qmp, "shift")
                shot()
                notes[n] = "Setup assistant: applying settings"
                txt = ocr(frames[n], w, (0, 730, w, h))
                busy = txt is not None and sum(ch.isalpha() for ch in txt) > 12
                stable = stable + 1 if (not busy and bright > 20 and hashes[-1] == hashes[-2]) else 0
                if stable >= 2:
                    break
        # Login screen: type the password with the keyboard only (clicking the
        # avatar submits an empty password).
        stable = 0
        for _ in range(int(12 * a.slow)):
            time.sleep(10)
            key_combo(qmp, "shift")  # keep the display awake (slow emulated boots idle for minutes)
            shot()
            notes[n] = "Login screen"
            stable = stable + 1 if (bright > 20 and hashes[-1] == hashes[-2]) else 0
            if stable >= 2:
                break
        type_text(qmp, TEST_USER["password"], enter=True)
        stable, desktop = 0, False
        # An image's first login starts Plasma from scratch on an emulated CPU (wallpaper and
        # widgets show up minutes before the menu bar and dock): wait for the menu bar itself.
        for _ in range(int((40 if P.get("image") else 12) * a.slow)):
            time.sleep(10)
            key_combo(qmp, "shift")
            shot()
            notes[n] = "Logging in"
            stable = stable + 1 if (bright > 20 and hashes[-1] == hashes[-2] and
                                    changed_fraction(frames[n], frames[n - 3] if n > 3 else frames[n]) < 0.05) else 0
            if stable >= 2:
                if P.get("image") and not dock_visible(frames[n], w, h):
                    stable = 0
                    continue
                desktop = True
                break
        if desktop and P.get("image"):
            # A steady picture is not enough on an image: the assistant itself is steady too.
            # The real desktop has the dock.
            if not dock_visible(frames[n], w, h):
                desktop = False
                print("  desktop check: no dock on screen, not the desktop")
        notes[n] = "Installed system: desktop"
        check("login + desktop", desktop)

        # Menu bar + dock of the installed desktop vs. the reference.
        # The installed desktop has its own reference: after the first-boot
        # assistant it is Light mode (light wallpaper), unlike the dark live desktop.
        ref_path = os.path.join(REFDIR, "installed.png")
        if a.update_reference and desktop:
            os.makedirs(REFDIR, exist_ok=True)
            write_png(ref_path, w, h, frames[n])
            print(f"reference saved: {ref_path}")
        if not os.path.exists(ref_path):
            ref_path = os.path.join(REFDIR, "desktop.png")
        if desktop and os.path.exists(ref_path):
            rw, rh, ref = read_png(ref_path)
            if (rw, rh) == (w, h):
                top = strip_similarity(frames[n], ref, w, 0, 30)
                dock = strip_similarity(frames[n], ref, w, h - 100, h)
                u["ui_installed"] = {"top": top, "dock": dock}
                check("UI sanity (installed)", top >= a.ui_threshold and dock >= a.ui_threshold,
                      f"top {top:.0f}% / dock {dock:.0f}%")
        if not desktop:
            return

        # Konsole + the OS identity (fastfetch on Arch, /etc/os-release on Debian).
        before = peek()
        key_combo(qmp, "ctrl+alt+t")
        frame("Konsole opened", 6)
        id_cmd, id_label = P["identity"]
        type_text(qmp, id_cmd, enter=True)
        frame(f"Konsole: {id_cmd}", 5)
        rgb = peek()
        text = ocr(rgb, w, KONSOLE_BOX)
        opened = changed_fraction(crop_rgb(before, w, 0, 40, w, 690), crop_rgb(rgb, w, 0, 40, w, 690)) > 0.05
        check("Konsole opens", opened)
        if text is None:
            check(id_label, False, "(tesseract not installed)")
        else:
            check(id_label, "pearos" in text.lower().replace("0", "o"))

        # The system update (sudo pacman -Syyu --noconfirm / apt-get dist-upgrade)
        U = P["update"]
        type_text(qmp, "clear", enter=True)
        type_text(qmp, f"{U['cmd']} && echo {U['marker']}-OK || echo {U['marker']}-FAILED", enter=True)
        time.sleep(4 * a.slow)
        type_text(qmp, TEST_USER["password"], enter=True)
        t0, result, last = time.time(), None, time.time()
        while time.time() - t0 < a.pacman_timeout:
            time.sleep(15)
            key_combo(qmp, "shift")  # keep the screen from blanking while pacman runs
            rgb = peek()
            txt = ocr(rgb, w, KONSOLE_BOX) or ""
            m = re.search(r"^\s*" + U["marker"] + r"\s*[-\u2013\u2014]\s*(OK|FAILED)\s*$", txt, re.M)
            if m:
                result = m.group(1)
                break
            if time.time() - last > 120:
                last = time.time()
                shot()
                notes[n] = f"Konsole: {U['cmd']} (running)"
        shot()
        detail = {"OK": "", "FAILED": U["error"], None: "timed out"}[result]
        if result == "FAILED":
            m = re.findall(r"^(?:error|::)\s.*$", ocr(peek(), w, KONSOLE_BOX) or "", re.M)
            if m:
                detail = m[-1][:90]
        notes[n] = f"Konsole: {U['label']} {'succeeded' if result == 'OK' else 'FAILED'}"
        check(U["check"], result == "OK", detail)

        # Basic apps: launch, see that a window appears, close it.
        for app in P["apps"]:
            label, desktop_id, words = app[:3]
            launch_cmd = app[3] if len(app) > 3 else None
            type_text(qmp, "clear", enter=True)
            time.sleep(1)
            before = peek()
            # gtk-launch is not installed on Debian; gio launch is the fallback.
            if launch_cmd:
                type_text(qmp, f"{launch_cmd} >/dev/null 2>&1 &", enter=True)
            else:
                type_text(qmp, f"gtk-launch {desktop_id} 2>/dev/null || gio launch /usr/share/applications/{desktop_id}.desktop",
                          enter=True)
            # First start can be slow (Nautilus on Debian took ~15 s): poll for up to ~28 s.
            opened, changed, seen = False, False, ""
            for _ in range(int(7 * a.slow)):
                time.sleep(4)
                rgb = peek()
                changed = changed_fraction(crop_rgb(before, w, 0, 40, w, 690), crop_rgb(rgb, w, 0, 40, w, 690)) > 0.05
                # A window that really opened takes focus: the menu bar then shows its name.
                title = ocr(rgb, w, (40, 0, 640, 32), both=True)
                if title is None:
                    titled, seen = True, ""
                else:
                    seen = " ".join(title.split())[:40]
                    low = title.lower().replace("0", "o")
                    # unreadable menu bar (< 3 letters) proves nothing: only a readable,
                    # different name counts as "another app has focus"
                    titled = any(wd in low for wd in words) or sum(ch.isalpha() for ch in low) < 3
                if changed and titled:
                    opened = True
                    break
            time.sleep(2)
            shot()
            notes[n] = f"App: {label} {'opened' if opened else 'did NOT open'}"
            check(f"{label} opens", opened,
                  "" if opened else (f"menu bar says '{seen}'" if changed else "the screen did not change"))
            if opened:
                key_combo(qmp, "alt+f4")  # close the app (never Konsole, if the app did not open)
            time.sleep(3)

        if a.upgrade_reboot or a.canary:
            # Reboot after the update. No login screen here is the failure
            # users reported after `pacman -Syu` (black screen).
            key_combo(qmp, "ctrl+alt+t")  # make sure a terminal has focus, whatever happened before
            time.sleep(5 * a.slow)
            type_text(qmp, "sudo systemctl reboot", enter=True)
            time.sleep(2)
            type_text(qmp, TEST_USER["password"], enter=True)  # in case sudo asks again
            # With KVM the whole reboot can take under 20 s, so the dark frames in
            # between are easy to miss. The login screen is: bright, unchanged
            # for two frames, and clearly different from the desktop we left.
            base = frames[n]
            t0, stable, login_seen = time.time(), 0, False
            while time.time() - t0 < a.reboot_wait:
                time.sleep(5)
                shot()
                notes[n] = "After the update: rebooting"
                if (bright > 20 and hashes[-1] == hashes[-2]
                        and changed_fraction(frames[n], base) > 0.15):
                    stable += 1
                    if stable >= 2:
                        login_seen = True
                        break
                else:
                    stable = 0
            notes[n] = "After the update: login screen" if login_seen else "After the update: NO login screen"
            check("after update: login screen", login_seen,
                  "" if login_seen else f"no login screen {a.reboot_wait}s after the reboot (black screen?)")
            if login_seen:
                type_text(qmp, TEST_USER["password"], enter=True)
                stable, desk = 0, False
                for _ in range(int((40 if P.get("image") else 12) * a.slow)):
                    time.sleep(10)
                    key_combo(qmp, "shift")
                    shot()
                    notes[n] = "After the update: logging in"
                    stable = stable + 1 if (bright > 20 and hashes[-1] == hashes[-2] and
                                            changed_fraction(frames[n], frames[n - 3]) < 0.05) else 0
                    if stable >= 2:
                        if P.get("image") and not dock_visible(frames[n], w, h):
                            stable = 0
                            continue
                        desk = True
                        break
                notes[n] = "After the update: desktop" if desk else "After the update: NO desktop"
                check("after update: desktop", desk)
                if desk:
                    rp = os.path.join(REFDIR, "installed.png")
                    if os.path.exists(rp):
                        rw, rh, ref = read_png(rp)
                        if (rw, rh) == (w, h):
                            top = strip_similarity(frames[n], ref, w, 0, 30)
                            dock = strip_similarity(frames[n], ref, w, h - 100, h)
                            check("UI sanity (after update)", top >= a.ui_threshold and dock >= a.ui_threshold,
                                  f"top {top:.0f}% / dock {dock:.0f}%")

    t_start = time.time()
    try:
        # Phase 1: boot until the desktop is up. "Up" = bright and identical
        # to the previous frame (Plymouth and the login transition are dark or
        # still animating).
        for _ in range(a.duration // a.interval):
            time.sleep(a.interval)
            if qemu.poll() is not None:
                print("QEMU exited early")
                break
            shot()
            if n >= 2 and bright > 20 and hashes[-1] == hashes[-2]:
                desktop_at = n
                notes[n] = "desktop ready"
                break

        if P.get("image"):
            # The image boots into the first-boot assistant: reaching it is the "install".
            install["ran"] = True
            install["finished"] = bool(desktop_at)
            install["booted"] = bool(desktop_at)
            install["minutes"] = round((time.time() - t_start) / 60, 1)
            if desktop_at:
                # The plasma desktop shows up first; the assistant then stops plasmashell and
                # covers the screen (slow on emulated CPUs). Wait until the menu bar is gone and
                # the picture is steady again before driving the assistant.
                base = frames[n]
                stable = 0
                for _ in range(int(60 * a.slow)):
                    time.sleep(10)
                    key_combo(qmp, "shift")
                    shot()
                    notes[n] = "Waiting for the setup assistant"
                    gone = strip_similarity(frames[n], base, size[0], 0, 30) < 60
                    stable = stable + 1 if (gone and bright > 5 and hashes[-1] == hashes[-2]) else 0
                    if stable >= 2:
                        break
                notes[n] = "First boot: setup assistant ready"
                run_usability()
            calamares_open = bool(desktop_at)
        # Phase 2: Welcome app -> pearOS installer -> Calamares. One action per
        # tick, performed right after that tick's screenshot (so each frame
        # shows the screen *before* its click). Tick 1 just lets the installer
        # load.
        steps = P["installer_ticks"]
        if desktop_at and not P.get("image"):
            click(qmp, cx, cy, *size)
            click_at = n
            notes[n] = "desktop ready, then clicked **Install pearOS** in Welcome"
            for tick in range(a.install_wait // a.interval):
                time.sleep(a.interval)
                if qemu.poll() is not None:
                    print("QEMU exited early")
                    break
                shot()
                if tick < len(steps):
                    screen, action, pos = steps[tick]
                    if pos:
                        click(qmp, *pos, *size)
                    notes[n] = f"{screen}, then {action}" if action else screen
                    if action and "Continue" in action:
                        continue_at = n
            if n > click_at:
                notes[n] = "Calamares"
        if not P.get("image"):
            calamares_open = bool(
                continue_at is not None and n > continue_at and bright > 2
                and changed_fraction(frames[n], frames[continue_at]) > P["calamares_change"])

        # Phase 3 (--full-install): click through Calamares, wait for it to
        # finish, then boot the installed disk on its own.
        if a.full_install and calamares_open and not P.get("image"):
            install["ran"] = True
            for what, pos in P["calamares_steps"]:
                time.sleep(P["calamares_delay"])
                shot()
                click(qmp, *pos, *size)
                notes[n] = f"Calamares: {what}"
            t0 = time.time()
            last_saved = t0
            while time.time() - t0 < a.install_timeout:
                time.sleep(30)
                key_combo(qmp, "shift")  # the live session would blank the screen while we wait
                if qemu.poll() is not None:
                    install["error"] = "QEMU exited during the installation"
                    break
                rgb = peek()
                fin = P["finish"]
                if fin[0] == "tab":
                    done = pixel(rgb, size[0], *fin[1])[2] > 200 and pixel(rgb, size[0], *fin[1])[0] < 80
                else:
                    txt = ocr(rgb, size[0], fin[1]) or ""
                    done = fin[2] in txt.lower()
                if done:
                    shot()
                    notes[n] = "Calamares: installation finished"
                    install["finished"] = True
                    break
                if time.time() - last_saved >= a.install_frame_every:
                    last_saved = time.time()
                    shot()
                    notes[n] = f"Calamares: installing ({int((time.time() - t0) / 60)} min)"
            install["minutes"] = round((time.time() - t0) / 60, 1)
            if install["finished"]:
                time.sleep(5)
                qmp.cmd("quit")
                qemu.wait(timeout=60)
                qemu = launch(with_iso=False)
                qmp = QMP(sock)
                stable = 0
                for _ in range(a.reboot_wait // a.interval):
                    time.sleep(a.interval)
                    if qemu.poll() is not None:
                        break
                    shot()
                    notes[n] = "Installed system: first boot"
                    if bright > 20 and hashes[-1] == hashes[-2]:
                        stable += 1
                        if stable >= 2:
                            notes[n] = "Installed system: reached the login screen / desktop"
                            install["booted"] = True
                            break
                    else:
                        stable = 0
                if install["booted"]:
                    run_usability()
    finally:
        qemu.kill()
        shutil.rmtree(tmp, ignore_errors=True)

    booted = desktop_at is not None and len(set(hashes[:desktop_at])) >= 3
    # Calamares is dark-themed, so judge it by how much the screen changed
    # since the click, not by brightness.
    # The last installer-flow frame is the one taken at the Continue click; if
    # Calamares really opened, the final frame is a different screen.
    installer = calamares_open
    full_ok = (not a.full_install) or bool(install["finished"] and install["booted"])
    if installer and a.full_install and full_ok:
        verdict = "booted, installed pearOS and booted it ✅"
    elif installer and a.full_install:
        verdict = "booted, installer opened, installation FAILED ❌"
    elif installer:
        verdict = "booted, installer opened ✅"
    elif booted:
        verdict = "booted, installer did NOT open ❌"
    else:
        verdict = "boot FAILED ❌"
    print(verdict)

    ui = None
    ref_path = os.path.join(REFDIR, "desktop.png")
    if desktop_at and not P.get("image"):
        cur = frames[desktop_at]
        w, h = size
        if a.update_reference:
            os.makedirs(os.path.dirname(ref_path), exist_ok=True)
            write_png(ref_path, w, h, cur)
            print(f"reference saved: {ref_path}")
        if os.path.exists(ref_path):
            rw, rh, ref = read_png(ref_path)
            if (rw, rh) == (w, h):
                top = strip_similarity(cur, ref, w, 0, 30)
                dock = strip_similarity(cur, ref, w, h - 100, h)
                ok = top >= a.ui_threshold and dock >= a.ui_threshold
                ui = {"top": top, "dock": dock, "tol": 16, "threshold": a.ui_threshold,
                      "frame": desktop_at, "ok": ok,
                      "verdict": "menu bar + dock look as expected ✅" if ok
                                 else "menu bar or dock DIFFER from the reference ❌"}
                print(f"UI Sanity: top bar {top:.1f}%, dock {dock:.1f}% -> {ui['verdict']}")
            else:
                print(f"UI Sanity: reference is {rw}x{rh}, screen is {w}x{h} -- skipped")
        else:
            print("UI Sanity: no reference yet (run with --update-reference)")
    # UI sanity gates publishing on BOTH desktops: the live one and, in a full
    # install, the installed one. A full install that reached a booted system
    # but could not be measured (no login/desktop, no matching reference) fails too.
    live_ui_ok = ui is None or ui["ok"]
    inst_ui_ok = True
    if a.full_install and install["booted"]:
        chk = usability["checks"].get("UI sanity (installed)")
        inst_ui_ok = bool(chk and chk["ok"])
    passed = bool(installer and full_ok and live_ui_ok and inst_ui_ok)
    canary_fail = []
    if a.canary:
        # Old ISO -> update from the live repo -> reboot. The look of an old ISO
        # differs from the references, so UI sanity does not gate here.
        need = ("login + desktop", P["update"]["check"],
                "after update: login screen", "after update: desktop")
        canary_fail = [k for k in need if not usability["checks"].get(k, {}).get("ok")]
        passed = bool(installer and full_ok and not canary_fail)
    failure = None
    if not passed:
        verdict = "FAIL TEST ❌"
        stage, reason = classify_failure(hashes, frames, n, desktop_at, installer, ui, size)
        if installer and not full_ok and (ui is None or ui["ok"]):
            stage = "install"
            if install.get("error"):
                reason = install["error"] + "."
            elif not install["finished"]:
                reason = (f"Calamares did not reach the Finish page within {a.install_timeout // 60} min "
                          f"(waited {install['minutes']} min); see the last frames.")
            else:
                reason = ("pearOS installed, but the installed system never reached a login screen/desktop "
                          f"within {a.reboot_wait // 60} min.")
        if a.canary and installer and full_ok and canary_fail:
            stage = "upgrade"
            why = "; ".join(f"{k}: {usability['checks'].get(k, {}).get('detail') or 'failed / not reached'}"
                            for k in canary_fail)
            reason = f"Upgrade canary failed after updating an old install from the repo ({why})."
        elif installer and full_ok and live_ui_ok and not inst_ui_ok:
            stage = "ui"
            m = usability.get("ui_installed")
            if m:
                reason = (f"The installed desktop looks different from the reference: menu bar {m['top']:.1f}%, "
                          f"dock {m['dock']:.1f}% (each must be at least {a.ui_threshold:.0f}%).")
            else:
                reason = ("The installed desktop could not be checked (no login/desktop reached or no matching "
                          "reference), so the UI sanity test cannot pass.")
        evidence = []
        if stage in ("bootloader", "black-screen", "splash"):
            print("Failure before the desktop: booting the kernel directly with a serial console to find out why...")
            log, facts, err = diagnose_guest(a.iso, a.memory, accel, a.diagnose_seconds)
            if err:
                evidence = [err]
            elif log is not None:
                with open(os.path.join(seq, "serial.log"), "w") as f:
                    f.write(log + "\n" + "\n".join(str(v) for v in facts.values()))
                cause, evidence = explain_guest(facts)
                if cause:
                    reason = f"{reason}  **Cause:** {cause}."
                elif "login:" not in log:
                    evidence = [l for l in log.splitlines() if l.strip()][-8:]
                    reason += "  The kernel never reached a login prompt on the serial console."
                else:
                    reason += "  The system booted fine over the serial console, so this looks like a graphics/display problem."
        failure = {"stage": stage, "reason": reason, "evidence": evidence}
        print(f"FAIL TEST at stage '{stage}': {reason}")
        for line in evidence:
            print("   |", line)
    # Success score: boot, UI sanity, installable and usability, 25 points each
    # (components that were not run are left out and the total is their mean).
    score = {"boot": 100 if booted else 0,
             "ui": None, "install": None, "usability": None, "checks": usability["checks"]}
    ui_parts = [100 if ui["ok"] else 0] if ui else []
    ui_inst = usability.get("ui_installed")
    if ui_inst:
        ui_parts.append(100 if min(ui_inst["top"], ui_inst["dock"]) >= a.ui_threshold else 0)
    if ui_parts:
        score["ui"] = round(sum(ui_parts) / len(ui_parts))
    if a.full_install:
        score["install"] = (60 if install["finished"] else 0) + (40 if install["booted"] else 0)
    else:
        score["install"] = 100 if installer else 0
    if usability["checks"]:
        ok_n = sum(1 for v in usability["checks"].values() if v["ok"])
        score["usability"] = round(100 * ok_n / len(usability["checks"]))
    parts = [score[k] for k in ("boot", "ui", "install", "usability") if score[k] is not None]
    score["total"] = round(sum(parts) / len(parts)) if parts else 0
    print("Success score:", score["total"], {k: score[k] for k in ("boot", "ui", "install", "usability")})
    with open(os.path.join(seq, "result.json"), "w") as f:
        json.dump({"passed": passed, "verdict": verdict, "iso": os.path.basename(a.iso),
                   "failure": failure, "ui": ui, "frames": n,
                   "booted": bool(booted), "installer": bool(installer),
                   "install": install if a.full_install else None, "score": score,
                   "interval": a.interval, "desktop_frame": desktop_at,
                   "notes": {str(k): v.replace("**", "") for k, v in notes.items()},
                   "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                  f, indent=2, ensure_ascii=False)
    if n:
        update_readme(n, a.interval, verdict, notes, ui, failure, score, out_dir=OUT,
                      ref_rel="tests/ui-reference/" + (P["ref_dir"] + "/" if P["ref_dir"] else ""))
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
