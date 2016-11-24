#!/bin/bash

. /appenv/bin/activate
alembic upgrade head
twistd -n -y src/$APPNAME/main.py
