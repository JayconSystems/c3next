#!/bin/bash

set -e

PG_USER=c3app_live

name=$1
db=$name
db_user=${name}_user
db_pass=$( pwgen -s 16 1 )
db_host="core4.nocko.se"
db_url="postgres+psycopg2cffi://${db_user}:${db_pass}@${db_host}/${db}/"
master_key=$( python -c "from binascii import hexlify; import os; print(hexlify(os.urandom(16)).decode())" )

# Create Database, user, permissions
#psql -h $db_host -U $PG_USER <<EOF
cat <<EOF
CREATE DATABASE $db;
\connect $db
CREATE USER $db_user WITH PASSWORD '$db_pass';
GRANT SELECT, INSERT, DELETE, UPDATE ON ALL TABLES IN SCHEMA public to $db_user;
GRANT CONNECT ON DATABASE $db to $db_user;
EOF

# Generate Systemd service file
cat <<EOF
[Unit]
Description=C3Next Service for $name
After=docker.service
Requires=docker.service

[Service]
User=core
TimeoutStartSec=0
Environment="DB_URL=${db_url}"
Environment="MASTER_KEY=${master_key}"
ExecStartPre=-/usr/bin/docker kill c3next-$name
ExecStartPre=-/usr/bin/docker rm c3api-$name
ExecStartPre=/usr/bin/docker pull nocko/c3next
ExecStart=/usr/bin/docker run --name c3api-$name \
			  -e DB_URL \
			  -e MASTER_KEY \
                          -p 443:8443 \
                          nocko/c3next
ExecStop=/usr/bin/docker stop c3next-$name
EOF
