import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import ios_texts


class MedalExchangeTextTests(unittest.TestCase):
    def test_adds_english_explanation_for_medal_exchange_reward(self):
        products = [{"jPV7Xc4N": "960070701", "P4puB2ch": "20:123:1"}]
        offers = {"960070701": {"medal": "70701"}}
        catalogue = SimpleNamespace(_catalogue=lambda cutoff: ({}, products, offers))
        original_shipped = ios_texts._shipped

        def shipped(table):
            if table == "F_TEXT_ITEM_NAME":
                return {"MST_ITEM_NAME_123": "Test Sword"}
            if table in ("F_TEXT_ITEM_EXPLAIN_SHORT", "F_TEXT_ITEM_EXPLAIN_LONG"):
                return {}
            return original_shipped(table)

        out = {name: {} for name in ios_texts.TABLES}
        with patch.dict(sys.modules, {"exvius_shop_catalogue": catalogue}), \
                patch.object(ios_texts, "_shipped", side_effect=shipped):
            ios_texts._shop_products(out)

        key = "mst_medal_exchange_explain_70701"
        self.assertEqual(out["F_TEXT_ITEM_EXPLAIN_SHORT"][key][0], "Exchange for Test Sword.")
        self.assertEqual(out["F_TEXT_ITEM_EXPLAIN_LONG"][key][0], "Exchange for Test Sword.")


if __name__ == "__main__":
    unittest.main()