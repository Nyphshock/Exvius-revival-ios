import unittest
import json
from unittest.mock import patch

import ios_tables


class MissionTableEsperGateTests(unittest.TestCase):
    def test_esper_missions_keep_native_requirements_and_add_checkpoint_switches(self):
        rows = [
            {"qo3PECw6": "1110406", "juA0Z4m7": "82001210", "dIPkNn61": "10007600,82001300"},
            {"qo3PECw6": "8980104", "juA0Z4m7": "", "dIPkNn61": "18710210"},
            {"qo3PECw6": "1515007", "juA0Z4m7": "82008210", "dIPkNn61": "10115700,82008300"},
            {"qo3PECw6": "8993201", "juA0Z4m7": "", "dIPkNn61": "18900210"},
            {"qo3PECw6": "8995303", "juA0Z4m7": "", "dIPkNn61": "18901420"},
            {"qo3PECw6": "2000101", "juA0Z4m7": "0", "dIPkNn61": "10005101"},
            {"qo3PECw6": "2000201", "juA0Z4m7": "0", "dIPkNn61": "10005201"},
            {"qo3PECw6": "9001603", "juA0Z4m7": "", "dIPkNn61": "90001154"},
            {"qo3PECw6": "9000406", "uv60hgDW": "906", "juA0Z4m7": "0",
             "1x4bG2J8": "0", "dIPkNn61": ""},
            {"qo3PECw6": "other-906-mission", "uv60hgDW": "906", "juA0Z4m7": "0",
             "1x4bG2J8": "0", "dIPkNn61": ""},
            {"qo3PECw6": "4000101", "juA0Z4m7": "0", "dIPkNn61": "10000000"},
        ]
        parsed_rows = [(json.dumps(row), row, True) for row in rows]

        with patch.object(ios_tables, "_rows", return_value=parsed_rows), \
                patch.object(ios_tables, "_encrypt",
                             side_effect=lambda _key, row, _double: json.dumps(row)), \
                patch("reward_overrides.for_mission", return_value=False):
            raw, first_clears, gated = ios_tables.patch_mission_table(b"")
        patched = {str(row["qo3PECw6"]): row for row in map(json.loads, raw.decode("ascii").splitlines())}

        self.assertEqual(first_clears, 0)
        self.assertEqual(gated, 3)
        self.assertEqual(patched["1110406"]["juA0Z4m7"], "82001210,18710210")
        self.assertEqual(patched["1515007"]["juA0Z4m7"], "82008210,18900210,18901420")
        self.assertEqual(patched["2000201"]["juA0Z4m7"], "90001154")
        self.assertEqual(patched["2000101"]["juA0Z4m7"], "0")
        self.assertEqual(patched["4000101"]["juA0Z4m7"], "0")
        self.assertEqual(patched["9000406"]["uv60hgDW"], "9061")
        self.assertEqual(patched["other-906-mission"]["uv60hgDW"], "906")
        self.assertEqual(rows[0]["juA0Z4m7"], "82001210")

    def test_book_of_memories_area_stays_and_dread_frost_gets_a_vortex_alias(self):
        area_rows = [
            {"uv60hgDW": "906", "G4L0YIB2": "Book of Memories", "Z0EN6jSh": "99",
             "0HUPxDf1": "2110002", "RB8zTc9G": "1,9001,62,55:23"},
            {"uv60hgDW": "899", "G4L0YIB2": "normal area", "Z0EN6jSh": "10",
             "0HUPxDf1": "2110005", "RB8zTc9G": ""},
        ]
        parsed = [(json.dumps(row), row, True) for row in area_rows]

        with patch.object(ios_tables, "_rows", return_value=parsed), \
                patch.object(ios_tables, "_encrypt",
                             side_effect=lambda _key, row, _double: json.dumps(row)), \
                patch("vortex_order.priorities", return_value={"906": "100", "9061": "100"}), \
                patch("player_state._load_ndjson", return_value={
                    "90006": {"U9iHsau3": "90006", "0HUPxDf1": "9000006"}}), \
                patch("event_archive.events", return_value=[{
                    "area": "906", "name": "Dread Frost Arrives", "first_dungeon": "90006"}]):
            raw, added = ios_tables.patch_area_order(b"")

        served = {row["uv60hgDW"]: row for row in map(json.loads, raw.decode("ascii").splitlines())}
        self.assertEqual(added, 2)
        self.assertEqual(served["906"]["0HUPxDf1"], "2110002")
        self.assertEqual(served["906"]["RB8zTc9G"], "1,9001,62,55:23")
        self.assertEqual(served["9061"]["G4L0YIB2"], "Dread Frost Arrives")
        self.assertEqual(served["9061"]["0HUPxDf1"], "9000006")
        self.assertEqual(served["9061"]["RB8zTc9G"], "")
        from event_archive import client_gate_row
        self.assertEqual(client_gate_row({"uv60hgDW": "906", "U9iHsau3": "90006"}),
                 {"uv60hgDW": "9061", "U9iHsau3": "90006"})
        self.assertEqual(client_gate_row({"uv60hgDW": "899"}), {"uv60hgDW": "899"})

    def test_area_alias_changes_force_client_table_refetch(self):
        with patch("vortex_order.priorities", return_value={"906": "100", "9061": "100"}):
            self.assertGreaterEqual(ios_tables.table_bump(ios_tables.AREA), 2000)
        with patch("reward_overrides.enabled", return_value=False):
            self.assertGreaterEqual(ios_tables.table_bump(ios_tables.MISSION), 4000)

    def test_dungeon_table_moves_only_dread_frost_to_alias_area(self):
        rows = [
            {"U9iHsau3": "90006", "uv60hgDW": "906", "0HUPxDf1": "9000006"},
            {"U9iHsau3": "other-dungeon", "uv60hgDW": "906", "0HUPxDf1": "other-destination"},
        ]
        parsed = [(json.dumps(row), row, True) for row in rows]

        with patch.object(ios_tables, "_rows", return_value=parsed), \
                patch.object(ios_tables, "_encrypt",
                             side_effect=lambda _key, row, _double: json.dumps(row)):
            raw, changed = ios_tables.patch_dungeon_table(b"")

        served = {row["U9iHsau3"]: row for row in map(json.loads, raw.decode("ascii").splitlines())}
        self.assertEqual(changed, 1)
        self.assertEqual(served["90006"]["uv60hgDW"], "9061")
        self.assertEqual(served["90006"]["0HUPxDf1"], "9000006")
        self.assertEqual(served["other-dungeon"]["uv60hgDW"], "906")

    def test_dungeon_alias_change_forces_client_table_refetch(self):
        self.assertGreaterEqual(ios_tables.table_bump(ios_tables.DUNGEON), 4000)

    def test_mission_table_version_bump_invalidates_client_cache(self):
        with patch("reward_overrides.enabled", return_value=False):
            self.assertGreaterEqual(ios_tables.table_bump(ios_tables.MISSION), 2000)
        with patch("captain_menu.table_bump", return_value=17):
            self.assertEqual(ios_tables.table_bump(ios_tables.MAP_CHECKSUM), 1017)


