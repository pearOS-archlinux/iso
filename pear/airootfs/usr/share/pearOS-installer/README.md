# pere os instaler uwu
This is work in progress. Not my fault if your disk gets erased :)

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
I added installation progress:)

# Current state
Various tests are done to this app
Going to add the POST INSTALL thins(like selecting OS language, username etc.

# License and copyrights:
This project is released under the PPL v2 License and later, which can be found on https://github.com/Pear-Project
The Electron Framework is released under the MIT license
The original arch install script is released under the GPL v3 license.

## Note:
The arch install script was a Terminal UI installer. The number of lines of that code, was `1207` lines. I then edited the script to make it command line interface (it uses $1 as arguments), removef the graphical Dialog, split up the code in 2 parts. Now it has ~220 lines of code:)) <sub><sub><sub><sub><sub><sub>is this what you want me to do, amy?</sub></sub></sub></sub></sub></sub>

# Contributors:
- Alexandru Balan (developing and modifying most of the code)
- ~~equal (cleaning the code, some UI adjustments)~~ I did not commit his work, closed pull request
- zhovner(base of the UI, made in electron. It is highly modified, not even 10% of zhovner's code is stil present, but *someone* wants me to mention that xd)
- @jorgeluiscarrillo (the Install script. It is EXTREMLY modified, I used only the coding structure from this, but still, *someone* can report this as *stolen code* :) )
- GitHub(developing the Electron Framework)
- Microsoft (maintaining and developing GitHub)
