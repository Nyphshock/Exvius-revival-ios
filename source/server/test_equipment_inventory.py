import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import ffbe_state
from exvius_actions import unit_equip
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


if __name__ == "__main__":
    unittest.main()