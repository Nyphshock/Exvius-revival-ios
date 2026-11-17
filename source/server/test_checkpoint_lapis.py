from types import SimpleNamespace
import unittest
from unittest.mock import patch

import ffbe_battle
from ffbe_config import RESULT_TAG, SWITCH_TYPE_MISSION
from trial_progression import CHECKPOINTS, CHECKPOINT_LAPIS_BONUS


class CheckpointLapisTests(unittest.TestCase):
    def test_completed_checkpoint_group_pays_once_and_shows_bonus(self):
        day, missions = next((day, group) for day, group in CHECKPOINTS if len(group) > 1)
        pending = next(iter(missions))
        cleared = {mission for checkpoint, group in CHECKPOINTS if checkpoint < day for mission in group}
        cleared.update(set(missions) - {pending})
        currencies = {'lapis_free': 0, 'lapis_paid': 0}

        def clear_mission(mission_id):
            if mission_id not in cleared:
                cleared.add(mission_id)
            return []

        def add_currency(kind, amount):
            currencies[kind] = currencies.get(kind, 0) + amount
            return currencies[kind]

        player = SimpleNamespace(data={'progress': {'cleared_missions': cleared}},
                                 switches={SWITCH_TYPE_MISSION: set()}, mode='live', currencies=currencies,
                                 clear_mission=clear_mission, add_currency=add_currency)
        spec = {RESULT_TAG: [{}]}

        with patch.object(ffbe_battle.State, 'player', player), \
                patch.object(ffbe_battle.State, 'state_dirty', False), \
                patch('ffbe_battle.mission_wave_count', return_value=0), \
                patch('ffbe_battle.story_beast_for_mission', return_value=None):
            ffbe_battle.grant_cleared_mission(spec, pending)
            self.assertEqual(currencies['lapis_free'], CHECKPOINT_LAPIS_BONUS)
            self.assertEqual(spec[RESULT_TAG][0]['p1K5NecV'], '50:1:50000')

            ffbe_battle.grant_cleared_mission(spec, pending)

        self.assertEqual(currencies['lapis_free'], CHECKPOINT_LAPIS_BONUS)
        self.assertEqual(spec[RESULT_TAG][0]['p1K5NecV'], '50:1:50000')


if __name__ == '__main__':
    unittest.main()