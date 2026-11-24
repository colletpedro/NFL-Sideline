"""Independent mutations of the visual fixture contract; no engine/provider calls."""
import copy
import json
import unittest
from verify_visual_contract import CONTRACT, ContractError, check_schema, SCHEMA, display_value, validate, verify_fixtures

class VisualContractTest(unittest.TestCase):
    def fixture(self, name='opportunity'):
        return json.loads((CONTRACT / 'fixtures/valid' / (name + '.json')).read_text())

    def reject(self, doc, code):
        with self.assertRaises(ContractError) as error:
            validate(doc)
        self.assertEqual(code, error.exception.code)

    def test_all_fixtures_and_exact_failure_codes(self):
        self.assertEqual(verify_fixtures()['status'], 'PASS')

    def test_decimal_sign_and_rounding_boundaries(self):
        for value, expected in [('0','0,000'),('-0.000','0,000'),('0.00049','0 < EPA < 0,0005'),
                                ('-0.00049','-0,0005 < EPA < 0'),('0.0005','+0,001'),
                                ('-0.0005','-0,001'),('1.060','+1,060')]:
            with self.subTest(value=value): self.assertEqual(display_value(value), expected)

    def test_renaming_teams_preserves_relations_and_highlights(self):
        doc = self.fixture('both-sides')
        original = copy.deepcopy(doc)
        doc['game']['awayTeam'], doc['game']['homeTeam'] = 'ZZZ', 'CCC'
        rename = {'AAA':'ZZZ','BBB':'CCC'}
        for e in doc['evidence']: e['team'] = rename[e['team']]
        for e in doc['encounters']:
            e['attackTeam'], e['defenseTeam'] = rename[e['attackTeam']], rename[e['defenseTeam']]
        validate(doc)  # IDs are opaque; never parse team names from identifiers.
        self.assertEqual(doc['findings'], original['findings'])
        self.assertEqual(doc['presentation'], original['presentation'])

    def test_top_level_array_order_is_not_analytical_merit(self):
        doc = self.fixture('tie')
        for key in ['evidence','series','encounters','findings','restrictions']: doc[key].reverse()
        validate(doc)
        self.assertEqual(len(doc['presentation']['highlightFindingIds']), 2)

    def test_removing_evidence_does_not_silently_zero_fill(self):
        doc = self.fixture()
        doc['evidence'].pop()
        self.reject(doc, 'INVALID_REFERENCE')

    def test_scalar_types_and_nested_unknown_fields(self):
        doc = self.fixture()
        doc['publicationApproved'] = 0
        self.reject(doc, 'SCHEMA')
        doc = self.fixture()
        doc['findings'][0]['confidence'] = 0.9
        self.reject(doc, 'SCHEMA')

    def test_unsupported_schema_keyword_fails_closed(self):
        with self.assertRaises(ContractError) as error:
            check_schema({}, {'allOf':[]})
        self.assertEqual(error.exception.code, 'UNSUPPORTED_SCHEMA')

    def test_declared_date_does_not_create_temporal_guarantee(self):
        doc = self.fixture()
        doc['scope']['declaredAsOfDate'] = '2026-09-26'
        validate(doc)
        doc['scope']['temporalGuarantee'] = 'POINT_IN_TIME_VERIFIED'
        self.reject(doc, 'SCHEMA')

    def test_same_week_is_rejected_even_with_old_declared_date(self):
        doc = self.fixture()
        doc['scope']['declaredAsOfDate'] = '2026-09-01'
        doc['evidence'][0]['week'] = doc['game']['week']
        self.reject(doc, 'TEMPORAL_LEAK')

    def test_unavailable_encounter_cannot_be_highlighted(self):
        doc = self.fixture('missing')
        doc['presentation']['highlightFindingIds'] = ['f:AAA:PASS']
        self.reject(doc, 'INVALID_REFERENCE')

    def test_independent_opportunity_is_not_direct_conflict(self):
        doc = self.fixture('independent-opportunity')
        validate(doc)
        doc['links'][0]['relation'] = 'DIRECT_CONFLICT'
        self.reject(doc, 'SCHEMA')

    def test_general_grouping_cannot_hide_other_team(self):
        doc = self.fixture('general-represented')
        target = next(e for e in doc['encounters'] if e['state'] == 'REPRESENTED_BY')
        target['representedByFindingIds'] = ['missing']
        self.reject(doc, 'INVALID_REFERENCE')

if __name__ == '__main__': unittest.main()
