#
# Development/Test Dockerfile for PostgreSQL
#

FROM gavinmroy/nrpadev
MAINTAINER gavinmroy@gmail.com

# Maintain our own PostgreSQL user and group
RUN /usr/sbin/groupadd -r -g 105 postgres
RUN /usr/sbin/useradd -M -r -u 105 -g postgres postgres -d /var/lib/postgres

# Add the PostgreSQL PGP key to verify their Debian packages.
# It should be the same key as https://www.postgresql.org/media/keys/ACCC4CF8.asc
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" > /etc/apt/sources.list.d/pgdg.list

# Update the Ubuntu and PostgreSQL repository indexes
RUN apt-get update

#  There are some warnings (in red) that show up during the build. You can hide
#  them by prefixing each apt-get statement with DEBIAN_FRONTEND=noninteractive
RUN apt-get -y -q install python-software-properties software-properties-common python-pip make
RUN apt-get -y -q install postgresql-9.3 postgresql-client-9.3 postgresql-contrib-9.3 postgresql-server-dev-9.3 pgbouncer
RUN pip install pgxnclient

# Hack to make sure the src directory exists for PostgreSQL 9.3 extension installations
RUN mkdir -p /usr/lib/postgresql/9.3/lib/src

# Remove the external pidfile reference in the config
RUN /bin/sed -i 's/external_pid_file =/#external_pid_file =/' /etc/postgresql/9.3/main/postgresql.conf

# Ensure that /var/run/postgres doesn't exist anymore, we'll use /tmp/postgresql for docker reasons
RUN rm -rf /var/run/postgres /var/lib/postgresql

# Run the rest of the commands as the ``postgres`` user created by the ``postgres-9.3`` package when it was # For the unix domain socket location
RUN mkdir -p /tmp/postgresql; chmod 0755 /tmp/postgresql; chown postgres:postgres /tmp/postgresql;touch /tmp/postgresql/.no-delete

# Adjust PostgreSQL configuration so that remote connections to the database are possible.
RUN echo "host    all    all         0.0.0.0/0  trust" >> /etc/postgresql/9.3/main/pg_hba.conf

# Listen on all IP addresses
RUN echo "listen_addresses='*'" >> /etc/postgresql/9.3/main/postgresql.conf

RUN mkdir /etc/service/postgresql
ADD postgresql.sh /etc/service/postgresql/run

RUN mkdir /etc/service/pgbouncer
ADD pgbouncer.sh /etc/service/pgbouncer/run

# Expose the PostgreSQL && pgBouncer ports
EXPOSE 5432 6000

# Add VOLUMEs to allow backup of config, logs and databases
VOLUME	["/etc/postgresql", "/var/log/postgresql", "/tmp/postgresql"]
