#
# LAMP environment with apache2, mysql, memcached, php5 and php5-apcu
#

FROM nrpa/base
MAINTAINER gavinmroy@gmail.com

RUN echo "mysql-server mysql-server/root_password password root" | debconf-set-selections
RUN echo "mysql-server mysql-server/root_password_again password root" | debconf-set-selections

RUN apt-get update && apt-get install -y apache2 php5 php5-apcu memcached mysql-server

RUN mkdir -p /etc/service/apache2 /etc/service/memcached /etc/service/mysqld
ADD bin/apache2.sh /etc/service/apache2/run
ADD bin/memcached.sh /etc/service/memcached/run
ADD bin/mysqld.sh /etc/service/mysqld/run

ADD newrelic-plugin-agent.cfg /etc/newrelic/newrelic-plugin-agent.cfg

ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2
ENV APACHE_LOCK_DIR /var/run/lock/apache2
ENV APACHE_PID_FILE /var/run/apache2/apache2.pid

RUN echo "ServerName nrpa-lamp.docker" >> /etc/apache2/apache2.conf

EXPOSE 80 3306 11211
