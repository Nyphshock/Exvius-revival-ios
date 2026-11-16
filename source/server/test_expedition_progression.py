from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import Mock, mock_open, patch

import exvius_actions_expedition
import ffbe_player
import ios_tables
import ios_texts
from ffbe_config import (EXPEDITION_ORIGINAL_INDEX, EXPEDITION_UNLOCK_INDEX, EXPEDITION_UNLOCK_SWITCH,
                         PANEL_QUEST_UNLOCK_INDEX, PANEL_QUEST_UNLOCK_SWITCH)
from ffbe_state import State
from player_state import PlayerState
from trial_progression import CHECKPOINTS


class ExpeditionProgressionTests(unittest.TestCase):
    def player_before(self, day):
        cleared = [mission for checkpoint, missions in CHECKPOINTS if checkpoint < day for mission in missions]
        return PlayerState({"progress": {"cleared_missions": cleared, "switches": {}}})

    def test_feature_switch_preserves_original_unlock_and_tracks_each_profile(self):
        locked = self.player_before(date(2017, 6, 8))
        unlocked = self.player_before(date(2017, 7, 20))
        locked.grant_switch("101", EXPEDITION_ORIGINAL_INDEX)
        locked.grant_switch("101", EXPEDITION_UNLOCK_INDEX)

        def enabled(player, index):
            with patch.object(State, "player", player):
                result = ffbe_player.serve_switches({}, "75fYdNxq")
            bits = next(row["juA0Z4m7"] for row in result["8J1R5PXG"] if row["5opcUT9t"] == "101")
            offset, bit = divmod(index, 4)
            return bool(int(bits[offset], 16) & (8 >> bit))

        with patch("player_state._load_ndjson", return_value={}):
            self.assertFalse(enabled(locked, EXPEDITION_UNLOCK_INDEX))
            self.assertTrue(enabled(locked, EXPEDITION_ORIGINAL_INDEX))
            self.assertFalse(enabled(unlocked, EXPEDITION_UNLOCK_INDEX))
            unlocked.grant_switch("101", EXPEDITION_ORIGINAL_INDEX)
            self.assertTrue(enabled(unlocked, EXPEDITION_UNLOCK_INDEX))
            self.assertNotIn(EXPEDITION_UNLOCK_INDEX, unlocked.switches["101"])
            locked.data["progress"]["cleared_missions"].append("8993803")
            self.assertTrue(enabled(locked, EXPEDITION_UNLOCK_INDEX))

    def test_locked_requests_are_rejected_without_state_changes(self):
        player = self.player_before(date(2017, 6, 8))
        request_ids = ("hW0804Q9", "Ik142Ff6", "2pe3Xa8b", "r4A791RF", "vTgYyHM6",
                       "I8uq68c3", "0Fb87D0F")
        before = deepcopy(player.data)
        with patch.object(State, "player", player), patch.object(exvius_actions_expedition, "_note"):
            for request_id in request_ids:
                with self.subTest(request_id=request_id):
                    response = {"sentinel": []}
                    self.assertIs(exvius_actions_expedition.HANDLERS[request_id](response, {}), response)
                    self.assertEqual(player.data, before)

        handler = Mock(return_value={"allowed": True})
        with patch.object(State, "player", self.player_before(date(2017, 7, 20))):
            self.assertEqual(exvius_actions_expedition._expedition_guard(handler)({}, {}), {"allowed": True})
        handler.assert_called_once()

    def test_expedition_tables_use_new_switch_and_refetch_versions(self):
        function = {"G1nfeht7": "FUNCTION_REEL_EXPEDITION", "5U0bAqgR": "1", "juA0Z4m7": "10012300"}
        raw = (ios_tables._encrypt(ios_tables.FUNCTION[2], function, False) + "\n").encode("ascii")
        patched, changed = ios_tables._patch_feature_function(raw, "FUNCTION_REEL_EXPEDITION",
                                                               EXPEDITION_UNLOCK_SWITCH)
        row = next(ios_tables._rows(patched, ios_tables.FUNCTION[2]))[1]
        self.assertEqual(changed, 1)
        self.assertEqual(row["juA0Z4m7"], EXPEDITION_UNLOCK_SWITCH)

        original = {"8vAYn3IX": "10012300", "5opcUT9t": "101", "QLfe23bu": str(EXPEDITION_ORIGINAL_INDEX)}
        raw = (ios_tables._encrypt(ios_tables.SWITCH[2], original, False) + "\n").encode("ascii")
        patched, changed = ios_tables._patch_feature_switch(raw, EXPEDITION_UNLOCK_SWITCH, EXPEDITION_UNLOCK_INDEX)
        rows = [row for _, row, _ in ios_tables._rows(patched, ios_tables.SWITCH[2])]
        self.assertEqual(changed, 1)
        self.assertEqual(rows[0], original)
        self.assertEqual(rows[1], {"8vAYn3IX": EXPEDITION_UNLOCK_SWITCH, "5opcUT9t": "101",
                                   "QLfe23bu": str(EXPEDITION_UNLOCK_INDEX)})
        self.assertEqual(ios_tables._patch_feature_switch(patched, EXPEDITION_UNLOCK_SWITCH,
                                                           EXPEDITION_UNLOCK_INDEX), (patched, 0))
        for spec in (ios_tables.FUNCTION, ios_tables.SWITCH):
            self.assertGreater(ios_tables.table_bump(spec), 1000)

    def test_served_tables_include_both_panel_and_expedition_gates(self):
        examples = (
            (ios_tables.FUNCTION, [
                {"G1nfeht7": "FUNCTION_PANEL_QUEST", "juA0Z4m7": "0"},
                {"G1nfeht7": "FUNCTION_REEL_EXPEDITION", "juA0Z4m7": "10012300"},
            ]),
            (ios_tables.SWITCH, [
                {"8vAYn3IX": "10012300", "5opcUT9t": "101", "QLfe23bu": str(EXPEDITION_ORIGINAL_INDEX)},
            ]),
        )
        for spec, original in examples:
            with self.subTest(table=spec[0]):
                raw = ("\n".join(ios_tables._encrypt(spec[2], row, False) for row in original) + "\n").encode()
                with patch.object(ios_texts, "wants", return_value=False), \
                        patch.object(ios_tables, "source_table", return_value="original.dat"), \
                        patch("builtins.open", mock_open(read_data=raw)):
                    data, _ = ios_tables.serve(f"mst/Ver9999_{spec[1]}.dat")
                rows = [row for _, row, _ in ios_tables._rows(data, spec[2])]
                if spec == ios_tables.FUNCTION:
                    self.assertEqual([row["juA0Z4m7"] for row in rows],
                                     [PANEL_QUEST_UNLOCK_SWITCH, EXPEDITION_UNLOCK_SWITCH])
                else:
                    self.assertEqual(rows[0], original[0])
                    self.assertEqual([(row["8vAYn3IX"], row["QLfe23bu"]) for row in rows[1:]],
                                     [(PANEL_QUEST_UNLOCK_SWITCH, str(PANEL_QUEST_UNLOCK_INDEX)),
                                      (EXPEDITION_UNLOCK_SWITCH, str(EXPEDITION_UNLOCK_INDEX))])


if __name__ == "__main__":
    unittest.main()
