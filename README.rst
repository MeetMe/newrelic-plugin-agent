NewRelic Plugin Agent
=====================

An agent that polls supported backend systems and submits the results to the
NewRelic platform. Currently supported backend systems are:

- Alternative PHP Cache
- Apache HTTP Server
- CouchDB
- Elasticsearch
- HAProxy
- Memcached
- MongoDB
- Nginx
- pgBouncer
- PHP FPM
- PostgreSQL
- RabbitMQ
- Redis
- Riak
- uWSGI

Base Requirements
-----------------
The agent requires Python 2.6 or 2.7 and ``pip`` for installation. Individual plugin backends may require additional libraries and are detailed below.

Configuration File Note
-----------------------
The configuration file uses YAML as its format. Most tickets for non-working installs are due to configuration file formatting errors. Please make sure you are properly formatting your configuration file prior to submitting a ticket. YAML is a whitespace dependent markup format. More information on writing proper YAML can be found at http://yaml.org.

Installation Instructions
-------------------------
1. Install via ``pip`` *:

::

    $ pip install newrelic-plugin-agent

* See ``pip`` installation instructions at http://www.pip-installer.org/en/latest/installing.html

2. Copy the configuration file example from ``/opt/newrelic-plugin-agent/newrelic-plugin-agent.cfg`` to ``/etc/newrelic/newrelic-plugin-agent.cfg`` and edit the configuration in that file.

3. Make a ``/var/log/newrelic`` directory and make sure it is writable by the user specified in the configuration file

4. Make a ``/var/run/newrelic`` directory and make sure it is writable by the user specified in the configuration file

5. Run the app:

::

    $ newrelic-plugin-agent -c PATH-TO-CONF-FILE [-f]

Where ``-f`` is to run it in the foreground instead of as a daemon.

Sample configuration and init.d scripts are installed to ``/opt/newrelic-plugin-agent`` in addition to a PHP script required for APC monitoring.

Installing Additional Requirements
----------------------------------

