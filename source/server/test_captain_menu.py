import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import captain_menu
import exvius_shop_catalogue


class CaptainMenuTests(unittest.TestCase):
    def test_lists_every_owned_event_exchange(self):
        shops = SimpleNamespace(
            _held=lambda: {"106300400": 10, "106300500": 20},
            _table=lambda name, *_: ({
                "900108": {"kaG4xf3I": "5"}, "900109": {"kaG4xf3I": "5"},
            } if name == "F_TOWN_STORE_MST" else {
                "70701": {"kR4n5DxP": "2"}, "70702": {"kR4n5DxP": "2"},
            }),
            _rows=lambda *_: [
                {"Z20mNDvL": "900108", "YWF08vZS": "50", "6uIYE15X": "70701"},
                {"Z20mNDvL": "900109", "YWF08vZS": "50", "6uIYE15X": "70702"},
            ],
            _event_exchanges=lambda: {"exchanges": [
                {"store": "900108", "currency": "106300400", "name": "First Exchange",
                 "event_areas": ["708"], "first_run": "2017-02-03", "rows": ["70701"]},
                {"store": "900109", "currency": "106300500", "name": "Second Exchange",
                 "event_areas": ["709"], "first_run": "2017-02-10", "rows": ["70702"]},
            ]},
            _area_runs=lambda: {},
        )

        with patch.dict(sys.modules, {"exvius_actions_shops": shops}):
            with patch.object(exvius_shop_catalogue, "shared_medal_counts", return_value={}):
                entries = captain_menu.entries(week=({}, "2017-02-17", None, None, set()))

        self.assertEqual({entry["store"] for entry in entries}, {"900108", "900109"})
        self.assertEqual({entry["currency"] for entry in entries}, {"106300400", "106300500"})

    def test_lists_owned_currency_store_before_replay_and_when_counter_shows_it(self):
        currency = "106300400"
        store = "900108"
        shops = SimpleNamespace(
            _held=lambda: {currency: 4859},
            _table=lambda name, *_: ({store: {"kaG4xf3I": "5"}} if name == "F_TOWN_STORE_MST"
                                     else {"70701": {"kR4n5DxP": "2"}}),
            _rows=lambda *_: [],
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
            with patch.object(exvius_shop_catalogue, "shared_medal_counts", return_value={}):
                entries = captain_menu.entries(week=week)

        self.assertEqual([entry["store"] for entry in entries], [store])
        self.assertEqual(entries[0]["currency"], currency)
        self.assertEqual(entries[0]["name"], "Mana Mystery")

    def test_hides_exchange_when_all_stock_is_exhausted(self):
        currency = "106300400"
        store = "900108"
        shops = SimpleNamespace(
            _held=lambda: {currency: 4859},
            _table=lambda name, *_: ({store: {"kaG4xf3I": "5"}} if name == "F_TOWN_STORE_MST"
                                     else {"70701": {"kR4n5DxP": "1", "x0NDnEC9": "1"}}),
            _rows=lambda *_: [{"Z20mNDvL": store, "YWF08vZS": "50", "6uIYE15X": "70701"}],
            _event_exchanges=lambda: {"exchanges": [{
                "store": store,
                "currency": currency,
                "name": "Mana Mystery Exchange",
                "event_areas": ["708"],
                "first_run": "2017-02-03",
                "rows": ["70701"],
            }]},
            _area_runs=lambda: {},
        )
        week = ({}, "2016-12-16", None, None, set())

        with patch.dict(sys.modules, {"exvius_actions_shops": shops}):
            with patch.object(exvius_shop_catalogue, "shared_medal_counts", return_value={"70701": 1}):
                entries = captain_menu.entries(week=week)

        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()