#!/usr/bin/env python3
"""pearOS ISO Builder -- a Cubic-inspired GUI wrapper around ./build-binary.

Structured the way Cubic itself is: a HeaderBar with Back/Next, one
concern per page (GtkStack, SLIDE transition), a big instructional label
at the top of each page, and -- for compression -- the same diagonal
triangle-of-radio-buttons widget Cubic uses (see compression_triangle.py).

The Terminal page is a real Vte.Terminal, exactly like Cubic's own
terminal_page during Generate: build-binary now has a full CLI
(--build/--profile/--compression/--clean/--chroot/--sha256/--usb/--upload/
--list-cdn/--get-links/--delete-cdn, all chainable), so this GUI just
builds the command line from the wizard's pages and streams it into Vte.
Anything build-binary still asks live (sudo's password, the arch-chroot
shell if --chroot is used, a USB/CDN-delete confirmation) is answered by
the user directly in that real terminal.
"""

from __future__ import annotations

import glob
import os
import shlex
import shutil
import socket
import subprocess
from datetime import date
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Vte", "2.91")
gi.require_version("GtkVnc", "2.0")

from gi.repository import Gdk, GLib, Gtk, GtkVnc, Vte  # noqa: E402

try:
    gi.require_version("GtkSource", "3.0")
    from gi.repository import GtkSource  # noqa: E402
    HAS_GTKSOURCE = True
except (ValueError, ImportError):
    GtkSource = None
    HAS_GTKSOURCE = False

from compression_triangle import CompressionTriangle
from packages_editor import parse_packages, render_packages
from pacman_conf_editor import COMMON_SIGLEVELS, extract_global_siglevel, new_repo, parse_repos, render_repos
from qemu_test import MIN_CPUS, MIN_DISK_GIB, MIN_RAM_MIB, QemuTestSession, find_ovmf
from profiledef_editor import parse_profiledef, render_profiledef

_INSTALLED_DEV_ROOT = "/usr/share/pearOS/dev"
_USER_DEV_ROOT = os.path.join(GLib.get_user_data_dir(), "pearOS", "dev")
_DEV_VERSION_MARKER = ".pearos-dev-version"

# Set by _ensure_writable_repo_root(): None when running from a dev
# checkout (no sync involved), else "synced" or "resynced" -- used to show
# a small status indicator in the header.
SYNC_STATUS = None


