#!/bin/bash

inf() {
    echo "[I] - $1"
}

err() {
    echo "[E] - $1"
}

inf "Building all custom packages"
for directory in $(echo */); do
    if [[ ! "$directory" == "out" && ! "$directory" == "pear" ]]; then
        inf "Now building: $directory"
        pushd $directory
        if [[ -f create_package.sh ]]; then
            inf "Handing off to create script."
            ./create_package.sh
            inf "Script done."
        else
            inf "No special script found, running generic."
            updpkgsums && makepkg -s
        fi
        fn=$(echo *.pkg.tar.zst)
        if [[ ! "$fn" == "" ]]; then
            inf "Build of $directory was good. Moving $fn for upload"
            cp -v $fn ../out/.
        else
            err "Seems like $directory failed."
            err "Exiting."
            exit 1
        fi
        popd
    fi
done

if [[ -f aur-targets ]]; then
    inf "Finished building all Pear-* packages."
    inf "Starting build of AUR packages"
    inf "Checking for any old versions to purge"

    tgts=$(cat aur-targets)

    for tgt in $tgts; do
        if [[ -d $tgt ]]; then
            inf "Found old clone of $tgt. Removing."
            rm -rfv $tgt
        fi
    done

    inf "All cleaned up. Starting builds."
    for tgt in $tgts; do
        git clone https://aur.archlinux.org/${tgt}.git
        cd $tgt
        updpkgsums && makepkg -s
        fn=$(echo *.pkg.tar.zst)
        if [[ ! "$fn" == "" ]]; then
            inf "Build of $directory was good. Moving $fn for upload"
            cp -v $fn ../out/.
        else
            err "Seems like $directory failed."
            err "Exiting."
            exit 1
        fi
    done
else
    inf "No AUR target file found. We're done!"
    exit 0
fi

echo "We are completely done! :)"