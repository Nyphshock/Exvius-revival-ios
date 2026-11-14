from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import event_archive
import ffbe_banner
import gacha_archive
import gacha_rotation
import history_runs
import replay
from trial_progression import CHECKPOINTS


class ArchiveReplayTests(unittest.TestCase):
    def test_event_trials_and_direct_loads_stop_at_next_checkpoint(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": []}})
        row = {"area": "899", "release": "2016-07-14",
               "missions": ["8991101", "8991103", "8991106"]}
        visible = event_archive.filter_events_by_story([row], player)
        self.assertEqual(visible[0]["missions"], ["8991101"])
        self.assertTrue(event_archive.mission_is_available(player, "8991101"))
        self.assertFalse(event_archive.mission_is_available(player, "8991103"))

    def test_all_difficulties_in_active_trial_dungeon_are_loadable(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": []}})
        with patch.object(event_archive, "_mission_dungeon",
                          side_effect=lambda mission: "active" if str(mission) in ("8991101", "8991100")
                          else "later"):
            self.assertTrue(event_archive.mission_is_available(player, "8991100"))
            self.assertFalse(event_archive.mission_is_available(player, "8991103"))

    def test_home_marquee_hides_checkpoint_date_banners_per_profile(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": []}})
        entries = [
            {"name": "Earlier", "start": "2016-08-24"},
            {"name": "At checkpoint", "start": "2016-08-25"},
            {"name": "Undated promotion"},
        ]
        visible = ffbe_banner._filter_entries_for_player(entries, player)
        self.assertEqual([entry["name"] for entry in visible], ["Earlier", "Undated promotion"])

    def test_vortex_combines_full_runs_and_pre_checkpoint_archive(self):
        running = {"area": "1", "name": "Running", "release": "2018-01-01", "group": "season2"}
        seasonal = {"area": "2", "name": "Seasonal", "release": "2018-02-01", "group": "season2"}
        locked = {"area": "3", "name": "Locked", "release": "2020-04-01", "group": "season3"}
        rows = [running, seasonal, locked]
        cleared = [mission for day, missions in CHECKPOINTS if day < date(2020, 2, 20)
                   for mission in missions]
        player = SimpleNamespace(data={"progress": {"cleared_missions": cleared}})
        window = {"from": date(2020, 1, 8), "to": date(2020, 1, 15), "index": 1, "finished": False}
        runs = {
            "1": [(date(2020, 1, 1), date(2020, 1, 10))],
            "2": [(date(2018, 2, 1), date(2018, 2, 14))],
            "3": [(date(2020, 4, 1), date(2020, 4, 10))],
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
            self.assertCountEqual([row["area"] for row in event_archive.vortex_events(player)], ["1", "2"])

    def test_rotation_off_summons_stop_at_next_trial_date(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": ["8991101"]}})
        banners = [
            {"id": "1", "name": "Before checkpoint", "release": "2016-11-23", "art": {"banner": "one"}},
            {"id": "2", "name": "At checkpoint", "release": "2016-11-24", "art": {"banner": "two"}},
        ]
        with patch.dict("os.environ", {"EXVIUS_SUMMON_ROTATION": "0"}), \
                patch.object(gacha_archive, "held_ticket_ids", return_value=[]):
            self.assertEqual([banner["id"] for banner in gacha_archive.visible_banners(player, banners)], ["1"])
            self.assertEqual(gacha_archive.menu(player, banners)["groups"][0]["count"], 1)


if __name__ == "__main__":
    unittest.main()
