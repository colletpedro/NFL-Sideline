"""Golden ledgers plus metamorphic tests; no production imports or self-generated goldens."""
import copy
import itertools
import json
import random
import unittest
from fractions import Fraction

import verify as model

CASES = json.loads((model.ROOT / 'fixtures/cases.json').read_text())['cases']
BY_ID = {c['id']: c for c in CASES}


def case(name):
    return copy.deepcopy(BY_ID[name])


class ContractExamples(unittest.TestCase):
    def test_all_hand_authored_goldens(self):
        self.assertEqual(model.verify_cases(), 26)

    def test_contract_ids_and_formulas_are_explicit(self):
        c = model.CONTRACT
        self.assertEqual(c['status'], 'ORCHESTRATOR_REVIEW_CANDIDATE')
        self.assertFalse(c['productionImplemented'])
        ids = {m['id'] for m in c['metrics']}
        self.assertEqual(len(ids), 22)
        expected = {f'{r}.{family}.{f}' for r in ['off', 'def']
                    for family in ['epa', 'success_rate', 'volume']
                    for f in ['general', 'classified_pass', 'classified_rush']}
        expected |= {f'{r}.frequency.{f}' for r in ['off', 'def']
                     for f in ['classified_pass', 'classified_rush']}
        self.assertEqual(ids, expected)
        for metric in c['metrics']:
            self.assertEqual(metric['definitionVersion'], '1.0.0')
            self.assertEqual(metric['populationVersion'], 'classified-scrimmage-v1')
            self.assertTrue(metric['formula'])
            self.assertTrue(metric['sourceFields'])
        self.assertFalse(c['temporal']['gamedayIsAvailability'])

    def test_weighted_sum_differs_from_weekly_average(self):
        output = model.evaluate(case('unequal_week_volumes'))
        # Independent manual ledger: two plays total +1; six plays total -2.
        self.assertEqual(Fraction(output['stats']['general']['epa_mean']), Fraction(-1, 8))
        weekly_average = (Fraction(1, 2) + Fraction(-2, 6)) / 2
        self.assertEqual(weekly_average, Fraction(1, 12))
        self.assertNotEqual(Fraction(output['stats']['classified_pass']['epa_mean']), weekly_average)

    def test_permutation_every_order_of_classification_fixture(self):
        c = case('classified_pass_vs_dropback')
        before = model.evaluate(c)
        for permutation in itertools.permutations(c['plays']):
            changed = copy.deepcopy(c)
            changed['plays'] = list(permutation)
            changed['games'].reverse()
            self.assertEqual(model.evaluate(changed), before)

    def test_permutation_larger_ledger(self):
        c = case('unequal_week_volumes')
        baseline = model.evaluate(c)
        random_source = random.Random(5105)
        for _ in range(40):
            random_source.shuffle(c['plays'])
            random_source.shuffle(c['games'])
            self.assertEqual(model.evaluate(c), baseline)

    def test_split_recombine_preserves_sufficient_statistics(self):
        c = case('partial_epa')
        whole = model.aggregate(c['plays'], 'A', 'off')['stats']
        for cut in range(len(c['plays']) + 1):
            a = model.aggregate(c['plays'][:cut], 'A', 'off')['stats']
            b = model.aggregate(c['plays'][cut:], 'A', 'off')['stats']
            for foundation in model.FOUNDATIONS:
                for key in ['eligible_n', 'epa_n', 'success_n', 'epa_missing_n', 'epa_nonfinite_n']:
                    self.assertEqual(a[foundation][key] + b[foundation][key], whole[foundation][key])
                summed = Fraction(a[foundation]['epa_sum'] or '0') + Fraction(b[foundation]['epa_sum'] or '0')
                self.assertEqual(summed, Fraction(whole[foundation]['epa_sum'] or '0'))
            self.assertEqual(model.aggregate(c['plays'][cut:] + c['plays'][:cut], 'A', 'off')['stats'], whole)

    def test_general_reconciles_partition_not_average_of_foundations(self):
        s = model.evaluate(case('partial_epa'))['stats']
        for key in ['eligible_n', 'epa_n', 'success_n', 'epa_missing_n', 'epa_nonfinite_n']:
            self.assertEqual(s['general'][key], s['classified_pass'][key] + s['classified_rush'][key])
        self.assertEqual(Fraction(s['general']['epa_sum']),
                         Fraction(s['classified_pass']['epa_sum']) + Fraction(s['classified_rush']['epa_sum']))
        self.assertNotEqual(Fraction(s['general']['epa_mean']),
                            (Fraction(s['classified_pass']['epa_mean']) + Fraction(s['classified_rush']['epa_mean'])) / 2)

    def test_future_addition_changes_no_observed_statistics(self):
        c = case('target_future_unknown_bound')
        before = model.evaluate(c)
        c['plays'] = [r for r in c['plays'] if r['game_id'] != 'future']
        c['games'] = [g for g in c['games'] if g['game_id'] != 'future']
        after = model.evaluate(c)
        for field in ['stats', 'metrics', 'coverage', 'observed_game_ids', 'game_ids']:
            self.assertEqual(before[field], after[field])

    def test_removing_source_data_never_increases_coverage(self):
        original = case('unequal_week_volumes')
        baseline = model.evaluate(original)['coverage']
        for count in range(len(original['plays']) + 1):
            changed = copy.deepcopy(original)
            changed['plays'] = changed['plays'][:count]
            coverage = model.evaluate(changed)['coverage']
            self.assertEqual(coverage['expected_games'], baseline['expected_games'])
            self.assertLessEqual(coverage['observed_complete_games'], baseline['observed_complete_games'])
            self.assertLessEqual(coverage['metric_observed_games'], baseline['metric_observed_games'])
        changed = copy.deepcopy(original)
        changed['games'][0]['pbp_status'] = 'SOURCE_UNKNOWN'
        self.assertEqual(model.evaluate(changed)['coverage']['source_ratio'], '1/2')

    def test_absence_is_not_zero_and_zero_is_not_success(self):
        missing = model.evaluate(case('only_unknown_source'))['stats']['general']
        zero = model.evaluate(case('zero_and_negative'))['stats']['classified_pass']
        empty = model.evaluate(case('no_eligible_plays'))['stats']['general']
        self.assertIsNone(missing['eligible_n'])
        self.assertIsNone(missing['epa_mean'])
        self.assertEqual(zero['epa_mean'], '0')
        self.assertEqual(zero['success_n'], 0)
        self.assertEqual(empty['eligible_n'], 0)
        self.assertIsNone(empty['epa_mean'])

    def test_identical_duplication_does_not_double_sample(self):
        c = case('classified_pass_vs_dropback')
        baseline = model.evaluate(c)
        c['plays'] = [copy.deepcopy(r) for _ in range(7) for r in c['plays']]
        duplicated = model.evaluate(c)
        self.assertEqual(duplicated['stats'], baseline['stats'])
        self.assertEqual(duplicated['coverage'], baseline['coverage'])
        self.assertEqual(duplicated['duplicate_rows_ignored'], 24)
        c['plays'][-1]['epa'] = '999'
        with self.assertRaisesRegex(ValueError, 'Conflicting identity'):
            model.evaluate(c)

    def test_split_overlapping_batches_require_deduplication(self):
        c = case('classified_pass_vs_dropback')
        baseline = model.aggregate(c['plays'], 'A', 'off')
        joined = c['plays'][:3] + c['plays'][2:]
        result = model.aggregate(joined, 'A', 'off')
        self.assertEqual(result['stats'], baseline['stats'])
        self.assertEqual(result['duplicate_rows_ignored'], 1)

    def test_attack_defense_reconcile_same_plays_every_foundation(self):
        for c in CASES:
            if 'expected_error' in c or not c['plays']:
                continue
            rows = [r for r in c['plays'] if r['season'] == c['query']['season']
                    and r['season_type'] == c['query']['phase']]
            off = model.aggregate(rows, 'A', 'off')['stats']
            defense = model.aggregate(rows, 'B', 'def')['stats']
            self.assertEqual(off, defense)

    def test_pass_attempt_and_dropback_are_distinct_from_classified_pass(self):
        rows = case('classified_pass_vs_dropback')['plays']
        self.assertEqual(sum(r['play_type'] == 'pass' for r in rows), 2)
        self.assertEqual(sum(r['qb_dropback'] for r in rows), 3)
        self.assertEqual(sum(r['pass_attempt'] for r in rows), 2)  # source includes sack
        self.assertEqual(sum(r['pass_attempt'] == 1 and r['sack'] == 0 for r in rows), 1)
        self.assertEqual(sum(r['qb_scramble'] for r in rows), 1)

    def test_mixed_seasons_or_phases_are_rejected_at_rollup_boundary(self):
        rows = case('seasons_phases_scoped_separately')['plays']
        with self.assertRaisesRegex(ValueError, 'Mixed season/phase'):
            model.aggregate(rows, 'A', 'off')
        with self.assertRaisesRegex(ValueError, 'Mixed season/phase'):
            model.aggregate([rows[0], rows[2]], 'A', 'off')

    def test_temporal_precision_boundary_and_availability(self):
        with self.assertRaisesRegex(ValueError, 'UTC Z'):
            model.instant('2026-09-28T09:00:00-03:00')  # adapter must normalize first
        with self.assertRaisesRegex(ValueError, 'second precision'):
            model.instant('2026-09-28T12:00:00.001Z')
        c = case('point_in_time_requires_receipts')
        c['games'][2]['ingested_at'] = c['query']['as_of_instant']
        self.assertEqual(model.evaluate(c)['game_ids'], [])
        c['calendar']['available_at'] = None
        with self.assertRaisesRegex(ValueError, 'Calendar not proven'):
            model.evaluate(c)

    def test_named_gap_cause_requires_evidence(self):
        c = case('only_unknown_source')
        c['games'][0]['pbp_status'] = 'INGESTION_FAILED'
        with self.assertRaisesRegex(ValueError, 'Missing source state evidence'):
            model.evaluate(c)
        c['games'][0]['source_state_evidence'] = 'SYNTHETIC_GAME_RUN_FAILURE'
        self.assertEqual(model.evaluate(c)['game_states'], {'unknown': 'INGESTION_FAILED'})

    def test_descriptive_comparison_integrity_is_not_statistical_minimum(self):
        a = case('single_tiny_positive')
        b = copy.deepcopy(a)
        b['query'].update(team='B', role='def')
        self.assertTrue(model.comparison_eligible(a, b))  # one play; no confidence claim
        b['query']['as_of_instant'] = '2026-09-29T12:00:00Z'
        self.assertFalse(model.comparison_eligible(a, b))
        a = case('partial_epa'); b = copy.deepcopy(a); b['query'].update(team='B', role='def')
        self.assertFalse(model.comparison_eligible(a, b))
        self.assertFalse(model.comparison_eligible(a, b, 'classified_pass'))

    def test_unknown_flag_invalid_schema_and_calendar_collision(self):
        c = case('single_tiny_positive')
        c['plays'][0]['qb_kneel'] = 2
        with self.assertRaisesRegex(ValueError, 'Invalid filter flag'):
            model.evaluate(c)
        c['plays'][0]['qb_kneel'] = 0
        del c['plays'][0]['play_id']
        with self.assertRaisesRegex(ValueError, 'Missing play field'):
            model.evaluate(c)
        c = case('single_tiny_positive')
        c['games'].append(copy.deepcopy(c['games'][0]))
        c['games'][1]['week'] = 2
        with self.assertRaisesRegex(ValueError, 'Conflicting identity'):
            model.evaluate(c)

    def test_tiny_sign_survives_exact_cancellation(self):
        c = case('single_tiny_positive')
        row = c['plays'][0]
        rows = []
        for i, value in enumerate(['100000000000000000000000000000000000',
                                   '0.000000000000000000000000000000000001',
                                   '-100000000000000000000000000000000000'], 1):
            r = copy.deepcopy(row); r['play_id'] = i; r['epa'] = value; rows.append(r)
        result = model.aggregate(rows, 'A', 'off')['stats']['general']
        self.assertEqual(Fraction(result['epa_sum']), Fraction(1, 10**36))
        self.assertEqual(Fraction(result['epa_mean']), Fraction(1, 3 * 10**36))
        self.assertEqual(result['success_n'], 2)

    def test_pit_unavailable_revisions_remain_expected(self):
        result = model.evaluate(case('point_in_time_requires_receipts'))
        self.assertEqual(result['coverage']['expected_games'], 3)
        self.assertEqual(result['coverage']['source_ratio'], '1/3')
        self.assertEqual(result['event_eligible_game_ids'], ['known-before', 'late-revision', 'unknown-availability'])
        c = case('single_tiny_positive')
        c['games'][0]['event_upper_bound'] = None
        changed = model.evaluate(c)
        self.assertIsNone(changed['coverage']['expected_games'])
        self.assertIsNone(changed['coverage']['source_ratio'])
        self.assertEqual(changed['coverage']['observed_complete_games'], 0)

    def test_metric_coverage_is_per_foundation_and_missing_epa_distinct(self):
        result = model.evaluate(case('unequal_week_volumes'))
        self.assertEqual(result['coverage']['metric_by_foundation']['classified_pass']['ratio'], '1')
        self.assertEqual(result['coverage']['metric_by_foundation']['classified_rush']['ratio'], '0')
        missing = model.evaluate(case('all_epa_missing'))
        empty = model.evaluate(case('no_eligible_plays'))
        self.assertEqual(missing['weekly_states']['1'], 'NO_EPA_OBSERVATIONS')
        self.assertEqual(empty['weekly_states']['1'], 'NO_ELIGIBLE_PLAYS')

    def test_a_complete_game_without_role_plays_does_not_disappear(self):
        c = case('single_tiny_positive')
        c['query']['role'] = 'def'  # A has offense only in this complete synthetic source.
        result = model.evaluate(c)
        self.assertEqual(result['coverage']['source_ratio'], '1')
        self.assertEqual(result['stats']['general']['eligible_n'], 0)
        self.assertIsNone(result['stats']['general']['epa_mean'])


if __name__ == '__main__':
    unittest.main()
