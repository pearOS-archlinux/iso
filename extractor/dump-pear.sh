#!/usr/bin/zsh

un=$(whoami)

if [[ ! -d .config ]]; then
    mkdir .config
fi

if [[ ! -f .config/isoloc ]]; then
    if [[ "$1" == "" ]]; then
        printf "Path to Pear ISO: "
        read ISOP
    else
        ISOP=$1
    fi

    echo $ISOP >> .config/isoloc
else
    ISOP=$(cat .config/isoloc)
fi

OUTF=dump/

loopdev=$(sudo losetup -Pf --show ${ISOP})
mntpt=$(mktemp -d)
sudo mount ${loopdev}p1 ${mntpt}

if [[ ! -d $OUTF ]]; then
    mkdir -p $OUTF
fi

sudo cp -rv ${mntpt}/* ${OUTF}/.
sudo chown -R ${un}:${un} ${OUTF}/*
sudo umount ${mntpt}
sudo rm -rf $mntpt

echo "Contents of ${ISOP} extracted to $OUTF"