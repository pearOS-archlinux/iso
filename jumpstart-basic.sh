!#/bin/bash

# Simple Check to make sure it is executed as root
if [[ ! "$EUID" == "0" ]]; then
  echo "Run as root pls"
  exit 1
fi

# Install requirements
pacman -S --needed git make cmake linux-headers libreoffice vi vim python

# Install yay (to download from the aur repo)
cd /opt
sudo git clone https://aur.archlinux.org/yay-git.git
sudo chown -R $USER:$USER ./yay-git && cd yay-git
makepkg -si

# Install pacman GUI
yay -S pamac-aur

# Install gambas3 (required to run pearOS apps)
pacman -S gambas3

#get pear apps
#mkdir ~/pearApps
#cd ~/pearApps
#mkdir control-centre
#cd control-centre
#wget https://github.com/alxb421/Control-Centre/releases/download/11.0.1/xyz.pearos.control-centre_11.1.0_all.deb
#pacman -S fakeroot binutils
#yay -S debtap
#debtap -U
#package=$(xyz.pearos.control-centre_11.1.0_all.deb)
#debtap $package
#pacmanpkg=$(echo *.pkg.tar.xz)
#pacmanpkg=$(echo *.pkg.tar.zst)
#pacman -U $pacmanpkg
#cd ~/pearApps
#git clone https://github.com/alxb421/pext-installer.git
#cd pext-installer
#mv pext-installer /usr/share/
#cd pext-installer/system-update /tmp
#python /usr/share/pext-installer/pext-installer
#cd ~/pearApps
#git clone https://github.com/alxb421/piri-backend.git
#cd piri-backend
#chmod +x install.sh
#./install.sh
#cd ~/pearApps
#mkdir sys-overview
#cd sys-overview
#wget https://github.com/alxb421/system-overview/releases/download/11.0.1/xyz.pearos.system-overview_11.1.0_all.deb
#debtap -U
#pkg=$(xyz.pearos.system-overview_11.1.0_all.deb)
#debtap $pkg
#pacmanpkg=$(echo *.pkg.tar.xz)
#pacmanpkg=$(echo *.pkg.tar.zst)
#pacman -U $pacmanpkg
#cd~/pearApps
#mkdir updatemgr
#cd updatemgr
#wget https://github.com/alxb421/update-mgr/releases/download/11.1/xyz.pearos.update-mgr_11.1_all.deb
#debtap -U
#pckg=$(https://github.com/alxb421/update-mgr/releases/download/11.1/xyz.pearos.update-mgr_11.1_all.deb)
#debtap $pckg
#pacmanpkg=$(echo *.pkg.tar.xz)
#pacmanpkg=$(echo *.pkg.tar.zst)
#pacman -U $pacmanpkg
cd ~
#end
