#!/bin/bash
cp /mnt/source/docker/base/id_rsa* /home/core/.ssh/
chmod 0600 /mnt/source/docker/base/id_rsa
cp /mnt/source/docker/base/ssh_config /home/core/.ssh/config
chmod 0644 /mnt/source/docker/base/id_rsa.pub
chown -R core:core /home/core/.ssh