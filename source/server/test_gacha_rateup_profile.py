import copy
import json
import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import ffbe_gacha
import player_state
from ffbe_state import State

SERVER = Path(__file__).parent


class RateUpProfileTests(unittest.TestCase):
    def test_selected_banners_use_the_requested_rarity_and_featured_rates(self):
        banner = {
            'id': '9100004',
            'release': '2016-08-26',
            'pool': [],
            'community': {'unit_ids': ['featured-3', 'featured-4', 'featured-5']},
        }
        pool = [
            {'unit_id': 'featured-3', 'rarity': 3, 'rate': 0.1},
            {'unit_id': 'off-3a', 'rarity': 3, 'rate': 0.1},
            {'unit_id': 'off-3b', 'rarity': 3, 'rate': 0.1},
            {'unit_id': 'featured-4', 'rarity': 4, 'rate': 0.1},
            {'unit_id': 'off-4', 'rarity': 4, 'rate': 0.1},
            {'unit_id': 'featured-5', 'rarity': 5, 'rate': 0.1},
            {'unit_id': 'off-5', 'rarity': 5, 'rate': 0.1},
        ]

        with patch.object(player_state, 'expand_pool', return_value=pool):
            actual = player_state.summon_pool(banner)

        rates = {row['unit_id']: row['rate'] for row in actual}
        self.assertAlmostEqual(rates['featured-3'], 0.195)
        self.assertAlmostEqual(rates['off-3a'] + rates['off-3b'], 0.585)
        self.assertAlmostEqual(rates['featured-4'], 0.0475)
        self.assertAlmostEqual(rates['off-4'], 0.1425)
        self.assertAlmostEqual(rates['featured-5'], 0.01)
        self.assertAlmostEqual(rates['off-5'], 0.02)
        self.assertAlmostEqual(sum(rates.values()), 1.0)

    def test_unlisted_featured_banner_keeps_its_existing_pool_rates(self):
        banner = {'id': '9200999', 'release': '2021-01-01', 'pool': [],
              'community': {'unit_ids': ['featured']}}
        pool = [{'unit_id': 'featured', 'rarity': 5, 'rate': 0.123}]

        actual = player_state.apply_rateup_profile(banner, pool)

        self.assertFalse(player_state.uses_rateup_profile(banner))
        self.assertEqual(actual, pool)

    def test_unlisted_featured_banner_keeps_rateup_but_uses_rare_shared_pool(self):
        banner_pool = []
        banner = {'id': '9200999', 'release': '2019-01-01', 'pool': banner_pool,
                  'community': {'unit_ids': ['featured']}}
        banner_rows = [
            {'unit_id': 'featured', 'rarity': 5, 'rate': 0.1},
            {'unit_id': 'banner-only-offbanner', 'rarity': 3, 'rate': 0.9},
        ]
        rare_rows = [
            {'unit_id': 'rare-shared-3', 'rarity': 3, 'rate': 0.78},
            {'unit_id': 'rare-shared-4', 'rarity': 4, 'rate': 0.19},
            {'unit_id': 'rare-shared-5', 'rarity': 5, 'rate': 0.03},
        ]
        with patch.object(player_state, '_rare_summon_template', return_value={'pool': {'tiers': []}}), \
                patch.object(player_state, 'expand_pool',
                             side_effect=lambda source: banner_rows if source['pool'] is banner_pool
                             else rare_rows):
            actual = player_state.summon_pool(banner)

        self.assertEqual({row['unit_id'] for row in actual},
                         {'featured', 'rare-shared-3', 'rare-shared-4', 'rare-shared-5'})
        rates = {row['unit_id']: row['rate'] for row in actual}
        self.assertAlmostEqual(rates['featured'], 0.1)
        self.assertAlmostEqual(sum(rates.values()), 1.0)

    def test_listed_featured_banner_uses_the_profile(self):
        banner = {'id': '9100004', 'release': '2016-08-26', 'pool': [],
              'community': {'unit_ids': ['featured-3']}}
        pool = [
            {'unit_id': 'featured-3', 'rarity': 3, 'rate': 0.5},
            {'unit_id': 'off-3', 'rarity': 3, 'rate': 0.5},
            {'unit_id': 'off-4', 'rarity': 4, 'rate': 1.0},
            {'unit_id': 'off-5', 'rarity': 5, 'rate': 1.0},
        ]

        actual = player_state.apply_rateup_profile(banner, pool)
        rates = {row['unit_id']: row['rate'] for row in actual}

        self.assertAlmostEqual(rates['featured-3'], 0.195)
        self.assertAlmostEqual(rates['off-4'], 0.19)
        self.assertAlmostEqual(rates['off-5'], 0.03)

    def test_featured_unit_includes_its_forms_through_five_star(self):
        banner = {'release': '2016-08-26', 'community': {'unit_ids': ['unit-3']}, 'pool': []}
        rows = [
            {'3HriTp6B': 'unit-3', 'woghJa61': 'unit-3', '9fW0TePj': '3'},
            {'3HriTp6B': 'unit-4', 'woghJa61': 'unit-3', '9fW0TePj': '4'},
            {'3HriTp6B': 'unit-5', 'woghJa61': 'unit-3', '9fW0TePj': '5'},
            {'3HriTp6B': 'unit-7', 'woghJa61': 'unit-3', '9fW0TePj': '7'},
            {'3HriTp6B': 'other-5', 'woghJa61': 'other-3', '9fW0TePj': '5'},
        ]
        by_id = {row['3HriTp6B']: row for row in rows}

        with patch.object(player_state, '_UNIT_FAMILY_FORMS', None), \
                patch.object(player_state, '_load_ndjson', return_value={'__rows__': rows}), \
                patch.object(player_state, 'unit_mst', side_effect=lambda uid: by_id.get(str(uid), {})):
            featured = player_state._featured_family_ids(banner)

        self.assertEqual(featured, {'unit-3', 'unit-4', 'unit-5'})

    def test_expand_pool_marks_each_evolution_as_featured_at_its_own_rarity(self):
        banner = {
            'id': '9100004',
            'release': '2016-08-26',
            'community': {'unit_ids': ['unit-3']},
            'pool': {'tiers': [
                {'rarity': 3, 'rate': 0.78, 'units': ['unit-3', 'off-3']},
                {'rarity': 4, 'rate': 0.19, 'units': ['off-4']},
                {'rarity': 5, 'rate': 0.03, 'units': ['off-5']},
            ]},
        }
        forms = [
            {'3HriTp6B': 'unit-3', 'woghJa61': 'unit-3', '9fW0TePj': '3'},
            {'3HriTp6B': 'unit-4', 'woghJa61': 'unit-3', '9fW0TePj': '4'},
            {'3HriTp6B': 'unit-5', 'woghJa61': 'unit-3', '9fW0TePj': '5'},
        ]
        by_id = {row['3HriTp6B']: row for row in forms}

        with patch.object(player_state, '_UNIT_FAMILY_FORMS', None), \
                patch.object(player_state, '_load_ndjson', return_value={'__rows__': forms}), \
                patch.object(player_state, 'unit_mst', side_effect=lambda uid: by_id.get(str(uid), {})), \
                patch.object(player_state, 'unit_roots_by_rarity', return_value={'3': [], '4': [], '5': []}), \
                patch.object(player_state, 'named_unit_ids', return_value=set()), \
                patch('summon_exclusions.excluded', return_value=frozenset()), \
                patch('summon_exclusions.limited_out', return_value=frozenset()), \
                patch('replay.pool_cutoff', return_value=None):
            pool = player_state.expand_pool(banner)

        featured = {int(row['rarity']): row['unit_id'] for row in pool
                    if row['unit_id'] in {'unit-3', 'unit-4', 'unit-5'} and row['rate'] > 0}
        self.assertEqual(featured, {3: 'unit-3', 4: 'unit-4', 5: 'unit-5'})

    def test_mixed_reward_pool_keeps_its_original_weights(self):
        banner = {
            'id': '9200998',
            'pool': [],
            'community': {'unit_ids': ['featured-3']},
            'reward_pool': [{'kind': 20, 'id': 123, 'count': 1, 'rate': 0.5}],
        }
        pool = [{'unit_id': 'featured-3', 'rarity': 3, 'rate': 0.5}]

        self.assertFalse(player_state.uses_rateup_profile(banner))
        self.assertEqual(player_state.apply_rateup_profile(banner, pool), pool)

    def test_explicit_tier_pool_excludes_limited_offbanner_but_keeps_featured(self):
        banner = {
            'id': '9100013',
            'release': '2016-11-04',
            'pool': {'tiers': [{
                'rarity': 5,
                'rate': 0.03,
                'units': ['limited-featured', 'limited-offbanner'],
                'featured': ['limited-featured'],
                'featured_share': 0.5,
            }]},
        }

        with patch('replay.pool_cutoff', return_value=date(2016, 11, 16)), \
                patch('replay.released_by', return_value=True), \
                patch.object(player_state, 'unit_roots_by_rarity', return_value={'5': []}), \
                patch.object(player_state, 'unit_mst', return_value={'9fW0TePj': '5'}), \
                patch.object(player_state, 'named_unit_ids', return_value=set()), \
                patch('summon_exclusions.excluded', return_value=frozenset()), \
                patch('summon_exclusions.limited_out', return_value=frozenset({'limited-offbanner'})):
            pool = player_state.expand_pool(banner)

        self.assertEqual([row['unit_id'] for row in pool], ['limited-featured'])

    def test_shared_pool_cannot_pass_the_player_checkpoint(self):
        banner = {
            'id': '9100004',
            'release': '2016-08-26',
            'community': {'unit_ids': ['featured-future']},
            'pool': [
                {'unit_id': 'featured-future', 'rarity': 3, 'rate': 0.2},
                {'unit_id': 'released-at-checkpoint', 'rarity': 3, 'rate': 0.4},
                {'unit_id': 'released-after-checkpoint', 'rarity': 3, 'rate': 0.4},
            ],
        }
        dates = {
            'featured-future': '2024-01-01',
            'released-at-checkpoint': '2016-08-24',
            'released-after-checkpoint': '2016-08-25',
        }
        player = SimpleNamespace(data={'progress': {'cleared_missions': []}})

        with patch.object(State, 'player', player), \
                patch.dict(os.environ, {'EXVIUS_SUMMON_ARCHIVE': '1'}), \
                patch('replay.enabled', return_value=True), \
                patch('replay.pool_cutoff', return_value=date(2024, 10, 30)), \
                patch('replay.unit_dates', return_value=dates), \
                patch.object(player_state, 'named_unit_ids', return_value=set()):
            actual = player_state.expand_pool(banner)

        self.assertEqual({row['unit_id'] for row in actual},
                         {'featured-future', 'released-at-checkpoint'})

    def test_featured_banner_uses_rare_summon_as_its_shared_pool(self):
        banner_pool = {'tiers': [{'rarity': 3, 'rate': 1.0, 'featured': ['featured-3']}]}
        banner = {'id': '9100004', 'release': '2016-08-26', 'pool': banner_pool,
                  'community': {'unit_ids': ['featured-3']}}
        banner_pool_rows = [
            {'unit_id': 'featured-3', 'rarity': 3, 'rate': 0.1},
            {'unit_id': 'banner-only-offbanner', 'rarity': 3, 'rate': 0.9},
        ]
        rare_summon_pool = [
            {'unit_id': 'rare-shared-3', 'rarity': 3, 'rate': 0.8},
            {'unit_id': 'rare-shared-4', 'rarity': 4, 'rate': 0.19},
            {'unit_id': 'rare-shared-5', 'rarity': 5, 'rate': 0.03},
        ]

        with patch.object(player_state, '_rare_summon_template', return_value={'pool': {'tiers': []}}), \
                patch.object(player_state, 'expand_pool',
                             side_effect=lambda source: banner_pool_rows if source['pool'] is banner_pool
                             else rare_summon_pool):
            actual = player_state.summon_pool(banner)

        self.assertEqual({row['unit_id'] for row in actual},
                         {'featured-3', 'rare-shared-3', 'rare-shared-4', 'rare-shared-5'})
        rates = {row['unit_id']: row['rate'] for row in actual}
        self.assertAlmostEqual(rates['featured-3'], 0.195)
        self.assertAlmostEqual(rates['rare-shared-3'], 0.585)
        self.assertAlmostEqual(rates['rare-shared-4'], 0.19)
        self.assertAlmostEqual(rates['rare-shared-5'], 0.03)

    def test_rarity_without_a_featured_unit_gets_its_full_rate_as_offbanner(self):
        banner = {'id': '9100017', 'release': '2016-12-02', 'pool': [],
              'community': {'unit_ids': ['featured-3']}}
        pool = [
            {'unit_id': 'featured-3', 'rarity': 3, 'rate': 0.5},
            {'unit_id': 'off-3', 'rarity': 3, 'rate': 0.5},
            {'unit_id': 'off-5a', 'rarity': 5, 'rate': 0.5},
            {'unit_id': 'off-5b', 'rarity': 5, 'rate': 0.5},
        ]

        actual = player_state.apply_rateup_profile(banner, pool)
        rates = {row['unit_id']: row['rate'] for row in actual}

        self.assertAlmostEqual(rates['off-5a'] + rates['off-5b'], 0.03)
        self.assertAlmostEqual(sum(rates.values()), 0.81)

    def test_nv_era_banner_keeps_native_forms_and_pool(self):
        banner = {
            'id': '9200999',
            'release': '2020-08-20',
            'community': {'unit_ids': ['featured-5']},
            'pool': {'tiers': [{'rarity': 5, 'rate': 0.05, 'featured': ['featured-5'],
                                'featured_share': 0.75}]},
        }
        pool = [{'unit_id': 'featured-5', 'rarity': 5, 'rate': 0.0375},
                {'unit_id': 'off-5', 'rarity': 5, 'rate': 0.0125}]

        self.assertEqual(player_state._featured_family_ids(banner), {'featured-5'})
        self.assertFalse(player_state.uses_shared_rare_pool(banner))
        self.assertFalse(player_state.uses_rateup_profile(banner))
        self.assertEqual(player_state.apply_rateup_profile(banner, pool), pool)

    def test_all_listed_campaign_pools_follow_the_requested_profile(self):
        doc = json.loads((SERVER / 'gacha_community.json').read_text(encoding='utf-8'))
        banners = [banner for banner in doc['banners']
                   if 9100000 <= int(banner['id']) <= 9100018]
        self.assertEqual(len(banners), 19)
        expected = {3: (0.78, 0.195), 4: (0.19, 0.0475), 5: (0.03, 0.01)}

        for source in banners:
            banner = ffbe_gacha._ffv_gilgamesh_fix(source)
            raw_pool = banner['pool']
            if isinstance(raw_pool, list):
                pool = copy.deepcopy(raw_pool)
            else:
                pool = [{'unit_id': str(uid), 'rarity': tier['rarity'], 'rate': tier['rate']}
                        for tier in raw_pool['tiers'] for uid in (tier.get('units') or [])]
            actual = player_state.apply_rateup_profile(banner, pool)
            featured_ids = set(map(str, (banner.get('community') or {}).get('unit_ids') or []))
            for tier in (raw_pool.get('tiers') or [] if isinstance(raw_pool, dict) else []):
                featured_ids.update(map(str, tier.get('featured') or []))

            with self.subTest(banner_id=banner['id'], name=banner['name']):
                for rarity, (tier_total, featured_total) in expected.items():
                    rows = [row for row in actual if int(row.get('rarity') or 0) == rarity]
                    if not rows:
                        continue
                    self.assertAlmostEqual(sum(float(row['rate']) for row in rows), tier_total)
                    featured = sum(float(row['rate']) for row in rows
                                    if str(row['unit_id']) in featured_ids)
                    self.assertAlmostEqual(featured, featured_total if featured else 0.0)
                self.assertAlmostEqual(sum(float(row['rate']) for row in actual), 1.0)


if __name__ == '__main__':
    unittest.main()
