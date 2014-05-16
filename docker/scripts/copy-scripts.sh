#!/bin/bash
mkdir -p /home/core/bin
rm /home/core/.bashrc
echo "export PATH=/home/core/bin:$PATH" > /home/core/.bashrc
cp /mnt/source/docker/scripts/* /home/core/bin

# Remove the setup scripts
rm /home/core/bin/*.sh

# Make sure the core user can execute the scripts
chown core:core /home/core/bin/*
chmod u+x /home/core/bin/*
