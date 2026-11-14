import unittest
from unittest.mock import patch

import ffbe_battle
from ffbe_config import DROP_TAG_ROWS, DROP_TOKEN


class EnhanceDropTests(unittest.TestCase):
    def test_enhance_missions_get_triple_guaranteed_drops(self):
        self.assertTrue(ffbe_battle._is_enhance_mission("2280101"))
        self.assertEqual(
            ffbe_battle._triple_enhance_drops("20:101:2:30,20:101:3:30,28:202:350:50"),
            "20:101:6:100,20:101:9:100,28:202:1050:100",
        )

    def test_non_enhance_missions_are_not_classified(self):
        self.assertFalse(ffbe_battle._is_enhance_mission("1110101"))
        self.assertEqual(
            ffbe_battle._triple_enhance_drops("20:101:2"),
            "20:101:6:100",
        )

    def test_roll_drops_triples_only_enhance_missions(self):
        spec = {DROP_TAG_ROWS: [{DROP_TOKEN: "20:101:2:100,20:101:3:100,28:202:350:100"}]}
        with patch("ffbe_battle.calamity_writ_chance", return_value=0):
            enhanced = ffbe_battle.roll_drops(spec, mid="2280101")
            normal = ffbe_battle.roll_drops(spec, mid="1110101")
        self.assertEqual(enhanced[DROP_TAG_ROWS][0][DROP_TOKEN],
                         "20:101:6:100,20:101:9:100,28:202:1050:100")
        self.assertEqual(normal[DROP_TAG_ROWS][0][DROP_TOKEN],
                         "20:101:2:100,20:101:3:100,28:202:350:100")

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


if __name__ == "__main__":
    unittest.main()