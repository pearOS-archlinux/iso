#! /bin/bash

sudo cp boot-sound.wav /boot/boot-sound.wav
sudo cp bootsound.service /etc/systemd/system/

sudo systemctl enable bootsound.service