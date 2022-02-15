#!/bin/bash
set -e

### Colors ##
ESC=$(printf '\033') RESET="${ESC}[0m" BLACK="${ESC}[30m" RED="${ESC}[31m"
GREEN="${ESC}[32m" YELLOW="${ESC}[33m" BLUE="${ESC}[34m" MAGENTA="${ESC}[35m"
CYAN="${ESC}[36m" WHITE="${ESC}[37m" DEFAULT="${ESC}[39m"
### Color Functions ##
greenprint() { printf "${GREEN}%s${RESET}\n" "$1"; }
blueprint() { printf "${BLUE}%s${RESET}\n" "$1"; }
redprint() { printf "${RED}%s${RESET}\n" "$1"; }
yellowprint() { printf "${YELLOW}%s${RESET}\n" "$1"; }
magentaprint() { printf "${MAGENTA}%s${RESET}\n" "$1"; }
cyanprint() { printf "${CYAN}%s${RESET}\n" "$1"; }
fn_bye() { echo "Program terminated: [user_quit]"; exit 0; }
fn_fail() { echo "Program terminated: [wrong_option]"; exit 1; }
fn_noroot() { echo "Program terminated: [user_notroot]"; exit 1; }

OUT="./build_$RANDOM"

# the ISO building script
actual_build() {
	# start a simple timer
	start=`date +%s`

	# creates randomly named dir. This tool uses it as cache so it needs to be removed many time by hand.
	mkdir -p $OUT

	# copy files from packages dir to where arch needs them
	cp -r packages/pacman.out pear/pacman.conf
	cp -r pear/pacman.conf pear/airootfs/etc/.
	cp packages/packages.x86_64 pear/airootfs/etc/packages.x86_64
	cp /etc/pacman.d/mirrorlist pear/airootfs/etc/pacman.d/.

	# makes iso
	sudo ./mkarchiso -v -w $OUT -o . pear

	# ends the timer, calculates time ended minus time started, printing result in seconds
	end=`date +%s`
	runtime=$((end-start))
	echo "The command was completed in $runtime s"

	# make current user the owner of the iso file
	sudo chown $USER:$USER *.iso
}

mainmenu() {
    echo -ne "
$(magentaprint 'MAIN MENU')
$(greenprint '1)') Build ISO file
$(magentaprint '2)') Clean the Build Directory (! Removes ISO ! )
$(redprint '0)') Exit
Choose an option:  "
    read -r ans
    case $ans in
    1)
        actual_build
        ;;
    2)  clean_out
	;;
    0)
        fn_bye
        ;;
    *)
        fn_fail
        ;;
    esac
}

mainmenu
