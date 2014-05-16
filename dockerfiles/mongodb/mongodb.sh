#!/bin/sh
consulate register check 10 /usr/local/bin/check-mongodb mongodb 27017
exec /sbin/setuser mongodb /usr/bin/mongod --dbpath /var/lib/mongodb/ >>/var/log/mongodb.log 2>&1
