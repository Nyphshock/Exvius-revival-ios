import json
import unittest
from unittest.mock import patch

import player_state


class EsperBoardResetTests(unittest.TestCase):
    def make_player(self, lapis_free=80, lapis_paid=50):
        player = object.__new__(player_state.PlayerState)
        player.data = {
            "beasts": [{"esper_id": "2", "rarity": 2, "level": 40, "cp": 38,
                        "board": "7", "reset_count": 0}],
            "currencies": {"lapis_free": lapis_free, "lapis_paid": lapis_paid},
        }
        player.mode = "live"
        player.dirty = False
        player._team_row = lambda: {}
        return player

    def shop_data(self):
        pieces = {
            "20002": {player_state.BEAST_ID: "2", player_state.BEAST_PIECE_BIT: "1",
                      player_state.BEAST_PIECE_CP_COST: "5", player_state.BEAST_PIECE_UNLOCK_COUNT: "0"},
            "20003": {player_state.BEAST_ID: "2", player_state.BEAST_PIECE_BIT: "2",
                      player_state.BEAST_PIECE_CP_COST: "5", player_state.BEAST_PIECE_UNLOCK_COUNT: "0"},
            "20004": {player_state.BEAST_ID: "2", player_state.BEAST_PIECE_BIT: "3",
                      player_state.BEAST_PIECE_CP_COST: "0", player_state.BEAST_PIECE_UNLOCK_COUNT: "1"},
            "30002": {player_state.BEAST_ID: "3", player_state.BEAST_PIECE_BIT: "4",
                      player_state.BEAST_PIECE_CP_COST: "99", player_state.BEAST_PIECE_UNLOCK_COUNT: "0"},
        }
        shop = {player_state.SHOP_ID_TOKEN: "60", player_state.SHOP_USE_DIA_TOKEN: "100",
                player_state.SHOP_PARAM_TOKEN: "0"}
        return pieces, shop

    def test_shop_use_reset_refunds_cp_preserves_unlock_and_is_idempotent(self):
        player = self.make_player()
        pieces, shop = self.shop_data()
        request = json.dumps({"L5Nj3cKE": [{"gdR2tJI9": "60", "Qy5EvcK1": "0", "Vt2I4RjX": "2"}]})

        with patch.object(player_state, "board_piece_rows", return_value=pieces), \
                patch.object(player_state, "shop_mst", return_value=shop), \
                patch.object(player_state, "beast_status", return_value={}):
            reply = player.apply_shop_use({}, player_state.SHOP_USE_REQUEST, request)
            retry = player.apply_shop_use({}, player_state.SHOP_USE_REQUEST, request)

        beast = player.data["beasts"][0]
        self.assertIn("3oU9Ktb7", reply)
        self.assertEqual(beast["board"], "1")
        self.assertEqual(beast["cp"], 48)
        self.assertEqual(beast["reset_count"], 1)
        self.assertEqual(player.data["currencies"], {"lapis_free": 0, "lapis_paid": 30})
        self.assertIn("3oU9Ktb7", retry)

    def test_reset_with_insufficient_lapis_changes_nothing(self):
        player = self.make_player(lapis_free=20, lapis_paid=30)
        pieces, shop = self.shop_data()

        with patch.object(player_state, "board_piece_rows", return_value=pieces), \
                patch.object(player_state, "shop_mst", return_value=shop), \
                patch.object(player_state, "beast_status", return_value={}):
            result = player.reset_beast_board_with_shop("60", "2")

        beast = player.data["beasts"][0]
        self.assertIsNone(result)
        self.assertEqual((beast["board"], beast["cp"], beast["reset_count"]), ("7", 38, 0))
        self.assertEqual(player.data["currencies"], {"lapis_free": 20, "lapis_paid": 30})


if __name__ == "__main__":
    unittest.main()