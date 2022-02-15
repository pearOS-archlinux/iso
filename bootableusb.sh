#!/bin/bash
set -e
bold=$(tput bold)
normal=$(tput sgr0)
USB=""
clear
echo "
 ___ ____   ___    _          _   _ ____  ____                  _ _
|_ _/ ___| / _ \  | |_ ___   | | | / ___|| __ )  __      ___ __(_) |_ ___ _ __ 
 | |\___ \| | | | | __/ _ \  | | | \___ \|  _ \  \ \ /\ / / '__| | __/ _ \ '__|
 | | ___) | |_| | | || (_) | | |_| |___) | |_) |  \ V  V /| |  | | ||  __/ |   
|___|____/ \___/   \__\___/   \___/|____/|____/    \_/\_/ |_|  |_|\__\___|_|"
echo "this script was made by ${bold}Alexandru Balan${normal}"

printUSBDevices() {
  typeset -a usbDevices
  typeset -a devices
  getDeviceType() {
    typeset deviceName=/sys/block/${1#/dev/}
    typeset deviceType=$(udevadm info --query=property --path="$deviceName" | grep -Po 'ID_BUS=\K\w+')
    echo "$deviceType"
  }
  mapfile -t devices < <(lsblk -o NAME,TYPE | grep --color=never -oP '^\K\w+(?=\s+disk$)')
  for device in "${devices[0]}" ; do
    if [ "$(getDeviceType "/dev/$device")" == "usb" ]; then
      usbDevices+=("/dev/$device")
    fi
  done
  USB=$usbDevices
}
printUSBDevices
#echo $USB

# make the bootable usb
echo "Making pearOS Arch Base Bootable USB . . ."
sudo dd if=pearOS-NiceC0re-$(date +%Y.%m)-x86_64.iso of=$USB bs=4M status='progress' conv='sync'; sync
echo "Your bootable USB is ready!"
