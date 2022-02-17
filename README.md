# pearOS-arch-base
This is pearOS but I had enough with debian-basd distros where "it uses a different distribution for the base with almost every release" or "switch between debian, kde neon and kubuntu"



# Deps:
```sh
sudo pacman -S mtools
sudo pacman -S squashfs-tools
sudo pacman -S pkgfile
sudo pkgfile --update
pkgfile pacstrap
sudo pacman -S extra/arch-install-scripts
```
