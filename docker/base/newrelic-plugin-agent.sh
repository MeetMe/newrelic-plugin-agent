#!/bin/bash
exec /sbin/setuser newrelic /usr/local/bin/newrelic-plugin-agent -c /etc/newrelic/newrelic-plugin-agent.cfg -f
