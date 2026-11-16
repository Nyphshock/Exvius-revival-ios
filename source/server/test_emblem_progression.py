from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import ffbe_player
from ffbe_config import (EMBLEM_CAMPAIGN_TOKEN, EMBLEM_EVENT_REQUEST, EMBLEM_MILESTONE_GROUP,
                         EMBLEM_MONTHLY_GROUP, EMBLEM_WEEKLY_GROUP)
from ffbe_state import State


class EmblemProgressionTests(unittest.TestCase):
    def test_adventurer_rewards_are_unavailable_before_release(self):
        player = SimpleNamespace()
        spec = {'sentinel': []}
        plaintext = '{"jQsE54Iz":[{"qo3PECw6":"mission"}]}'

        with patch.object(State, 'player', player), \
                patch('replay.enabled', return_value=True), \
                patch('replay.window', return_value={'from': date(2021, 3, 30)}):
            self.assertIs(ffbe_player.serve_emblem_event(spec, EMBLEM_EVENT_REQUEST), spec)
            self.assertIs(ffbe_player.credit_emblem_objectives(plaintext, spec), spec)
            self.assertEqual(ffbe_player.deliver_emblem_tier_mail(), [])

    def test_adventurer_rewards_unlock_on_march_31_2021(self):
        player = SimpleNamespace(
            emblem_objectives=lambda: [],
            emblem_event=lambda: {'campaign': '9000001'},
            emblem_tokens=lambda: 0,
        )
        with patch.object(State, 'player', player), \
                patch('replay.enabled', return_value=True), \
                patch('replay.window', return_value={'from': date(2021, 3, 31)}), \
                patch.object(ffbe_player, 'deliver_emblem_tier_mail', return_value=[]):
            result = ffbe_player.serve_emblem_event({}, EMBLEM_EVENT_REQUEST)

        self.assertEqual(result[EMBLEM_MONTHLY_GROUP][0][EMBLEM_CAMPAIGN_TOKEN], '9000001')
        self.assertIn(EMBLEM_WEEKLY_GROUP, result)
        self.assertIn(EMBLEM_MILESTONE_GROUP, result)


if __name__ == '__main__':
    unittest.main()
