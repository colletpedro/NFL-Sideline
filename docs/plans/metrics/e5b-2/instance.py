"""Disposable native PostgreSQL 17 harness. Never reads .env or remote settings.

Use start/stop with --root and --pg-bin; start refuses any existing root.
Only this delivery's marker allows stop. Credentials are generated in /tmp.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import uuid

REPO = Path(__file__).resolve().parents[4]


def command(args, *, output=None):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True,
                            timeout=60, check=False)
    if result.returncode:
        raise RuntimeError('Disposable runtime command failed: ' + str(args[0]))
    if output:
        Path(output).write_text(result.stdout + result.stderr)
    return result.stdout


def start(root, pg_bin, port):
    root, pg_bin = Path(root).resolve(), Path(pg_bin).resolve()
    if root.exists():
        raise ValueError('Refusing existing instance root; choose a new directory')
    if not str(root).startswith('/private/tmp/'):
        raise ValueError('Disposable instance root must be under /tmp')
    # Inventory and availability probe before starting any server.
    inventory = subprocess.run(['lsof', '-nP', '-iTCP', '-sTCP:LISTEN'],
                               capture_output=True, text=True, timeout=10)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', port))
    instance_id = str(uuid.uuid4())
    database = 'nfl_e5b2_' + instance_id.replace('-', '')[:12]
    root.mkdir(mode=0o700)
    (root / 'ports-before.txt').write_text(inventory.stdout)
    marker = {'purpose': 'metrics-persistence-e5b2-disposable', 'instance_id': instance_id,
              'pg_bin': str(pg_bin), 'port': port, 'database': database}
    (root / 'INSTANCE.json').write_text(json.dumps(marker, indent=2))
    for executable in ('initdb', 'pg_ctl', 'psql'):
        command([pg_bin / executable, '--help'], output=root / f'{executable}-help.txt')
    command([pg_bin / 'initdb', '-D', root / 'data', '-U', 'postgres',
             '--auth-local=trust', '--auth-host=scram-sha-256', '--encoding=UTF8', '--no-locale'],
            output=root / 'initdb.txt')
    with (root / 'data/postgresql.conf').open('a') as stream:
        stream.write(f"\nlisten_addresses='127.0.0.1'\nport={port}\nunix_socket_directories='{root}'\n")
    command([pg_bin / 'pg_ctl', '-D', root / 'data', '-l', root / 'postgres.log', '-w', 'start'])
    # Trust is only the private Unix socket; TCP logins use SCRAM.
    import psycopg2
    from psycopg2 import sql
    admin = dict(host=str(root), port=port, dbname='postgres', user='postgres')
    connection = psycopg2.connect(**admin)
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL('create database {}').format(sql.Identifier(database)))
    finally:
        connection.close()
    admin['dbname'] = database
    login = 'nfl_e5b2_writer'
    password = secrets.token_urlsafe(24)
    with psycopg2.connect(**admin) as connection:
        with connection.cursor() as cursor:
            # Reproduce Supabase roles and permissive public schema ownership.
            # No auth/rest/extensions service required by these migrations.
            cursor.execute('create role anon nologin; create role authenticated nologin; '
                           'create role service_role nologin bypassrls; grant usage on schema public to public')
            for migration in sorted((REPO / 'supabase/migrations').glob('*.sql')):
                cursor.execute(migration.read_text())
            cursor.execute(sql.SQL('create role {} login inherit nosuperuser nocreatedb nocreaterole '
                                   'noreplication nobypassrls password %s').format(sql.Identifier(login)), (password,))
            cursor.execute(sql.SQL('grant metric_persistence_writer to {}').format(sql.Identifier(login)))
            cursor.execute('create schema e5b2_instance; revoke all on schema e5b2_instance from public; '
                           'grant usage on schema e5b2_instance to metric_persistence_writer; '
                           'create table e5b2_instance.identity(instance_id uuid primary key, purpose text not null); '
                           'revoke all on e5b2_instance.identity from public; '
                           'grant select on e5b2_instance.identity to metric_persistence_writer')
            cursor.execute('insert into e5b2_instance.identity values (%s,%s)',
                           (instance_id, marker['purpose']))
            calendar = json.loads((REPO / 'etl-pipeline/tests/fixtures/offline_metrics/calendar.json').read_text())
            participants = {row[k] for row in calendar['rows'] for k in ('home_team', 'away_team')}
            for team in participants:
                cursor.execute('insert into public.teams(team_abbr,team_name) values (%s,%s)', (team, team))
            for row in calendar['rows']:
                cursor.execute('insert into public.games(game_id,season,week,game_type,home_team,away_team) '
                               'values (%s,%s,%s,%s,%s,%s)',
                               tuple(row[k] for k in ('game_id', 'season', 'week', 'game_type', 'home_team', 'away_team')))
    config = dict(host='127.0.0.1', port=port, database=database, user=login,
                  password=password, instance_id=instance_id)
    config_path = root / 'writer.json'
    config_path.write_text(json.dumps(config, indent=2))
    config_path.chmod(0o600)
    return marker  # never return credentials to terminal


def stop(root, pg_bin):
    root, pg_bin = Path(root).resolve(), Path(pg_bin).resolve()
    marker = json.loads((root / 'INSTANCE.json').read_text())
    if (marker['purpose'] != 'metrics-persistence-e5b2-disposable' or
            marker['pg_bin'] != str(pg_bin) or not str(root).startswith('/private/tmp/')):
        raise ValueError('Refusing unidentified instance')
    command([pg_bin / 'pg_ctl', '-D', root / 'data', '-m', 'fast', '-w', 'stop'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop'))
    parser.add_argument('--pg-bin', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--port', type=int, default=55482)
    args = parser.parse_args()
    if args.action == 'start':
        print(json.dumps(start(args.root, args.pg_bin, args.port), sort_keys=True))
    else:
        stop(args.root, args.pg_bin)
        print('Stopped identified E5b-2 instance; files preserved.')
