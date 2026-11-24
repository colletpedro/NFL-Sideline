"""Explicit real PostgreSQL suite: missing instance is a failure, never a skip."""
import json
from pathlib import Path

import psycopg2
from psycopg2 import sql
import pytest

from nfl_sideline_etl.metrics_persistence.connection import configuration, connect
from nfl_sideline_etl.metrics_persistence.writer import TABLES


def pytest_addoption(parser):
    parser.addoption('--e5b2-instance-root', required=True, help='Identified disposable instance created by instance.py')


@pytest.fixture(scope='session')
def instance(request):
    root = Path(request.config.getoption('--e5b2-instance-root')).resolve()
    marker = json.loads((root / 'INSTANCE.json').read_text())
    assert marker['purpose'] == 'metrics-persistence-e5b2-disposable'
    assert str(root).startswith('/private/tmp/')
    config = configuration(root / 'writer.json')
    conn = connect(config)
    conn.close()
    admin = dict(host=str(root),port=config['port'],dbname=config['database'],user='postgres')
    return root, config, admin


@pytest.fixture
def db(instance):
    root, config, admin = instance
    # Only this disposable delivery's new schema; no stack reset or legacy cleanup.
    with psycopg2.connect(**admin) as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL('truncate {}').format(sql.SQL(',').join(
                sql.Identifier('metrics_private', t) for t in TABLES)))
    return config, admin
