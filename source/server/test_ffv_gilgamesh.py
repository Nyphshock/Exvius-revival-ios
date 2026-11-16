import json
from pathlib import Path
import unittest
from unittest.mock import patch

import ffbe_gacha
import player_state


SERVER = Path(__file__).parent
GILGAMESH_FFV = '205000805'


class FinalFantasyVBannerTests(unittest.TestCase):
    def test_gilgamesh_is_featured_and_drawable_in_both_banner_records(self):
        records = (
            ('gacha_catalogue.json', '800090'),
            ('gacha_community.json', '9100016'),
        )
        with patch('player_state.unit_roots_by_rarity', return_value={
                    '3': ['generic-offbanner-3'], '4': ['generic-offbanner-4'],
                    '5': ['generic-offbanner-5']}), \
                patch('player_state.unit_mst', side_effect=lambda uid: {
                    '9fW0TePj': '5' if str(uid) == GILGAMESH_FFV else '3'}), \
                patch('player_state.named_unit_ids', return_value=set()), \
                patch('summon_exclusions.excluded', return_value=frozenset()), \
                patch('summon_exclusions.limited_out', return_value=frozenset()), \
                patch('replay.pool_cutoff', return_value=None):
            for filename, banner_id in records:
                with self.subTest(banner_id=banner_id):
                    doc = json.loads((SERVER / filename).read_text(encoding='utf-8'))
                    source = next(row for row in doc['banners'] if str(row.get('id')) == banner_id)
                    banner = ffbe_gacha._ffv_gilgamesh_fix(source)
                    tiers = banner['pool']['tiers']
                    five_star = next(tier for tier in tiers if str(tier['rarity']) == '5')

                    self.assertIn(GILGAMESH_FFV, banner['community']['unit_ids'])
                    self.assertIn(GILGAMESH_FFV, five_star['units'])
                    self.assertIn(GILGAMESH_FFV, five_star['featured'])
                    self.assertAlmostEqual(five_star['featured_share'], 1 / 3)
                    self.assertEqual(ffbe_gacha.gacha_field_units(banner)[0], GILGAMESH_FFV)

                    expanded = player_state.summon_pool(banner)
                    gilgamesh = next(row for row in expanded if row['unit_id'] == GILGAMESH_FFV)
                    self.assertAlmostEqual(gilgamesh['rate'], 0.01)
                    self.assertAlmostEqual(sum(row['rate'] for row in expanded), 1.0)

    def test_banner_loader_repairs_selected_ffv_alias(self):
        with patch.object(ffbe_gacha, 'gacha_only_ids', return_value={'9100016'}):
            banners = ffbe_gacha.all_banners()

        self.assertEqual(len(banners), 1)
        self.assertEqual(str(banners[0]['id']), '9100016')
        self.assertIn(GILGAMESH_FFV, ffbe_gacha.gacha_field_units(banners[0]))
        featured = next(tier for tier in banners[0]['pool']['tiers'] if str(tier['rarity']) == '5')
        self.assertIn(GILGAMESH_FFV, featured['featured'])


if __name__ == '__main__':
    unittest.main()
