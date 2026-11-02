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


UI_BEGIN, UI_END = "<!-- ui-sanity:begin -->", "<!-- ui-sanity:end -->"


def replace_block(text, begin, end, body, heading):
    block = "\n".join([begin, "", body, "", end])
    if begin in text and end in text:
        return re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _: block, text, flags=re.S)
    return text.replace("\n## Star History", f"\n## {heading} 📌\n{block}\n\n## Star History", 1)


def update_readme(frames, interval, verdict, notes, ui, failure=None):
    lines = [f"Result: **{verdict}**  "]
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
    path = os.path.join(ROOT, "README.md")
    text = open(path).read()
    text = replace_block(text, BEGIN, END, "\n".join(lines), "Boot Status sequence")
    if ui:
        u = ["Result: **%s**  " % ui["verdict"],
             f"Compared against the reference [`tests/ui-reference/desktop.png`](tests/ui-reference/desktop.png) "
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
    ap.add_argument("--install-wait", type=int, default=110,
                    help="seconds to keep capturing after clicking Install pearOS")
    ap.add_argument("--update-reference", action="store_true",
                    help="save the desktop-ready frame as the UI sanity reference")
    ap.add_argument("--ui-threshold", type=float, default=90.0)
    ap.add_argument("--diagnose-seconds", type=int, default=150,
                    help="how long to wait for graphical.target when diagnosing a failure")
    ap.add_argument("--click", default="575,181",
                    help="x,y of the Install pearOS button in the Welcome app")
    a = ap.parse_args()

    seq = os.path.join(ROOT, "seq")
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)

    tmp = tempfile.mkdtemp()
    vars_copy = os.path.join(tmp, "vars.fd")
    shutil.copy(first_existing(OVMF_VARS, "vars"), vars_copy)
    sock = os.path.join(tmp, "qmp.sock")
    disk = os.path.join(tmp, "disk.img")
    with open(disk, "wb") as f:
        f.truncate(20 * 1024 ** 3)  # sparse
    accel = "kvm" if os.access("/dev/kvm", os.W_OK) else "tcg"
    qemu = subprocess.Popen([
        "qemu-system-x86_64", "-machine", f"q35,accel={accel}", "-m", a.memory,
        "-smp", "2", "-display", "none", "-vga", "std",
        "-device", "qemu-xhci", "-device", "usb-tablet",
        "-drive", f"if=pflash,format=raw,readonly=on,file={first_existing(OVMF_CODE, 'code')}",
        "-drive", f"if=pflash,format=raw,file={vars_copy}",
        # Blank target disk, otherwise Calamares stops at "no partitions to install on".
        "-drive", f"if=virtio,format=raw,file={disk}",
        "-cdrom", a.iso, "-boot", "d", "-qmp", f"unix:{sock},server=on,wait=off",
    ])
    print(f"QEMU started (accel={accel})")

    qmp = QMP(sock)
    cx, cy = (int(v) for v in a.click.split(","))
    hashes, notes, frames = [], {}, {}
    n, bright, desktop_at, click_at, continue_at, size = 0, 0.0, None, None, None, (1280, 800)

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

        # Phase 2: Welcome app -> pearOS installer -> Calamares. One action per
        # tick, performed right after that tick's screenshot (so each frame
        # shows the screen *before* its click). Tick 1 just lets the installer
        # load.
        steps = [  # (what the frame shows, click performed after it)
            ("pearOS installer loading", None, None),
            ("Language screen", "selected English", (657, 385)),
            ("Language screen", "clicked Next", (1022, 704)),
            ("Recovery screen", "selected **Install pearOS NiceC0re** (offline installer)", (655, 353)),
            ("Recovery screen", "clicked **Continue**", (858, 655)),
        ]
        if desktop_at:
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
    finally:
        qemu.kill()
        shutil.rmtree(tmp, ignore_errors=True)

    booted = desktop_at is not None and len(set(hashes[:desktop_at])) >= 3
    # Calamares is dark-themed, so judge it by how much the screen changed
    # since the click, not by brightness.
    # The last installer-flow frame is the one taken at the Continue click; if
    # Calamares really opened, the final frame is a different screen.
    installer = (continue_at is not None and n > continue_at and bright > 2
                 and changed_fraction(frames[n], frames[continue_at]) > 0.4)
    if installer:
        verdict = "booted, installer opened ✅"
    elif booted:
        verdict = "booted, installer did NOT open ❌"
    else:
        verdict = "boot FAILED ❌"
    print(verdict)

    ui = None
    ref_path = os.path.join(ROOT, "tests", "ui-reference", "desktop.png")
    if desktop_at:
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
    passed = bool(installer and (ui is None or ui["ok"]))
    failure = None
    if not passed:
        verdict = "FAIL TEST ❌"
        stage, reason = classify_failure(hashes, frames, n, desktop_at, installer, ui, size)
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
    with open(os.path.join(seq, "result.json"), "w") as f:
        json.dump({"passed": passed, "verdict": verdict, "iso": os.path.basename(a.iso),
                   "failure": failure, "ui": ui, "frames": n,
                   "booted": bool(booted), "installer": bool(installer),
                   "interval": a.interval, "desktop_frame": desktop_at,
                   "notes": {str(k): v.replace("**", "") for k, v in notes.items()},
                   "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                  f, indent=2, ensure_ascii=False)
    if n:
        update_readme(n, a.interval, verdict, notes, ui, failure)
    sys.exit(0 if passed else 1)

main()
