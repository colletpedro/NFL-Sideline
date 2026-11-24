import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import evaluate_coverage as e
from compare_local_rules import fixture

BASE = e.ROOT / 'editorial/coverage-clarity-v1'
KNOWN = BASE / 'known-development'


class EvaluationTest(unittest.TestCase):
    def test_normalization_ignores_order_duplicates_market_and_decimal_spelling(self):
        root = fixture('synthetic', [('AAA', 'PASS', ['.2'] * 3, ['-.1'] * 3)])
        changed = copy.deepcopy(root)
        changed['evidence'].reverse()
        changed['evidence'] += copy.deepcopy(changed['evidence'])
        changed['market'] = {'irrelevant': 'value'}
        for item in changed['evidence']:
            item['value'] = str(float(item['value'])) + '0'
        self.assertEqual(e.canonical(root), e.canonical(changed))
        changed['game']['game_id'] = 'renamed'
        self.assertEqual(e.canonical(root, False), e.canonical(changed, False))
        self.assertNotEqual(e.canonical(root), e.canonical(changed))

    def test_real_evidence_difference_and_temporal_cut_are_not_normalized_away(self):
        root = fixture('synthetic', [('AAA', 'PASS', ['.2'] * 3, ['-.1'] * 3)])
        for field, value in [('value', '.3'), ('week', 4), ('sourceKey', 'other')]:
            changed = copy.deepcopy(root)
            changed['evidence'][0][field] = value
            self.assertNotEqual(e.canonical(root), e.canonical(changed))

    def test_distribution_denominators_nearest_rank_and_empty_sample(self):
        self.assertEqual(e.distribution([]), {'n': 0, 'values': [], 'median': None, 'p90': None, 'max': None})
        self.assertEqual(e.distribution(range(1, 11))['p90'], 9)
        self.assertEqual(e.distribution([1, 9])['median'], 5)
        self.assertEqual(e.summarize([])['encountersDenominator'], 0)

    def test_repetition_uses_six_pairs_and_normalizes_unicode_punctuation(self):
        d = dict(zip(e.FIELDS, ['O ataque de A teve EPA positivo.', 'O ATAQUE de A teve EPA positivo!', 'Outro texto', 'Sem par']))
        pairs = e.repetition(d)
        self.assertEqual(len(pairs), 6)
        self.assertFalse(pairs[0]['exact'])
        self.assertTrue(pairs[0]['normalized'])
        self.assertTrue(pairs[0]['sharedSentences'])

    def test_known_outputs_and_unchanged_selection_against_v2(self):
        manifest = e.read(BASE / 'manifest.json')
        for case in manifest['cases']:
            if not (case['knownSix'] or case['cohort'] == 'synthetic'):
                continue
            directory = KNOWN / case['gameId']
            selection, text = e.read(directory / 'selection.json'), e.read(directory / 'rendered.json')
            self.assertEqual(e.checks(selection, text)['issues'], [], case['gameId'])
            old = e.ROOT / 'editorial/local-rules-v2/regression-final'
            if case['cohort'] == 'synthetic': old /= 'synthetic'
            self.assertEqual(selection, e.read(old / case['gameId'] / 'selection.json'))

    def test_numeric_probe_detects_wrong_team_and_number_in_its_own_segment(self):
        directory = KNOWN / 'both-teams'
        selection, text = e.read(directory / 'selection.json'), e.read(directory / 'rendered.json')
        for replacement in ['AAA (EPA permitido)', 'BBB (EPA permitido)']:
            bad = copy.deepcopy(text)
            bad['vantagem_tatica'] = bad['vantagem_tatica'].replace('BBB (EPA permitido): +0,222', replacement + ': +0,999')
            self.assertTrue(any(i['type'] == 'NUMERIC_ATTRIBUTION' for i in e.checks(selection, bad)['issues']))

    def test_verdict_probe_detects_wrong_defense_and_erased_contrary_sign(self):
        directory = KNOWN / 'weekly-variation'
        selection, text = e.read(directory / 'selection.json'), e.read(directory / 'rendered.json')
        for old, new in [('contra a defesa de BBB', 'contra a defesa de AAA'), ('positivos e negativos', 'positivos')]:
            bad = copy.deepcopy(text)
            bad['veredito'] = bad['veredito'].replace(old, new)
            self.assertTrue(any(i['type'] == 'VERDICT_ATTRIBUTION_OR_SIGNAL' for i in e.checks(selection, bad)['issues']))

    def test_endpoint_semicolon_does_not_break_attack_defense_attribution(self):
        directory = KNOWN / 'both-teams'
        selection, text = e.read(directory / 'selection.json'), e.read(directory / 'rendered.json')
        text['vantagem_tatica'] = text['vantagem_tatica'].replace('AAA (ataque): +0,111 EPA;',
                'AAA (ataque): +0,111 EPA, faixa semanal: mínimo (0 < EPA < 0,0005); máximo (+0,116 EPA);')
        self.assertEqual(e.checks(selection, text)['issues'], [])
        bad = copy.deepcopy(text)
        bad['vantagem_tatica'] = bad['vantagem_tatica'].replace('BBB (EPA permitido): +0,222 EPA', 'BBB (EPA permitido): +0,999 EPA')
        self.assertTrue(any(i['type'] == 'NUMERIC_ATTRIBUTION' for i in e.checks(selection, bad)['issues']))

    def test_omitted_inventory_and_self_link_are_detected(self):
        directory = KNOWN / 'both-teams'
        selection, text = e.read(directory / 'selection.json'), e.read(directory / 'rendered.json')
        selection['document']['links'][0]['from'] = selection['document']['links'][0]['to']
        self.assertTrue(any(i['type'] == 'SELF_LINK' for i in e.checks(selection, text)['issues']))

    def test_exclusive_writes_and_freeze_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            e.write(root / 'source', {'value': 1})
            with self.assertRaises(FileExistsError): e.write(root / 'source', {})
            e.write(root / 'freeze.json', {'hashes': {'source': e.sha(root / 'source')}})
            with patch.object(e, 'ROOT', root):
                self.assertEqual(e.verify(root)['mismatches'], [])
                (root / 'source').write_text('modified')
                with self.assertRaises(ValueError): e.verify(root)

    def test_public_output_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'public').mkdir(); (root / 'alias').symlink_to(root / 'public')
            with self.assertRaises(ValueError): e.safe_directory(root / 'alias' / 'output')
            with self.assertRaises(ValueError): e.safe_directory(root / 'web-ui' / 'output')

    def test_html_escapes_text_attributes_and_details(self):
        data = e.read(BASE / 'known-development-metrics.json')
        data['cases'][0]['rendered']['fator_chave'] = '<script>alert("secret")</script>&'
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            e.write(p / 'metrics.json', data)
            e.build_html(BASE, p / 'metrics.json', p / 'page.html')
            source = (p / 'page.html').read_text()
            self.assertNotIn('<script>alert', source)
            self.assertIn('&lt;script&gt;', source)
            self.assertNotIn('innerHTML', source)
            self.assertNotIn('https://', source)
            self.assertNotIn('<link', source)
            self.assertIn("connect-src 'none'", source)
            self.assertIn('<details>', source)
            self.assertIn('controlled-claims-v5.0.1', source)
            self.assertNotIn('RENDERER_VERSIONS', source)


if __name__ == '__main__':
    unittest.main()
