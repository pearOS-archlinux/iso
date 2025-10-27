# pearOS Installer made in Electron
This is work in progress. Installer may fail and you will end up with no system installed

# How do I run this?
Open a terminal and:
```sh
cd system-install
make
```

# What it does?
Installs the system on the selected disk.
Extremly important: it will use the <b>WHOLE</b> disk.
All the data in the selected disk will be <b>erased</b> in the moment you press `Continue`
Looks a lot like the macOS's installer

# Current state
Various tests are done to this app

# Contributors:
- zhovner(base of the UI, made in electron. It is highly modified, not even 10% of zhovner's code is stil present, but *someone* wants me to mention that xd)
- @jorgeluiscarrillo (the Install script. It is EXTREMLY modified, I used only the coding structure from this, but still, *someone* can report this as *stolen code* :) )
