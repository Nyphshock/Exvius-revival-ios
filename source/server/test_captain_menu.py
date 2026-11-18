import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import captain_menu
import exvius_shop_catalogue


class CaptainMenuTests(unittest.TestCase):
    def test_builds_flat_item_list_across_stores_and_hides_exhausted_rows(self):
        stores = [
            {"store": "900108", "currency": "106300400", "name": "First Exchange"},
            {"store": "900109", "currency": "106300500", "name": "Second Exchange"},
        ]
        shops = SimpleNamespace(_rows=lambda *_: [
            {"Z20mNDvL": "900108", "YWF08vZS": "50", "6uIYE15X": "70701"},
            {"Z20mNDvL": "900108", "YWF08vZS": "50", "6uIYE15X": "70702"},
            {"Z20mNDvL": "900109", "YWF08vZS": "50", "6uIYE15X": "70703"},
        ])
        offers = {
            "one": {"medal": "70701"},
            "sold": {"medal": "70702"},
            "two": {"medal": "70703"},
        }

        with patch.dict(sys.modules, {"exvius_actions_shops": shops}):
            with patch.object(exvius_shop_catalogue, "catalogue", return_value=([], [], offers)):
                with patch.object(exvius_shop_catalogue, "labels", return_value={
                    "one": {"name": "Phoenix Down"}, "two": {"name": "Hero Ring"},
                }):
                    with patch.object(exvius_shop_catalogue, "exhausted_medal_rows",
                                      return_value={"70702"}):
                        items = captain_menu.exchange_items(stores)

        self.assertEqual({(item["store"], item["currency"]) for item in items}, {
            ("900108", "106300400"), ("900109", "106300500"),
        })
        self.assertTrue(any("Phoenix Down" in item["name"] for item in items))
        self.assertTrue(any("Hero Ring" in item["name"] for item in items))

    def test_king_menu_starts_with_one_item_exchange_button(self):
        items = [
            {"store": "900108", "currency": "106300400", "name": "Phoenix Down - First"},
            {"store": "900109", "currency": "106300500", "name": "Hero Ring - Second"},
        ]
        labels, body = captain_menu.script(items)
        root = captain_menu._commands(body, labels[0], labels[1])
        choice = next(command for command in root if command[1] == 0x15)
        payload = choice[2]
        options = [int.from_bytes(payload[1 + 5 * index:5 + 5 * index], "big")
                   for index in range(payload[0])]
        stores = [int.from_bytes(data, "big") for _, command, data in captain_menu._commands(
            body, labels[2], labels[-1]) if command == 0x44]

        self.assertEqual(options, [captain_menu.TEXT_ITEM_EXCHANGE, captain_menu.LEAVE_TEXT])
        self.assertEqual(stores, [900108, 900109])

    def test_flat_item_menu_paginates_products_three_at_a_time(self):
        items = [{"store": str(900108 + index), "currency": str(106300400 + index),
                  "name": "Item " + str(index)} for index in range(4)]
        labels, body = captain_menu.script(items)
        first_page = captain_menu._commands(body, labels[1], labels[2])
        second_page = captain_menu._commands(body, labels[2], labels[3])

        def choices(commands):
            command = next(row for row in commands if row[1] == 0x15)
            payload = command[2]
            return [int.from_bytes(payload[1 + 5 * index:5 + 5 * index], "big")
                    for index in range(payload[0])]

        self.assertEqual(choices(first_page), [
            captain_menu.TEXT_ENTRY, captain_menu.TEXT_ENTRY + 1, captain_menu.TEXT_ENTRY + 2,
            captain_menu.NEXT_TEXT, captain_menu.TEXT_BACK,
        ])
        self.assertEqual(choices(second_page), [
            captain_menu.TEXT_ENTRY + 3, captain_menu.TEXT_BACK,
        ])

    def test_menu_signature_changes_when_layout_revision_changes(self):
        entries = [{"store": "900108", "currency": "106300400", "name": "Exchange"}]
        with patch.object(captain_menu, "MENU_LAYOUT_REVISION", 1):
            old_signature = captain_menu._menu_signature(entries)
        with patch.object(captain_menu, "MENU_LAYOUT_REVISION", 2):
            new_signature = captain_menu._menu_signature(entries)

        self.assertNotEqual(old_signature, new_signature)

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