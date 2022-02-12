#!/bin/bash

rm *.tar.*

tar -cvzf resources.tar.gz extras
updpkgsums && makepkg -s
rm -rfv pkg src