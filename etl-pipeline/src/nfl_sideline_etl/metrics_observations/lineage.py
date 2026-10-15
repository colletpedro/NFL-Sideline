"""Reverify the complete accepted chain, never trust an externally rehashed marker."""
from ..metrics_materialization.core import materialize
from ..metrics_materialization.publication import read
from ..offline_metrics.artifact import json_bytes
from ..temporal_metrics.validation import validate


def verify_source(temporal, lineage):
    if (temporal.get('inputVersion') != 'metrics-temporal-input-v3' or
            lineage.get('materializationVersion') != 'metrics-materialization-v2'):
        raise ValueError('Unsupported materialization/input versions')
    rebuilt, audit = materialize(lineage['relations'], lineage['recoveredArchives'],
                                 lineage['auxiliary'], lineage['derivedAt'])
    if json_bytes(rebuilt) != json_bytes(temporal) or json_bytes(audit) != json_bytes(lineage):
        raise ValueError('Source materialization diverges from accepted originals')
    return validate(rebuilt)


def load_source(path):
    temporal, lineage = read(path)
    verify_source(temporal, lineage)
    return temporal, lineage
