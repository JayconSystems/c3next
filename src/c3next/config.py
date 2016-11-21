""" Singleton for storing some default config values """
import os
from binascii import hexlify

from datetime import timedelta

if 'MASTER_KEY' in os.environ:
    MASTER_KEY = os.environ['MASTER_KEY']
else:
    MASTER_KEY = b'\xc3' * 16
    print("Using bogus master key")

if 'JWT_SECRET' in os.environ:
    JWT_SECRET = os.environ['JWT_SECRET']
else:
    JWT_SECRET = hexlify(os.urandom(16)).decode()
    print("JWT_SECRET uninitialized, using 128bits of urandom:", JWT_SECRET)

if 'JWT_EXPIRES' in os.environ:
    JWT_EXPIRES = timedelta(minutes=int(os.environ['JWT_EXPIRES']))
else:
    print("JWT_EXPIRES uninitialized, using default")
    JWT_EXPIRES = timedelta(hours=6)

if 'DB_URL' in os.environ:
    DB_URL = os.environ['PG_URL']
else:
    DB_URL = 'postgresql+psycopg2cffi://c3app_live:apidemo@127.0.0.1:5432/'

DK0_INTERVAL = 7200
DK1_INTERVAL = 86400
BEACON_LISTENER_TIMEOUT = timedelta(seconds=30)
SYNC_INTERVAL = 5
DEFAULT_PER_PAGE = 20
