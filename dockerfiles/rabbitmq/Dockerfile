#
# Dockerfile for stand-alone RabbitMQ Server running on Ubuntu Precise
#

FROM gavinmroy/nrpadev
MAINTAINER gavinmroy@gmail.com

# Don't let upstart start rabbitmq-server on install
ADD policy-rc.d /usr/sbin/policy-rc.d
RUN /bin/chmod 755 /usr/sbin/policy-rc.d

# Add the RabbitMQ signing key and repo
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv F7B8CEA6056E8E56 && \
    echo "deb http://www.rabbitmq.com/debian/ testing main" > /etc/apt/sources.list.d/rabbitmq.list

# Add the Erlang Solutions signing key and repo
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv D208507CA14F4FCA && \
    echo "deb http://packages.erlang-solutions.com/debian precise contrib" > /etc/apt/sources.list.d/pgdg.list

# Update the repository indexes and install Erlang and RabbitMQ
RUN apt-get -qq update && apt-get install -y -qq rabbitmq-server

# Write out a rabbitmq.config that allows for the guest user to connect from an external IP address
ADD rabbitmq.config /etc/rabbitmq/rabbitmq.config

# Enable a few default plugins
RUN rabbitmq-plugins enable rabbitmq_management

# If there is no file in /var/log/rabbitmq, the directory will be mounted as owned by root in mode 0700
RUN touch /var/log/rabbitmq/.docker-volume-workaround

# Export the volumes for configuration and log file examination
VOLUME ["/etc/rabbitmq", "/var/log/rabbitmq"]

# Set the HOME env variable to the right location for RabbitMQ to run
ENV HOME /var/lib/rabbitmq

RUN mkdir /etc/service/rabbitmq
ADD rabbitmq.sh /etc/service/rabbitmq/run

# Ports to expose
EXPOSE 5672 15672
