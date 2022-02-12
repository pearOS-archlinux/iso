# PearISO
Build the (new) Arch-based pear iso.

## Packages:
* `pacman-contrib`
* `archiso`
That's all, I think

## Build ISO:
* `build_iso.sh`
* If you get an error about `/tmp/<something>` running out of space, reboot (to clear tmpfs), then edit the `WORKDIR=...` line to a regular dir name.
    * This (could) happen because the script is written to make a temp dir in `/tmp`, which is a virtual FS that lives in RAM.
    * If it happens to many people, we can just add a commandline arg to change `WORKDIR`