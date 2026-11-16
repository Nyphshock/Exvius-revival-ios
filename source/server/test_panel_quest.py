from datetime import date
import json
import unittest
from unittest.mock import patch

import ffbe_player
import exvius_actions_expedition
import ios_tables
import ios_texts
from ffbe_config import PANEL_QUEST_UNLOCK_INDEX, PANEL_QUEST_UNLOCK_SWITCH
from ffbe_state import State
from player_state import PlayerState
from trial_progression import CHECKPOINTS


class PanelQuestTests(unittest.TestCase):
    def player_before(self, day):
        cleared = [
            mission for checkpoint, missions in CHECKPOINTS if checkpoint < day for mission in missions
        ]
        return PlayerState({"progress": {"cleared_missions": cleared, "switches": {}}})

    def test_friend_invite_is_cleared_but_still_claimable_once(self):
        player = self.player_before(date(2021, 10, 28))
        meta = {"family": "panelquest", "schedule": "10001", "cond": "14", "param": "", "max": 1}
        index = {"1000103": meta}
        tables = {"groups": {"10001": {"fK3W9qYA": "100"}},
                  "quests": {"10001": [{"V36ygRYs": "1000103"}]}}
        claim = json.dumps({"QxrSeO56": [{"fK3W9qYA": "100", "zF6QIY2r": "10001",
                                         "V36ygRYs": "1000103"}]})
        reward = [{"kind": "50", "id": "1", "count": 300}]
        with patch.object(State, "player", player), \
                patch.object(ffbe_player, "_quest_index", return_value=index), \
                patch.object(ffbe_player, "panel_quest_tables", return_value=tables), \
                patch.object(ffbe_player, "_quest_reward", return_value=reward), \
                patch.object(player, "_can_credit", return_value=True), \
                patch.object(player, "_grant_items", return_value=reward) as grant:
            row = ffbe_player.panel_quest_info_rows([("10001", tables["groups"]["10001"])])[0]
            self.assertEqual((row["oz5Vt6AR"], row["Ag8bisM0"], row["QCLs6SV8"]), ("1", "1", "0"))
            ffbe_player.claim_panel_quest(None, "6uue8aKx", claim)
            ffbe_player.claim_panel_quest(None, "6uue8aKx", claim)
            self.assertEqual(grant.call_count, 1)
            self.assertEqual(ffbe_player.player_progress("100106", dict(meta, family="spchallenge")), 0)

    def test_panel_unlocks_only_after_preceding_checkpoint(self):
        before = self.player_before(date(2020, 3, 5))
        after = self.player_before(date(2021, 10, 28))
        tables = {"groups": {"10001": {"fK3W9qYA": "100"}}, "quests": {}}
        with patch.object(ffbe_player, "panel_quest_tables", return_value=tables):
            with patch.object(State, "player", before):
                self.assertEqual(ffbe_player.panel_quest_picked(), [])
            with patch.object(State, "player", after):
                self.assertEqual(len(ffbe_player.panel_quest_picked()), 1)

    def test_locked_panel_cannot_serve_or_pay_rewards(self):
        player = self.player_before(date(2020, 3, 5))
        meta = {"family": "panelquest", "schedule": "10001", "cond": "14", "param": "", "max": 1}
        claim = json.dumps({"QxrSeO56": [{"fK3W9qYA": "100", "zF6QIY2r": "10001",
                                         "V36ygRYs": "1000103"}]})
        with patch.object(State, "player", player), \
                patch.object(ffbe_player, "_quest_index", return_value={"1000103": meta}), \
                patch.object(player, "_grant_items") as grant:
            response = ffbe_player.serve_panel_quest(None, "GVyjSq16")
            self.assertEqual(response["nnR59m0N"], [])
            self.assertEqual(response["ELPwhZj0"], [])
            ffbe_player.claim_panel_quest(None, "6uue8aKx", claim)
            exvius_actions_expedition.panel_extra({}, {"QxrSeO56": [{"fK3W9qYA": "100",
                                                                     "zF6QIY2r": "10001",
                                                                     "xm7c08IS": "COMPLETED"}]})
            grant.assert_not_called()

    def test_client_switch_tracks_each_profile_and_out_of_order_completion(self):
        before = self.player_before(date(2020, 2, 20))
        after = self.player_before(date(2021, 10, 28))
        before.data["progress"]["cleared_missions"].append("8997001")
        before.grant_switch("101", 3681)
        before.grant_switch("101", PANEL_QUEST_UNLOCK_INDEX)

        def bits(player):
            with patch.object(State, "player", player):
                result = ffbe_player.serve_switches({}, "75fYdNxq")
            return next(row["juA0Z4m7"] for row in result["8J1R5PXG"] if row["5opcUT9t"] == "101")

        def enabled(container, index):
            offset, bit = divmod(index, 4)
            return bool(int(container[offset], 16) & (8 >> bit)) if offset < len(container) else False

        with patch("player_state._load_ndjson", return_value={}):
            locked = bits(before)
            self.assertTrue(enabled(locked, 3681))
            self.assertFalse(enabled(locked, PANEL_QUEST_UNLOCK_INDEX))
            self.assertTrue(enabled(bits(after), PANEL_QUEST_UNLOCK_INDEX))
            self.assertNotIn(PANEL_QUEST_UNLOCK_INDEX, after.switches["101"])
            before.data["progress"]["cleared_missions"].append("8996001")
            self.assertTrue(enabled(bits(before), PANEL_QUEST_UNLOCK_INDEX))

    def test_function_table_requires_the_derived_panel_switch(self):
        original = {"G1nfeht7": "FUNCTION_PANEL_QUEST", "5U0bAqgR": "1", "juA0Z4m7": "0"}
        other = {"G1nfeht7": "FUNCTION_REEL_DIMENSION", "5U0bAqgR": "1", "juA0Z4m7": "10005001"}
        raw = ("\n".join(ios_tables._encrypt("sy6GRuY2", row, False)
                         for row in (original, other)) + "\n").encode("ascii")
        patched, changed = ios_tables.patch_panel_function(raw)
        rows = [row for _, row, _ in ios_tables._rows(patched, "sy6GRuY2")]
        self.assertEqual(changed, 1)
        self.assertEqual(rows[0]["juA0Z4m7"], PANEL_QUEST_UNLOCK_SWITCH)
        self.assertEqual(rows[1], other)
        bump = ios_tables.table_bump(ios_tables.FUNCTION)
        with patch.object(ios_tables, "table_bump", side_effect=lambda spec: bump if spec == ios_tables.FUNCTION else 0), \
                patch.object(ios_tables, "version_bump", return_value=0), \
                patch.object(ios_texts, "index_bump", return_value=0):
            self.assertEqual(ios_tables.version_bumps()["F_FUNCTION_MST"], bump)
        self.assertTrue(ios_tables.wants("mst/Ver1044_6wibj9m8.dat"))

    def test_switch_table_adds_reserved_bit_and_rejects_collisions(self):
        original = {"8vAYn3IX": "18902200", "5opcUT9t": "101", "QLfe23bu": "3681"}
        raw = (ios_tables._encrypt(ios_tables.SWITCH[2], original, False) + "\n").encode("ascii")
        patched, changed = ios_tables.patch_panel_switch(raw)
        rows = [row for _, row, _ in ios_tables._rows(patched, ios_tables.SWITCH[2])]
        self.assertEqual(changed, 1)
        self.assertEqual(rows, [original, {"8vAYn3IX": PANEL_QUEST_UNLOCK_SWITCH, "5opcUT9t": "101",
                                          "QLfe23bu": str(PANEL_QUEST_UNLOCK_INDEX)}])
        self.assertEqual(ios_tables.patch_panel_switch(patched), (patched, 0))
        for conflict in (dict(original, **{"8vAYn3IX": PANEL_QUEST_UNLOCK_SWITCH}),
                         dict(original, **{"QLfe23bu": str(PANEL_QUEST_UNLOCK_INDEX)})):
            data = (ios_tables._encrypt(ios_tables.SWITCH[2], conflict, False) + "\n").encode("ascii")
            with self.assertRaises(ValueError):
                ios_tables.patch_panel_switch(data)
        self.assertTrue(ios_tables.wants("mst/Ver1044_T46RpNZH.dat"))
        self.assertGreater(ios_tables.table_bump(ios_tables.SWITCH), 0)


if __name__ == "__main__":
    unittest.main()
