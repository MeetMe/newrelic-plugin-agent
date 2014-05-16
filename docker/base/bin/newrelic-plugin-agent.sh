#!/bin/sh
sed -i 's/REPLACE_WITH_REAL_KEY/'$NEWRELIC_KEY'/g' /etc/newrelic/newrelic-plugin-agent.cfg
