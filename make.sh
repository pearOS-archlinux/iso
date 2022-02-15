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

if [ $(id -u) != 0 ]; then
     fn_noroot
 fi

# create out directory
create_out() {
	echo "Creating out directory..."
	mkdir -p out
	echo "Directory created."
}

# clean the project files (i.e. when want to push to gh)
clean_out() {
	echo "Cleaning the project folder..."
	rm -ri out
	echo "Project folder is clean."
}

# the ISO building script
actual_build() {
	start=`date +%s`
	./mkarchiso -v -w ./out -o . pear
	end=`date +%s`
	runtime=$((end-start))
	echo "The command was completed in $runtime s"
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
        create_out; actual_build
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
