import unittest

from battle_content import rebalance_intangir_trial


class IntangirBalanceTests(unittest.TestCase):
    def test_only_intangir_stats_are_changed_without_mutating_authored_bundle(self):
        intangir = {
            'xqartN26': '401011000',
            '6Yc4RkdM': '1',
            'fh31sk7B': '230000',
            '9NBV1XCS': '350',
            'Pn5w9dfh': '25',
            '84FJM3PD': '250',
            'T8xMDAZ4': '20',
        }
        other_part = {'xqartN26': '401011001', 'fh31sk7B': '100'}
        skills = [{'6E5u1xrs': '151200'}]
        bundle = {'bV34YIJQ': [intangir, other_part], 'Wp39QX52': skills}

        balanced = rebalance_intangir_trial('8991101', bundle)

        self.assertIsNot(balanced, bundle)
        self.assertEqual(
            {key: balanced['bV34YIJQ'][0][key]
             for key in ('fh31sk7B', '9NBV1XCS', 'Pn5w9dfh', '84FJM3PD', 'T8xMDAZ4')},
            {'fh31sk7B': '5750000', '9NBV1XCS': '420', 'Pn5w9dfh': '40',
             '84FJM3PD': '300', 'T8xMDAZ4': '30'},
        )
        self.assertEqual(balanced['bV34YIJQ'][1], other_part)
        self.assertIs(balanced['Wp39QX52'], skills)
        self.assertEqual(intangir['fh31sk7B'], '230000')

    def test_other_missions_keep_the_original_bundle(self):
        bundle = {'bV34YIJQ': [{'xqartN26': '401011000', 'fh31sk7B': '230000'}]}

        self.assertIs(rebalance_intangir_trial('8991103', bundle), bundle)


if __name__ == '__main__':
    unittest.main()