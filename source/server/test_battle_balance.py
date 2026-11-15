import unittest

from battle_content import rebalance_trial_bosses


class TrialBalanceTests(unittest.TestCase):
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

        balanced = rebalance_trial_bosses('8991101', bundle)

        self.assertIsNot(balanced, bundle)
        self.assertEqual(
            {key: balanced['bV34YIJQ'][0][key]
             for key in ('fh31sk7B', '9NBV1XCS', 'Pn5w9dfh', '84FJM3PD', 'T8xMDAZ4')},
            {'fh31sk7B': '14950000', '9NBV1XCS': '420', 'Pn5w9dfh': '40',
             '84FJM3PD': '300', 'T8xMDAZ4': '30'},
        )
        self.assertEqual(balanced['bV34YIJQ'][1], other_part)
        self.assertIs(balanced['Wp39QX52'], skills)
        self.assertEqual(intangir['fh31sk7B'], '230000')

    def test_antennolla_stats_increase_for_every_part(self):
        original_parts = [
            {'xqartN26': '411001000', '6Yc4RkdM': str(number), 'fh31sk7B': '290000',
             '9NBV1XCS': atk, 'Pn5w9dfh': '25', '84FJM3PD': mag, 'T8xMDAZ4': spr}
            for number, atk, mag, spr in (
                (1, '380', '280', '25'),
                (2, '230', '25', '25'),
                (3, '290', '250', '25'),
                (4, '200', '0', '40'),
            )
        ]
        bundle = {'bV34YIJQ': original_parts}

        balanced = rebalance_trial_bosses('8991103', bundle)

        self.assertEqual(len(balanced['bV34YIJQ']), 4)
        self.assertEqual(
            [{key: part[key] for key in ('fh31sk7B', '9NBV1XCS', 'Pn5w9dfh', '84FJM3PD', 'T8xMDAZ4')}
             for part in balanced['bV34YIJQ']],
            [
                {'fh31sk7B': '18850000', '9NBV1XCS': '456', 'Pn5w9dfh': '40', '84FJM3PD': '336', 'T8xMDAZ4': '37'},
                {'fh31sk7B': '18850000', '9NBV1XCS': '276', 'Pn5w9dfh': '40', '84FJM3PD': '30', 'T8xMDAZ4': '37'},
                {'fh31sk7B': '18850000', '9NBV1XCS': '348', 'Pn5w9dfh': '40', '84FJM3PD': '300', 'T8xMDAZ4': '37'},
                {'fh31sk7B': '18850000', '9NBV1XCS': '240', 'Pn5w9dfh': '40', '84FJM3PD': '0', 'T8xMDAZ4': '60'},
            ],
        )
        self.assertEqual(original_parts[0]['9NBV1XCS'], '380')

    def test_surging_menace_stats_and_hp_increase_for_every_enemy_part(self):
        original_parts = [
            {'xqartN26': monster_id, '6Yc4RkdM': str(part_number), 'fh31sk7B': hp,
             '9NBV1XCS': '300', 'Pn5w9dfh': '25', '84FJM3PD': '250', 'T8xMDAZ4': '30'}
            for monster_id, part_number, hp in (
                ('211011001', 1, '1500'),
                ('104021006', 1, '30000'),
                ('104022006', 1, '30000'),
                ('106002007', 1, '60000'),
                ('303011003', 1, '90000'),
                ('303011003', 2, '45000'),
                ('303011003', 3, '45000'),
                ('303011003', 4, '45000'),
                ('306001001', 1, '230000'),
                ('404002000', 1, '280000'),
            )
        ]
        bundle = {'bV34YIJQ': original_parts}

        balanced = rebalance_trial_bosses('8991102', bundle)

        self.assertEqual(len(balanced['bV34YIJQ']), 10)
        for original, updated in zip(original_parts, balanced['bV34YIJQ']):
            self.assertEqual(updated['fh31sk7B'], str(int(original['fh31sk7B']) * 65))
            self.assertEqual(updated['9NBV1XCS'], '360')
            self.assertEqual(updated['Pn5w9dfh'], '40')
            self.assertEqual(updated['84FJM3PD'], '300')
            self.assertEqual(updated['T8xMDAZ4'], '45')
        self.assertEqual(original_parts[0]['fh31sk7B'], '1500')

    def test_other_missions_keep_the_original_bundle(self):
        bundle = {'bV34YIJQ': [{'xqartN26': '401011000', 'fh31sk7B': '230000'}]}

        self.assertIs(rebalance_trial_bosses('8991106', bundle), bundle)


if __name__ == '__main__':
    unittest.main()