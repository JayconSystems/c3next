import sqlalchemy as sa
from alchimia import TWISTED_STRATEGY

from twisted.internet import reactor

from .config import DB_URL

ENGINE = sa.create_engine(DB_URL, reactor=reactor,
                          strategy=TWISTED_STRATEGY, pool_size=90)

METADATA = sa.MetaData()


def get_connection():
    return ENGINE.connect()


# CREATE TABLE zones (
#   id serial PRIMARY KEY,
#   name varchar NOT NULL
# );

zones = sa.Table('zones', METADATA,
                 sa.Column('id', sa.Integer, primary_key=True),
                 sa.Column('name', sa.String, nullable=True))

# CREATE TABLE beacon_groups (
#   id serial PRIMARY KEY,
#   name varchar NOT NULL,
#   description text DEFAULT NULL
# );

beacon_groups = sa.Table('beacon_groups', METADATA,
                         sa.Column('id', sa.Integer, primary_key=True),
                         sa.Column('name', sa.String, nullable=False),
                         sa.Column('description', sa.String,
                                   nullable=False, default=''))

# CREATE TABLE listeners (
#   id varchar PRIMARY KEY,
#   name varchar DEFAULT NULL,
#   description text DEFAULT NULL,
#   zone_id integer REFERENCES zones,
#   last_seen timestamp DEFAULT NULL
# );

listeners = sa.Table('listeners', METADATA,
                     sa.Column('id', sa.Binary, primary_key=True),
                     sa.Column('name', sa.String, nullable=True),
                     sa.Column('zone_id', sa.ForeignKey('zones.id'),
                               nullable=True),
                     sa.Column('last_seen', sa.DateTime(timezone=True),
                               default=sa.func.now()))


# CREATE TABLE beacons (
#   id integer PRIMARY KEY,
#   name varchar DEFAULT NULL,
#   group_id integer REFERENCES beacon_groups DEFAULT NULL,
#   description text DEFAULT NULL,
#   battery percent DEFAULT NULL,
#   listener_id varchar REFERENCES listeners,
#   last_seen timestamp DEFAULT NULL
# );

beacons = sa.Table('beacons', METADATA,
                   sa.Column('id', sa.Binary, primary_key=True),
                   sa.Column('name', sa.String, nullable=True),
                   sa.Column('group_id',
                             sa.ForeignKey('beacon_groups.id'), nullable=True),
                   sa.Column('listener_id',
                             sa.ForeignKey('listeners.id')),
                   sa.Column('last_seen', sa.DateTime(timezone=True),
                             default=sa.func.now()),
                   sa.Column('key', sa.Binary, nullable=False),
                   sa.Column('dk', sa.BigInteger,
                             sa.CheckConstraint('dk>=0<4294967296'),
                             nullable=False),
                   sa.Column('clock', sa.BigInteger,
                             sa.CheckConstraint('dk>=0<4294967296'),
                             nullable=False),
                   sa.Column('clock_origin', sa.Float,
                             nullable=True),
                   sa.Column('rejected_replay', sa.Integer, nullable=False,
                             default=0),
                   sa.Column('rejected_mac', sa.Integer, nullable=False,
                             default=0),
                   sa.Column('rejected_dk', sa.Integer, nullable=False,
                             default=0))

# CREATE TABLE beacon_logs (
#   id serial PRIMARY KEY,
#   beacon_id integer REFERENCES beacons,
#   listener_id varchar REFERENCES listeners,
#   timestamp timestamp NOT NULL DEFAULT now()
# );
# CREATE INDEX beacon_logs_beacon_id ON beacon_logs(beacon_id);
# CREATE INDEX beacon_logs_timestamp ON beacon_logs(timestamp);

beacon_logs = sa.Table('beacon_logs', METADATA,
                       sa.Column('id', sa.Integer, primary_key=True),
                       sa.Column('beacon_id', sa.ForeignKey('beacons.id')),
                       sa.Column('listener_id', sa.ForeignKey('listeners.id')),
                       sa.Column('timestamp', sa.DateTime(timezone=True),
                                 nullable=False, default=sa.func.now()))

# CREATE OR REPLACE FUNCTION log_beacon_changes() RETURNS TRIGGER AS $$
# BEGIN
#   IF (OLD.listener_id IS DISTINCT FROM NEW.listener_id)
#     THEN
#       INSERT INTO beacon_logs (beacon_id, listener_id)
#         VALUES (NEW.id, NEW.listener_id);
#   END IF;
#   RETURN NEW;
# END;
# $$ LANGUAGE plpgsql;

# CREATE TRIGGER insert_beacon_log_rows AFTER UPDATE ON beacons FOR EACH ROW
#   EXECUTE PROCEDURE log_beacon_changes();

# CREATE TABLE users (
#   id serial PRIMARY KEY,
#   username varchar UNIQUE NOT NULL,
#   password varchar NOT NULL,
#   first_name varchar NOT NULL DEFAULT '',
#   last_name varchar NOT NULL DEFAULT '',
#   last_login timestamp DEFAULT NULL,
#   is_active boolean NOT NULL DEFAULT TRUE,
#   email varchar NOT NULL
# );
# CREATE INDEX users_username ON users (username);
# CREATE INDEX users_email ON users (email);

users = sa.Table('users', METADATA,
                 sa.Column('id', sa.Integer, primary_key=True),
                 sa.Column('username', sa.String, unique=True, nullable=False),
                 sa.Column('password', sa.String, nullable=False),
                 sa.Column('first_name', sa.String, nullable=False,
                           default=''),
                 sa.Column('last_name', sa.String, nullable=False,
                           default=''),
                 sa.Column('last_login_time', sa.DateTime(timezone=True),
                           nullable=True),
                 sa.Column('is_active',
                           sa.Boolean, nullable=False, default=True),
                 sa.Column('email', sa.String, nullable=False, unique=True))

# CREATE USER c3api WITH PASSWORD 'apidemo';
# GRANT SELECT, INSERT, DELETE, UPDATE ON ALL TABLES IN SCHEMA public to c3api;
# GRANT ALL ON ALL SEQUENCES IN SCHEMA public to c3api;
# GRANT CONNECT ON DATABASE c3 to c3api;


def execute(*args, **kwargs):
    return ENGINE.execute(*args, **kwargs)
