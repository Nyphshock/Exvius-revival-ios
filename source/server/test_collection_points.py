from types import SimpleNamespace
import unittest
from unittest.mock import patch

import collection_points
from ffbe_state import State


class CollectionPointTests(unittest.TestCase):
    def test_catalogued_vortex_exploration_serves_collection_rewards(self):
        mid = '7260101'
        attempt = {'mid': mid}
        player = SimpleNamespace(data={'exvius_repeat': {'attempt': attempt}}, mode='normal', dirty=False)
        catalogue = {'missions': {mid: []}}

        with patch.object(State, 'player', player), \
                patch.object(State, 'state_dirty', False), \
                patch.object(collection_points, '_doc', return_value=catalogue), \
                patch.object(collection_points, 'roll', return_value={'10000': '20:123:1'}), \
                patch.object(collection_points, 'enabled', return_value=True):
            result = collection_points.serve({}, mid, True)

        self.assertEqual(result[collection_points.GROUP], [{
            collection_points.POINT: '10000',
            collection_points.NUMBER: '1',
            collection_points.REWARDS: '20:123:1',
        }])
        self.assertEqual(attempt['collection'], {'10000': '20:123:1'})


if __name__ == '__main__':
    unittest.main()