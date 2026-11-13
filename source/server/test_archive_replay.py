from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import event_archive
import gacha_archive
import gacha_rotation
import history_runs
import replay


class ArchiveReplayTests(unittest.TestCase):
    def test_vortex_combines_full_runs_and_unlocked_seasons(self):
        running = {"area": "1", "name": "Running", "release": "2018-01-01", "group": "season2"}
        seasonal = {"area": "2", "name": "Seasonal", "release": "2018-02-01", "group": "season2"}
        locked = {"area": "3", "name": "Locked", "release": "2020-01-01", "group": "season3"}
        rows = [running, seasonal, locked]
        player = SimpleNamespace(data={"progress": {"cleared_missions": ["2000101"]}})
        window = {"from": date(2020, 1, 8), "to": date(2020, 1, 15), "index": 1, "finished": False}
        runs = {
            "1": [(date(2020, 1, 1), date(2020, 1, 10))],
            "2": [(date(2018, 2, 1), date(2018, 2, 14))],
            "3": [(date(2020, 1, 1), date(2020, 1, 10))],
        }
        with patch.dict("os.environ", {"EXVIUS_SUMMON_ROTATION": "1", "EXVIUS_VORTEX_ROTATION": "1",
                                        "EXVIUS_REPLAY_FULL_RUNS": "1"}), \
                patch.object(event_archive, "events", return_value=rows), \
                patch.object(event_archive, "listings", return_value=[(row, []) for row in rows]), \
                patch.object(event_archive, "hidden_areas", return_value=set()), \
                patch.object(event_archive, "only_existing_quests", side_effect=lambda rows, *args: rows), \
                patch.object(event_archive, "hide_clone_quests", side_effect=lambda rows: rows), \
                patch.object(gacha_rotation, "vortex_week", return_value={"dates": [], "holiday": None,
                                                                           "years": []}), \
                patch.object(gacha_rotation, "week", return_value=(1, None, None)), \
                patch.object(replay, "enabled", return_value=True), \
                patch.object(replay, "window", return_value=window), \
                patch.object(history_runs, "event_runs", side_effect=lambda row: runs[row["area"]]):
            self.assertEqual([row["area"] for row in event_archive.vortex_events(player)], ["1", "2"])

    def test_rotation_off_summons_still_obey_story_unlocks(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": ["2000101"]}})
        banners = [
            {"id": "1", "name": "Season two", "release": "2018-01-01", "art": {"banner": "one"}},
            {"id": "2", "name": "Season three", "release": "2020-01-01", "art": {"banner": "two"}},
        ]
        with patch.dict("os.environ", {"EXVIUS_SUMMON_ROTATION": "0"}), \
                patch.object(gacha_archive, "held_ticket_ids", return_value=[]):
            self.assertEqual([banner["id"] for banner in gacha_archive.visible_banners(player, banners)], ["1"])
            self.assertEqual(gacha_archive.menu(player, banners)["groups"][0]["count"], 1)


if __name__ == "__main__":
    unittest.main()