class StoreItemStockFilterTests(unittest.TestCase):
    def test_removes_only_exhausted_medal_rows_and_preserves_encrypted_bytes(self):
        raw = b"ordinary\r\nexhausted\navailable"
        decoded = [
            {"YWF08vZS": "20", "6uIYE15X": "100"},
            {"YWF08vZS": "50", "6uIYE15X": "70701"},
            {"YWF08vZS": "50", "6uIYE15X": "70702"},
        ]

        filtered, removed = ios_tables.filter_store_item_rows(raw, decoded, {"70701"})

        self.assertEqual(filtered, b"ordinary\r\navailable")
        self.assertEqual(removed, 1)

    def test_exhausted_rows_force_a_stable_store_master_version(self):
        with patch("exvius_shop_catalogue.exhausted_medal_rows", return_value={"70701", "70702"}):
            first = ios_tables.table_bump(ios_tables.STORE_ITEMS)
        with patch("exvius_shop_catalogue.exhausted_medal_rows", return_value={"70702", "70701"}):
            second = ios_tables.table_bump(ios_tables.STORE_ITEMS)
        with patch("exvius_shop_catalogue.exhausted_medal_rows", return_value=set()):
            none = ios_tables.table_bump(ios_tables.STORE_ITEMS)

        self.assertGreaterEqual(first, 100000)
        self.assertEqual(first, second)
        self.assertEqual(none, 0)


if __name__ == "__main__":
    unittest.main()