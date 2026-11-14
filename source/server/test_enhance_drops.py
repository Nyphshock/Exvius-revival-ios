import unittest
from unittest.mock import patch

import ffbe_battle
from ffbe_config import DROP_TAG_ROWS, DROP_TOKEN


class EnhanceDropTests(unittest.TestCase):
    def test_enhance_drops_preserve_their_own_chances_and_quantities(self):
        spec = {DROP_TAG_ROWS: [{DROP_TOKEN: "20:101:2:30,20:101:3:30,28:202:350:50"}]}
        with patch("ffbe_battle.calamity_writ_chance", return_value=0), \
                patch("ffbe_battle.random.randint", return_value=100):
            rolled = ffbe_battle.roll_drops(spec, mid="2280101")
        self.assertEqual(rolled[DROP_TAG_ROWS][0][DROP_TOKEN], "28:202:350:50")

    def test_cactuar_dunes_drops_metal_units_instead_of_fallback_materials(self):
        spec = {
            "an6TB4WS": [{"6v7y3QcJ": "1", "2fY1IomW": "group-1"}],
            "Bi6hVv34": [
                {"2fY1IomW": "group-1", "xqartN26": "111051000"},
                {"2fY1IomW": "group-1", "xqartN26": "111061000"},
                {"2fY1IomW": "group-1", "xqartN26": "211011000"},
                {"2fY1IomW": "group-1", "xqartN26": "111091000"},
            ],
            DROP_TAG_ROWS: [{"6v7y3QcJ": "1", DROP_TOKEN: ""}],
        }
        with patch("ffbe_battle.calamity_writ_chance", return_value=0):
            rolled = ffbe_battle.roll_drops(spec, mid="2111201")
        self.assertEqual(
            rolled[DROP_TAG_ROWS][0][DROP_TOKEN],
            "10:900020101:3:100,10:900020201:3:100,10:900020301:3:100,10:900020401:3:100",
        )
        self.assertNotIn("20:", rolled[DROP_TAG_ROWS][0][DROP_TOKEN])

    def test_gil_snapper_cave_replaces_material_pool_with_matching_unit(self):
        spec = {
            "an6TB4WS": [{"6v7y3QcJ": "1", "2fY1IomW": "group-1"}],
            "Bi6hVv34": [
                {"2fY1IomW": "group-1", "xqartN26": "103041000"},
                {"2fY1IomW": "group-1", "xqartN26": "103041000"},
                {"2fY1IomW": "group-1", "xqartN26": "103041000"},
            ],
            DROP_TAG_ROWS: [{"6v7y3QcJ": "1", DROP_TOKEN: "20:290010000:1:100"}],
        }
        with patch("ffbe_battle.calamity_writ_chance", return_value=0):
            rolled = ffbe_battle.roll_drops(spec, mid="2111301")
        self.assertEqual(rolled[DROP_TAG_ROWS][0][DROP_TOKEN],
                         "10:900010101:1:100,10:900010101:1:100,10:900010101:1:100")

    def test_vault_adds_only_the_units_its_enemy_group_drops(self):
        spec = {
            "an6TB4WS": [{"6v7y3QcJ": "1", "2fY1IomW": "group-1"}],
            "Bi6hVv34": [
                {"2fY1IomW": "group-1", "xqartN26": "208011000"},
                {"2fY1IomW": "group-1", "xqartN26": "103111000"},
                {"2fY1IomW": "group-1", "xqartN26": "111041010"},
            ],
            DROP_TAG_ROWS: [{"6v7y3QcJ": "1", DROP_TOKEN: "20:202000100:1:100"}],
        }
        with patch("event_archive.events", return_value=[{
            "area": "301", "name": "Vault of Hidden Treasures", "missions": ["3010115"],
        }]), patch("ffbe_battle.calamity_writ_chance", return_value=0), \
                patch("ffbe_battle.random.randint", return_value=1):
            ffbe_battle._VAULT_HIDDEN_TREASURES_MISSIONS = None
            rolled = ffbe_battle.roll_drops(spec, mid="3010115")
        self.assertEqual(
            rolled[DROP_TAG_ROWS][0][DROP_TOKEN],
            "20:202000100:1:100,10:900000301:1:100,10:900010401:1:100",
        )

    def test_lost_maps_use_their_specific_unit_rewards(self):
        def spec_with_enemy(enemy):
            return {
                "an6TB4WS": [{"6v7y3QcJ": "1", "2fY1IomW": "group-1"}],
                "Bi6hVv34": [{"2fY1IomW": "group-1", "xqartN26": enemy}],
                DROP_TAG_ROWS: [{"6v7y3QcJ": "1", DROP_TOKEN: ""}],
            }
        with patch("ffbe_battle.calamity_writ_chance", return_value=0):
            trust = ffbe_battle.roll_drops(spec_with_enemy("204231000"), mid="8180101")
            gil = ffbe_battle.roll_drops(spec_with_enemy("103121000"), mid="8180106")
        self.assertEqual(trust[DROP_TAG_ROWS][0][DROP_TOKEN], "10:904000101:1:100")
        self.assertEqual(gil[DROP_TAG_ROWS][0][DROP_TOKEN], "10:900010501:5:100")

    def test_vault_wiki_no_drop_bosses_do_not_get_generic_materials(self):
        spec = {
            "an6TB4WS": [{"6v7y3QcJ": "1", "2fY1IomW": "group-1"}],
            "Bi6hVv34": [{"2fY1IomW": "group-1", "xqartN26": "203020004"}],
            DROP_TAG_ROWS: [{"6v7y3QcJ": "1", DROP_TOKEN: ""}],
        }
        with patch("event_archive.events", return_value=[{
            "area": "960", "name": "Vault of Hidden Treasures", "missions": ["9600101"],
        }]):
            ffbe_battle._VAULT_HIDDEN_TREASURES_MISSIONS = None
            out = ffbe_battle._unit_vortex_drop_pools(spec, "9600101")
        self.assertNotIn(DROP_TOKEN, out[DROP_TAG_ROWS][0])


if __name__ == "__main__":
    unittest.main()