import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import quest_trust


class QuestTrustTests(unittest.TestCase):
    def test_every_party_unit_gets_fixed_five_percent(self):
        calls = []
        player = SimpleNamespace(
            roster_row=lambda _iid: {'affinity_points': ['0']},
            gain_trust=lambda iid, amount: (calls.append((iid, amount)) or (0, amount, [])),
        )

        with patch.dict(os.environ, {'EXVIUS_QUEST_TRUST': '1'}):
            result = quest_trust.roll(player, ['unit-1', 'unit-2', 'unit-3'])

        self.assertEqual(calls, [('unit-1', 50), ('unit-2', 50), ('unit-3', 50)])
        self.assertEqual(result, {
            '_rewards': [],
            'unit-1': (0, 50),
            'unit-2': (0, 50),
            'unit-3': (0, 50),
        })


if __name__ == '__main__':
    unittest.main()