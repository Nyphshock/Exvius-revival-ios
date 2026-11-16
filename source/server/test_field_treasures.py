from types import SimpleNamespace
import unittest
from unittest.mock import patch

import exvius_field_treasures
from ffbe_state import State


class FieldTreasureTests(unittest.TestCase):
    def test_vortex_exploration_auto_collects_catalogued_treasure(self):
        mid = '7260101'
        attempt = {
            'mid': mid,
            'status': 'completed',
            'normal_rewards_recorded': True,
            'cleared': True,
        }
        player = SimpleNamespace(data={'exvius_repeat': {'attempt': attempt}})
        treasures = {
            '7260101': {
                'switch': '48326001',
                'rewards': '20:210000100:1',
                'resources': ['726010100'],
            },
            '7260103': {
                'switch': '48326003',
                'rewards': '21:315021300:1',
            },
        }
        request = {
            'jQsE54Iz': [{'qo3PECw6': mid, 'dIPkNn61': ''}],
            '09HRWXDf': [{}],
        }
        response = {'09HRWXDf': [{}]}

        with patch.object(State, 'player', player), \
                patch('player_state.mission_row', return_value={'Y4VoF8yu': '1', 'U9iHsau3': '72601'}), \
                patch('battle_content.resource_kind', return_value='exploration'), \
                patch.object(exvius_field_treasures, 'catalogue', return_value=treasures), \
                patch.object(exvius_field_treasures, '_credit', return_value=True) as credit:
            result = exvius_field_treasures._mission_treasures(response, request)

        self.assertEqual(credit.call_count, 2)
        credit.assert_any_call('7260101', treasures['7260101'])
        credit.assert_any_call('7260103', treasures['7260103'])
        self.assertEqual(attempt['field_treasures'], ['7260101', '7260103'])
        self.assertEqual(result['09HRWXDf'][0]['Z7G0yxXe'], '20:210000100:1')
        self.assertEqual(result['09HRWXDf'][0]['Mh1BA4uv'], '21:315021300:1')


if __name__ == '__main__':
    unittest.main()