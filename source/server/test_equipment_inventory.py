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

    def test_party_edit_projects_global_equipment_for_the_active_deck(self):
        groups = {
            "5Eb0Rig6": [{"r21y0YzS": "0"}, {"r21y0YzS": "1"}],
            "TJ9eL80N": [{"og2GHy49": "unit-1", "r21y0YzS": "1",
                           "93Y6evuT": "1-403040200"}],
            "DW7uH6Mn": [], "VE7KZ8CY": [], "wc8vSHPS": [],
        }
        with patch.object(self.player, "groups", return_value=groups):
            reply = self.player.apply_to_reply({"5Eb0Rig6": []}, reply_id="TS5Dx9aZ")
            refresh = self.player.apply_to_reply({"5Eb0Rig6": []}, reply_id="X07iYtp5")
        self.assertEqual(reply["5Eb0Rig6"], groups["5Eb0Rig6"])
        self.assertEqual(reply["TJ9eL80N"], groups["TJ9eL80N"])
        self.assertEqual(reply["TJ9eL80N"][0]["r21y0YzS"], "1")
        self.assertIn("1-403040200", reply["TJ9eL80N"][0]["93Y6evuT"])
        for tag in ("DW7uH6Mn", "VE7KZ8CY", "wc8vSHPS"):
            self.assertIn(tag, reply)
            self.assertIn(tag, refresh)

    def test_moving_equipped_unit_between_decks_preserves_server_loadout(self):
        unit = {"instance_id": "unit-1", "equipment": {str(slot): "0" for slot in range(1, 7)},
                "materia": ["0"] * 4}
        other = {"instance_id": "unit-2", "equipment": {}, "materia": ["0"] * 4}
        player = PlayerState({
            "identity": {"user_id": "300000001"},
            "roster": [unit, other],
            "inventory": {"equipment": [{"item_id": 403040200, "count": 1}], "items": []},
            "progress": {"switches": {}, "cleared_challenges": {}, "paid_challenges": {}},
            "vision_cards": [],
            "party": {"active_deck": 0, "decks": [
                {"id": 0, "name": "Team 1", "members": [
                    {"member_type": 0, "disp_order": 0, "instance_id": "unit-1"}]},
                {"id": 1, "name": "Team 2", "members": [
                    {"member_type": 0, "disp_order": 0, "instance_id": "unit-2"}]},
            ]},
        })
        equip_request = {"Er92Kdhm": [{"93Y6evuT": "unit-1:1-403040200"}]}
        party_request = {"5Eb0Rig6": [{"r21y0YzS": "1", "2A6fYiEC": "0:0:unit-1,0:1:unit-2"}],
                         "CN92arJK": [{"r21y0YzS": "1"}]}
        with patch.object(ffbe_state.State, "player", player), \
                patch("player_state._load_ndjson", return_value={"403040200": {}}), \
                patch("ffbe_player.score_quest_action"):
            unit_equip({}, equip_request)
            apply_party_edit(json.dumps(party_request))
            self.assertEqual(player.data["party"]["active_deck"], 1)
            self.assertEqual(player.data["roster"][0]["equipment"]["1"], "403040200")
            empty_equip_request = {"Er92Kdhm": [{"93Y6evuT": "unit-1:1-0@2-0@3-0@4-0@5-0@6-0"}]}
            unit_equip({}, empty_equip_request)
            self.assertEqual(player.data["roster"][0]["equipment"]["1"], "403040200")
            groups = {"5Eb0Rig6": player._deck_rows(), "TJ9eL80N": player._equip_rows(),
                      "DW7uH6Mn": [], "VE7KZ8CY": [], "wc8vSHPS": []}
            with patch.object(player, "groups", return_value=groups):
                reply = player.apply_to_reply({"5Eb0Rig6": []}, reply_id="TS5Dx9aZ")
            projected = [row for row in reply["TJ9eL80N"] if row["og2GHy49"] == "unit-1"]
            self.assertEqual(len(projected), 1)
            self.assertEqual(projected[0]["r21y0YzS"], "1")
            self.assertIn("1-403040200", projected[0]["93Y6evuT"])
            team_two_row = projected[0]
            unit_equip({}, {"Er92Kdhm": [{"93Y6evuT": f"unit-1:{team_two_row['93Y6evuT']}"}]})
            self.assertEqual(player.data["roster"][0]["equipment"]["1"], "403040200")
            rows = [row for row in player._equip_rows() if row["og2GHy49"] == "unit-1"]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["r21y0YzS"], "1")
            self.assertIn("1-403040200", row["93Y6evuT"])
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "player.json"
                self.assertTrue(player.save(str(path)))
                saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["roster"][0]["equipment"]["1"], "403040200")

    def test_explicit_unequip_without_party_edit_still_clears_loadout(self):
        player = PlayerState({
            "identity": {"user_id": "300000001"},
            "roster": [{"instance_id": "unit-1", "equipment": {"1": "403040200"},
                        "materia": ["0"] * 4}],
            "inventory": {"equipment": [{"item_id": 403040200, "count": 1}], "items": []},
        })
        with patch.object(ffbe_state.State, "player", player), \
                patch("player_state._load_ndjson", return_value={"403040200": {}}):
            unit_equip({}, {"Er92Kdhm": [{"93Y6evuT": "unit-1:1-0@2-0@3-0@4-0@5-0@6-0"}]})

        self.assertEqual(player.data["roster"][0]["equipment"]["1"], "0")

    def test_unit_equip_uses_active_deck_loadout_when_duplicate_rows_disagree(self):
        player = PlayerState({
            "identity": {"user_id": "300000001"},
            "roster": [{"instance_id": "unit-1", "equipment": {"1": "403040200"},
                        "materia": ["0"] * 4}],
            "inventory": {"equipment": [
                {"item_id": 403040200, "count": 1}, {"item_id": 403040300, "count": 1}],
                "items": []},
            "party": {"active_deck": 1, "decks": []},
        })
        request = {"Er92Kdhm": [{
            "r21y0YzS": "1;0",
            "93Y6evuT": "unit-1:1-403040300@2-0@3-0@4-0@5-0@6-0;"
                         "unit-1:1-403040200@2-0@3-0@4-0@5-0@6-0",
        }]}

        with patch.object(ffbe_state.State, "player", player), \
                patch("player_state._load_ndjson", return_value={"403040200": {}, "403040300": {}}):
            unit_equip({}, request)

        self.assertEqual(player.data["roster"][0]["equipment"]["1"], "403040300")


if __name__ == "__main__":
    unittest.main()