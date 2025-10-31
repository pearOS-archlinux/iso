<div align='center'>
<p align="center">
  <img src="https://user-images.githubusercontent.com/72302254/154438822-2cc5e98a-02eb-4655-ab31-59a39eb35f5a.png" alt="drawing" width="200"/>
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

> "it uses a different distribution for the base with almost every release"

> "this require you to reinstall with every new release"

> "sudo apt upgrade would/will destroy your installation"

> "if they really don't have the money, they just shouldn't have used the third party host"

> "They use the macos icons and are making money off of it"

Not anymore. With arch, there no more base-hopping
Now, with arch, the system is now Rolling Release, as it should be :>

( fixed in the latest debian builds but eh")
You can do now `sudo pacman -Syu` and you will stil have the pearOS branding.
With the new Arch base, the system is 2GB in size!! Good enough to save storage space on what I call the pearOS CDN.
I heard that too! I do not make money from macOS icons but I changed them in NiceC0re anyways!!

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

Copyright: Alexandru Balan @ The Pear Project
