import unittest
from unittest.mock import patch

import exvius_shop_catalogue as shop_catalogue


class ShopCatalogueTests(unittest.TestCase):
    def test_hides_sold_out_products_and_empty_stores(self):
        details = [
            {'3X1gLufw': 'medal-store'},
            {'3X1gLufw': 'shop-store'},
            {'3X1gLufw': 'unlimited-store'},
        ]
        products = [
            {'jPV7Xc4N': 'medal-sold', '3X1gLufw': 'medal-store'},
            {'jPV7Xc4N': 'medal-available', '3X1gLufw': 'medal-store'},
            {'jPV7Xc4N': 'shop-sold', '3X1gLufw': 'shop-store'},
            {'jPV7Xc4N': 'unlimited', '3X1gLufw': 'unlimited-store'},
        ]
        offers = {
            'medal-sold': {'detail': 'medal-store', 'limit': 1, 'medal': 'row-sold'},
            'medal-available': {'detail': 'medal-store', 'limit': 2, 'medal': 'row-available'},
            'shop-sold': {'detail': 'shop-store', 'limit': 1, 'medal': None, 'monthly': False},
            'unlimited': {'detail': 'unlimited-store', 'limit': 2147483647, 'medal': None, 'monthly': False},
        }
        counts = {'shop-sold': 1, 'unlimited': 5}

        with (patch.object(shop_catalogue, 'catalogue', return_value=(details, products, offers)),
              patch.object(shop_catalogue, 'hidden_details', return_value=set()),
              patch.object(shop_catalogue, '_reply', return_value={}),
              patch.object(shop_catalogue, '_feature', return_value={'counts': counts}),
              patch.object(shop_catalogue, 'shared_medal_counts', return_value={
                  'row-sold': 1, 'row-available': 1,
              })):
            result = shop_catalogue.entry({}, {})

        self.assertEqual([row['jPV7Xc4N'] for row in result['TPrh6Ay3']],
                         ['medal-available', 'unlimited'])
        self.assertEqual([row['3X1gLufw'] for row in result['F2rNo6qf']],
                         ['medal-store', 'unlimited-store'])
        self.assertEqual([row['jPV7Xc4N'] for row in result['qS62ewjH']],
                         ['medal-available', 'unlimited'])


if __name__ == '__main__':
    unittest.main()