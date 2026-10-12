"""Explicit local PostgreSQL adapter; no writes, domain preparation or .env."""
from datetime import datetime
from decimal import Decimal

from ..metrics_persistence.connection import connect
from . import RELATIONS_VERSION
from .core import selection
from .relations import TABLES


def transport(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError('Nonfinite SQL numeric')
        return str(value)
    if isinstance(value, dict):
        return {k: transport(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [transport(v) for v in value]
    return value


def extract(config, choices):
    package = {'relationsVersion': RELATIONS_VERSION, 'selection': choices,
               'relations': {t: [] for t in TABLES}}
    choices = selection(package)
    conn = connect(config)  # accepted literal loopback/instance/unprivileged/PG* guards
    try:
        conn.set_session(isolation_level='REPEATABLE READ', readonly=True, autocommit=False)
        with conn.cursor() as cursor:
            def read(table, predicate, params):
                if table not in TABLES:
                    raise ValueError('Unknown relation')
                # Both identifiers and predicates are constants in this module.
                cursor.execute('select * from metrics_private.' + table + ' where ' + predicate, params)
                cols = [d.name for d in cursor.description]
                rows = [transport(dict(zip(cols, row))) for row in cursor.fetchall()]
                package['relations'][table] = rows
                return rows
            cids = [s['calculation_id'] for s in choices]; aids = [s['artifact_id'] for s in choices]
            calculations = read('metric_calculation', 'calculation_id = ANY(%s)', (cids,))
            if len(calculations) != len(cids):
                raise ValueError('Selected calculation absent')
            artifacts = read('metric_artifact', 'artifact_id = ANY(%s)', (aids,))
            if len(artifacts) != len(aids):
                raise ValueError('Selected artifact absent')
            associations = read('metric_calculation_coverage', 'calculation_id = ANY(%s)', (cids,))
            covs = sorted({r['coverage_revision_id'] for r in associations})
            read('game_metric_coverage_revision', 'coverage_revision_id = ANY(%s)', (covs,))
            read('team_game_metric_sums', 'coverage_revision_id = ANY(%s)', (covs,))
            calendars = sorted({r['calendar_set_id'] for r in calculations})
            pbps = sorted({r['pbp_set_id'] for r in calculations})
            read('metric_source_set', "(revision_id = ANY(%s) and kind = 'calendar') or (revision_id = ANY(%s) and kind = 'pbp')", (calendars, pbps))
            members = read('metric_source_member', "(set_id = ANY(%s) and kind = 'calendar') or (set_id = ANY(%s) and kind = 'pbp')", (calendars, pbps))
            sources = read('metric_source_revision', 'revision_id = ANY(%s)', (sorted({m['source_id'] for m in members}),))
            files = read('metric_artifact_file', 'artifact_id = ANY(%s)', (aids,))
            hashes = sorted({r['sha256'] for r in sources + files})
            read('metric_archive_blob', 'sha256 = ANY(%s)', (hashes,))
            # Full source sets + files for the nominal archive of each calculation.
            receipt_rows = []
            for choice in choices:
                c = next(c for c in calculations if c['calculation_id'] == choice['calculation_id'])
                local_hashes = {m['source_id'][7:] for m in members if
                    (m['kind'] == 'calendar' and m['set_id'] == c['calendar_set_id']) or
                    (m['kind'] == 'pbp' and m['set_id'] == c['pbp_set_id'])}
                local_hashes.update(f['sha256'] for f in files if f['artifact_id'] == choice['artifact_id'])
                rows = read('metric_archive_receipt', 'archive_id = %s and sha256 = ANY(%s)',
                            (choice['archive_id'], sorted(local_hashes)))
                for row in rows:
                    if row not in receipt_rows:
                        receipt_rows.append(row)
            package['relations']['metric_archive_receipt'] = receipt_rows
        conn.rollback()  # never commit a write; release repeatable snapshot
        from .core import sorted_rows
        package['relations'] = {t: sorted_rows(r) for t, r in package['relations'].items()}
        package['selection'] = choices
        return package
    finally:
        conn.close()
