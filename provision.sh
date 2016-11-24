#!/bin/bash

set -e

PG_USER=c3app_live

name=$1
port=$2
db=$name
db_user=${name}_user
db_pass=$( pwgen -s 16 1 )
db_host="10.1.11.91"
db_url="postgres+psycopg2cffi://${db_user}:${db_pass}@${db_host}/${db}/"
master_key=$( python -c "from binascii import hexlify; import os; print(hexlify(os.urandom(16)).decode())" )

# Create Database, user, permissions
ssh roo@$db_host psql -U postgres <<EOF
CREATE DATABASE $db;
\connect $db
CREATE USER $db_user WITH PASSWORD '$db_pass';
GRANT SELECT, INSERT, DELETE, UPDATE ON ALL TABLES IN SCHEMA public to $db_user;
GRANT CONNECT ON DATABASE $db to $db_user;
EOF

# Generate Systemd service file
cat <<EOF |tee $name.monadnock.ca.service
[Unit]
Description=C3Next Service for $name
After=docker.service
Requires=docker.service

[Service]
TimeoutStartSec=0
Environment="DB_URL=${db_url}"
Environment="MASTER_KEY=${master_key}"
ExecStartPre=-/usr/bin/docker kill c3next-$name
ExecStartPre=-/usr/bin/docker rm c3api-$name
ExecStart=/usr/bin/docker run --name c3next-$name \
			  -e DB_URL \
			  -e MASTER_KEY \
                          -p $port:8000 \
			  -p $port:9999/udp \
                          c3next
ExecStop=/usr/bin/docker stop c3next-$name
EOF

cat <<EOF > /tmp/rproxy.ini
${name}.monadnock.ca_port=${port}
${name}.monadnock.ca_onlysecure=True
${name}.monadnock.ca_sendhsts=True
${name}.monadnock.ca_iamokwithalocalnetworkattackerpwningmyusers=True

EOF
sudo sh -c "cat /tmp/rproxy.ini >> /home/rproxy/rproxy.ini"
sudo cp -b ${name}.monadnock.ca.service /etc/systemd/system
sudo systemctl enable ${name}.monadnock.ca
sudo systemctl start ${name}.monadnock.ca
