#!/usr/bin/env bash
#This script runds inside airootfs chroot during build
# it's executed automatically by mkarchiso

set -e -u

echo "==========================="
echo "Customizing pearOS Live env"
echo "==========================="

echo "Setting OS release"
echo "pearOS" > /etc/arch-release && \
	echo "OS release updated" ||\
	echo "Failed to set OS release"

if command -v plymouth-set-default-theme &> /dev/null; then
	echo "Setting plymouth theme"
	plymouth-set-default-theme -R pear-plymouth && \
		echo "Success!" || \
		echo "Failed to set plymouth theme"
else
	echo "Plymouth command theme not found"
fi

echo "Removing stock plasma-welcome app"
if pacman -R --noconfirm plasma-welcome; then
	echo "Stock plasma-welcome removed OK"
else
	echo "Failes to remove plasma-welcome"
fi

sleep 5

echo "Installing plasma-welcome patch"
if pacman -S --noconfirm plasma-welcome; then
	echo "plasma-welcome installed successfully"
else
	echo "Failed to install plasma-welcome"
fi

echo "==================="
echo "Script run complete"
echo "==================="
