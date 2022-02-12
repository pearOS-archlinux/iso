#!/bin/bash
# This file is run via mkarchiso while chrooted as the new system
echo "We're in the new system. :)"
echo "Performing minor tweaks"
sed -i 's/Arch/PearOS/g' /etc/issue
sed -i 's/Arch/PearOS/g' /etc/arch-release
sed -i 's/Arch/PearOS/g' /etc/os-release
echo "PearOS-Live" > /etc/hostname
# We don't add carly until here so that our packages which change
# /etc/skel have been installed already
/usr/bin/useradd -m carly
/usr/bin/usermod -p $(echo "pear" | openssl passwd -6 -stdin) carly
/usr/bin/chmod +x /home/carly/.xinitrc
echo "Configured the 'carly' user. Exiting chroot."