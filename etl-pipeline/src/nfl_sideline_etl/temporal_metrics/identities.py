"""v3 original dimensions, distinct from auxiliary temporal qualifications.

Checks a closed materialized package, not the complete calculation hash or PBP.
The complete batch is checked by the accepted adapter/prepare/materializer.
"""
from ..offline_metrics.artifact import identity, json_bytes, VERSIONS

GAME = ('game_id', 'season', 'phase', 'round', 'week', 'home_team', 'away_team')
MANIFEST = ('artifactVersion', 'versions', 'mode', 'inputs', 'metadata',
            'source_model_versions', 'replica_projection', 'requested_seasons',
            'limitations', 'calculation_id')
COVERAGE = (*GAME, 'coverage_revision_id', 'pbp_content_id', 'calendar_revision_id',
            'pbp_revision_id', 'raw_n', 'unique_n', 'duplicate_rows_ignored',
            'calendar_duplicate_rows_ignored', 'excluded_n', 'exclusions',
            'outside_pass_run_null_teams_n', 'eligible_content_n',
            'unknown_filter_flags_n', 'declared_completeness', 'completeness',
            'expected_unique_rows', 'expected_raw_unique_count_matches', 'scope',
            'statistics_status', 'provenance')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def frozen(seen, key, content):
    # Exact JSON types and original array ordering belong to persisted content.
    content = json_bytes(content)
    require(key not in seen or seen[key] == content, 'IDENTITY_CONFLICT: ' + str(key))
    seen[key] = content


def validate_identities(calculations, resources, proofs):
    from .validation import fields, integer
    batches, coverages, associations = {}, {}, {}
    for c in calculations.values():
        fields(c.get('original'), ('manifest', 'coverage'))
        m, a = c['original']['manifest'], c['original']['coverage']
        fields(m, MANIFEST); fields(a, COVERAGE)
        require(m['calculation_id'] == c['calculation_id'] and
                a['coverage_revision_id'] == c['coverage_revision_id'], 'Original identity binding mismatch')
        require(m['versions'] == VERSIONS and m['artifactVersion'] == 'metrics-offline-v1' and
                m['mode'] == 'OFFLINE_DRY_RUN', 'Unsupported original batch versions/mode')
        require(c['versions'] == {k: m['versions'][k] for k in ('population', 'definition', 'adapter')},
                'Original versions mismatch')
        require(c['game'] == {k: a[k] for k in GAME} and
                c['pbp_revision_id'] == a['pbp_revision_id'] and
                c['unknown_filter_flags_n'] == a['unknown_filter_flags_n'], 'Original coverage projection mismatch')
        # Original coverage ID has a complete local projection, unlike batch ID.
        require(a['coverage_revision_id'] == identity(dict(game=c['game'],
            calendar_revision=a['calendar_revision_id'], pbp_revision=a['pbp_revision_id'],
            content_id=a['pbp_content_id'], provenance={k: v for k, v in a['provenance'].items()
                if k not in ('available_at', 'event_upper_bound', 'ingested_at') or v is not None},
            versions=m['versions'])), 'Original coverage identity mismatch')
        fields(m['metadata'], ('metadataVersion', 'games', 'sources'))
        original_provenance = {k: v for k, v in a['provenance'].items()
            if k not in ('available_at', 'event_upper_bound', 'ingested_at') or v is not None}
        require(m['metadata']['games'].get(a['game_id'], {}) == original_provenance,
                'Original batch/coverage provenance mismatch')
        for sha, declaration in m['source_model_versions'].items():
            require(declaration == m['metadata']['sources'].get(sha, {}).get('source_model_version',
                {'value': 'UNKNOWN', 'evidence': None}), 'Original batch/source declaration mismatch')
        for k in ('raw_n', 'unique_n', 'duplicate_rows_ignored', 'calendar_duplicate_rows_ignored',
                  'excluded_n', 'outside_pass_run_null_teams_n', 'unknown_filter_flags_n'):
            integer(a[k])
        require(a['raw_n'] == a['unique_n'] + a['duplicate_rows_ignored'] and
                a['unique_n'] == a['excluded_n'] + a['eligible_content_n'], 'Original population reconciliation failed')
        require(a['eligible_content_n'] == sum(r['eligible_n'] for r in c['statistics']
            if r['role'] == 'off' and r['foundation'] == 'general'), 'Original eligible count mismatch')
        require(a['completeness'] in ('COMPLETE', 'PARTIAL', 'UNKNOWN') and
                a['scope'] == ('FULL_GAME_CONTENT' if a['completeness'] == 'COMPLETE' else 'AUDITABLE_SUBSET') and
                a['statistics_status'] == ('COMPLETE' if a['completeness'] == 'COMPLETE' else 'PARTIAL'),
                'Original observed coverage required')
        for count in a['exclusions'].values():
            integer(count)
        require(sum(a['exclusions'].values()) == a['excluded_n'] and
                a['unknown_filter_flags_n'] == a['exclusions'].get('unknown_filter_flags', 0),
                'Original exclusion reconciliation failed')
        require(a['unique_n'] > 0 or (a['completeness'] == 'COMPLETE' and a['expected_unique_rows'] == 0),
                'Empty observation requires original COMPLETE zero proof')
        for k in ('calendar', 'pbp'):
            rid = a[k + '_revision_id']
            r = resources.get(rid)
            require(r is not None and r['kind'] == 'SET' and r['payload']['source_kind'] == k,
                    'Original source set binding mismatch')
            members = sorted(i['source_revision_id'] for i in m['inputs'] if i['kind'] == k)
            require(members == sorted(r['dependencies']), 'Original batch/source members mismatch')
        require(a['calendar_revision_id'] in resources[c['calendar_revision_id']]['dependencies'],
                'Auxiliary calendar must bind original SET')
        require(set(m['source_model_versions']) == {i['sha256'] for i in m['inputs'] if i['kind'] == 'pbp'},
                'Original source model map mismatch')
        def qualification(env, subject, kind):
            if env is None:
                return
            e = proofs[env['evidence_id']]
            require(e['subject_id'] == subject and e['kind'] == kind and
                    type(e['value']) is type(env['value']) and e['value'] == env['value'],
                    'Auxiliary qualification binding mismatch')
        qualification(c['completeness'], c['coverage_revision_id'], 'PBP_COMPLETE')
        require(c['completeness'] is None or c['completeness']['value'] == a['completeness'],
                'Qualification cannot rewrite original completeness')
        qualification(c['model'], c['calculation_id'], 'METADATA')
        known = set()
        for sid, env in c['source_models'].items():
            qualification(env, sid, 'METADATA')
            original = m['source_model_versions'][sid[7:]]['value']
            if original != 'UNKNOWN':
                known.add(original)
                require(env is None or env['value'] == original, 'Qualification cannot rewrite original source model')
        require(c['model'] is None or not known or known == {c['model']['value']},
                'Qualification cannot rewrite original batch model')
        qualification(c.get('source_cause'), c['coverage_revision_id'], 'METADATA')
        frozen(batches, c['calculation_id'], m)
        frozen(coverages, c['coverage_revision_id'],
               {'coverage': a, 'statistics': sorted(c['statistics'], key=json_bytes), 'versions': c['versions']})
        frozen(associations, (c['calculation_id'], c['coverage_revision_id']),
               {**{k: c[k] for k in ('original', 'game', 'pbp_revision_id', 'versions',
                                  'unknown_filter_flags_n')}, 'statistics': sorted(c['statistics'], key=json_bytes)})
