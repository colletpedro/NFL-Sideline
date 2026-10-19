"""One public E5c-2 read per configured entry; explicit allowlist, no raw lineage DTO."""
from copy import deepcopy
from pathlib import Path
import re

from ..offline_metrics.artifact import identity
from ..temporal_metrics.validation import fields
from ..metrics_observations.publication import read, safe_path
from ..metrics_observations.core import FIELD_SCOPES

HASH = re.compile(r'^sha256:[0-9a-f]{64}$')
ID = re.compile(r'^[A-Za-z0-9_:-]{1,128}$')
CODE = re.compile(r'^[A-Z][A-Z0-9_]{0,127}$')


def require(ok):
    if not ok:
        raise ValueError('Unsupported restricted transport profile')


def statistics(value):
    return None if value is None else {k: v if k == 'epaSum' else str(v) for k, v in value.items()}


def ratio(value):
    return None if value is None else {'numerator': value['numerator'], 'denominator': str(value['denominator'])}


def dto(d, manifest, entry):
    require(manifest['fieldScopes'] == FIELD_SCOPES)
    require(all(ID.fullmatch(v) for v in (d['subject']['team'], *[m['gameId'] for m in d['members']])))
    require(re.fullmatch(r'[A-Z0-9]{2,4}', d['subject']['team']))
    require(all(CODE.fullmatch(x['code']) and ID.fullmatch(x['subjectId']) for x in d['limitations']))
    require(all(CODE.fullmatch(c) for g in d['guarantees'].values() for c in g['reasonCodes']))
    model = d['guarantees']['compatibility']['epaModel']
    require(model['id'] is None or re.fullmatch(r'[A-Za-z0-9_.:@+-]{1,128}', model['id']))
    require(0 <= d['presentation']['epaDecimals'] <= 12 and 0 <= d['presentation']['ratePercentDecimals'] <= 12)
    require(d['guarantees']['temporal']['state'] == 'UNKNOWN')
    if d['totals'] is not None:
        require(any(x['code'] == 'UNKNOWN_FILTER_FLAGS_GAME_SCOPE' for x in d['limitations']))
    guarantees = {k: {'state': g['state'], 'reasonCodes': g['reasonCodes']} for k, g in d['guarantees'].items()}
    cov = d['guarantees']['coverage']
    guarantees['coverage'].update(expectedCount=None if cov['expectedCount'] is None else str(cov['expectedCount']), coverageRatio=ratio(cov['coverageRatio']))
    guarantees['compatibility']['epaModel'] = deepcopy(model)
    count = len(d['observed']['includedGameIds'])
    value = {'dtoVersion': 'metrics-lab-observation-v1', 'entryId': entry['entryId'],
        'bundleId': manifest['bundleId'], 'observationId': d['observationId'],
        'subject': deepcopy(d['subject']),
        'request': {k: deepcopy(d['request'][k]) for k in ('season', 'phase', 'origin', 'period')},
        'observed': {'actualWeeks': deepcopy(d['observed']['actualWeeks']), 'includedGameIds': deepcopy(d['observed']['includedGameIds'])},
        'totals': statistics(d['totals']), 'values': {k: ratio(v) for k, v in d['values'].items()},
        'guarantees': guarantees, 'limitations': deepcopy(d['limitations']),
        'members': [{k: statistics(m[k]) if k == 'statistics' else deepcopy(m[k])
                     for k in ('gameId', 'week', 'round', 'sourceState', 'completeness', 'statistics')} for m in d['members']],
        'fieldScopes': deepcopy(FIELD_SCOPES), 'presentation': deepcopy(d['presentation']),
        'scope': {'aggregation': 'NO_OBSERVATION' if count == 0 else 'SINGLE_GAME' if len(d['members']) == 1 else 'MULTI_GAME',
                  'population': 'DECLARED_POPULATION' if guarantees['coverage']['state'] == 'KNOWN' and guarantees['completeness']['state'] == 'COMPLETE' else 'OBSERVED_SAMPLE'}}
    value['dtoId'] = identity(value)
    return value


def prepare(config):
    fields(config, ('configVersion', 'bundles'))
    require(config['configVersion'] == 'metrics-lab-config-v1' and isinstance(config['bundles'], list))
    entries, seen = [], set()
    for entry in config['bundles']:
        fields(entry, ('entryId', 'label', 'dataKind', 'path', 'expectedBundleId'))
        require(isinstance(entry['entryId'], str) and re.fullmatch(r'[a-z0-9_-]{1,48}', entry['entryId']) and entry['entryId'] not in seen)
        seen.add(entry['entryId'])
        require(isinstance(entry['label'], str) and 0 < len(entry['label']) <= 160 and
                not any(x in entry['label'] for x in ('/', '\\', '<', '>', '\n', '\r')))
        require(entry['dataKind'] in ('REAL_ARCHIVE', 'SYNTHETIC') and isinstance(entry['expectedBundleId'], str) and HASH.fullmatch(entry['expectedBundleId']))
        require(isinstance(entry['path'], str) and Path(entry['path']).is_absolute())
        item = {k: entry[k] for k in ('entryId', 'label', 'dataKind')}
        item.update(status='ERROR', errorCode='BUNDLE_VALIDATION_FAILED', bundleId=None, documents=[])
        try:
            source = safe_path(entry['path'])
            require(not source.resolve().is_relative_to(Path(__file__).resolve().parents[4] / 'web-ui'))
            docs, manifest = read(source)
            if manifest['bundleId'] != entry['expectedBundleId']:
                item['errorCode'] = 'BUNDLE_ID_MISMATCH'
            elif entry['dataKind'] == 'REAL_ARCHIVE' and any(
                    d['subject']['team'] in ('AAA', 'BBB') or any(m['gameId'].lower().startswith('synthetic') for m in d['members']) for d in docs):
                item['errorCode'] = 'SYNTHETIC_KIND_MISMATCH'
            else:
                projected = [dto(d, manifest, entry) for d in docs]
                item.update(status='READY', errorCode=None, bundleId=manifest['bundleId'], documents=projected)
        except (ValueError, OSError, KeyError, TypeError, StopIteration, ArithmeticError):
            pass  # Never expose a path, assertion, traceback or source message.
        entries.append(item)
    result = {'snapshotVersion': 'metrics-lab-snapshot-v1', 'entries': entries}
    result['sessionId'] = identity(result)
    return result
