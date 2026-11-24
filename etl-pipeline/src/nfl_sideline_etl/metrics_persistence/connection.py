"""No .env, DSN, remote address, libpq ambient defaults or privileged login."""
import os
from pathlib import Path
import uuid

from ..offline_metrics.inputs import load_json


class LocalConfig(dict):
    def __repr__(self):
        return repr({k: '[REDACTED]' if k == 'password' else v for k, v in self.items()})


def configuration(path):
    config = load_json(Path(path).read_bytes())
    keys = {'host', 'port', 'database', 'user', 'password', 'instance_id'}
    if not isinstance(config, dict) or set(config) != keys:
        raise ValueError('Explicit local connection file requires all six fields')
    if config['host'] not in ('127.0.0.1', '::1'):
        raise ValueError('Only literal loopback local connections are allowed')
    instance = str(uuid.UUID(config['instance_id']))
    if config['database'] != 'nfl_e5b2_' + instance.replace('-', '')[:12]:
        raise ValueError('Database must identify this E5b-2 instance')
    if (type(config['port']) is not int or not 1 <= config['port'] <= 65535 or
            not all(isinstance(config[k], str) and config[k] for k in ('user', 'password'))):
        raise ValueError('Invalid explicit connection parameters')
    return LocalConfig({**config, 'instance_id': instance})


def connect(config):
    if any(k.startswith('PG') for k in os.environ):
        raise ValueError('Ambient libpq PG* configuration is forbidden; unset it explicitly')
    # Also validate configurations supplied by Python callers, without temp files.
    if config['host'] not in ('127.0.0.1', '::1'):
        raise ValueError('Remote connection refused')
    instance = str(uuid.UUID(config['instance_id']))
    if config['database'] != 'nfl_e5b2_' + instance.replace('-', '')[:12]:
        raise ValueError('Unidentified E5b-2 database')
    import psycopg2
    conn = psycopg2.connect(host=config['host'], hostaddr=config['host'], port=config['port'],
                            dbname=config['database'], user=config['user'], password=config['password'],
                            connect_timeout=5, sslmode='disable', gssencmode='disable',
                            passfile='/dev/null', application_name='metrics-persistence-e5b2',
                            options='-c search_path=pg_catalog -c timezone=UTC')
    try:
        with conn.cursor() as cursor:
            cursor.execute('select current_database(), inet_server_addr() is not null, '
                           'rolsuper, rolbypassrls, rolcreatedb, rolcreaterole, '
                           "pg_has_role(current_user, 'metric_persistence_writer', 'USAGE') "
                           'from pg_roles where rolname = current_user')
            db, tcp, superuser, bypass, createdb, createrole, member = cursor.fetchone()
            if db != config['database'] or not tcp or any((superuser, bypass, createdb, createrole)) or not member:
                raise ValueError('Connection must use the unprivileged explicit writer role')
            cursor.execute('select instance_id::text, purpose from e5b2_instance.identity')
            if cursor.fetchall() != [(instance, 'metrics-persistence-e5b2-disposable')]:
                raise ValueError('Local instance identification mismatch')
        conn.rollback()
        return conn
    except BaseException:
        conn.close()
        raise
