import contextlib
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import ffbe_state
from exvius_actions import unit_equip
from ffbe_player import apply_party_edit
from player_state import PlayerState


class EquipmentInventoryTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState({
            "roster": [{"equipment": {"1": "403040300", "2": "403040200"}}],
            "inventory": {"equipment": [
                {"item_id": 403040300, "count": 1},
                {"item_id": 403040200, "count": 1},
            ]},
        })

    def test_unknown_equipment_is_not_projected_or_credited(self):
        with patch("player_state._load_ndjson", return_value={"403040200": {}}):
            rows = self.player.equip_item_rows()
            self.assertEqual([row["J1YX9kmM"] for row in rows], ["403040200"])
            self.assertFalse(self.player._can_credit({"kind": 21, "id": 403040300, "count": 1}))
            self.assertTrue(self.player._can_credit({"kind": 21, "id": 403040200, "count": 1}))
            invalid_reward = {"kind": 21, "id": 403040300, "count": 1}
            valid_reward = {"kind": 21, "id": 403040200, "count": 1}
            self.assertEqual(self.player._grant_items([invalid_reward]), [])
            self.assertEqual(self.player._grant_items([valid_reward]), [valid_reward])
            self.assertEqual(self.player.data["inventory"]["equipment"][1]["count"], 2)

    def test_unit_equip_round_trips_equipment_and_materia(self):
        unit = {"instance_id": "unit-1", "equipment": {str(slot): "0" for slot in range(1, 7)},
                "materia": ["0"] * 4}
        player = PlayerState({
            "identity": {"user_id": "300000001"},
            "roster": [unit],
            "inventory": {
                "equipment": [{"item_id": 403040200, "count": 1}],
                "items": [{"item_type": 22, "item_id": 200100001, "count": 1}],
            },
            "progress": {"switches": {}, "cleared_challenges": {}, "paid_challenges": {}},
            "vision_cards": [],
            "party": {"active_deck": 0, "decks": []},
        })
        request = {"Er92Kdhm": [{
            "xBi3L6yR": "7",
            "93Y6evuT": "stale-unit:1-0;unit-1:1-403040200",
            "80NUYFMJ": "stale-unit:1-0;unit-1:1-200100001",
        }]}

        with patch.object(ffbe_state.State, "player", player), \
                patch("player_state._load_ndjson", return_value={"403040200": {}}), \
                patch("ffbe_player.score_quest_action"):
            unit_equip({}, request)
            self.assertTrue(player.dirty)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "player.json"
                self.assertTrue(player.save(str(path)))
                saved = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(saved["roster"][0]["equipment"]["1"], "403040200")
            self.assertEqual(saved["roster"][0]["materia"][0], "200100001")
            row = player._equip_rows()[0]
            self.assertIn("1-403040200", row["93Y6evuT"])
            self.assertIn("1-200100001", row["80NUYFMJ"])

    GEAR = {"403040200": {}, "403040300": {}, "403040400": {}}
    SWITCH_TO_TEAM_2 = {"5Eb0Rig6": [{"r21y0YzS": "1", "2A6fYiEC": "0:0:unit-1,0:1:unit-2"}],
                        "CN92arJK": [{"r21y0YzS": "1"}]}

    def two_team_player(self, worn=None):
        """unit-1 (wearing `worn`) is in team 1 only; team 1 is the active deck."""
        unit = {"instance_id": "unit-1", "materia": ["0"] * 4,
                "equipment": {**{str(slot): "0" for slot in range(1, 7)}, **(worn or {})}}
        other = {"instance_id": "unit-2", "equipment": {}, "materia": ["0"] * 4}
        return PlayerState({
            "identity": {"user_id": "300000001"},
            "roster": [unit, other],
            "inventory": {"equipment": [{"item_id": int(item), "count": 1} for item in self.GEAR], "items": []},
            "progress": {"switches": {}, "cleared_challenges": {}, "paid_challenges": {}},
            "vision_cards": [],
            "party": {"active_deck": 0, "decks": [
                {"id": 0, "name": "Team 1", "members": [
                    {"member_type": 0, "disp_order": 0, "instance_id": "unit-1"}]},
                {"id": 1, "name": "Team 2", "members": [
                    {"member_type": 0, "disp_order": 0, "instance_id": "unit-2"}]},
            ]},
        })

    def serving(self, player):
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(ffbe_state.State, "player", player))
        stack.enter_context(patch("player_state._load_ndjson", return_value=self.GEAR))
        stack.enter_context(patch("ffbe_player.score_quest_action"))
        return stack

    def test_party_edit_reply_leaves_unsent_equipment_edits_alone(self):
        groups = {
            "5Eb0Rig6": [{"r21y0YzS": "0"}, {"r21y0YzS": "1"}],
            "TJ9eL80N": [{"og2GHy49": "unit-1"}],
            "DW7uH6Mn": [], "VE7KZ8CY": [], "wc8vSHPS": [],
        }
        with patch.object(self.player, "groups", return_value=groups):
            reply = self.player.apply_to_reply({"5Eb0Rig6": []}, reply_id="TS5Dx9aZ")
            refresh = self.player.apply_to_reply({"5Eb0Rig6": []}, reply_id="X07iYtp5")
        self.assertEqual(reply["5Eb0Rig6"], groups["5Eb0Rig6"])
        for tag in ("TJ9eL80N", "DW7uH6Mn", "VE7KZ8CY", "wc8vSHPS"):
            self.assertNotIn(tag, reply)
            self.assertIn(tag, refresh)

    def test_equipped_unit_has_the_same_row_under_every_deck(self):
        rows = self.two_team_player({"1": "403040200"})._equip_rows()
        worn = [row for row in rows if row["og2GHy49"] == "unit-1"]
        self.assertEqual([row["r21y0YzS"] for row in worn], ["0", "1"])
        self.assertEqual({row["93Y6evuT"] for row in worn}, {"1-403040200@2-0@3-0@4-0@5-0@6-0"})
        self.assertEqual([row["r21y0YzS"] for row in rows if row["og2GHy49"] == "unit-2"], ["0"])

    def test_equipment_edit_survives_a_team_switch_sent_first(self):
        """Recorded 2026-11-17 18:49: an item added under team 1, then the team switched, so the phone sent
        PartyDeckEditRequest before UnitEquipRequest."""
        player = self.two_team_player({"1": "403040200"})
        edited = "1-403040200@2-0@3-403040300@4-0@5-0@6-0"
        with self.serving(player):
            apply_party_edit(json.dumps(self.SWITCH_TO_TEAM_2))
            groups = {"5Eb0Rig6": player._deck_rows(), "TJ9eL80N": player._equip_rows(),
                      "DW7uH6Mn": [], "VE7KZ8CY": [], "wc8vSHPS": []}
            with patch.object(player, "groups", return_value=groups):
                reply = player.apply_to_reply({"5Eb0Rig6": []}, reply_id="TS5Dx9aZ")
            unit_equip({}, {"Er92Kdhm": [{"r21y0YzS": "0", "93Y6evuT": f"unit-1:{edited}"}]})
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "player.json"
                self.assertTrue(player.save(str(path)))
                saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(player.data["party"]["active_deck"], 1)
        self.assertNotIn("TJ9eL80N", reply)
        self.assertEqual(saved["roster"][0]["equipment"]["3"], "403040300")
        self.assertEqual([(row["r21y0YzS"], row["93Y6evuT"]) for row in player._equip_rows()
                          if row["og2GHy49"] == "unit-1"], [("0", edited), ("1", edited)])

    def test_untouched_copy_under_another_team_does_not_undo_an_edit(self):
        """Recorded 2026-11-17 17:44: team 1's copy carried the new weapon, team 2's copy was still the old one."""
        old, new = "unit-1:1-403040200@2-0@3-0@4-0@5-0@6-0", "unit-1:1-403040300@2-0@3-0@4-0@5-0@6-0"
        for copies in (f"{new};{old}", f"{old};{new}"):
            with self.subTest(copies=copies):
                player = self.two_team_player({"1": "403040200"})
                with self.serving(player):
                    unit_equip({}, {"Er92Kdhm": [{"r21y0YzS": "0;1", "93Y6evuT": copies}]})
                self.assertEqual(player.data["roster"][0]["equipment"]["1"], "403040300")

    def test_edits_made_under_two_teams_are_both_kept(self):
        player = self.two_team_player({"1": "403040200"})
        with self.serving(player):
            unit_equip({}, {"Er92Kdhm": [{
                "r21y0YzS": "0;1",
                "93Y6evuT": "unit-1:1-403040200@2-0@3-403040300@4-0@5-0@6-0;"
                             "unit-1:1-403040200@2-0@3-0@4-403040400@5-0@6-0"}]})
        self.assertEqual(player.data["roster"][0]["equipment"],
                         {"1": "403040200", "2": "0", "3": "403040300", "4": "403040400", "5": "0", "6": "0"})

    def test_unequip_all_is_stored_right_after_a_party_edit(self):
        player = self.two_team_player({"1": "403040200"})
        with self.serving(player):
            apply_party_edit(json.dumps(self.SWITCH_TO_TEAM_2))
            unit_equip({}, {"Er92Kdhm": [{"r21y0YzS": "1", "93Y6evuT": "unit-1:1-0@2-0@3-0@4-0@5-0@6-0"}]})
        self.assertEqual(player.data["roster"][0]["equipment"]["1"], "0")
        self.assertEqual([row["r21y0YzS"] for row in player._equip_rows() if row["og2GHy49"] == "unit-1"], ["1"])

    def test_explicit_unequip_without_party_edit_still_clears_loadout(self):
        player = PlayerState({
            "identity": {"user_id": "300000001"},
            "roster": [{"instance_id": "unit-1",
                        "equipment": {"1": "403040200", **{str(slot): "0" for slot in range(2, 7)}},
                        "materia": ["0"] * 4}],
            "inventory": {"equipment": [{"item_id": 403040200, "count": 1}], "items": []},
        })
        with patch.object(ffbe_state.State, "player", player), \
                patch("player_state._load_ndjson", return_value={"403040200": {}}):
            unit_equip({}, {"Er92Kdhm": [{"93Y6evuT": "unit-1:1-0@2-0@3-0@4-0@5-0@6-0"}]})

        self.assertEqual(player.data["roster"][0]["equipment"]["1"], "0")

    def test_unit_equip_merges_changed_deck_segment_into_global_loadout(self):
        player = PlayerState({
            "identity": {"user_id": "300000001"},
            "roster": [{"instance_id": "unit-1", "equipment": {"1": "403040200",
                        **{str(slot): "0" for slot in range(2, 7)}},
                        "materia": ["0"] * 4}],
            "inventory": {"equipment": [
                {"item_id": 403040200, "count": 1}, {"item_id": 403040300, "count": 1}],
                "items": []},
            "party": {"active_deck": 0, "decks": []},
        })
        request = {"Er92Kdhm": [{
            "r21y0YzS": "0;1",
            "93Y6evuT": "unit-1:1-403040200@2-0@3-0@4-0@5-0@6-0;"
                         "unit-1:1-403040300@2-0@3-0@4-0@5-0@6-0",
        }]}

        with patch.object(ffbe_state.State, "player", player), \
                patch("player_state._load_ndjson", return_value={"403040200": {}, "403040300": {}}):
            unit_equip({}, request)

        self.assertEqual(player.data["roster"][0]["equipment"]["1"], "403040300")


if __name__ == "__main__":
    unittest.main()