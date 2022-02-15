#!/bin/bash
set -e
cd pear/airootfs/etc/systemd/system/

# enable sddm
ln -sv /usr/lib/systemd/system/graphical.target default.target
ln -sv /usr/lib/systemd/system/sddm.service display-manager.service

# enable ew network manager
ln -sv /usr/lib/systemd/system/NetworkManager.service multi-user.target.wants/NetworkManager.service
ln -sv /usr/lib/systemd/system/NetworkManager-wait-online.service network-online.target.wants/NetworkManager-wait-online.service
ln -sv /usr/lib/systemd/system/NetworkManager-dispatcher.service dbus-org.freedesktop.nm-dispatcher.service

# enable printer
mkdir printer.target.wants
ln -sv /usr/lib/systemd/system/cups.service printer.target.wants/cups.service
ln -sv /usr/lib/systemd/system/cups.socket sockets.target.wants/cups.socket
ln -sv /usr/lib/systemd/system/cups.path multi-user.target.wants/cups.path

# enable bt
ln -sv /usr/lib/systemd/system/bluetooth.service dbus-org.bluez.service
mkdir bluetooth.target.wants
ln -sv /usr/lib/systemd/system/bluetooth.service bluetooth.target.wants/bluetooth.service
