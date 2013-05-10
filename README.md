newrelic_plugin_agent
=====================

Agent that polls supported backend systems and submits the results to the
NewRelic platform. Currently supported backend systems are:

- Apache HTTP Server
- CouchDB
- Edgecast CDN "Realtime" API
- Memcached
- Nginx
- pgBouncer
- RabbitMQ
- Redis
- Riak

Installation Instructions
-------------------------
1. Unzip the archive
2. In the archive directory:

    python setup.py install

3. Copy the configuration file example from /opt/newrelic_plugin_agent/example.yml to /etc/newrelic_plugin_agent.yml and edit the configuration in that file.
4. Run the app:

    newrelic_plugin_agent -c PATH-TO-CONF-FILE [-f]

* - Where -f is to run it in the foreground instead of as a daemon.

Sample configuration and init.d script are installed in /opt/newrelic_plugin_agent

Installing Additional Requirements
----------------------------------

To use the pgBouncer plugin you must install the psycopg2 library. To easily do
this, make sure you have the latest version of pip installed (http://www.pip-installer.org/). This should be done after installing the agent itself.

Once installed, from inside the source directory run the following command:

    pip install -e .[pgbouncer]

Configuration Example
---------------------

    %YAML 1.2
    ---
    Application:
      license_key: VALUE
      poll_interval: 60

      apache_httpd:
        name: hostname
        host: localhost
        port: 80
        path: /server-status

      couchdb:
        name: localhost
        host: localhost
        port: 5984

      edgecast:
        name: My Edgecase Account
        account: ACCOUNT_NUMBER
        token: API_TOKEN

      memcached:
        name: localhost
        host: localhost
        port: 11211

      nginx:
        name: hostname
        host: localhost
        port: 80
        path: /nginx_stub_status

      pgbouncer:
        host: localhost
        port: 6000
        user: stats

      rabbitmq:
        name: rabbitmq@localhost
        host: localhost
        port: 15672
        username: guest
        password: guest

      redis:
        - name: localhost
          host: localhost
          port: 6379
          db_count: 16

      riak:
        name: localhost
        host: localhost
        port: 8098

    Daemon:
      pidfile: /var/run/newrelic_plugin_agent.pid

    Logging:
      formatters:
        verbose:
          format: '%(levelname) -10s %(asctime)s %(process)-6d %(processName) -15s %(threadName)-10s %(name) -25s %(funcName) -25s L%(lineno)-6d: %(message)s'
      handlers:
        file:
          class : logging.handlers.RotatingFileHandler
          formatter: verbose
          filename: /tmp/newrelic_plugin_agent.log
          maxBytes: 10485760
          backupCount: 3
      loggers:
        newrelic_plugin_agent:
          level: INFO
          propagate: True
          handlers: [console, file]
        requests:
          level: ERROR
          propagate: True
          handlers: [console, file]
