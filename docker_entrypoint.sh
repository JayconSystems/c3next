#!/bin/bash

. /appenv/bin/activate
alembic upgrade head
exec twistd -n -y src/$APPNAME/main.py
