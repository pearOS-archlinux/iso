#!/usr/bin/env bash
# Builds the ISO locally the same way CI does (privileged archlinux container),
# leaving pearOS-NiceC0re-<version>-x86_64.iso in the repo directory.
# Needs docker (run with sudo if your user is not in the docker group).
# The pacman package cache lives in the "pearos-pacman-cache" volume, so
# rebuilds only download what changed.
#
# Usage: tests/local-build.sh            # then: tests/boot-test.py pearOS-*.iso
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
DOCKER="docker"; docker ps >/dev/null 2>&1 || DOCKER="sudo docker"

$DOCKER run --rm --privileged --network host \
  -v "$ROOT":/work -w /work \
  -v pearos-pacman-cache:/var/cache/pacman/pkg \
  archlinux:latest bash -euxo pipefail -c '
    cp gh-actions/pacman.conf /etc/pacman.conf
    cp gh-actions/mirrorlist /etc/pacman.d/mirrorlist
    # Slow mirrors would otherwise abort the build ("Operation too slow").
    sed -i "/^\[options\]/a DisableDownloadTimeout" /etc/pacman.conf

    pacman-key --init
    pacman-key --populate archlinux
    pacman-key -a packages/pearos.gpg
    pacman-key --lsign-key 4C1A9F3C131ACA95
    pacman-key -a packages/inled.gpg
    pacman-key --lsign-key 89F828A9675B63CD0077CE9965AA57CF36E2018F

    # [cachyos] keyring comes from our own repo, signed with our key.
    awk "/^\[cachyos\]/{skip=1; next} /^\[/{skip=0} !skip" /etc/pacman.conf > /tmp/pacman-bootstrap.conf
    pacman -Sy --noconfirm --config /tmp/pacman-bootstrap.conf
    pacman -S --noconfirm --config /tmp/pacman-bootstrap.conf cachyos-keyring
    pacman-key --populate cachyos
    pacman -Sy --noconfirm

    pacman -Syu --noconfirm
    pacman -S --noconfirm archiso arch-install-scripts mtools dosfstools squashfs-tools \
      xorriso e2fsprogs git pv rclone
    git config --global --add safe.directory /work

    chmod +x ./kickstart.sh
    # Network hiccups happen; downloads are cached in the volume, so retrying is cheap.
    for attempt in 1 2 3; do
      ./kickstart.sh && break
      echo "build attempt $attempt failed, retrying"; rm -rf work; sleep 5
    done
    ls pearOS-*.iso
  '
# kickstart.sh rewrites sha.txt with the local build; do not commit that.
git -C "$ROOT" checkout -- sha.txt 2>/dev/null || true
ls -lh "$ROOT"/pearOS-*.iso
