#!/bin/bash

echo "midstep.sh started."

echo "Chrooting to $1, and running chrooted.sh"
cp chrooted.sh ${1}/.
chmod +x ${1}/chrooted.sh
chroot $1 /bin/bash -c ./chrooted.sh

echo "midstep.sh completed."