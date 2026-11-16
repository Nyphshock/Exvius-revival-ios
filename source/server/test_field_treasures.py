from types import SimpleNamespace
import unittest
from unittest.mock import patch

import exvius_field_treasures
from ffbe_state import State


class FieldTreasureTests(unittest.TestCase):
    def test_vortex_exploration_auto_collects_catalogued_treasure(self):
        mid = '7110101'
        attempt = {
            'mid': mid,
            'status': 'completed',
            'normal_rewards_recorded': True,
            'cleared': True,
        }
        player = SimpleNamespace(data={'exvius_repeat': {'attempt': attempt}})
        treasure = {
            'switch': '40010001',
            'rewards': '20:101000200:1',
            'missions': [mid],
        }
        request = {
            'jQsE54Iz': [{'qo3PECw6': mid, 'dIPkNn61': ''}],
            '09HRWXDf': [{}],
        }
        response = {'09HRWXDf': [{}]}

        with patch.object(State, 'player', player), \
                patch('player_state.mission_row', return_value={'Y4VoF8yu': '2'}), \
                patch.object(exvius_field_treasures, 'catalogue', return_value={'123': treasure}), \
                patch.object(exvius_field_treasures, '_credit', return_value=True) as credit:
            result = exvius_field_treasures._mission_treasures(response, request)

        credit.assert_called_once_with('123', treasure)
        self.assertEqual(attempt['field_treasures'], ['123'])
        self.assertEqual(result['09HRWXDf'][0]['Z7G0yxXe'], '20:101000200:1')


if __name__ == '__main__':
    unittest.main()