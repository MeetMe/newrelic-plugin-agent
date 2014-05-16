#!/bin/bash
exec /sbin/setuser postgres /usr/lib/postgresql/9.3/bin/postgres -k /tmp/postgresql -D /var/lib/postgresql/9.3/main -c config_file=/etc/postgresql/9.3/main/postgresql.conf >>/var/log/postgres.log 2>&1
