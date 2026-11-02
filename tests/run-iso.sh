#!/usr/bin/env bash
# Opens an ISO in a QEMU window (UEFI, 16 GB, KVM, mouse, user networking) so you
# can watch the real boot. Usage: tests/run-iso.sh path/to.iso
set -euo pipefail
ISO="${1:?usage: $0 file.iso}"
for f in /usr/share/edk2/x64/OVMF_CODE.4m.fd /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd; do [ -e "$f" ] && CODE=$f && break; done
for f in /usr/share/edk2/x64/OVMF_VARS.4m.fd /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd; do [ -e "$f" ] && VARS=$f && break; done
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cp "$VARS" "$TMP/vars.fd"
exec qemu-system-x86_64 -machine q35,accel=kvm -cpu host -m 16G -smp 4 \
  -vga std -display gtk -device qemu-xhci -device usb-tablet -nic user \
  -drive if=pflash,format=raw,readonly=on,file="$CODE" -drive if=pflash,format=raw,file="$TMP/vars.fd" \
  -cdrom "$ISO" -boot d -name "pearOS test VM"
