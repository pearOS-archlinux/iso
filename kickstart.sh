#!/usr/bin/env bash
set -e -u

# Clean, non-interactive ISO build: pear profile, no chroot, no USB, no CDN upload.
# End to end: wipe ./work, build ISO as testbuild-<version>-<arch>.iso, write sha256sum to ./sha.txt.
SCRIPT_DIR="$(cd -- "$(dirname -- "$(readlink -f -- "$0")")" && pwd)"

if [[ "${EUID}" -eq 0 ]]; then
    "${SCRIPT_DIR}/build-binary" --build --profile pear --filename testbuild --clean
else
    sudo "${SCRIPT_DIR}/build-binary" --build --profile pear --filename testbuild --clean
fi

iso_file=$(find "${SCRIPT_DIR}" -maxdepth 1 -name "testbuild-*.iso" -type f | head -1)
if [[ -n "${iso_file}" ]]; then
    sha256sum -- "${iso_file}" > "${SCRIPT_DIR}/sha.txt"
    cat "${SCRIPT_DIR}/sha.txt"
else
    echo "No testbuild ISO found for sha256" >&2
    exit 1
fi
