#!/usr/bin/env bash
#This script runds inside airootfs chroot during build
# it's executed automatically by mkarchiso

set -e -u

# Function to ask for continuation on error
ask_continue() {
	local error_msg="$1"
	echo ""
	echo "ERROR: $error_msg"
	echo ""
	read -p "Do you want to continue? (y/N): " answer < /dev/tty
	if [[ ! "$answer" =~ ^[Yy]$ ]]; then
		echo "Aborting script execution..."
		exit 1
	fi
	echo "Continuing..."
}

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

echo "############################################################################################################################"
echo "###						REGENERATING PACMAN KEYS					       ###"
echo "############################################################################################################################"
# Ensure gnupg directory exists with correct permissions
mkdir -p /etc/pacman.d/gnupg
chmod 700 /etc/pacman.d/gnupg

# Temporarily disable exit on error for pacman-key operations
set +e

# Initialize pacman keyring if it doesn't exist
if [ ! -d /etc/pacman.d/gnupg/private-keys-v1.d ] || [ ! -f /etc/pacman.d/gnupg/pubring.gpg ]; then
	echo "Initializing pacman keyring..."
	pacman-key --init
	if [ $? -ne 0 ]; then
		ask_continue "pacman-key --init failed"
	fi
fi

# Populate Arch Linux keys
echo "Populating Arch Linux GPG keys..."
pacman-key --populate archlinux
if [ $? -ne 0 ]; then
	ask_continue "pacman-key --populate archlinux failed"
fi

# Re-enable exit on error
set -e

echo "Installing plasma-welcome patch"
if pacman -S --noconfirm plasma-welcome; then
        cp -r /usr/share/applications/welcome.desktop /etc/skel/.config/autostart/welcome.desktop
	echo "plasma-welcome installed successfully"
else
	echo "Failed to install plasma-welcome"
fi


echo "############################################################################################################################"
echo "###                                               Forcing X11 on build                                                   ###"
echo "############################################################################################################################"
#rm -rf /usr/share/wayland-sessions || :
echo "Testing with Wayland by default, might remove X11 later if everything OK!"
sleep 5




echo "==================="
echo "Script run complete"
echo "==================="
