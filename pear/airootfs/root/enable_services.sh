#!/bin/bash
set -e
#cd pear/airootfs/etc/systemd/system/

# 1. Display Manager & Graphical Target
#ln -sv /usr/lib/systemd/system/graphical.target default.target
#ln -sv /usr/lib/systemd/system/sddm.service display-manager.service

# 2. Network Manager (NM)
mkdir -p multi-user.target.wants
#ln -sv /usr/lib/systemd/system/NetworkManager.service multi-user.target.wants/NetworkManager.service
#ln -sv /usr/lib/systemd/system/NetworkManager-wait-online.service network-online.target.wants/NetworkManager-wait-online.service
#ln -sv /usr/lib/systemd/system/NetworkManager-dispatcher.service dbus-org.freedesktop.nm-dispatcher.service

# 3. Printing (CUPS)
#ln -sv /usr/lib/systemd/system/cups.service multi-user.target.wants/cups.service
#ln -sv /usr/lib/systemd/system/cups.socket sockets.target.wants/cups.socket
#ln -sv /usr/lib/systemd/system/cups.path multi-user.target.wants/cups.path

# 4. Bluetooth
#ln -sv /usr/lib/systemd/system/bluetooth.service dbus-org.bluez.service
#mkdir -p bluetooth.target.wants
#ln -sv /usr/lib/systemd/system/bluetooth.service bluetooth.target.wants/bluetooth.service
#ln -sv /usr/lib/systemd/system/bluetooth.service multi-user.target.wants/bluetooth.service

# 5. Virtualization Support
ln -sv /usr/lib/systemd/system/vmtoolsd.service multi-user.target.wants/vmtoolsd.service
# VirtualBox
ln -sv /usr/lib/systemd/system/vboxservice.service multi-user.target.wants/vboxservice.service
ln -sv /usr/lib/systemd/system/qemu-guest-agent.service multi-user.target.wants/qemu-guest-agent.service

# 6. Power & System Management
ln -sv /usr/lib/systemd/system/power-profiles-daemon.service multi-user.target.wants/power-profiles-daemon.service
ln -sv /usr/lib/systemd/system/fprintd.service multi-user.target.wants/fprintd.service
