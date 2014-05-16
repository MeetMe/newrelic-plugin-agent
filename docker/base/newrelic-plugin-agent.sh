#!/bin/bash
sed -i 's/REPLACE_WITH_REAL_KEY/'$NEWRELIC_KEY'/g' /etc/newrelic/newrelic-plugin-agent.cfg
exec /sbin/setuser newrelic /usr/local/bin/newrelic-plugin-agent -c /etc/newrelic/newrelic-plugin-agent.cfg -f
