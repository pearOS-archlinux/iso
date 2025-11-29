<div align='center'>
<p align="center">
  <img width="300" height="300" src="https://github.com/user-attachments/assets/c6bec808-b8b5-42a6-a459-e05656e47c3c" />
  </p>
<img src='https://img.shields.io/github/v/release/pearOS-archlinux/iso?color=%23FDD835&label=version&style=for-the-badge'>

</a>
  
<img src='https://img.shields.io/github/license/pearOS-archlinux/iso?style=for-the-badge'>
  
</a>

  <p><a href="https://discord.gg/QJPetvVhUb"><img alt="Discord" src="https://discordapp.com/api/guilds/697456171631509515/widget.png?style=banner2"?link=https://discord.gg/yp4xpZeAgW&link=https://discord.gg/yp4xpZeAgW> </a></p>
  
</div>

<br />

---


# pearOS-arch-base 📌
It is pearOS, but with Arch Base. Yes! It uses vanilla arch, less bugs, easier, better etc.

## Why? 📌
I had enough with debian-based distros.
pearOS with arch base, solve some of the big problems with pearOS, for example:

> "this require you to reinstall with every new release"

> "sudo apt upgrade would/will destroy your installation"

Not anymore. With arch, there no more base-hopping
Now, with arch, the system is now Rolling Release, as it should be :>

You can do now `sudo pacman -Syu` and you will stil have the pearOS branding.

## Ok... How do I build it? 📌
Make sure you satisfy the deps in the section below.
After that, run `./build-binary` and ~~pray~~ wait.


### Deps: 📌
```sh
sudo pacman -S mtools
sudo pacman -S squashfs-tools
sudo pacman -S pkgfile
sudo pacman -S xorriso
sudo pkgfile --update
pkgfile pacstrap
sudo pacman -S extra/arch-install-scripts
```

## Copyright and Licensing  📌
This project is released under the GNU Pubilc License v3 or later

Copyright: Alexandru Balan @ Pear Software and Services S.R.L. based in Romania, Dacia Boulevard 133, floor D, Sector 2, Bucharest CIF: 50888207
