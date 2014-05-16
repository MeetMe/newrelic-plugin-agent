#!/bin/bash

IFS=$'\n';
echo
echo "Container Name                 IP Address"
echo "-----------------------------------------------"
for CONTAINER in `docker ps | awk '{print $(NF)}' | tail -n+2`
do
  IFS=,
  C=($CONTAINER)
  IP=`docker inspect --format '{{ .NetworkSettings.IPAddress }}' ${C}`
  echo "$C $IP" | awk '{printf "%-30s %-20s\n", $1, $2}'
done
echo