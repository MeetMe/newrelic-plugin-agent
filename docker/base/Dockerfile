#
# Base development environment docker image
#

FROM phusion/baseimage
MAINTAINER gavinmroy@gmail.com

# Let aptitude know it's a non-interactive install
ENV DEBIAN_FRONTEND noninteractive

# Update apt caches and install python dev environment, pip and curl
RUN apt-get -q update && apt-get install -y -q python-dev python-pip curl screen

# Make sure the base development requirements are installed
RUN pip install helper requests

# Hack for initctl
# See: https://github.com/dotcloud/docker/issues/1024
RUN rm /sbin/initctl
RUN ln -sf /bin/true /sbin/initctl
RUN dpkg-divert --local --rename --add /sbin/initctl

# Don't let upstart start installed services
ADD policy-rc.d /usr/sbin/policy-rc.d
RUN /bin/chmod 755 /usr/sbin/policy-rc.d

# Add the root .ssh files
RUN mkdir -p /root/.ssh & chmod 0700 /root/.ssh
ADD id_rsa /root/.ssh/id_rsa
ADD id_rsa.pub /root/.ssh/id_rsa.pub
ADD ssh_config /root/.ssh/config
RUN chmod 0700 /root/.ssh/id_rsa && cp /root/.ssh/id_rsa.pub /root/.ssh/authorized_keys

# Add a newrelic user
RUN /usr/sbin/groupadd -r -g 110 newrelic
RUN /usr/sbin/useradd -M -r -u 110 -g newrelic newrelic -d /var/lib/postgres

# Setup the newrelic-plugin-agent defaults
RUN mkdir -p /etc/newrelic /var/log/newrelic /var/run/newrelic /etc/service/newrelic-plugin-agent
RUN chown newrelic /var/log/newrelic /var/run/newrelic
ADD newrelic-plugin-agent.cfg /etc/newrelic/newrelic-plugin-agent.cfg
ADD bin/newrelic-plugin-agent.sh /etc/service/newrelic-plugin-agent/run

# Set the HOME environment variable for normal login behavior
ENV HOME /root

# Base Image Init
CMD ["/sbin/my_init"]