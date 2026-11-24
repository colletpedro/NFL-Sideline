"""Test-only schema parity. This does not validate operational lineage."""
import argparse
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[4]
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations', type=Path, nargs='+', required=True)
    args = parser.parse_args()
    schema = json.loads((ROOT / 'contracts/metrics/consumption-e5c1-v1/observation.schema.json').read_bytes())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    count = 0
    for path in args.observations:
        documents = json.loads(path.read_bytes())
        for document in documents:
            validator.validate(document)
            count += 1
    print(json.dumps({'schema': 'PASS', 'documents': count}))
