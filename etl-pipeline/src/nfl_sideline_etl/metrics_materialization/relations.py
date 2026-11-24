"""Closed relational projection of the accepted E5b-2 writer, without SQL."""
from ..offline_metrics.artifact import identity
from ..metrics_persistence.archive import digest

TABLES = ('metric_archive_blob', 'metric_source_revision', 'metric_source_set',
          'metric_source_member', 'metric_calculation', 'game_metric_coverage_revision',
          'metric_calculation_coverage', 'team_game_metric_sums', 'metric_artifact',
          'metric_artifact_file', 'metric_archive_receipt')


def records(plan):
    r = {t: [] for t in TABLES}
    def put(t, row):
        r[t].append(row)
    all_bytes = {sha: data for sha, (data, _) in plan.source_bytes.items()}
    all_bytes.update({digest(data): data for data in plan.artifact_bytes.values()})
    for sha, data in sorted(all_bytes.items()):
        put('metric_archive_blob', {'sha256': sha, 'byte_length': len(data)})
    for sha in sorted(plan.source_bytes):
        put('metric_source_revision', {'revision_id': 'sha256:' + sha, 'sha256': sha})
    for kind, members in plan.sets.items():
        sid = identity([d['source_revision_id'] for d in members])
        put('metric_source_set', {'revision_id': sid, 'kind': kind, 'members_json': members})
        for ordinal, d in enumerate(members):
            put('metric_source_member', {'set_id': sid, 'kind': kind, 'ordinal': ordinal,
                'source_id': d['source_revision_id'], 'raw_rows': d['raw_rows'], 'descriptor_json': d})
    m = plan.result['manifest.json']; v = m['versions']; cid = m['calculation_id']
    put('metric_calculation', {'calculation_id': cid, 'artifact_version': m['artifactVersion'],
        'adapter_version': v['adapter'], 'definition_version': v['definition'],
        'population_version': v['population'], 'calendar_kind': 'calendar', 'pbp_kind': 'pbp',
        'calendar_set_id': identity([d['source_revision_id'] for d in plan.sets['calendar']]),
        'pbp_set_id': identity([d['source_revision_id'] for d in plan.sets['pbp']]), 'manifest_json': m})
    fields = ('coverage_revision_id', 'game_id', 'season', 'week', 'phase', 'round',
              'home_team', 'away_team', 'calendar_revision_id', 'pbp_revision_id',
              'pbp_content_id', 'completeness', 'declared_completeness', 'scope',
              'statistics_status', 'raw_n', 'unique_n', 'duplicate_rows_ignored',
              'excluded_n', 'eligible_content_n', 'expected_unique_rows',
              'calendar_duplicate_rows_ignored', 'outside_pass_run_null_teams_n', 'unknown_filter_flags_n')
    for a in plan.result['game-audit.json']:
        put('game_metric_coverage_revision', {**{k: a[k] for k in fields},
            'calendar_kind': 'calendar', 'pbp_kind': 'pbp', 'audit_json': a})
        put('metric_calculation_coverage', {'calculation_id': cid, 'game_id': a['game_id'],
                                          'coverage_revision_id': a['coverage_revision_id']})
    fields = ('coverage_revision_id', 'team', 'role', 'foundation', 'population_version',
              'definition_version', 'scope', 'statistics_status', 'completeness',
              'eligible_n', 'epa_n', 'success_n', 'epa_missing_n', 'epa_nonfinite_n', 'epa_sum')
    for s in plan.result['statistics.json']:
        put('team_game_metric_sums', {**{k: s[k] for k in fields}, 'record_json': s})
    put('metric_artifact', {'artifact_id': plan.artifact_id, 'calculation_id': cid,
                            'files_json': plan.file_hashes})
    for name, sha in sorted(plan.file_hashes.items()):
        put('metric_artifact_file', {'artifact_id': plan.artifact_id, 'filename': name, 'sha256': sha})
    return r
