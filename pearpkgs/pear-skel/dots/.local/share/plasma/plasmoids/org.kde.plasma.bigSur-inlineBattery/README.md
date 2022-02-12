# mcOS BS Inline Battery
🔋 ***This is a fork of Kelvin Zhang's original Mac OSX Inline Battery.***

Subtle changes that makes a big difference.
I have made small modifications to make the battery icon look like the new macOS Big Sur, with its corners a little more rounded than the classic version of macOS.
I hope you like it and enjoy this new look at the battery icon on your top panel.

## Install
To install, first ***right click on the KDE desktop***, when the menu appears, choose the ***"Add Widgets"*** option, then the Widgets sidebar appears and at the bottom click ***"Get New Widget"*** and then ***"Download New Plasma Widget "***, a window will open and just search for the widget and then click ***"install "***.

Another way to install is to use the terminal, first download the ***".tar.gz"*** file from the link [mcOS BS Battery](https://www.pling.com/p/1402942/ "mcOS BS Battery"), then extract the compressed file and open a terminal to run the command, for example:

```
kpackagetool5 -t Plasma/Applet --install org.kde.plasma.bigSur-inlineBattery
```

## Development
To update the package from the terminal is a similar process, download the file, then unzip, open the terminal and run the command:
```
kpackagetool5 -t Plasma/Applet --upgrade org.kde.plasma.bigSur-inlineBattery
```

## Uninstall
If you want to uninstall the package run the command:
```
kpackagetool5 -t Plasma/Applet --remove org.kde.plasma.bigSur-inlineBattery
```