def _dev_tree_version(root):
    try:
        with open(os.path.join(root, _DEV_VERSION_MARKER), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def _sync_dev_tree(system_root, user_root):
    """Overwrite only the entries that exist in system_root. build-binary
    writes work/, out/ (ISOs) and sha.txt into user_root's cwd -- none of
    those exist in the packaged source tree, so they're never touched
    here and survive a re-sync.
    """
    os.makedirs(user_root, exist_ok=True)
    for name in os.listdir(system_root):
        src = os.path.join(system_root, name)
        dst = os.path.join(user_root, name)
        if os.path.isdir(dst) and not os.path.islink(dst):
            shutil.rmtree(dst)
        elif os.path.lexists(dst):
            os.remove(dst)
        if os.path.isdir(src) and not os.path.islink(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst, follow_symlinks=False)


def _ensure_writable_repo_root(raw_root):
    """The pearos-builder Arch package installs the dev tree read-only,
    root:root, at /usr/share/pearOS/dev. This GUI's editors (packages,
    pacman.conf, profiledef, airootfs) write straight into REPO_ROOT with
    no sudo -- only build-binary itself runs elevated -- so when launched
    from the installed copy those saves would fail. Mirror it into a
    user-writable copy and work out of that instead. A repo checkout used
    for development (raw_root elsewhere) is left untouched.

    Re-synced whenever the installed .pearos-dev-version marker doesn't
    match the user copy's (fresh install or package upgrade) -- this
    overwrites source files (packages/, pear/, iso-builder/, build-binary,
    ...) with the installed version, so edits made only in the user copy
    to those are lost. Build output (work/, out/, sha.txt) isn't part of
    the packaged tree and is left alone. If the markers already match,
    nothing is touched.
    """
    global SYNC_STATUS
    if raw_root != _INSTALLED_DEV_ROOT:
        return raw_root
    if _dev_tree_version(_USER_DEV_ROOT) != _dev_tree_version(_INSTALLED_DEV_ROOT):
        _sync_dev_tree(_INSTALLED_DEV_ROOT, _USER_DEV_ROOT)
        SYNC_STATUS = "resynced"
    else:
        SYNC_STATUS = "synced"
    return _USER_DEV_ROOT


REPO_ROOT = _ensure_writable_repo_root(str(Path(__file__).resolve().parent.parent))
BUILD_BINARY = os.path.join(REPO_ROOT, "build-binary")

# packages/packages.x86_64 is the real source of truth: build-binary copies
# it over pear/airootfs/etc/packages.x86_64 (and pear/packages.x86_64) at
# the start of every fresh (non-continue) build, so editing the airootfs
# copy directly would just get overwritten on the next build.
PACKAGES_FILE = os.path.join(REPO_ROOT, "packages", "packages.x86_64")
# packages/pacman.out is the real source: _generate_pear_pacman_conf() copies
# it over pear/pacman.conf (then merges in host-detected repos) at the start
# of every fresh build, so pear/pacman.conf is a disposable build artifact --
# editing it directly gets overwritten on the next fresh build.
PACMAN_CONF_FILE = os.path.join(REPO_ROOT, "packages", "pacman.out")

# Ordered fastest/biggest -> slowest/smallest, same diagonal order as
# Cubic's lz4 -> lzo -> gzip -> zstd -> xz.
COMPRESSION_OPTIONS = [
    ("fastest", "lz4", "Fastest -- minimal compression, largest file"),
    ("big", "zstd-3", "Fast, bigger file (zstd level 3)"),
    ("default", "xz", "Balanced -- default"),
    ("max", "xz-9", "Small file, slower (xz level 9)"),
    ("slim", "zstd-19", "Slowest -- smallest file (Pear Slim, zstd level 19)"),
]

# rclone doesn't need root (unlike build-binary), so these run directly as
# the GUI's own user -- no sudo, no --list-cdn/--get-links/--delete-cdn
# indirection through build-binary.
UPLOAD_SCRIPT = os.path.join(REPO_ROOT, "ISO Uploader", "upload")


def fetch_cdn_files():
    """Returns (files, error). files: [{"name","size_bytes","date","url"}]."""
    try:
        list_result = subprocess.run(
            [UPLOAD_SCRIPT, "--list-raw"], capture_output=True, text=True, timeout=30
        )
        links_result = subprocess.run(
            [UPLOAD_SCRIPT, "--get-links"], capture_output=True, text=True, timeout=30
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return None, str(exc)
    if list_result.returncode != 0:
        return None, (list_result.stderr or list_result.stdout).strip() or "rclone list failed"

    links_by_name = {}
    for line in links_result.stdout.splitlines():
        url = line.strip()
        if url:
            links_by_name[os.path.basename(url)] = url

    files = []
    for line in list_result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        size_bytes, date, _time, name = parts
        try:
            size_bytes = int(size_bytes)
        except ValueError:
            size_bytes = 0
        files.append({"name": name, "size_bytes": size_bytes, "date": date, "url": links_by_name.get(name, "")})
    return files, None


def delete_cdn_file(filename):
    try:
        result = subprocess.run(
            [UPLOAD_SCRIPT, "--delete", filename, "--yes"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, str(exc)
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output

PAGE_START = "start"
PAGE_PROFILEDEF = "profiledef"
PAGE_PACKAGES = "packages"
PAGE_REPOS = "repos"
PAGE_BUILD = "build"
PAGE_CUSTOMIZE = "customize"
PAGE_COMPRESSION = "compression"
PAGE_CHROOT = "chroot"
PAGE_USB = "usb"
PAGE_UPLOAD = "upload"
PAGE_TERMINAL = "terminal"
PAGE_QEMU = "qemu"
PAGE_FINISH = "finish"
# Chroot is implicit/automatic now, not a settings page: build-binary's
# --chroot always stops right after the chroot shell exits (see
# check_chroot_request / cli_chroot), so "discuss the ISO" (Build's
# filename/sha256/clean, then Compression) only happens AFTER you've
# actually been in and out of the chroot shell -- for both flows:
#   fresh: welcome > profiledef > packages > repos > customize airootfs >
#          [pacstrap + chroot shell runs] > build (settings) > compression >
#          [build iso runs] > test in qemu > usb > publish to server > finished
#   dirty (./work exists): welcome > [chroot shell runs] > build (settings) >
#          compression > [build iso runs] > test in qemu > usb > publish >
#          finished
# PAGE_CHROOT is not in this list -- both the pacstrap+chroot phase and the
# dirty-build chroot phase are launched directly (see on_next's PAGE_CUSTOMIZE
# and PAGE_START/PAGE_REPOS branches), landing on PAGE_TERMINAL, not a
# settings page with a checkbox.
PAGE_ORDER = [
    PAGE_START, PAGE_PROFILEDEF, PAGE_PACKAGES, PAGE_REPOS, PAGE_CUSTOMIZE,
    PAGE_BUILD, PAGE_COMPRESSION, PAGE_TERMINAL,
    PAGE_QEMU, PAGE_USB, PAGE_UPLOAD, PAGE_FINISH,
]

KNOWN_BOOTMODES = [
    "bios.syslinux.mbr",
    "bios.syslinux.eltorito",
    "uefi-x64.systemd-boot.esp",
    "uefi-x64.systemd-boot.eltorito",
    "uefi-x64.ploader.esp",
    "uefi-x64.ploader.eltorito",
]


def profiledef_path(profile):
    return os.path.join(REPO_ROOT, profile, "profiledef.sh")

def customize_script_path(profile):
    return os.path.join(REPO_ROOT, profile, "airootfs", "root", "customize_airootfs.sh")


def find_existing_airootfs():
    """Same detection build-binary itself uses (./work/tmp.*/x86_64/airootfs).
    airootfs is never deleted after a build (see build-binary's --chroot
    help text), so finding one here means standalone --chroot has
    something to chroot into.

    This GUI runs unprivileged on purpose (only build-binary itself runs
    as root, via sudo). While a build is in progress -- or right after one
    -- ./work/tmp.XXXX is root-owned with mode 0700, so this process can't
    see inside it at all; glob.glob() just silently finds nothing. Returns
    ("confirmed", path), ("unknown", tmp_dir_name), or ("none", None) so
    the caller can tell "definitely not there" apart from "can't check
    from here, but sudo will be able to" -- the latter should NOT disable
    the chroot shortcut, since build-binary's own check (running as root)
    is the one that actually matters.
    """
    matches = glob.glob(os.path.join(REPO_ROOT, "work", "*", "x86_64", "airootfs"))
    if matches:
        return "confirmed", matches[0]
    work_dir = os.path.join(REPO_ROOT, "work")
    try:
        tmp_dirs = [d for d in os.listdir(work_dir) if d.startswith("tmp.")]
    except (FileNotFoundError, PermissionError):
        tmp_dirs = []
    if tmp_dirs:
        return "unknown", tmp_dirs[0]
    return "none", None


def find_iso():
    matches = [p for p in glob.glob(os.path.join(REPO_ROOT, "*.iso")) if "pearos" in os.path.basename(p).lower()]
    return matches[0] if matches else None


def decode_wait_status(status):
    """Vte's "child-exited" signal (and GLib.child_watch_add's callback)
    pass the RAW waitpid() status word, not a plain exit code -- e.g. a
    real exit code of 1 shows up as 256 (1 << 8) unless decoded via
    WIFEXITED/WEXITSTATUS. Mirrors Python's subprocess convention: a
    signal-killed child is reported as the negative signal number.
    """
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return -os.WTERMSIG(status)
    return status


def human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def instruction_label(text):
    """Cubic's big top-of-page instructional text: scale 1.25, wraps, fills."""
    label = Gtk.Label(label=text, xalign=0.0)
    label.set_line_wrap(True)
    label.set_justify(Gtk.Justification.FILL)
    label.set_margin_start(24)
    label.set_margin_end(24)
    label.set_margin_top(18)
    label.set_margin_bottom(18)
    label.get_style_context().add_class("instruction-label")
    return label


class ISOBuilderWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="pearOS ISO Builder")
        self.set_default_size(980, 740)

        self.child_pid = None
        self.session_active = False

        css = Gtk.CssProvider()
        css.load_from_data(
            b".instruction-label { font-size: 130%; }"
            b".welcome-title { font-size: 220%; font-weight: bold; color: #7cb342; }"
        )
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title("pearOS ISO Builder")
        self.set_titlebar(header)

        if SYNC_STATUS is not None:
            sync_label = Gtk.Label()
            if SYNC_STATUS == "resynced":
                sync_label.set_markup('<span color="#e5c07b">⟳ dev tree re-synced</span>')
            else:
                sync_label.set_markup('<span color="#7cb342">● synced</span>')
            header.pack_start(sync_label)

        self.back_button = Gtk.Button(label="Back")
        self.back_button.connect("clicked", self.on_back)
        header.pack_start(self.back_button)

        self.next_button = Gtk.Button(label="Next")
        self.next_button.get_style_context().add_class("suggested-action")
        self.next_button.connect("clicked", self.on_next)
        header.pack_end(self.next_button)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.add(self.stack)

        self.stack.add_named(self._build_start_page(), PAGE_START)
        self.stack.add_named(self._build_profiledef_page(), PAGE_PROFILEDEF)
        self.stack.add_named(self._build_packages_page(), PAGE_PACKAGES)
        self.stack.add_named(self._build_repos_page(), PAGE_REPOS)
        self.stack.add_named(self._build_build_page(), PAGE_BUILD)
        self.stack.add_named(self._build_customize_page(), PAGE_CUSTOMIZE)
        self.stack.add_named(self._build_compression_page(), PAGE_COMPRESSION)
        self.stack.add_named(self._build_chroot_page(), PAGE_CHROOT)
        self.stack.add_named(self._build_usb_page(), PAGE_USB)
        self.stack.add_named(self._build_upload_page(), PAGE_UPLOAD)
        self.stack.add_named(self._build_terminal_page(), PAGE_TERMINAL)
        self.stack.add_named(self._build_qemu_page(), PAGE_QEMU)
        self.stack.add_named(self._build_finish_page(), PAGE_FINISH)

        self._current_page = PAGE_START
        self.stack.set_visible_child_name(PAGE_START)
        self.refresh_dashboard()
        self.update_nav()

        self.connect("delete-event", self.on_close)

    def _install_terminal_shortcuts(self, vte_widget):
        vte_widget.connect("key-press-event", self._on_terminal_key_press)

    def _on_terminal_key_press(self, vte_widget, event):
        # Ctrl+Shift+C/V are the standard terminal-emulator Copy/Paste
        # bindings, but a bare Vte.Terminal doesn't provide them itself --
        # without this, the pty driver turns Shift+Ctrl+C into the exact
        # same control byte as plain Ctrl+C (Shift doesn't change how
        # letter keys map to control characters), sending SIGINT to
        # whatever's running in the foreground (e.g. killing an
        # in-progress build). Always swallow both instead of ever letting
        # them reach the child process.
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)
        if ctrl and shift and event.keyval in (Gdk.KEY_C, Gdk.KEY_c):
            if vte_widget.get_has_selection():
                vte_widget.copy_clipboard()
            return True
        if ctrl and shift and event.keyval in (Gdk.KEY_V, Gdk.KEY_v):
            vte_widget.paste_clipboard()
            return True
        return False

    def on_close(self, *_args):
        if getattr(self, "qemu_session", None) is not None:
            self._teardown_qemu("")
        if self.child_pid:
            try:
                os.kill(self.child_pid, 15)
            except ProcessLookupError:
                pass
        if getattr(self, "upload_child_pid", None):
            try:
                os.kill(self.upload_child_pid, 15)
            except ProcessLookupError:
                pass
        if getattr(self, "clean_child_pid", None):
            try:
                os.kill(self.clean_child_pid, 15)
            except ProcessLookupError:
                pass
        return False

    # ---------------------------------------------------------------- #
    # Page: Start
    # ---------------------------------------------------------------- #
    def _build_start_page(self):
        # Cubic-style splash: everything centered both ways, big icon, big
        # bold title, dimmed version/subtitle, then a compact info card --
        # not the left-aligned instruction-label layout the other pages use.
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        centered = Gtk.Grid(row_spacing=6, column_spacing=0, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        centered.set_vexpand(True)
        centered.set_hexpand(True)

        icon = Gtk.Image.new_from_icon_name("media-optical", Gtk.IconSize.DIALOG)
        icon.set_pixel_size(180)
        centered.attach(icon, 0, 0, 1, 1)

        title = Gtk.Label(label="pearOS ISO Builder")
        title.get_style_context().add_class("welcome-title")
        title.set_margin_top(6)
        centered.attach(title, 0, 1, 1, 1)

        subtitle = Gtk.Label(label="GUI front-end for ./build-binary")
        subtitle.get_style_context().add_class("dim-label")
        centered.attach(subtitle, 0, 2, 1, 1)

        version_label = Gtk.Label(label=f"Next build version: {date.today().strftime('%Y.%m')}")
        version_label.set_opacity(0.5)
        version_label.set_margin_bottom(18)
        centered.attach(version_label, 0, 3, 1, 1)

        frame = Gtk.Frame()
        frame.set_size_request(440, -1)
        info_grid = Gtk.Grid(row_spacing=8, column_spacing=14)
        info_grid.set_border_width(16)
        frame.add(info_grid)

        def info_row(row, icon_name, caption, value_widget):
            row_icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            info_grid.attach(row_icon, 0, row, 1, 1)
            caption_label = Gtk.Label(label=caption, xalign=0.0)
            caption_label.get_style_context().add_class("dim-label")
            info_grid.attach(caption_label, 1, row, 1, 1)
            value_widget.set_xalign(0.0)
            value_widget.set_line_wrap(True)
            info_grid.attach(value_widget, 2, row, 1, 1)

        repo_label = Gtk.Label(label=REPO_ROOT)
        info_row(0, "folder-symbolic", "Repository", repo_label)

        self.iso_label = Gtk.Label()
        info_row(1, "media-optical-symbolic", "Current ISO", self.iso_label)

        self.usb_label = Gtk.Label()
        info_row(2, "drive-removable-media-symbolic", "USB devices", self.usb_label)

        self.airootfs_label = Gtk.Label()
        info_row(3, "folder-open-symbolic", "Existing airootfs", self.airootfs_label)

        centered.attach(frame, 0, 4, 1, 1)

        self.start_console_button = Gtk.Button()
        console_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        console_icon = Gtk.Image.new_from_icon_name("utilities-terminal", Gtk.IconSize.LARGE_TOOLBAR)
        console_content.pack_start(console_icon, False, False, 0)
        console_content.pack_start(Gtk.Label(label="Start Airootfs Console"), False, False, 0)
        self.start_console_button.add(console_content)
        # Show the button's contents once, right now -- children default to
        # invisible until shown, and no_show_all below means the window's
        # own show_all() will never do it for us. Only the button's own
        # "visible" is toggled later (via set_visible, never show_all,
        # which no_show_all blocks even when called directly on this
        # widget).
        console_content.show_all()
        self.start_console_button.get_style_context().add_class("suggested-action")
        self.start_console_button.set_margin_top(12)
        self.start_console_button.set_no_show_all(True)
        self.start_console_button.set_visible(False)
        self.start_console_button.connect("clicked", lambda b: self._chroot_shortcut(PAGE_START))
        centered.attach(self.start_console_button, 0, 5, 1, 1)

        self.start_qemu_button = Gtk.Button()
        qemu_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        qemu_icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        qemu_content.pack_start(qemu_icon, False, False, 0)
        qemu_content.pack_start(Gtk.Label(label="Start QEMU Test"), False, False, 0)
        self.start_qemu_button.add(qemu_content)
        qemu_content.show_all()
        self.start_qemu_button.set_margin_top(6)
        self.start_qemu_button.set_no_show_all(True)
        self.start_qemu_button.set_visible(False)
        self.start_qemu_button.connect("clicked", self.on_start_qemu_shortcut)
        centered.attach(self.start_qemu_button, 0, 6, 1, 1)

        self.start_usb_button = Gtk.Button()
        usb_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        usb_icon = Gtk.Image.new_from_icon_name("drive-removable-media-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        usb_content.pack_start(usb_icon, False, False, 0)
        usb_content.pack_start(Gtk.Label(label="Write to USB"), False, False, 0)
        self.start_usb_button.add(usb_content)
        usb_content.show_all()
        self.start_usb_button.set_margin_top(6)
        self.start_usb_button.set_no_show_all(True)
        self.start_usb_button.set_visible(False)
        self.start_usb_button.connect("clicked", self.on_start_usb_shortcut)
        centered.attach(self.start_usb_button, 0, 7, 1, 1)

        self.start_publish_button = Gtk.Button()
        publish_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        publish_icon = Gtk.Image.new_from_icon_name("network-transmit-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        publish_content.pack_start(publish_icon, False, False, 0)
        publish_content.pack_start(Gtk.Label(label="Publish"), False, False, 0)
        self.start_publish_button.add(publish_content)
        publish_content.show_all()
        self.start_publish_button.set_margin_top(6)
        self.start_publish_button.set_no_show_all(True)
        self.start_publish_button.set_visible(False)
        self.start_publish_button.connect("clicked", self.on_start_publish_shortcut)
        centered.attach(self.start_publish_button, 0, 8, 1, 1)

        danger_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        danger_row.set_margin_top(12)

        self.clean_project_shortcut_button = Gtk.Button(label="Clean Project (delete ./work)")
        self.clean_project_shortcut_button.get_style_context().add_class("destructive-action")
        self.clean_project_shortcut_button.set_no_show_all(True)
        self.clean_project_shortcut_button.set_visible(False)
        self.clean_project_shortcut_button.connect("clicked", self.on_clean_project_shortcut)
        danger_row.pack_start(self.clean_project_shortcut_button, False, False, 0)

        self.remove_iso_button = Gtk.Button(label="Remove ISO")
        self.remove_iso_button.get_style_context().add_class("destructive-action")
        self.remove_iso_button.set_no_show_all(True)
        self.remove_iso_button.set_visible(False)
        self.remove_iso_button.connect("clicked", self.on_remove_iso)
        danger_row.pack_start(self.remove_iso_button, False, False, 0)

        centered.attach(danger_row, 0, 9, 1, 1)

        # Same in-place pattern as the Publish page's upload panel: a small
        # embedded terminal instead of swapping to the full Terminal page.
        # Still needs a real pty (sudo asks for a password interactively),
        # just not a full page for what's normally a near-instant rm -rf.
        self.clean_status_label = Gtk.Label(xalign=0.5)
        self.clean_status_label.set_no_show_all(True)
        self.clean_status_label.set_visible(False)
        centered.attach(self.clean_status_label, 0, 10, 1, 1)

        self.clean_vte = Vte.Terminal()
        self.clean_vte.set_scrollback_lines(2000)
        self._install_terminal_shortcuts(self.clean_vte)
        self.clean_vte.set_size_request(440, 140)
        self.clean_vte.connect("child-exited", self.on_clean_child_exited)
        self.clean_vte.set_no_show_all(True)
        self.clean_vte.set_visible(False)
        centered.attach(self.clean_vte, 0, 11, 1, 1)
        self.clean_child_pid = None

        outer.pack_start(centered, True, True, 0)
        return outer

    # ---------------------------------------------------------------- #
    # Page: profiledef.sh -- structured editor
    # ---------------------------------------------------------------- #
    def _build_profiledef_page(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.pack_start(instruction_label(
            "Edit the selected profile's profiledef.sh."
        ), False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.pack_start(scroller, True, True, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(24)
        scroller.add(box)

        # Which profile's profiledef.sh this page edits -- independent
        # from the Build page's profile field so this page can stand on
        # its own; keep them the same value if you use a non-default
        # profile.
        profile_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        profile_row.pack_start(Gtk.Label(label="Profile:"), False, False, 0)
        self.profiledef_profile_entry = Gtk.Entry(text="pear")
        self.profiledef_profile_entry.connect("activate", lambda *_: self._load_profiledef())
        profile_row.pack_start(self.profiledef_profile_entry, False, False, 0)
        reload_button = Gtk.Button(label="Reload")
        reload_button.connect("clicked", lambda *_: self._load_profiledef())
        profile_row.pack_start(reload_button, False, False, 0)
        box.pack_start(profile_row, False, False, 0)

        # -- ISO identity --
        identity_frame = Gtk.Frame(label="ISO Identity")
        identity_grid = Gtk.Grid(row_spacing=8, column_spacing=12)
        identity_grid.set_border_width(12)
        identity_frame.add(identity_grid)
        box.pack_start(identity_frame, False, False, 0)

        self.profiledef_scalar_entries = {}
        identity_fields = [
            ("iso_name", "ISO name"),
            ("iso_label", "ISO label"),
            ("iso_publisher", "Publisher"),
            ("iso_application", "Application"),
            ("iso_version", "Version"),
            ("install_dir", "Install dir"),
        ]
        for row, (key, caption) in enumerate(identity_fields):
            identity_grid.attach(Gtk.Label(label=caption + ":", xalign=0.0), 0, row, 1, 1)
            entry = Gtk.Entry()
            entry.set_hexpand(True)
            identity_grid.attach(entry, 1, row, 1, 1)
            self.profiledef_scalar_entries[key] = entry

        # -- Boot modes --
        boot_frame = Gtk.Frame(label="Boot Modes")
        boot_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        boot_box.set_border_width(12)
        boot_frame.add(boot_box)
        box.pack_start(boot_frame, False, False, 0)

        self.profiledef_bootmode_checks = {}
        for mode in KNOWN_BOOTMODES:
            check = Gtk.CheckButton(label=mode)
            boot_box.pack_start(check, False, False, 0)
            self.profiledef_bootmode_checks[mode] = check

        # -- Image --
        image_frame = Gtk.Frame(label="Image")
        image_grid = Gtk.Grid(row_spacing=8, column_spacing=12)
        image_grid.set_border_width(12)
        image_frame.add(image_grid)
        box.pack_start(image_frame, False, False, 0)

        image_grid.attach(Gtk.Label(label="Arch:", xalign=0.0), 0, 0, 1, 1)
        arch_entry = Gtk.Entry()
        image_grid.attach(arch_entry, 1, 0, 1, 1)
        self.profiledef_scalar_entries["arch"] = arch_entry

        image_grid.attach(Gtk.Label(label="pacman.conf:", xalign=0.0), 0, 1, 1, 1)
        pacman_conf_entry = Gtk.Entry()
        image_grid.attach(pacman_conf_entry, 1, 1, 1, 1)
        self.profiledef_scalar_entries["pacman_conf"] = pacman_conf_entry

        image_grid.attach(Gtk.Label(label="Image type:", xalign=0.0), 0, 2, 1, 1)
        self.profiledef_image_type_combo = Gtk.ComboBoxText()
        self.profiledef_image_type_combo.append_text("squashfs")
        self.profiledef_image_type_combo.append_text("erofs")
        image_grid.attach(self.profiledef_image_type_combo, 1, 2, 1, 1)

        tool_options_note = Gtk.Label(
            label="airootfs_image_tool_options is set from the Compression page when "
            "building through this GUI (--compression); the raw value is kept and saved "
            "as-is, but isn't editable here to avoid the two getting out of sync.",
            xalign=0.0,
        )
        tool_options_note.set_line_wrap(True)
        tool_options_note.get_style_context().add_class("dim-label")
        box.pack_start(tool_options_note, False, False, 0)

        # -- File permissions --
        perm_frame = Gtk.Frame(label="File Permissions")
        perm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        perm_box.set_border_width(12)
        perm_frame.add(perm_box)
        box.pack_start(perm_frame, False, False, 0)

        self.profiledef_perm_grid = Gtk.Grid(row_spacing=4, column_spacing=8)
        perm_box.pack_start(self.profiledef_perm_grid, False, False, 0)

        add_perm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.profiledef_new_perm_path = Gtk.Entry()
        self.profiledef_new_perm_path.set_placeholder_text("/path")
        add_perm_row.pack_start(self.profiledef_new_perm_path, True, True, 0)
        self.profiledef_new_perm_spec = Gtk.Entry()
        self.profiledef_new_perm_spec.set_placeholder_text("uid:gid:mode")
        self.profiledef_new_perm_spec.set_width_chars(12)
        add_perm_row.pack_start(self.profiledef_new_perm_spec, False, False, 0)
        add_perm_button = Gtk.Button(label="Add")
        add_perm_button.connect("clicked", lambda *_: self._add_profiledef_permission())
        add_perm_row.pack_start(add_perm_button, False, False, 0)
        perm_box.pack_start(add_perm_row, False, False, 0)

        # -- Save --
        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.profiledef_status_label = Gtk.Label(xalign=0.0)
        self.profiledef_status_label.get_style_context().add_class("dim-label")
        save_row.pack_start(self.profiledef_status_label, True, True, 0)
        save_button = Gtk.Button(label="Save profiledef.sh")
        save_button.get_style_context().add_class("suggested-action")
        save_button.connect("clicked", lambda *_: self._save_profiledef())
        save_row.pack_start(save_button, False, False, 0)
        box.pack_start(save_row, False, False, 0)

        self._load_profiledef()
        return outer

    def _load_profiledef(self):
        profile = self.profiledef_profile_entry.get_text().strip() or "pear"
        path = profiledef_path(profile)
        self._profiledef_path = path
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            self.profiledef_status_label.set_text(f"Could not read {path}: {exc}")
            return
        self._profiledef_data = parse_profiledef(text)

        for key, entry in self.profiledef_scalar_entries.items():
            entry.set_text(self._profiledef_data["scalars"].get(key, ""))

        bootmodes = self._profiledef_data["arrays"].get("bootmodes", [])
        for mode, check in self.profiledef_bootmode_checks.items():
            check.set_active(mode in bootmodes)

        image_type = self._profiledef_data["scalars"].get("airootfs_image_type", "squashfs")
        model = self.profiledef_image_type_combo.get_model()
        for i, row in enumerate(model):
            if row[0] == image_type:
                self.profiledef_image_type_combo.set_active(i)
                break

        self._profiledef_permissions = list(self._profiledef_data["permissions"])
        self._render_profiledef_permissions()
        self.profiledef_status_label.set_text("")

    def _render_profiledef_permissions(self):
        for child in list(self.profiledef_perm_grid.get_children()):
            self.profiledef_perm_grid.remove(child)
        for row, (path, spec) in enumerate(self._profiledef_permissions):
            path_label = Gtk.Label(label=path, xalign=0.0)
            path_label.set_selectable(True)
            self.profiledef_perm_grid.attach(path_label, 0, row, 1, 1)
            spec_label = Gtk.Label(label=spec, xalign=0.0)
            spec_label.get_style_context().add_class("dim-label")
            self.profiledef_perm_grid.attach(spec_label, 1, row, 1, 1)
            remove_button = Gtk.Button(label="Remove")
            remove_button.connect("clicked", lambda _b, i=row: self._remove_profiledef_permission(i))
            self.profiledef_perm_grid.attach(remove_button, 2, row, 1, 1)
        self.profiledef_perm_grid.show_all()

    def _add_profiledef_permission(self):
        path = self.profiledef_new_perm_path.get_text().strip()
        spec = self.profiledef_new_perm_spec.get_text().strip()
        if not path or not spec:
            return
        self._profiledef_permissions.append((path, spec))
        self.profiledef_new_perm_path.set_text("")
        self.profiledef_new_perm_spec.set_text("")
        self._render_profiledef_permissions()

    def _remove_profiledef_permission(self, index):
        del self._profiledef_permissions[index]
        self._render_profiledef_permissions()

    def _save_profiledef(self):
        if not hasattr(self, "_profiledef_data"):
            return
        for key, entry in self.profiledef_scalar_entries.items():
            self._profiledef_data["scalars"][key] = entry.get_text()
        self._profiledef_data["scalars"]["airootfs_image_type"] = (
            self.profiledef_image_type_combo.get_active_text() or "squashfs"
        )
        self._profiledef_data["arrays"]["bootmodes"] = [
            mode for mode, check in self.profiledef_bootmode_checks.items() if check.get_active()
        ]
        self._profiledef_data["permissions"] = list(self._profiledef_permissions)

        try:
            with open(self._profiledef_path, "w", encoding="utf-8") as fh:
                fh.write(render_profiledef(self._profiledef_data))
        except OSError as exc:
            self.profiledef_status_label.set_text(f"Failed to save: {exc}")
            return
        self._load_profiledef()
        self.profiledef_status_label.set_text("Saved.")

    # ---------------------------------------------------------------- #
    # Page: Packages
    # ---------------------------------------------------------------- #
    def _build_packages_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            f"Select packages to install.\nEditing {os.path.relpath(PACKAGES_FILE, REPO_ROOT)} "
            "-- this is copied into the profile at the start of every fresh build."
        ), False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.set_border_width(16)
        box.pack_start(content, True, True, 0)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.package_search = Gtk.SearchEntry()
        self.package_search.set_placeholder_text("Filter packages...")
        self.package_search.connect("search-changed", lambda *_: self.package_listbox.invalidate_filter())
        top_row.pack_start(self.package_search, True, True, 0)

        self.package_count_label = Gtk.Label()
        self.package_count_label.get_style_context().add_class("dim-label")
        top_row.pack_start(self.package_count_label, False, False, 0)
        content.pack_start(top_row, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content.pack_start(scroller, True, True, 0)

        self.package_listbox = Gtk.ListBox()
        self.package_listbox.set_filter_func(self._filter_package_row)
        scroller.add(self.package_listbox)

        add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.new_package_entry = Gtk.Entry()
        self.new_package_entry.set_placeholder_text("package-name")
        self.new_package_entry.connect("activate", lambda *_: self._add_package())
        add_row.pack_start(self.new_package_entry, True, True, 0)
        add_button = Gtk.Button(label="Add package")
        add_button.connect("clicked", lambda *_: self._add_package())
        add_row.pack_start(add_button, False, False, 0)
        content.pack_start(add_row, False, False, 0)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.packages_status_label = Gtk.Label(xalign=0.0)
        self.packages_status_label.get_style_context().add_class("dim-label")
        save_row.pack_start(self.packages_status_label, True, True, 0)
        save_button = Gtk.Button(label="Save packages.x86_64")
        save_button.connect("clicked", lambda *_: self._save_packages())
        save_row.pack_start(save_button, False, False, 0)
        content.pack_start(save_row, False, False, 0)

        self._load_packages()
        return box

    def _load_packages(self):
        self.package_entries = []
        for child in list(self.package_listbox.get_children()):
            self.package_listbox.remove(child)
        try:
            with open(PACKAGES_FILE, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            self.packages_status_label.set_text(f"Could not read {PACKAGES_FILE}: {exc}")
            return
        self.package_entries = parse_packages(text)
        for entry in self.package_entries:
            if entry["kind"] != "package":
                continue
            row = Gtk.ListBoxRow()
            check = Gtk.CheckButton(label=entry["name"])
            check.set_active(entry["enabled"])
            check.connect("toggled", lambda c, e=entry: e.__setitem__("enabled", c.get_active()))
            row.add(check)
            row.package_name = entry["name"]
            self.package_listbox.add(row)
        self.package_listbox.show_all()
        self._update_package_count()
        self.packages_status_label.set_text("")

    def _filter_package_row(self, row):
        query = self.package_search.get_text().strip().lower()
        return not query or query in getattr(row, "package_name", "").lower()

    def _update_package_count(self):
        total = sum(1 for e in self.package_entries if e["kind"] == "package")
        enabled = sum(1 for e in self.package_entries if e["kind"] == "package" and e["enabled"])
        self.package_count_label.set_text(f"{enabled} / {total} enabled")

    def _add_package(self):
        name = self.new_package_entry.get_text().strip()
        if not name:
            return
        if any(e["kind"] == "package" and e["name"] == name for e in self.package_entries):
            self.packages_status_label.set_text(f"\"{name}\" is already in the list.")
            return
        entry = {"kind": "package", "name": name, "enabled": True}
        self.package_entries.append(entry)
        row = Gtk.ListBoxRow()
        check = Gtk.CheckButton(label=name)
        check.set_active(True)
        check.connect("toggled", lambda c, e=entry: e.__setitem__("enabled", c.get_active()))
        row.add(check)
        row.package_name = name
        row.show_all()
        self.package_listbox.add(row)
        self.new_package_entry.set_text("")
        self._update_package_count()

    def _save_packages(self):
        try:
            with open(PACKAGES_FILE, "w", encoding="utf-8") as fh:
                fh.write(render_packages(self.package_entries))
        except OSError as exc:
            self.packages_status_label.set_text(f"Failed to save: {exc}")
            return
        self._update_package_count()
        self.packages_status_label.set_text("Saved.")

    # ---------------------------------------------------------------- #
    # Page: Repos & SigLevel
    # ---------------------------------------------------------------- #
    def _build_repos_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            f"Enable/disable repositories and set each one's SigLevel.\n"
            f"Editing {os.path.relpath(PACMAN_CONF_FILE, REPO_ROOT)}."
        ), False, False, 0)

        warning = Gtk.Label(
            label="This is the real source: _generate_pear_pacman_conf() copies it into "
            "pear/pacman.conf (then merges in any extra repos it detects on the build "
            "host) at the start of every fresh build, so edits here persist across builds.",
            xalign=0.0,
        )
        warning.set_line_wrap(True)
        warning.set_margin_start(24)
        warning.set_margin_end(24)
        warning.get_style_context().add_class("dim-label")
        box.pack_start(warning, False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.set_border_width(16)
        box.pack_start(content, True, True, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content.pack_start(scroller, True, True, 0)

        self.repos_grid = Gtk.Grid(row_spacing=8, column_spacing=10)
        self.repos_grid.set_border_width(4)
        scroller.add(self.repos_grid)

        add_frame = Gtk.Frame(label="Add repo")
        add_grid = Gtk.Grid(row_spacing=6, column_spacing=8)
        add_grid.set_border_width(10)
        add_frame.add(add_grid)
        content.pack_start(add_frame, False, False, 0)

        add_grid.attach(Gtk.Label(label="Name:", xalign=0.0), 0, 0, 1, 1)
        self.new_repo_name_entry = Gtk.Entry()
        self.new_repo_name_entry.set_placeholder_text("myrepo")
        add_grid.attach(self.new_repo_name_entry, 1, 0, 1, 1)

        add_grid.attach(Gtk.Label(label="Server:", xalign=0.0), 0, 1, 1, 1)
        self.new_repo_server_entry = Gtk.Entry()
        self.new_repo_server_entry.set_placeholder_text("https://example.com/$repo/$arch")
        self.new_repo_server_entry.set_hexpand(True)
        add_grid.attach(self.new_repo_server_entry, 1, 1, 1, 1)

        add_grid.attach(Gtk.Label(label="SigLevel:", xalign=0.0), 0, 2, 1, 1)
        self.new_repo_siglevel_combo = Gtk.ComboBoxText.new_with_entry()
        for value in COMMON_SIGLEVELS:
            self.new_repo_siglevel_combo.append_text(value)
        add_grid.attach(self.new_repo_siglevel_combo, 1, 2, 1, 1)

        add_repo_button = Gtk.Button(label="Add repo")
        add_repo_button.connect("clicked", lambda *_: self._add_repo())
        add_grid.attach(add_repo_button, 1, 3, 1, 1)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.repos_status_label = Gtk.Label(xalign=0.0)
        self.repos_status_label.get_style_context().add_class("dim-label")
        save_row.pack_start(self.repos_status_label, True, True, 0)
        save_button = Gtk.Button(label="Save pacman.conf")
        save_button.connect("clicked", lambda *_: self._save_repos())
        save_row.pack_start(save_button, False, False, 0)
        content.pack_start(save_row, False, False, 0)

        self._load_repos()
        return box

    def _load_repos(self):
        try:
            with open(PACMAN_CONF_FILE, encoding="utf-8") as fh:
                self._pacman_conf_text = fh.read()
        except OSError as exc:
            self.repos_status_label.set_text(f"Could not read {PACMAN_CONF_FILE}: {exc}")
            self.repo_entries = []
            return
        self.repo_entries = parse_repos(self._pacman_conf_text)
        global_siglevel = extract_global_siglevel(self._pacman_conf_text)
        for repo in self.repo_entries:
            if not repo["siglevel_value"]:
                # No explicit SigLevel line -- fill in what it actually
                # inherits from [options], as a real value rather than
                # leaving the field blank.
                repo["siglevel_value"] = global_siglevel

        self._render_repos_grid()
        self.repos_status_label.set_text("")

    def _render_repos_grid(self):
        for child in list(self.repos_grid.get_children()):
            self.repos_grid.remove(child)

        header = ["Enabled", "Repo", "SigLevel", ""]
        for col, text in enumerate(header):
            label = Gtk.Label(label=text, xalign=0.0)
            label.get_style_context().add_class("dim-label")
            self.repos_grid.attach(label, col, 0, 1, 1)

        seen_names = {}
        for row_idx, repo in enumerate(self.repo_entries, start=1):
            seen_names[repo["name"]] = seen_names.get(repo["name"], 0) + 1
            dup_count = seen_names[repo["name"]]

            check = Gtk.CheckButton()
            check.set_active(repo["enabled"])
            check.connect("toggled", lambda c, r=repo: r.__setitem__("enabled", c.get_active()))
            self.repos_grid.attach(check, 0, row_idx, 1, 1)

            if repo.get("new"):
                label_text = f"{repo['name']} (new -- click Save)"
            elif dup_count > 1:
                label_text = f"{repo['name']} (duplicate #{dup_count})"
            else:
                label_text = repo["name"]
            name_label = Gtk.Label(label=label_text, xalign=0.0)
            if repo.get("new") or dup_count > 1:
                name_label.get_style_context().add_class("warning")
            self.repos_grid.attach(name_label, 1, row_idx, 1, 1)

            sig_combo = Gtk.ComboBoxText.new_with_entry()
            for value in COMMON_SIGLEVELS:
                sig_combo.append_text(value)
            sig_combo.get_child().set_text(repo["siglevel_value"])
            sig_combo.connect(
                "changed", lambda c, r=repo: r.__setitem__("siglevel_value", c.get_child().get_text().strip())
            )
            self.repos_grid.attach(sig_combo, 2, row_idx, 1, 1)

            delete_button = Gtk.Button(label="Remove")
            delete_button.connect("clicked", lambda _b, r=repo, row=row_idx: self._delete_repo_row(r, row))
            self.repos_grid.attach(delete_button, 3, row_idx, 1, 1)

        self.repos_grid.show_all()

    def _add_repo(self):
        name = self.new_repo_name_entry.get_text().strip()
        if not name:
            self.repos_status_label.set_text("Enter a repo name first.")
            return
        siglevel = self.new_repo_siglevel_combo.get_child().get_text().strip()
        server = self.new_repo_server_entry.get_text().strip()
        self.repo_entries.append(new_repo(name, siglevel_value=siglevel, server=server))
        self.new_repo_name_entry.set_text("")
        self.new_repo_server_entry.set_text("")
        self.new_repo_siglevel_combo.get_child().set_text("")
        self._render_repos_grid()
        self.repos_status_label.set_text(f'"{name}" added -- click Save to write it to the file.')

    def _delete_repo_row(self, repo, row_idx):
        repo["delete"] = True
        for col in range(4):
            widget = self.repos_grid.get_child_at(col, row_idx)
            if widget is not None:
                widget.set_sensitive(False)
        self.repos_status_label.set_text(f"\"{repo['name']}\" marked for removal -- click Save to apply.")

    def _save_repos(self):
        if not hasattr(self, "_pacman_conf_text"):
            return
        try:
            new_text = render_repos(self._pacman_conf_text, self.repo_entries)
            with open(PACMAN_CONF_FILE, "w", encoding="utf-8") as fh:
                fh.write(new_text)
        except OSError as exc:
            self.repos_status_label.set_text(f"Failed to save: {exc}")
            return
        self._load_repos()
        self.repos_status_label.set_text("Saved.")

    # ---------------------------------------------------------------- #
    # Page: Build
    # ---------------------------------------------------------------- #
    def _build_build_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            "Build a new pearOS ISO image."
        ), False, False, 0)

        content = Gtk.Grid(row_spacing=10, column_spacing=12)
        content.set_border_width(32)
        box.pack_start(content, False, False, 0)

        # Reaching this page at all (via the normal Next-Next wizard flow,
        # or the dirty-build chroot-exit jump) already means "build" --
        # for_claude.txt's workflow doesn't have a yes/no gate here, just
        # settings, so there's no visible "Build ISO" checkbox to
        # uncheck. build_check is kept as an internal state holder (other
        # code -- the publish-phase reset, the chroot shortcuts -- still
        # reads/sets it) but it's never shown, and stays True except when
        # those flows explicitly turn it off for a non-build action.
        self.build_check = Gtk.CheckButton(label="Build ISO (--build)")
        self.build_check.set_active(True)
        self.build_check.connect("toggled", self._on_build_toggled)

        content.attach(Gtk.Label(label="Profile:", xalign=0.0), 0, 1, 1, 1)
        self.profile_entry = Gtk.Entry(text="pear")
        content.attach(self.profile_entry, 1, 1, 1, 1)

        content.attach(Gtk.Label(label="Filename (optional):", xalign=0.0), 0, 2, 1, 1)
        self.filename_entry = Gtk.Entry()
        self.filename_entry.set_placeholder_text("leave empty for profiledef.sh's default")
        content.attach(self.filename_entry, 1, 2, 1, 1)
        filename_note = Gtk.Label(
            label="Final name is always NAME-<version>-<arch>.iso. --usb/--sha256/--upload "
            "find the ISO with a case-insensitive \"pearos\" search, so keep that in NAME "
            "if you plan to chain them.",
            xalign=0.0,
        )
        filename_note.set_line_wrap(True)
        filename_note.get_style_context().add_class("dim-label")
        content.attach(filename_note, 0, 3, 2, 1)

        self.clean_check = Gtk.CheckButton(label="--clean (delete ./work first, build from scratch)")
        content.attach(self.clean_check, 0, 4, 2, 1)

        self.sha256_check = Gtk.CheckButton(label="--sha256 (write checksum to ./sha.txt when done)")
        self.sha256_check.set_active(True)
        content.attach(self.sha256_check, 0, 5, 2, 1)

        self._on_build_toggled(self.build_check)
        return box

    def _on_build_toggled(self, check):
        active = check.get_active()
        for widget in (self.profile_entry, self.filename_entry, self.clean_check, self.sha256_check):
            widget.set_sensitive(active)
        self._update_chroot_hint()

    # ---------------------------------------------------------------- #
    # Page: Customize script (profile's airootfs/root/customize_airootfs.sh)
    # ---------------------------------------------------------------- #
    def _build_customize_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            "Edit the profile's customize_airootfs.sh -- this script runs "
            "inside the chroot during every build, for scripted system setup."
        ), False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.set_border_width(16)
        box.pack_start(content, True, True, 0)

        self.customize_path_label = Gtk.Label(xalign=0.0)
        self.customize_path_label.get_style_context().add_class("dim-label")
        content.pack_start(self.customize_path_label, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        content.pack_start(scroller, True, True, 0)

        if HAS_GTKSOURCE:
            self.customize_buffer = GtkSource.Buffer()
            lang_manager = GtkSource.LanguageManager.get_default()
            language = lang_manager.get_language("sh")
            if language:
                self.customize_buffer.set_language(language)
            self.customize_buffer.set_highlight_syntax(True)
            self.customize_view = GtkSource.View.new_with_buffer(self.customize_buffer)
            self.customize_view.set_show_line_numbers(True)
            self.customize_view.set_tab_width(4)
        else:
            self.customize_buffer = Gtk.TextBuffer()
            self.customize_view = Gtk.TextView.new_with_buffer(self.customize_buffer)
        self.customize_view.set_monospace(True)
        scroller.add(self.customize_view)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.customize_status_label = Gtk.Label(xalign=0.0)
        self.customize_status_label.get_style_context().add_class("dim-label")
        save_row.pack_start(self.customize_status_label, True, True, 0)
        reload_button = Gtk.Button(label="Reload")
        reload_button.connect("clicked", lambda *_: self._load_customize_script())
        save_row.pack_start(reload_button, False, False, 0)
        save_button = Gtk.Button(label="Save")
        save_button.connect("clicked", lambda *_: self._save_customize_script())
        save_row.pack_start(save_button, False, False, 0)
        content.pack_start(save_row, False, False, 0)

        self._load_customize_script()
        return box

    def _load_customize_script(self):
        profile = self.profile_entry.get_text().strip() or "pear"
        path = customize_script_path(profile)
        self._customize_script_path = path
        self.customize_path_label.set_text(os.path.relpath(path, REPO_ROOT))
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            self.customize_buffer.set_text("")
            self.customize_status_label.set_text(f"Could not read: {exc}")
            return
        self.customize_buffer.set_text(text)
        self.customize_status_label.set_text("")

    def _save_customize_script(self):
        path = getattr(self, "_customize_script_path", None)
        if not path:
            return
        start, end = self.customize_buffer.get_bounds()
        text = self.customize_buffer.get_text(start, end, True)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            self.customize_status_label.set_text(f"Failed to save: {exc}")
            return
        self.customize_status_label.set_text("Saved.")

    # ---------------------------------------------------------------- #
    # Page: Compression (the Cubic triangle)
    # ---------------------------------------------------------------- #
    def _build_compression_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            "Select the compression for the Linux file system.\n"
            "Only used when Build is enabled."
        ), False, False, 0)

        self.compression_triangle = CompressionTriangle(COMPRESSION_OPTIONS)
        self.compression_triangle.set_halign(Gtk.Align.CENTER)
        self.compression_triangle.set_valign(Gtk.Align.CENTER)
        self.compression_triangle.set_margin_top(12)
        self.compression_triangle.set_margin_bottom(12)
        box.pack_start(self.compression_triangle, True, True, 0)
        return box

    # ---------------------------------------------------------------- #
    # Page: Chroot
    # ---------------------------------------------------------------- #
    def _build_chroot_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            "Customize the system directly, with an interactive chroot shell."
        ), False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_border_width(32)
        box.pack_start(content, False, False, 0)

        self.chroot_check = Gtk.CheckButton(label="--chroot")
        self.chroot_check.connect("toggled", lambda *_: None)
        content.pack_start(self.chroot_check, False, False, 0)

        self.chroot_hint = Gtk.Label(xalign=0.0)
        self.chroot_hint.set_line_wrap(True)
        self.chroot_hint.get_style_context().add_class("dim-label")
        content.pack_start(self.chroot_hint, False, False, 0)

        # Detected ./work airootfs: show status + a one-click shortcut that
        # skips straight to the terminal with just --chroot, instead of
        # having to walk Build/USB/Upload pages first.
        detect_frame = Gtk.Frame(label="Existing work directory")
        detect_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        detect_box.set_border_width(12)
        detect_frame.add(detect_box)
        content.pack_start(detect_frame, False, False, 12)

        self.chroot_detect_label = Gtk.Label(xalign=0.0)
        self.chroot_detect_label.set_line_wrap(True)
        detect_box.pack_start(self.chroot_detect_label, True, True, 0)

        self.chroot_only_button = Gtk.Button(label="Chroot now (skip everything else)")
        self.chroot_only_button.get_style_context().add_class("suggested-action")
        self.chroot_only_button.connect("clicked", lambda b: self._chroot_shortcut(PAGE_CHROOT))
        detect_box.pack_start(self.chroot_only_button, False, False, 0)

        self._update_chroot_hint()
        return box

    def on_chroot_only(self, _button):
        self._chroot_shortcut(None)

    def _chroot_shortcut(self, origin_page):
        # origin_page: where to send Back once landed on Terminal, since
        # this jumps there directly instead of through the linear wizard
        # order (None means "let Back use the normal linear order").
        # Set AFTER launch_session(), which clears it at the start of every
        # launch -- otherwise a later, normal (non-shortcut) launch would
        # inherit a stale origin from whatever shortcut ran before it.
        self.build_check.set_active(False)
        self.usb_check.set_active(False)
        self.chroot_check.set_active(True)
        self.launch_session()
        self._chroot_shortcut_origin = origin_page
        self.update_nav()

    def on_start_qemu_shortcut(self, _button):
        self._qemu_from_start = True
        self._goto(PAGE_QEMU)
        self.update_nav()

    def on_start_usb_shortcut(self, _button):
        # No --yes here on purpose: the "Continue? (yes/no)" confirmation
        # (with ISO/USB size and target device shown) stays live in the
        # terminal, same as the USB page's own checkbox default.
        self.launch_session(["--usb"])

    def on_start_publish_shortcut(self, _button):
        self._upload_from_start = True
        self._goto(PAGE_UPLOAD)
        self.update_nav()

    def on_clean_project_shortcut(self, _button):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Delete ./work?",
        )
        dialog.format_secondary_text(
            "Removes all build state -- pacstrap output, airootfs, everything an "
            "in-progress or finished build left behind. Does not touch the ISO file itself. "
            "This runs as root (sudo) since ./work is typically root-owned."
        )
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.YES:
            return

        if self.clean_child_pid is not None:
            return
        self.clean_status_label.set_visible(True)
        self.clean_status_label.set_text("Cleaning ./work...")
        self.clean_vte.set_visible(True)
        self.clean_vte.reset(True, True)
        self.clean_project_shortcut_button.set_sensitive(False)
        self.clean_vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            REPO_ROOT,
            ["sudo", "--", BUILD_BINARY, "--clean-project"],
            [],
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            self._on_clean_spawn_complete,
        )

    def _on_clean_spawn_complete(self, terminal, pid, error):
        if error:
            self.clean_status_label.set_text(f"Failed to start: {error}")
            self.clean_project_shortcut_button.set_sensitive(True)
            return
        self.clean_child_pid = pid

    def on_clean_child_exited(self, _terminal, exit_code):
        exit_code = decode_wait_status(exit_code)
        self.clean_child_pid = None
        self.clean_project_shortcut_button.set_sensitive(True)
        self.clean_status_label.set_text(
            "./work deleted." if exit_code == 0 else f"Failed (exit code {exit_code})."
        )
        self.refresh_dashboard()

    def on_remove_iso(self, _button):
        iso_path = find_iso()
        if not iso_path:
            return
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f'Delete "{os.path.basename(iso_path)}"?',
        )
        dialog.format_secondary_text("This permanently deletes the ISO file. It cannot be undone.")
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.YES:
            return
        try:
            os.remove(iso_path)
        except OSError as exc:
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Failed to delete ISO",
            )
            error_dialog.format_secondary_text(str(exc))
            error_dialog.run()
            error_dialog.destroy()
            return
        self.refresh_dashboard()

    def _update_chroot_hint(self, *_args):
        if not hasattr(self, "chroot_hint"):
            return
        if self.build_check.get_active():
            self.chroot_hint.set_text(
                "With Build enabled: offers the chroot prompt mid-build, at the one point "
                "where airootfs exists but hasn't been turned into the squashfs yet."
            )
        else:
            self.chroot_hint.set_text(
                "With Build disabled: chroots straight into the airootfs left over from an "
                "earlier build (it's never deleted). Inside the chroot menu, choose \"Enter "
                "chroot\", edit files, exit, then either \"Exit without building now\" to keep "
                "editing another day, or \"Continue and build\" to regenerate the squashfs + "
                "ISO from everything accumulated so far -- without rerunning pacstrap."
            )

    # ---------------------------------------------------------------- #
    # Page: USB
    # ---------------------------------------------------------------- #
    def _build_usb_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            "Write the ISO to a USB drive."
        ), False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_border_width(32)
        box.pack_start(content, False, False, 0)

        self.usb_check = Gtk.CheckButton(label="--usb (auto-detect the single connected USB device and write)")
        content.pack_start(self.usb_check, False, False, 0)

        self.usb_yes_check = Gtk.CheckButton(
            label="-y / --yes (skip the \"Continue? (yes/no)\" confirmation -- writes immediately)"
        )
        content.pack_start(self.usb_yes_check, False, False, 0)

        note = Gtk.Label(
            label="Off by default: the yes/no confirmation (with ISO/USB size and the target "
            "device shown) is answered live in the terminal. Only check --yes once you're "
            "sure -- it erases the device with no further warning.",
            xalign=0.0,
        )
        note.set_line_wrap(True)
        note.get_style_context().add_class("dim-label")
        content.pack_start(note, False, False, 0)

        frame = Gtk.Frame(label="Detected USB block devices")
        frame_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        frame_box.set_border_width(8)
        frame.add(frame_box)
        self.usb_devices_label = Gtk.Label(xalign=0.0)
        self.usb_devices_label.get_style_context().add_class("monospace")
        frame_box.pack_start(self.usb_devices_label, False, False, 0)
        content.pack_start(frame, False, False, 8)

        write_button = Gtk.Button(label="Write to USB Now")
        write_button.get_style_context().add_class("suggested-action")
        write_button.set_margin_top(8)
        write_button.connect("clicked", self.on_write_usb_now)
        content.pack_start(write_button, False, False, 0)

        skip_note = Gtk.Label(
            label="Click Next to skip USB writing and move on.", xalign=0.0
        )
        skip_note.get_style_context().add_class("dim-label")
        content.pack_start(skip_note, False, False, 0)
        return box

    def on_write_usb_now(self, _button):
        args = ["--usb"]
        if self.usb_yes_check.get_active():
            args.append("--yes")
        self.launch_session(args)

    # ---------------------------------------------------------------- #
    # Page: Upload / Publish -- rich in-app UI, not a terminal dump.
    # list/links/delete talk to rclone directly (no root needed, unlike
    # build-binary) and render as real widgets. Only the actual upload
    # (multi-GB, needs live progress) runs a process, and even that stays
    # embedded on this page -- a small Vte log panel, not a full-page swap.
    # ---------------------------------------------------------------- #
    def _build_upload_page(self):
        self.cdn_files = []
        self.upload_child_pid = None

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.pack_start(instruction_label(
            "Publish to the CDN."
        ), False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.pack_start(scroller, True, True, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(20)
        scroller.add(box)

        # -- Upload --
        upload_frame = Gtk.Frame(label="Upload")
        upload_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        upload_box.set_border_width(12)
        upload_frame.add(upload_box)
        box.pack_start(upload_frame, False, False, 0)

        upload_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.upload_now_button = Gtk.Button(label="Upload ISO to CDN")
        self.upload_now_button.get_style_context().add_class("suggested-action")
        self.upload_now_button.connect("clicked", self.on_upload_now)
        upload_row.pack_start(self.upload_now_button, False, False, 0)
        self.upload_status_label = Gtk.Label(xalign=0.0)
        upload_row.pack_start(self.upload_status_label, True, True, 0)
        upload_box.pack_start(upload_row, False, False, 0)

        self.upload_vte = Vte.Terminal()
        self.upload_vte.set_scrollback_lines(5000)
        self._install_terminal_shortcuts(self.upload_vte)
        self.upload_vte.set_size_request(-1, 160)
        self.upload_vte.connect("child-exited", self.on_upload_child_exited)
        upload_box.pack_start(self.upload_vte, False, False, 0)

        # -- Files on CDN --
        files_frame = Gtk.Frame(label="Files on CDN")
        files_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        files_box.set_border_width(12)
        files_frame.add(files_box)
        box.pack_start(files_frame, True, True, 0)

        refresh_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        refresh_button = Gtk.Button(label="Refresh")
        refresh_button.connect("clicked", lambda *_: self._refresh_cdn_files())
        refresh_row.pack_start(refresh_button, False, False, 0)
        self.cdn_status_label = Gtk.Label(xalign=0.0)
        refresh_row.pack_start(self.cdn_status_label, True, True, 0)
        files_box.pack_start(refresh_row, False, False, 0)

        self.cdn_files_grid = Gtk.Grid(row_spacing=6, column_spacing=10)
        files_box.pack_start(self.cdn_files_grid, False, False, 0)

        return outer

    def _refresh_cdn_files(self):
        self.cdn_status_label.set_text("Loading...")
        files, error = fetch_cdn_files()
        if error:
            self.cdn_status_label.set_text(f"Failed: {error}")
            self.cdn_files = []
        else:
            self.cdn_files = files
            self.cdn_status_label.set_text(f"{len(files)} file(s)" if files else "No files on CDN.")
        self._render_cdn_files()

    def _render_cdn_files(self):
        for child in list(self.cdn_files_grid.get_children()):
            self.cdn_files_grid.remove(child)

        header = ["File", "Size", "Date", "", ""]
        for col, text in enumerate(header):
            label = Gtk.Label(label=text, xalign=0.0)
            label.get_style_context().add_class("dim-label")
            self.cdn_files_grid.attach(label, col, 0, 1, 1)

        for row_idx, entry in enumerate(self.cdn_files, start=1):
            name_label = Gtk.Label(label=entry["name"], xalign=0.0)
            name_label.set_selectable(True)
            self.cdn_files_grid.attach(name_label, 0, row_idx, 1, 1)

            size_label = Gtk.Label(label=human_size(entry["size_bytes"]), xalign=0.0)
            size_label.get_style_context().add_class("dim-label")
            self.cdn_files_grid.attach(size_label, 1, row_idx, 1, 1)

            date_label = Gtk.Label(label=entry["date"], xalign=0.0)
            date_label.get_style_context().add_class("dim-label")
            self.cdn_files_grid.attach(date_label, 2, row_idx, 1, 1)

            copy_button = Gtk.Button(label="Copy Link")
            copy_button.set_sensitive(bool(entry["url"]))
            copy_button.connect("clicked", lambda _b, url=entry["url"]: self._copy_to_clipboard(url))
            self.cdn_files_grid.attach(copy_button, 3, row_idx, 1, 1)

            delete_button = Gtk.Button(label="Delete")
            delete_button.get_style_context().add_class("destructive-action")
            delete_button.connect("clicked", lambda _b, name=entry["name"]: self.on_delete_cdn_file(name))
            self.cdn_files_grid.attach(delete_button, 4, row_idx, 1, 1)

        self.cdn_files_grid.show_all()

    def _copy_to_clipboard(self, text):
        if not text:
            return
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()
        self.cdn_status_label.set_text(f"Copied: {text}")

    def on_delete_cdn_file(self, filename):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f'Delete "{filename}" from the CDN?',
        )
        dialog.format_secondary_text("This permanently deletes the file from the server. It cannot be undone.")
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.YES:
            return
        self.cdn_status_label.set_text(f"Deleting {filename}...")
        ok, message = delete_cdn_file(filename)
        self.cdn_status_label.set_text(message.strip() if message.strip() else ("Deleted." if ok else "Failed."))
        self._refresh_cdn_files()

    def on_upload_now(self, _button):
        if self.upload_child_pid is not None:
            return
        self.upload_vte.reset(True, True)
        self.upload_status_label.set_text("Uploading...")
        self.upload_now_button.set_sensitive(False)
        self.upload_vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            REPO_ROOT,
            [UPLOAD_SCRIPT],
            [],
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            self._on_upload_spawn_complete,
        )

    def _on_upload_spawn_complete(self, terminal, pid, error):
        if error:
            self.upload_status_label.set_text(f"Failed to start: {error}")
            self.upload_now_button.set_sensitive(True)
            return
        self.upload_child_pid = pid

    def on_upload_child_exited(self, _terminal, exit_code):
        exit_code = decode_wait_status(exit_code)
        self.upload_child_pid = None
        self.upload_now_button.set_sensitive(True)
        self.upload_status_label.set_text(
            "Upload complete." if exit_code == 0 else f"Upload failed (exit code {exit_code})."
        )
        self._refresh_cdn_files()

    # ---------------------------------------------------------------- #
    # Command construction
    # ---------------------------------------------------------------- #
    def build_args(self):
        args = []
        if self.build_check.get_active():
            args.append("--build")
            profile = self.profile_entry.get_text().strip() or "pear"
            args += ["--profile", profile]
            args += ["--compression", self.compression_triangle.get_active_key() or "default"]
            filename = self.filename_entry.get_text().strip()
            if filename:
                args += ["--filename", filename]
            if self.clean_check.get_active():
                args.append("--clean")
            if self.sha256_check.get_active():
                args.append("--sha256")
        if self.chroot_check.get_active():
            args.append("--chroot")
        # USB has its own dedicated "Write to USB Now" button (--usb [+
        # --yes], launched directly) and CDN publish/list/links/delete are
        # all handled in-page via direct rclone calls -- neither feeds
        # into this combined build/chroot/compression command anymore.
        return args

    # ---------------------------------------------------------------- #
    # Page: Terminal (Vte owns the pty, no scripting of prompts)
    # ---------------------------------------------------------------- #
    def _build_terminal_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            "Running. Answer any prompts here, same as a real terminal."
        ), False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.set_border_width(10)
        box.pack_start(content, True, True, 0)

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.terminal_status = Gtk.Label(label="Idle", xalign=0.0)
        header_row.pack_start(self.terminal_status, True, True, 0)
        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.connect("clicked", self.on_stop)
        self.stop_button.set_sensitive(False)
        header_row.pack_end(self.stop_button, False, False, 0)
        content.pack_start(header_row, False, False, 0)

        term_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.vte = Vte.Terminal()
        self.vte.set_scrollback_lines(20000)
        self._install_terminal_shortcuts(self.vte)
        self.vte.connect("child-exited", self.on_child_exited)
        term_row.pack_start(self.vte, True, True, 0)

        scrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL)
        scrollbar.set_adjustment(self.vte.get_vadjustment())
        term_row.pack_start(scrollbar, False, False, 0)

        content.pack_start(term_row, True, True, 0)
        return box

    # ---------------------------------------------------------------- #
    # Page: QEMU test -- ephemeral VM, embedded VNC display
    # ---------------------------------------------------------------- #
    def _build_qemu_page(self):
        self.qemu_session = None
        self.qemu_vnc_widget = None
        self.qemu_watch_id = None
        self.qemu_poll_id = None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label(
            "Test the ISO in a throwaway QEMU VM (UEFI, virtio disk/net).\n"
            "Stopping the VM -- however it stops -- destroys it completely: "
            "the disk, UEFI variables and everything else are deleted."
        ), False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_border_width(16)
        box.pack_start(content, True, True, 0)

        settings_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        content.pack_start(settings_row, False, False, 0)

        self.qemu_iso_label = Gtk.Label(xalign=0.0)
        settings_row.pack_start(self.qemu_iso_label, True, True, 0)

        settings_row.pack_start(Gtk.Label(label="RAM (MiB):"), False, False, 0)
        self.qemu_ram_spin = Gtk.SpinButton.new_with_range(MIN_RAM_MIB, 32768, 512)
        self.qemu_ram_spin.set_value(MIN_RAM_MIB)
        settings_row.pack_start(self.qemu_ram_spin, False, False, 0)

        settings_row.pack_start(Gtk.Label(label="CPUs:"), False, False, 0)
        self.qemu_cpu_spin = Gtk.SpinButton.new_with_range(MIN_CPUS, 16, 1)
        self.qemu_cpu_spin.set_value(MIN_CPUS)
        settings_row.pack_start(self.qemu_cpu_spin, False, False, 0)

        settings_row.pack_start(Gtk.Label(label="Disk (GiB):"), False, False, 0)
        self.qemu_disk_spin = Gtk.SpinButton.new_with_range(MIN_DISK_GIB, 500, 10)
        self.qemu_disk_spin.set_value(MIN_DISK_GIB)
        settings_row.pack_start(self.qemu_disk_spin, False, False, 0)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content.pack_start(button_row, False, False, 0)
        self.qemu_start_button = Gtk.Button(label="Start Test VM")
        self.qemu_start_button.get_style_context().add_class("suggested-action")
        self.qemu_start_button.connect("clicked", self.on_qemu_start)
        button_row.pack_start(self.qemu_start_button, False, False, 0)
        self.qemu_stop_button = Gtk.Button(label="Stop VM (destroys it)")
        self.qemu_stop_button.set_sensitive(False)
        self.qemu_stop_button.connect("clicked", self.on_qemu_stop)
        button_row.pack_start(self.qemu_stop_button, False, False, 0)

        self.qemu_status_label = Gtk.Label(xalign=0.0)
        content.pack_start(self.qemu_status_label, False, False, 0)

        self.qemu_display_area = Gtk.Frame()
        self.qemu_display_area.set_shadow_type(Gtk.ShadowType.IN)
        self.qemu_placeholder = Gtk.Label(label="VM not running.")
        self.qemu_placeholder.set_vexpand(True)
        self.qemu_placeholder.set_hexpand(True)
        self.qemu_display_area.add(self.qemu_placeholder)
        content.pack_start(self.qemu_display_area, True, True, 0)

        return box

    def on_qemu_start(self, _button):
        if self.qemu_session is not None:
            return
        iso_path = find_iso()
        if not iso_path:
            self.qemu_status_label.set_text("No pearOS *.iso found in the repository root.")
            return
        ovmf_code, ovmf_vars = find_ovmf()
        if not ovmf_code or not ovmf_vars:
            self.qemu_status_label.set_text("OVMF firmware not found -- install edk2-ovmf.")
            return

        session = QemuTestSession(
            iso_path,
            ram_mib=int(self.qemu_ram_spin.get_value()),
            cpus=int(self.qemu_cpu_spin.get_value()),
            disk_gib=int(self.qemu_disk_spin.get_value()),
        )
        try:
            session.start()
        except Exception as exc:  # noqa: BLE001 - surface any failure to the user
            self.qemu_status_label.set_text(f"Failed to start: {exc}")
            return

        self.qemu_session = session
        self.qemu_start_button.set_sensitive(False)
        self.qemu_stop_button.set_sensitive(True)
        self.qemu_status_label.set_text(f"Starting {os.path.basename(iso_path)}...")

        self.qemu_watch_id = GLib.child_watch_add(session.process.pid, self._on_qemu_process_exited)
        self._qemu_connect_attempts = 0
        self.qemu_poll_id = GLib.timeout_add(300, self._poll_qemu_vnc)

    def _poll_qemu_vnc(self):
        session = self.qemu_session
        if session is None:
            return False
        self._qemu_connect_attempts += 1
        try:
            with socket.create_connection(("127.0.0.1", session.vnc_port), timeout=0.3):
                pass
        except OSError:
            if self._qemu_connect_attempts > 50:  # ~15s
                self.qemu_status_label.set_text("VM did not open its display in time.")
                return False
            return True

        self.qemu_vnc_widget = GtkVnc.Display()
        self.qemu_vnc_widget.set_hexpand(True)
        self.qemu_vnc_widget.set_vexpand(True)
        # Without this, the widget's minimum size locks to the VM's native
        # framebuffer resolution and the whole app window can't be
        # shrunk below that. Scaling lets the picture shrink/grow with
        # the widget instead of dictating the window's minimum size.
        self.qemu_vnc_widget.set_scaling(True)
        self.qemu_vnc_widget.set_size_request(1, 1)
        self.qemu_vnc_widget.set_pointer_grab(True)
        self.qemu_vnc_widget.set_keyboard_grab(True)
        self.qemu_display_area.remove(self.qemu_placeholder)
        self.qemu_display_area.add(self.qemu_vnc_widget)
        self.qemu_vnc_widget.show()
        self.qemu_vnc_widget.open_host("127.0.0.1", str(session.vnc_port))
        self.qemu_vnc_widget.grab_focus()
        self.qemu_status_label.set_text(
            f"Running ({session.ram_mib} MiB RAM, {session.cpus} CPUs, {session.disk_gib} GiB disk, "
            "click inside to grab keyboard/mouse -- release with Ctrl+Alt)."
        )
        self.qemu_poll_id = None
        return False

    def on_qemu_stop(self, _button):
        self._teardown_qemu("Stopped -- VM destroyed.")

    def _on_qemu_process_exited(self, _pid, _status):
        self.qemu_watch_id = None
        self._teardown_qemu("QEMU exited -- VM destroyed.")

    def _teardown_qemu(self, status_text):
        if self.qemu_poll_id is not None:
            GLib.source_remove(self.qemu_poll_id)
            self.qemu_poll_id = None
        if self.qemu_watch_id is not None:
            GLib.source_remove(self.qemu_watch_id)
            self.qemu_watch_id = None
        if self.qemu_session is not None:
            self.qemu_session.stop()
            self.qemu_session = None
        if self.qemu_vnc_widget is not None:
            self.qemu_display_area.remove(self.qemu_vnc_widget)
            self.qemu_vnc_widget = None
            self.qemu_display_area.add(self.qemu_placeholder)
        self.qemu_start_button.set_sensitive(True)
        self.qemu_stop_button.set_sensitive(False)
        self.qemu_status_label.set_text(status_text)

    # ---------------------------------------------------------------- #
    # Page: Finish
    # ---------------------------------------------------------------- #
    def _build_finish_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(instruction_label("Finished."), False, False, 0)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_border_width(32)
        box.pack_start(content, False, False, 0)
        self.finish_label = Gtk.Label(xalign=0.0)
        self.finish_label.set_line_wrap(True)
        content.pack_start(self.finish_label, False, False, 0)
        self.command_summary_label = Gtk.Label(xalign=0.0)
        self.command_summary_label.set_line_wrap(True)
        self.command_summary_label.set_selectable(True)
        self.command_summary_label.get_style_context().add_class("monospace")
        content.pack_start(self.command_summary_label, False, False, 0)
        return box

    # ---------------------------------------------------------------- #
    # Dashboard info
    # ---------------------------------------------------------------- #
    def refresh_dashboard(self):
        iso_path = find_iso()
        if iso_path:
            size = human_size(os.path.getsize(iso_path))
            self.iso_label.set_text(f"{os.path.basename(iso_path)} ({size})")
            if hasattr(self, "qemu_iso_label"):
                self.qemu_iso_label.set_text(f"ISO: {os.path.basename(iso_path)} ({size})")
        else:
            self.iso_label.set_text("none found")
            if hasattr(self, "qemu_iso_label"):
                self.qemu_iso_label.set_text("ISO: none found")
        if hasattr(self, "start_qemu_button"):
            self.start_qemu_button.set_visible(iso_path is not None)
        if hasattr(self, "start_usb_button"):
            self.start_usb_button.set_visible(iso_path is not None)
        if hasattr(self, "start_publish_button"):
            self.start_publish_button.set_visible(iso_path is not None)
        if hasattr(self, "remove_iso_button"):
            self.remove_iso_button.set_visible(iso_path is not None)
        if hasattr(self, "clean_project_shortcut_button"):
            self.clean_project_shortcut_button.set_visible(
                os.path.isdir(os.path.join(REPO_ROOT, "work"))
            )

        try:
            out = subprocess.run(
                ["lsblk", "-d", "-o", "NAME,SIZE,TRAN"], capture_output=True, text=True, check=False
            ).stdout
        except FileNotFoundError:
            out = ""
        usb_lines = [line for line in out.splitlines()[1:] if "usb" in line.lower()]
        text = "\n".join(usb_lines) if usb_lines else "none detected"
        self.usb_label.set_text(text)
        if hasattr(self, "usb_devices_label"):
            self.usb_devices_label.set_text(text)

        status, detail = find_existing_airootfs()
        if hasattr(self, "airootfs_label"):
            if status == "confirmed":
                self.airootfs_label.set_text(detail)
            elif status == "unknown":
                self.airootfs_label.set_text(f"{detail} (root-owned, in progress -- can't inspect from here)")
            else:
                self.airootfs_label.set_text("none found")
        if hasattr(self, "chroot_detect_label"):
            # The button stays enabled regardless of what we can see here:
            # build-binary's own check runs as root and is the one that
            # actually matters. This is purely informational.
            if status == "confirmed":
                self.chroot_detect_label.set_text(f"Found: {detail}")
            elif status == "unknown":
                self.chroot_detect_label.set_text(
                    f"./work/{detail} exists but is root-owned (a build may be running or just "
                    "finished) -- this process can't check inside it, but \"Chroot now\" runs as "
                    "root via sudo and will find it fine."
                )
            else:
                self.chroot_detect_label.set_text(
                    "No existing ./work found -- build first (Build page), or with --chroot mid-build."
                )
            self.chroot_only_button.set_sensitive(True)

        if hasattr(self, "start_console_button"):
            self.start_console_button.set_visible(status in ("confirmed", "unknown"))

    # ---------------------------------------------------------------- #
    # Navigation
    #
    # Gtk.Stack.get_visible_child_name() returns None until the stack is
    # realized (first show_all()), so page state is tracked in Python
    # instead of queried back from the widget.
    # ---------------------------------------------------------------- #
    def _goto(self, name):
        self._current_page = name
        self.stack.set_visible_child_name(name)

    def _current_index(self):
        return PAGE_ORDER.index(self._current_page)

    def update_nav(self):
        page = self._current_page
        idx = self._current_index()
        # Back is disabled only while the build pipeline is actually
        # running (page == TERMINAL and still active) -- everywhere else,
        # including the QEMU test page, you can navigate freely.
        self.back_button.set_sensitive(idx > 0 and not (page == PAGE_TERMINAL and self.session_active))
        if page == PAGE_COMPRESSION:
            self.next_button.set_label("Build")
            self.next_button.set_sensitive(True)
        elif page == PAGE_TERMINAL:
            self.next_button.set_label("Next")
            self.next_button.set_sensitive(not self.session_active)
        elif page == PAGE_FINISH:
            self.next_button.set_label("Start Over")
            self.next_button.set_sensitive(True)
        else:
            self.next_button.set_label("Next")
            self.next_button.set_sensitive(True)

    def on_back(self, _button):
        if self._current_page == PAGE_QEMU and getattr(self, "_qemu_from_start", False):
            # Reached QEMU via the Start page's "Start QEMU Test" shortcut,
            # not through the normal wizard sequence -- Terminal (QEMU's
            # PAGE_ORDER predecessor) was never actually visited, so Back
            # should return to where this actually started.
            self._qemu_from_start = False
            self._goto(PAGE_START)
            self.update_nav()
            return
        if self._current_page == PAGE_UPLOAD and getattr(self, "_upload_from_start", False):
            # Reached Upload via the Start page's "Publish" shortcut, not
            # through the normal wizard sequence -- return to Start rather
            # than USB (Upload's PAGE_ORDER predecessor), which was never
            # actually visited.
            self._upload_from_start = False
            self._goto(PAGE_START)
            self.update_nav()
            return
        if self._current_page == PAGE_TERMINAL and getattr(self, "_chroot_shortcut_origin", None):
            # Landed on Terminal via one of the chroot shortcuts (Start
            # page's "Start Airootfs Console", Chroot page's "Chroot now",
            # or Repos page's auto-jump when an airootfs already exists) --
            # those all skip straight to Terminal, bypassing whatever
            # PAGE_ORDER says comes right before it, so Back needs to
            # return to wherever the shortcut was actually clicked from.
            origin = self._chroot_shortcut_origin
            self._chroot_shortcut_origin = None
            self._goto(origin)
            self.update_nav()
            return
        idx = self._current_index()
        if idx > 0:
            self._goto(PAGE_ORDER[idx - 1])
        self.update_nav()

    def on_next(self, _button):
        page = self._current_page
        if page == PAGE_QEMU:
            self._qemu_from_start = False
        if page == PAGE_TERMINAL:
            self._chroot_shortcut_origin = None

        if page == PAGE_START and find_existing_airootfs()[0] in ("confirmed", "unknown"):
            # Dirty-build entry point (./work already exists): per
            # for_claude.txt, Next from Welcome itself skips straight past
            # Profiledef/Packages/Repos/Customize into the chroot shell,
            # same as the Start page's "Start Airootfs Console" button.
            # With no existing airootfs there's nothing to chroot into
            # yet, so this falls through to the normal fresh-build flow.
            self._chroot_shortcut(PAGE_START)
        elif page == PAGE_CUSTOMIZE:
            # Fresh-build entry into the chroot phase: pacstrap runs
            # quietly, then --chroot drops you straight into the shell
            # (build-binary always stops right after, before touching the
            # squashfs/ISO -- see check_chroot_request). Filename/sha256/
            # compression have no effect on this run (it stops before an
            # ISO is ever produced) -- those are decided AFTER coming back
            # out, on Build/Compression, so leave them out here entirely
            # rather than pass values build-binary would just ignore.
            profile = self.profile_entry.get_text().strip() or "pear"
            self.launch_session(["--build", "--profile", profile, "--chroot"])
        elif page == PAGE_TERMINAL and "--chroot" in getattr(self, "_last_launch_args", []):
            # Manual Next click while still parked on Terminal after a
            # chroot phase (pacstrap+chroot, or dirty-build's standalone
            # chroot) -- matches what on_child_exited already does when
            # that session ends on its own: go straight to Build (the
            # ISO isn't built yet either way, see check_chroot_request /
            # cli_chroot in build-binary).
            self.chroot_check.set_active(False)
            self.build_check.set_active(True)
            self._goto(PAGE_BUILD)
        elif page == PAGE_COMPRESSION:
            # Compression is the last settings page before the ISO
            # actually gets built, for both the fresh and dirty-build
            # paths -- always launches. chroot is never part of this
            # launch (it already happened, in an earlier separate run);
            # USB/upload aren't part of it either.
            self.launch_session()
        elif page == PAGE_FINISH:
            self.refresh_dashboard()
            self._goto(PAGE_START)
        else:
            idx = self._current_index()
            next_page = PAGE_ORDER[idx + 1]
            self._goto(next_page)
            if next_page == PAGE_CUSTOMIZE:
                self._load_customize_script()
            elif next_page == PAGE_QEMU:
                self.refresh_dashboard()
            elif next_page == PAGE_UPLOAD:
                self._refresh_cdn_files()
        self.update_nav()

    # ---------------------------------------------------------------- #
    # Terminal session -- Vte owns the pty, no scripting of prompts
    # ---------------------------------------------------------------- #
    def launch_session(self, args=None):
        args = self.build_args() if args is None else args
        if not args:
            # No flags at all means build-binary opens its interactive
            # menu instead of doing anything -- this GUI has nothing
            # driving that menu (no automation, no --chroot-style
            # determinism), so it would just sit there stuck. Refuse
            # instead of spawning it.
            self.terminal_status.set_text("Nothing selected -- pick an action first.")
            return
        argv = ["sudo", "--", BUILD_BINARY] + args
        cmd_text = " ".join(shlex.quote(a) for a in argv)
        self._last_launch_args = args
        # --chroot always means "this session is a chroot shell, not a
        # finished/finishing build" now (build-binary stops right after
        # the shell exits either way -- see check_chroot_request /
        # cli_chroot), regardless of whether --build is also present.
        self._chroot_present_session = "--chroot" in args
        # Reset here, not just after shortcuts: a normal (non-shortcut)
        # launch must not inherit a stale origin from an earlier chroot
        # shortcut. _chroot_shortcut() re-sets this right after calling
        # launch_session(), for the shortcut case.
        self._chroot_shortcut_origin = None
        self._upload_from_start = False

        self.vte.reset(True, True)
        self.terminal_status.set_text("Running: " + cmd_text)
        self.command_summary_label.set_text(cmd_text)
        self.stop_button.set_label("Stop")
        stop_ctx = self.stop_button.get_style_context()
        stop_ctx.remove_class("suggested-action")
        stop_ctx.add_class("destructive-action")
        self.stop_button.set_sensitive(True)
        self.session_active = True

        self.vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            REPO_ROOT,
            argv,
            [],
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            self._on_spawn_complete,
        )

        self._goto(PAGE_TERMINAL)
        self.vte.grab_focus()
        self.update_nav()

    def _on_spawn_complete(self, terminal, pid, error):
        if error:
            self.terminal_status.set_text(f"Failed to launch: {error}")
            self.session_active = False
            self.stop_button.set_sensitive(False)
            self.update_nav()
            return
        self.child_pid = pid

    def on_stop(self, _button):
        if getattr(self, "_chroot_present_session", False) and self.session_active:
            # Send "exit" through the pty instead of SIGTERM'ing the
            # process tree. arch-chroot bind-mounts /dev, /proc, /sys
            # (the REAL host ones) into airootfs for the duration of the
            # shell and unmounts them in its own cleanup on a normal
            # shell exit; killing it abruptly races that cleanup and can
            # leave e.g. the host's real /dev bind-mounted at
            # work/.../airootfs/dev, silently shared with the live
            # system from then on ("umount: target is busy" is exactly
            # this happening). Ctrl+C first clears any foreground command
            # so `exit` lands on a fresh prompt either way. This behaves
            # identically to the user typing "exit" themselves --
            # on_child_exited does the actual navigation once the shell
            # process exits.
            self.vte.feed_child(b"\x03")
            GLib.timeout_add(
                150,
                lambda: (self.vte.feed_child(b"history -c && history -w && exit\r"), False)[1],
            )
            self.terminal_status.set_text("Exiting chroot...")
            return

        if self.child_pid:
            try:
                os.kill(self.child_pid, 15)
            except ProcessLookupError:
                pass

    def on_child_exited(self, _terminal, exit_code):
        exit_code = decode_wait_status(exit_code)
        self.session_active = False
        self.child_pid = None

        self.stop_button.set_sensitive(False)
        self.terminal_status.set_text(f"Finished (exit code {exit_code})")

        args = getattr(self, "_last_launch_args", [])
        chroot_present = "--chroot" in args

        if exit_code == 0:
            self.finish_label.set_text("build-binary exited normally (code 0).")
        else:
            self.finish_label.set_text(
                f"build-binary exited with code {exit_code}. Check the terminal "
                "output on the previous page for details."
            )

        if chroot_present:
            # --chroot (with or without --build) always stops right after
            # the chroot shell exits -- it never builds the squashfs/ISO
            # in this same run (see check_chroot_request / cli_chroot in
            # build-binary). So this session never produced an ISO either
            # way: go to Build to decide filename/sha256/compression for
            # the SEPARATE run that will actually finish it. Not gated on
            # exit_code == 0: a bash shell commonly exits non-zero on
            # plain `exit` (last command's status), that's not a real
            # failure here -- any actual error was already visible live
            # while typing in the shell.
            self.chroot_check.set_active(False)
            self.build_check.set_active(True)
            self._goto(PAGE_BUILD)
        elif exit_code == 0 and "--build" in args:
            # A real build (no --chroot this time) just finished -- next
            # stop is testing it, not the end of the wizard.
            self._goto(PAGE_QEMU)
            self.refresh_dashboard()
        elif exit_code == 0:
            # Any other successful action (clean-project, a lone --usb or
            # --upload/--delete-cdn from a Start-page shortcut, the
            # publish-phase launch from the Upload page, etc.) has nothing
            # further to chain -- done.
            self._goto(PAGE_FINISH)
        # Any other failure: stay on the Terminal page so the error is visible.

        self.update_nav()


class ISOBuilderApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="xyz.pearos.isobuilder")

    def do_activate(self):
        win = ISOBuilderWindow(self)
        win.show_all()


def main():
    if os.geteuid() == 0:
        dialog = Gtk.MessageDialog(
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Do not run as root",
        )
        dialog.format_secondary_text(
            "Run this GUI as your normal user. It will ask for your sudo "
            "password (via sudo, directly in the terminal page) only when "
            "build-binary itself needs it."
        )
        dialog.run()
        raise SystemExit(1)
    app = ISOBuilderApp()
    app.run()


if __name__ == "__main__":
    main()
