"""Pure temporal selection with explicit version dispatch; no acquisition."""
LEGACY_INPUT_VERSION = 'metrics-temporal-input-v1'
PREVIOUS_INPUT_VERSION = 'metrics-temporal-input-v2'
INPUT_VERSION = 'metrics-temporal-input-v3'
RESULT_VERSION = 'metrics-temporal-result-v3'
ALGORITHM_VERSION = 'metrics-temporal-1.1.0'
POLICY_VERSION = 'materialized-evidence-v1'


def result_versions(input_version):
    if input_version == INPUT_VERSION:
        return RESULT_VERSION, ALGORITHM_VERSION
    if input_version in (LEGACY_INPUT_VERSION, PREVIOUS_INPUT_VERSION):
        return 'metrics-temporal-result-v2', 'metrics-temporal-1.0.1'
    raise ValueError('Unsupported temporal input version')
