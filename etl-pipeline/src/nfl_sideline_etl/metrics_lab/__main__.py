import argparse
from pathlib import Path
from .adapter import prepare
from ..offline_metrics.artifact import json_bytes
from ..offline_metrics.inputs import load_json
from ..metrics_observations.publication import safe_path


def main():
    p = argparse.ArgumentParser(description='Validate configured bundles and emit a reduced local lab session.')
    p.add_argument('--config', type=Path, required=True)
    a = p.parse_args()
    try:
        if not a.config.is_absolute():
            raise ValueError('Absolute operator configuration required')
        result = prepare(load_json(safe_path(a.config).read_bytes()))
    except (ValueError, OSError, TypeError, KeyError, ArithmeticError):
        p.exit(2, 'OBSERVATION_CONFIGURATION_INVALID\n')
    print(json_bytes(result).decode(), end='')


if __name__ == '__main__':
    main()
