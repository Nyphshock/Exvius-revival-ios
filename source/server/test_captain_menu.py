import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import captain_menu


class CaptainMenuTests(unittest.TestCase):
    def test_lists_owned_currency_store_before_replay_and_when_counter_shows_it(self):
        currency = "106300400"
        store = "900108"
        shops = SimpleNamespace(
            _held=lambda: {currency: 4859},
            _table=lambda *_: {store: {"kaG4xf3I": "5"}},
            _event_exchanges=lambda: {"exchanges": [{
                "store": store,
                "currency": currency,
                "name": "Mana Mystery Exchange",
                "event_areas": ["708"],
                "first_run": "2017-02-03",
                "rows": ["70701"],
            }]},
            _area_runs=lambda: {},
            counter_schedules=lambda **_: [{"za2xsDj5": store}],
        )
        week = ({}, "2016-12-16", None, None, set())

        with patch.dict(sys.modules, {"exvius_actions_shops": shops}):
            entries = captain_menu.entries(week=week)

        self.assertEqual([entry["store"] for entry in entries], [store])
        self.assertEqual(entries[0]["currency"], currency)
        self.assertEqual(entries[0]["name"], "Mana Mystery")


if __name__ == "__main__":
    unittest.main()