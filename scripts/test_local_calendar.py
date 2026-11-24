import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import polars as pl
import export_local_calendar as cal
from evaluate_coverage import ROOT, read


class LocalCalendarTest(unittest.TestCase):
    def manifest(self):
        m = read(ROOT / 'editorial/coverage-clarity-v1/manifest.json')
        return {'cases': [c for c in m['cases'] if c['gameId'] == '2025_08_CHI_BAL']}

    def test_known_gaps_are_confirmed_by_complete_schedule_not_metric_absence(self):
        result = cal.build(self.manifest())
        gaps = result['cases']['2025_08_CHI_BAL']['gaps']
        self.assertEqual({(g['team'], g['week']) for g in gaps if g['byeConfirmed']}, {('BAL', 7), ('CHI', 5)})
        self.assertTrue(result['schedules'][2025]['completeModernRegularSeason'])
        self.assertEqual(set(result['schedules'][2025]['games'][0]), {'game_id', 'season', 'week', 'home_team', 'away_team'})

    def test_missing_scheduled_week_does_not_become_bye(self):
        m = self.manifest()
        m['cases'][0]['descriptors']['missingExpectedWeeks'] = {'CHI': [6]}
        result = cal.build(m)['cases']['2025_08_CHI_BAL']
        self.assertFalse(result['byeConfirmed'])
        self.assertTrue(result['unknownGap'])
        self.assertEqual(result['gaps'][0]['scheduledGameIds'], ['2025_06_CHI_WAS'])

    def test_incomplete_calendar_cannot_confirm_bye(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / 'etl-pipeline/data/raw/schedules/season=2025/schedules.parquet'
            p.parent.mkdir(parents=True)
            pl.read_parquet(ROOT / p.relative_to(root)).head(2).write_parquet(p)
            with patch.object(cal, 'ROOT', root), patch.object(cal, 'rel', lambda p: str(p.relative_to(root))):
                result = cal.build(self.manifest())
            self.assertFalse(result['schedules'][2025]['completeModernRegularSeason'])
            self.assertFalse(result['cases']['2025_08_CHI_BAL']['byeConfirmed'])
            self.assertTrue(result['cases']['2025_08_CHI_BAL']['unknownGap'])


if __name__ == '__main__':
    unittest.main()
