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
	echo "Failed to remove plasma-welcome (arch)"
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
	sudo pacman-key --init
	if [ $? -ne 0 ]; then
		ask_continue "pacman-key --init failed"
	fi
fi

# Populate Arch Linux keys
echo "Populating Arch Linux GPG keys..."
sudo pacman-key --populate
if [ $? -ne 0 ]; then
	ask_continue "pacman-key --populate failed"
fi

sudo pacman-key --recv-keys 4C1A9F3C131ACA95 --keyserver keyserver.ubuntu.com
sudo pacman-key --lsign-key 4C1A9F3C131ACA95

# Re-enable exit on error
set -e

echo "Installing plasma-welcome patch"
if pacman -S --noconfirm plasma-welcome; then
        cp -r /usr/share/applications/welcome.desktop /etc/skel/.config/autostart/welcome.desktop ||:
	echo "plasma-welcome installed successfully"
else
	echo "Failed to install plasma-welcome (pearOS)"
fi

echo "Reinstalling plasma-workspace..."
#
# Some KDE Plasma theme packages (e.g. oxygen/oxygen-cursors) may ship
# overlapping files. Use --overwrite to avoid build-time aborts.
#
if pacman -S --noconfirm --overwrite='*' plasma-workspace; then
        echo "plasma-workspace installed successfully"
else
        echo "Failed to install plasma-workspace"
fi


echo "Fixing permissions"
if chmod -R 0777 /usr/share/extras/; then
        echo "Permissions set!"
else
        echo "Failed to set permissions"
fi



sleep 5


echo "Installing CMake"
if pacman -S --noconfirm cmake extra-cmake-modules; then
        echo "CMake and Extra CMake Modules Installed!"
else
        echo "Failed to install CMake + Extra Modules"
fi

echo "Downloading Liquid Gel"
if git clone https://github.com/pearOS-archlinux/liquid-gel; then
        echo "Liquid Gel Downloaded..."
else
        echo "Failed to download Liquid Gel"
fi

echo "Compiling Liquid Gel"
if cd liquid-gel && mkdir build && cd build && cmake .. -DCMAKE_INSTALL_PREFIX=/usr && make -j$(nproc) && sudo make install; then
        echo "Liquid Gel Compiled..."
else
        echo "Failed to Compile Liquid Gel - Build Failed"
fi



echo "Cleaning up pearOS Build"

rm -rf /usr/share/{doc,man,info,help}/*
pacman -Scc --noconfirm
if [ ! -L /sbin/init ]; then
    ln -sf /usr/lib/systemd/systemd /sbin/init
fi
echo "Cleanup"
if rm -rf liquid-gel; then
        echo "Finish cleanup"
else
        echo "Failed to Cleanup files"
fi

sleep 10
echo "==================="
echo "Script run complete"
echo "==================="
sync
