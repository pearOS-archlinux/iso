#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="pearos-live"
iso_label="PEAR_$(date +%Y%m)"
iso_publisher="PearOS Linux <https://github.com/phoenix277yt/PearOS-arch>"
iso_application="PearOS Live"
iso_version="$(date +%Y.%m.%d)"
install_dir="arch"
bootmodes=('bios.syslinux.mbr' 'bios.syslinux.eltorito' 'uefi-x64.systemd-boot.esp' 'uefi-x64.systemd-boot.eltorito')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
file_permissions=()
