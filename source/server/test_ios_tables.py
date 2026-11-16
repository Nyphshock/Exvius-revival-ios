import unittest
import json
from unittest.mock import patch

import ios_tables


class MissionTableEsperGateTests(unittest.TestCase):
    def test_esper_missions_keep_native_requirements_and_add_checkpoint_switches(self):
        rows = [
            {"qo3PECw6": "1110406", "juA0Z4m7": "82001210", "dIPkNn61": "10007600,82001300"},
            {"qo3PECw6": "8980104", "juA0Z4m7": "", "dIPkNn61": "18710210"},
            {"qo3PECw6": "1515007", "juA0Z4m7": "82008210", "dIPkNn61": "10115700,82008300"},
            {"qo3PECw6": "8993201", "juA0Z4m7": "", "dIPkNn61": "18900210"},
            {"qo3PECw6": "8995303", "juA0Z4m7": "", "dIPkNn61": "18901420"},
            {"qo3PECw6": "2000101", "juA0Z4m7": "0", "dIPkNn61": "10005101"},
            {"qo3PECw6": "2000201", "juA0Z4m7": "0", "dIPkNn61": "10005201"},
            {"qo3PECw6": "9001603", "juA0Z4m7": "", "dIPkNn61": "90001154"},
            {"qo3PECw6": "4000101", "juA0Z4m7": "0", "dIPkNn61": "10000000"},
        ]
        parsed_rows = [(json.dumps(row), row, True) for row in rows]

        with patch.object(ios_tables, "_rows", return_value=parsed_rows), \
                patch.object(ios_tables, "_encrypt",
                             side_effect=lambda _key, row, _double: json.dumps(row)), \
                patch("reward_overrides.for_mission", return_value=False):
            raw, first_clears, gated = ios_tables.patch_mission_table(b"")
        patched = {str(row["qo3PECw6"]): row for row in map(json.loads, raw.decode("ascii").splitlines())}

        self.assertEqual(first_clears, 0)
        self.assertEqual(gated, 3)
        self.assertEqual(patched["1110406"]["juA0Z4m7"], "82001210,18710210")
        self.assertEqual(patched["1515007"]["juA0Z4m7"], "82008210,18900210,18901420")
        self.assertEqual(patched["2000201"]["juA0Z4m7"], "90001154")
        self.assertEqual(patched["2000101"]["juA0Z4m7"], "0")
        self.assertEqual(patched["4000101"]["juA0Z4m7"], "0")
        self.assertEqual(rows[0]["juA0Z4m7"], "82001210")

    def test_mission_table_version_bump_invalidates_client_cache(self):
        with patch("reward_overrides.enabled", return_value=False):
            self.assertGreaterEqual(ios_tables.table_bump(ios_tables.MISSION), 2000)
        with patch("captain_menu.table_bump", return_value=17):
            self.assertEqual(ios_tables.table_bump(ios_tables.MAP_CHECKSUM), 1017)


if __name__ == "__main__":
    unittest.main()