To use the MongoDB the ``mongodb`` library is required. For the pgBouncer or PostgreSQL plugin you must install the ``psycopg2`` library. To easily do
this, make sure you have the latest version of ``pip`` installed (http://www.pip-installer.org/). This should be done after installing the agent itself:

::

    $ pip install newrelic-plugin-agent[mongodb]

or::

    $ pip install newrelic-plugin-agent[pgbouncer]

or::

    $ pip install newrelic-plugin-agent[postgresql]

If this does not work for you, make sure you are running a recent copy of ``pip`` (>= 1.3).

Plugin Configuration Stanzas
----------------------------
Each plugin can support gathering data from a single or multiple targets. To support multiple targets for a plugin, you create a list of target stanzas:

::

    plugin_name:
      - name: target_name
        host: localhost
        foo: bar
      - name: target_name
        host: localhost
        foo: bar

While you can use the multi-target format for a plugin's configuration stanza like:

::

    plugin_name:
      - name: target_name
        host: localhost
        foo: bar

You can also use a single mapping like follows:

::

    plugin_name:
      name: target_name
      host: localhost
      foo: bar

The fields for plugin configurations can vary due to a plugin's configuration requirements. The name value in each stanza is only required when using multiple targets in a plugin. If it is only a single target, the name will be taken from the server's hostname.

APC Installation Notes
----------------------
Copy the ``apc-nrp.php`` script to a directory that can be served by your web server or ``php-fpm`` application. Edit the ``newrelic-plugin-agent`` configuration to point to the appropriate URL.

Apache HTTPd Installation Notes
-------------------------------
Enable the HTTPd server status page in the default virtual host. The following example configuration snippet for Apache HTTPd 2.2 demonstrates how to do this:

::

    <Location /server-status>
        SetHandler server-status
        Order deny,allow
        Deny from all
        Allow from 127.0.0.1
    </Location>

For HTTPd 2.4, it should look something like:

::

    <Location /server-status>
        SetHandler server-status
        Require ip 127.0.0.1
    </Location>

The agent requires the extended information to parse metrics. If you are not seeing any metrics on your graphs for Apache verify that you have enabled ``ExtendedStatus``, the default is off so you must enable it. In your global Apache HTTP configuration you need to enable exetended status using:

::

    ExtendedStatus On

If you are monitoring Apache HTTPd via a HTTPS connection you can use the ``verify_ssl_cert`` configuration value in the httpd configuration section to disable SSL certificate verification.

Memcached Installation Notes
----------------------------
The memcached plugin can communicate either over UNIX domain sockets using the path configuration variable or TCP/IP using the host and port variables. Do not include both.

MongoDB Installation Notes
--------------------------
You need to install the pymongo driver, either by running ``pip install pymongo`` or by following the "`Installing Additional Requirements`_" above. Each database you wish to collect metrics for must be enumerated in the configuration.

There are two configuration stanza formats for MongoDB. You must use one or the other, they can not be mixed. For non-authenticated polling, you can simply enumate the databases you would like stats from as a list:

::

      mongodb:
        name: hostname
        host: localhost
        port: 27017
        #admin_username: foo
        #admin_password: bar
        #ssl: False
        #ssl_keyfile: /path/to/keyfile
        #ssl_certfile: /path/to/certfile
        #ssl_cert_reqs: 0  # Should be 0 for ssl.CERT_NONE, 1 for ssl.CERT_OPTIONAL, 2 for ssl.CERT_REQUIRED
        #ssl_ca_certs: /path/to/cacerts file
        databases:
          - database_name_1
          - database_name_2

If your MongoDB server requires authentication, you must provide both admin credentials and database level credentials and the stanza is formatted as a nested array:

::

      mongodb:
        name: hostname
        host: localhost
        port: 27017
        #admin_username: foo
        #admin_password: bar
        #ssl: False
        #ssl_keyfile: /path/to/keyfile
        #ssl_certfile: /path/to/certfile
        #ssl_cert_reqs: 0  # Should be 0 for ssl.CERT_NONE, 1 for ssl.CERT_OPTIONAL, 2 for ssl.CERT_REQUIRED
        #ssl_ca_certs: /path/to/cacerts file
        databases:
          database_name_1:
            username: foo
            password: bar
          database_name_2:
            username: foo
            password: bar

Nginx Installation Notes
------------------------
Enable the Nginx ``stub_status`` setting on the default site in your configuration. The following example configuration snippet for Nginx demonstates how to do this:

::

      location /nginx_stub_status {
        stub_status on;
        allow 127.0.0.1;
        deny all;
      }

If you are monitoring Nginx via a HTTPS connection you can use the ``verify_ssl_cert`` configuration value in the httpd configuration section to disable SSL certificate verification.

pgBouncer Installation Notes
----------------------------
The user specified must be a stats user.

PostgreSQL Installation Notes
-----------------------------
By default, the specified user must be superuser to get PostgreSQL
directory listings. To skip those checks that require superuser
permissions, use the ``superuser: False`` setting in the configuration
file.

Several of the checks take O(N) time where N is the number of relations
in the database. If you need to use this on a database with a very large
number of relations, you can skip these, using ``relation_stats: False``.

E.g.:

::

    postgresql:
      host: localhost
      port: 5432
      user: newrelic
      dbname: postgres
      password: newrelic
      superuser: False
      relation_stats: False

RabbitMQ Installation Notes
---------------------------
The user specified must have access to all virtual hosts you wish to monitor and should have either the Administrator tag or the Monitoring tag.

If you are monitoring RabbitMQ via a HTTPS connection you can use the ``verify_ssl_cert`` configuration value in the httpd configuration section to disable SSL certificate verification.

Redis Installation Notes
------------------------
For Redis daemons that are password protected, add the password configuration value, otherwise omit it. The Redis configuration section allows for multiple redis servers. The syntax to poll multiple servers is in the example below.

The Redis plugin can communicate either over UNIX domain sockets using the path configuration variable or TCP/IP using the host and port variables. Do not include both.

Riak Installation Notes
-----------------------
If you are monitoring Riak via a HTTPS connection you can use the ``verify_ssl_cert`` configuration value in the httpd configuration section to disable SSL certificate verification.

UWSGI Installation Notes
------------------------
The UWSGI plugin can communicate either over UNIX domain sockets using the path configuration variable or TCP/IP using the host and port variables. Do not include both.

Make sure you have `enabled stats server 
<http://uwsgi-docs.readthedocs.org/en/latest/StatsServer.html>`_ in your uwsgi config.

Configuration Example
---------------------

::

    %YAML 1.2
    ---
    Application:
      license_key: REPLACE_WITH_REAL_KEY
      poll_interval: 60
      #newrelic_api_timeout: 10
      #proxy: http://localhost:8080

      apache_httpd:
         -  name: hostname1
            scheme: http
            host: localhost
            port: 80
            path: /server-status
            #verify_ssl_cert: true
         -  name: hostname2
            scheme: http
            host: localhost
            port: 80
            path: /server-status
            #verify_ssl_cert: true

      couchdb:
         -  name: localhost
            host: localhost
            port: 5984
            #verify_ssl_cert: true
            #username: foo
            #password: bar
         -  name: localhost
            host: localhost
            port: 5984
            #verify_ssl_cert: true
            #username: foo
            #password: bar

      elasticsearch:
        name: clustername
        host: localhost
        port: 9200

      haproxy:
        name: my-haproxy-server
        host: localhost
        port: 80
        path: /haproxy?stats;csv
        scheme: http
        #verify_ssl_cert: true
        #username: foo
        #password: bar

      mongodb:
        name: hostname
        host: localhost
        port: 27017
        admin_username: foo
        admin_password: bar
        databases:
          database_name_1:
            username: foo
            password: bar
          database_name_2:
            username: foo
            password: bar

      memcached:
        - name: localhost
          host: localhost
          port: 11211
          path: /path/to/unix/socket
        - name: localhost
          host: localhost
          port: 11211
          path: /path/to/unix/socket

      nginx:
        - name: hostname
          host: localhost
          port: 80
          path: /nginx_stub_status
          #verify_ssl_cert: true
        - name: hostname
          host: localhost
          port: 80
          path: /nginx_stub_status
          #verify_ssl_cert: true

      pgbouncer:
        - host: localhost
          port: 6000
          user: stats

      php_apc:
         scheme: http
         host: localhost
         port: 80
         path: /apc-nrp.php
         #username: foo
         #password: bar
         #verify_ssl_cert: t

      php_fpm:
        - name: fpm-pool
          scheme: https
          host: localhost
          port: 443
          path: /fpm_status
          query: json

      postgresql:
        - host: localhost
          port: 5432
          user: postgres
          dbname: postgres
          superuser: True

      rabbitmq:
        - name: rabbitmq@localhost
          host: localhost
          port: 15672
          username: guest
          password: guest
          #verify_ssl_cert: true
          api_path: /api

      redis:
        - name: localhost
          host: localhost
          port: 6379
          db_count: 16
          password: foobar
          #path: /var/run/redis/redis.sock
        - name: localhost
          host: localhost
          port: 6380
          db_count: 16
          password: foobar
          #path: /var/run/redis/redis.sock

      riak:
        - name: localhost
          host: localhost
          port: 8098
          #verify_ssl_cert: true

    Daemon:
      user: newrelic
      pidfile: /var/run/newrelic/newrelic-plugin-agent.pid

    Logging:
      formatters:
        verbose:
          format: '%(levelname) -10s %(asctime)s %(process)-6d %(processName) -15s %(threadName)-10s %(name) -25s %(funcName) -25s L%(lineno)-6d: %(message)s'
      handlers:
        file:
          class : logging.handlers.RotatingFileHandler
          formatter: verbose
          filename: /var/log/newrelic/newrelic-plugin-agent.log
          maxBytes: 10485760
          backupCount: 3
      loggers:
        newrelic-plugin-agent:
          level: INFO
          propagate: True
          handlers: [console, file]
        requests:
          level: ERROR
          propagate: True
          handlers: [console, file]

Troubleshooting
---------------
- If the installation does not install the ``newrelic-plugin-agent`` application in ``/usr/bin`` then it is likely that ``setuptools`` or ``distribute`` is not up to date. The following commands can be run to install ``distribute`` and ``pip`` for installing the application:

::

    $ curl http://python-distribute.org/distribute_setup.py | python
    $ curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python

- If the application installs but doesn't seem to be submitting status, check the logfile which at ``/tmp/newrelic-plugin-agent.log`` if the default example logging configuration is used.
- If the agent starts but dies shortly after ensure that ``/var/log/newrelic`` and ``/var/run/newrelic`` are writable by the same user specified in the daemon section of the configuration file.
- If the agent has died and won't restart, remove any files found in ``/var/run/newrelic/``
- If using the Apache HTTP plugin and your stats are blank, ensure the ExtendedStatus directive is on.
