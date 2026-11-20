from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from trial_progression import (CHECKPOINTS, active_checkpoint_missions, next_checkpoint_date,
                               release_is_available, mission_is_within_story_limit,
                               newly_completed_checkpoints, story_limit_for_checkpoint,
                               story_mission_is_available,
                               checkpoint_mission_is_available, _resolve_story_limit,
                               STORY_LIMIT_MISSION_OVERRIDES)


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

    def test_checkpoint_transition_pays_only_when_the_full_group_clears(self):
        day, missions = next((day, missions) for day, missions in CHECKPOINTS if len(missions) > 1)
        before = {mission for checkpoint, group in CHECKPOINTS if checkpoint < day for mission in group}
        before.update(set(missions) - {next(iter(missions))})
        after = before | set(missions)

        self.assertEqual(newly_completed_checkpoints(before, after), (day,))
        self.assertEqual(newly_completed_checkpoints(after, after), ())

    def test_completed_timeline_stops_at_global_closure(self):
        cleared = [mission for _day, missions in CHECKPOINTS for mission in missions]
        player = SimpleNamespace(data={'progress': {'cleared_missions': cleared}})
        self.assertTrue(release_is_available(player, '2024-10-30'))
        self.assertFalse(release_is_available(player, '2024-10-31'))

    def test_story_limit_uses_latest_entry_before_checkpoint_date(self):
        with patch('trial_progression._resolve_story_limit', return_value='story-end') as resolve:
            self.assertEqual(story_limit_for_checkpoint(date(2018, 5, 17)), 'story-end')
        resolve.assert_called_once_with('Energy Transfer Station', 'Beast Sealed Away')

    def test_unresolved_checkpoint_labels_use_verified_story_mission_endpoints(self):
        for checkpoint, mission in STORY_LIMIT_MISSION_OVERRIDES.items():
            with self.subTest(checkpoint=checkpoint):
                with patch('trial_progression._story_order_and_context', return_value=((mission,), {})):
                    self.assertEqual(story_limit_for_checkpoint(checkpoint), mission)

    def test_story_mission_limit_allows_endpoint_and_blocks_later_mission(self):
        order = ('story-before', 'story-end', 'story-after')
        self.assertTrue(mission_is_within_story_limit('story-before', 'story-end', order))
        self.assertTrue(mission_is_within_story_limit('story-end', 'story-end', order))
        self.assertFalse(mission_is_within_story_limit('story-after', 'story-end', order))

    def test_pending_trial_blocks_story_missions_after_endpoint(self):
        order = ('story-before', 'story-end', 'story-after')
        player = SimpleNamespace(data={'progress': {'cleared_missions': []}})
        with patch('trial_progression.story_limit_for_checkpoint', return_value='story-end'), \
                patch('trial_progression._story_order_and_context', return_value=(order, {})):
            self.assertTrue(story_mission_is_available(player, 'story-end'))
            self.assertFalse(story_mission_is_available(player, 'story-after'))

    def test_story_limit_resolves_mission_title_with_zone(self):
        names = {
            'F_TEXT_AREA_NAME': {"dwarves' forge": frozenset(('area-1',))},
            'F_TEXT_DUNGEON_NAME': {},
            'F_TEXT_MISSION': {"dwarves' forge - morphing flames": frozenset(('100',))},
        }
        context = {'100': {'dungeon': '500', 'area': 'area-1', 'names': {"dwarves' forge"}}}
        with patch('trial_progression._localized_names', side_effect=lambda table: names[table]), \
                patch('trial_progression._story_order_and_context', return_value=(('100',), context)):
            self.assertEqual(_resolve_story_limit("Dwarves' Forge", 'Morphing Flames'), '100')

    def test_story_limit_without_title_uses_last_mission_in_zone(self):
        names = {
            'F_TEXT_AREA_NAME': {'main colosseum': frozenset(('area-1',))},
            'F_TEXT_DUNGEON_NAME': {},
            'F_TEXT_MISSION': {},
        }
        context = {
            '100': {'dungeon': '500', 'area': 'area-1', 'names': {'main colosseum'}},
            '101': {'dungeon': '501', 'area': 'area-1', 'names': {'main colosseum'}},
        }
        with patch('trial_progression._localized_names', side_effect=lambda table: names[table]), \
                patch('trial_progression._story_order_and_context', return_value=(('100', '101'), context)):
            self.assertEqual(_resolve_story_limit('Main Colosseum', ''), '101')

    def test_chamber_of_awakening_five_star_is_held_until_first_trial_clear(self):
        player = SimpleNamespace(data={'progress': {'cleared_missions': []}})
        self.assertFalse(checkpoint_mission_is_available(player, '2110394'))
        player.data['progress']['cleared_missions'].append('8991101')
        self.assertTrue(checkpoint_mission_is_available(player, '2110394'))


if __name__ == '__main__':
    unittest.main()