from datetime import date
from types import SimpleNamespace
import unittest

from trial_progression import (CHECKPOINTS, active_checkpoint_missions, next_checkpoint_date,
                               release_is_available)


class TrialProgressionTests(unittest.TestCase):
    def test_initial_profile_is_before_intangir_checkpoint(self):
        player = SimpleNamespace(data={'progress': {'cleared_missions': []}})
        self.assertEqual(next_checkpoint_date(player), date(2016, 8, 25))
        self.assertEqual(active_checkpoint_missions(player), frozenset(('8991101',)))

    def test_clear_advances_only_that_profiles_checkpoint(self):
        first = SimpleNamespace(data={'progress': {'cleared_missions': ['8991101']}})
        second = SimpleNamespace(data={'progress': {'cleared_missions': []}})
        self.assertEqual(next_checkpoint_date(first), date(2016, 11, 24))
        self.assertEqual(next_checkpoint_date(second), date(2016, 8, 25))

    def test_content_on_checkpoint_date_waits_for_clear(self):
        player = SimpleNamespace(data={'progress': {'cleared_missions': []}})
        self.assertTrue(release_is_available(player, '2016-08-24'))
        self.assertFalse(release_is_available(player, '2016-08-25'))

    def test_same_date_trials_must_both_be_cleared(self):
        cleared = [mission for day, missions in CHECKPOINTS if day < date(2019, 3, 21)
                   for mission in missions]
        cleared.append('8980200')
        player = SimpleNamespace(data={'progress': {'cleared_missions': cleared}})
        self.assertEqual(next_checkpoint_date(player), date(2019, 3, 21))
        player.data['progress']['cleared_missions'].append('8993501')
        self.assertEqual(next_checkpoint_date(player), date(2019, 4, 11))

    def test_completed_timeline_stops_at_global_closure(self):
        cleared = [mission for _day, missions in CHECKPOINTS for mission in missions]
        player = SimpleNamespace(data={'progress': {'cleared_missions': cleared}})
        self.assertTrue(release_is_available(player, '2024-10-30'))
        self.assertFalse(release_is_available(player, '2024-10-31'))


if __name__ == '__main__':
    unittest.main()