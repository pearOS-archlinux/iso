# `Last update: 11 Mar 2026, 04:38 PM`

# Changelog


## 11 Mar 2026
## Information
https://pearos.xyz

* Add Dual Boot Support
* Add Offline Installer Support(hold ⌥ while clicking Continue with Install pearOS selected in installer to enable Offline & Dualboot)
* Add Calculator App
* Add To-Do App
* Add Contacts App
* Add Notes App
* Add Calendar App
* Add Notch
* Add nVidia drivers
* Add Qemu Guest utils
* Add Better Wayland Support
* Add Close button will HIDE the app instead of closing(the bitten fruit way)
* Add Hover effects to the CLS/MIN/MAX buttons
* Fixed Better LiquidGel Rules
* Fixed Most of the rounded corners
* Fixed Launcher Dark Icon
* Fixed wrong Window Borders
* Fixed Piri Download Quota Exceeded
* About pearOS app: Switched from Electron to C++
* Switched ark -> file-roller

### Known Bugs
* Some WiFi cards are not working (?)
* automatic theme not yer implemented
* pearOS Notch Not working smoothly, expecting fix in 26.4
* Other bugs: Please use the Issues tab in this repo. Thank you

## 09 Feb 2026
## Information
https://pearos.xyz

* X11 -> Wayland
* Added Liquid Gel
* Added Touchpad Settings into Settings Application
* Added Pir Voice Assistant
* Added Profile Picture in installer & Lock Screen
* Added cusotm profile Picture (Requires pearID)
* New lockscren
* Custom Watch Fonts in lockscreen
* New Fonts in Setting > Wallpapers > Customise Clock Appearance
* Fixed installer
* UI fixes
* Fixed Dowloads Folder fan view effect
* ... probably more which I forgot to mention :)

### Known Bugs
* Some WiFi cards are not working
* automatic theme not yer implemented
* Other bugs: Please use the Issues tab in this repo. Thank you


## 11 Dec 2025
## Information
```
The ISO file is now on an S3 bucket so expect high download speeds now
This update features pearID and a new settings app, with various updates
```
https://pearos.xyz

* fix rubbish bin icon
* fix light theme
* fix plasmoids not working on plasma 6.5.3
* UPDATE plasma to 6.5.3 (previous: 6.3.x)
* WORKAROUND: Plasma 6.5 set Wayland as defaule, I forced it to X11
* NEW settings app
* NEW about app
* NEW global menu plasmoid
* NEW downloads folder with fan view effect
* NEW Finder-like icon in the dock
* NEW Dock rework
* NEW pearID

### Known bugs
* Some apps not working good on Wayland seessions(see workaround)
* Graphical BUG in  Settings > Game Center
* Sometimes on fresh installs theme is not applied properly. To fix this you have to
   get into System Settings > Appearance > and reapply a theme (dark/light)
* Automatic theme not yet implemented
* Other bugs: Please use the Issues tab in this repo. Thank you

## 31 October 2025

## Information
```
ISO file moved to the personal server, it is 3.3GB in size, and GitHub file size limitation is only 2 GB
```
https://pearos.xyz

* fixed installer (hopefully it should auto repair itself when a package breaks or a signature gets expired/revoked)
* fixed progress bar
* updated design
* updated broken packages
* updated package repository(github -> personal server)
* added boot sound
* added plymouth theme
* added Hello screen after install
* added Activity bar to the installer
* added (half broken) control center (WIP)
* updated kernel to 6.17_MANJARO
* updated to plasma 6
* updated to Tahoe design
* updated Splash Screen
* removed useless packages
* removed gambas dependency
* removed all previously made pearOS apps, new apps are coming soon

## 18 October 2023
* fixed the gnome package kit error
* updated packages
* refreshed keys

## 30 January 2023:
* fixed pearOS installer
* updated packages
* refreshed keys

## 9 August 2022:
* fixed failed install due to the wrong electron version ( `electron11` instead of `electron` package was installed)
## 5 July 2022:
* The installer no longer lets the user to install on a USB (resoves the 'I accidentally installed pearOS on the bootable usb instead of my HDD' problem)
* The installer no longer lets the user to install pearOS without an internet connection. (resolves the 'I pressed install, but it fails here is the install log alex' problem)

# How do I install?
1. Connect to the internet
2. Double click on the Install icon form dekstop
3. Select your installer language
4. Agree to the Arch Linux Terms and Conditions
5. Select your disk
5.1. If you have troubles finding your disk, use the options in the toolbar to get the device where you want to install
6. Confirm the install
7. Save log in case of error (Localted on `~/Desktop/` )
8. Reboot your machine. You can unplug your USB drive now
9. The Setup will ask you to set:
* System locale
* Keymap (also called `Keyboard Layout`). The standard keyboard found in most computers is the `English U.S.` layout
* Select your time zone (500+ available time-zones)
* Create your local computer account. Full name, user, password and password confirm are required in order to install pearOS
* Agree to the License Agreement of Arch Linux.
* The setup will commit your changes and will automatically reboot.

# Important:
* The installer will WIPE the selected disk as soon as you press Continue in the Disk Selector window(I could add the option to partition, but this is how Apple does: Wipe the entire disk, so I chose the same approach)
* This build might be unstable. 
* <b><i>Report all bugs here as an issue, or in DMs(instagram, discord, twitter) or by mail. To help improve pearOS quality, I need user's feedback!!</i></b>

# Note:
* ~~VMWare tools will be automatically installed after setup (if you are in VMWare)~~ need to check
* ~~VirtualBox Guest Additions will be automatically installed after setup (if you are in VirtualBox)~~  need to check
*<b> I am not responsible of any data loss that may occour during the (failed) installation. </b>

# Roadmap
 * Develop the pearOS Desktop Environment (named Soda)
 * ~~Switch to a GTK Desktop Environment until I finish developing the Soda DE(shortly: SDE)~~ Keeping KDE, SDE is Work in Progress, however don t expect it soon
 * Add a theme chooser in the post-install application -- Work in Progress
 * Add `Refresh Disks` button in the Disk Selector app -- Work in Progress
 * Develop piri (expected in 26.1) -- Work in Progress
 * Develop auto-theme. It changes based on the TOD (Time Of the Day) -- Work in Progress
 * ~~Pre-install `gparted` in the LIVE environment. Needed to format and manage boot disks~~ DONE
  * ~~Add disks label under `/dev/sdX` so the users will identify disks more easy~~ DONE
 * ~~Add error handling, so you will know when something goes wrong with the installer (added 'no internet' handler)~~ DONE

**Full Changelog**: https://github.com/pearOS-archlinux/iso/compare/v25.10...v25.12_relese_candidate
