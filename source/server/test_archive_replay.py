from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import event_archive
import exvius_events
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

    def test_undated_future_vortex_events_wait_for_their_first_release(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": []}})
        rows = [
            {"area": "1096", "name": "Daily Eggstravaganza", "group": "other",
             "missions": ["10960101"]},
            {"area": "1041", "name": "Monthly Fortune Hunt", "group": "other",
             "missions": ["10410101"]},
            {"area": "909", "name": "Series Boss Battle", "group": "other",
             "missions": ["9000901"]},
        ]
        with patch.object(event_archive, "events", return_value=rows):
            self.assertEqual(event_archive.filter_events_by_story(rows, player), [])
            for mission in ("10960101", "10410101", "9000901"):
                self.assertFalse(event_archive.mission_is_available(player, mission))

    def test_recurring_vortex_events_unlock_at_their_release_dates(self):
        def player_before(day):
            cleared = [mission for checkpoint, missions in CHECKPOINTS if checkpoint < day
                       for mission in missions]
            return SimpleNamespace(data={"progress": {"cleared_missions": cleared}})

        rows = [
            {"area": "909", "name": "Series Boss Battle", "group": "other", "missions": ["9000901"]},
            {"area": "1041", "name": "Monthly Fortune Hunt", "group": "other", "missions": ["10410101"]},
            {"area": "1096", "name": "Daily Eggstravaganza", "group": "other", "missions": ["10960101"]},
        ]
        march_2020 = event_archive.filter_events_by_story(rows, player_before(date(2020, 3, 5)))
        self.assertEqual([row["area"] for row in march_2020], ["909"])
        january_2022 = event_archive.filter_events_by_story(rows, player_before(date(2022, 1, 13)))
        self.assertEqual([row["area"] for row in january_2022], ["909", "1041"])
        august_2022 = event_archive.filter_events_by_story(rows, player_before(date(2022, 8, 18)))
        self.assertEqual([row["area"] for row in august_2022], ["909", "1041", "1096"])

    def test_series_boss_quests_unlock_on_individual_release_dates(self):
        cleared = [mission for checkpoint, missions in CHECKPOINTS if checkpoint < date(2019, 9, 12)
                   for mission in missions]
        player = SimpleNamespace(data={"progress": {"cleared_missions": cleared}})
        row = {"area": "909", "name": "Series Boss Battle", "group": "other",
               "missions": ["9091102", "9091101", "9091104"]}
        visible = event_archive.filter_events_by_story([row], player)
        self.assertEqual(visible[0]["missions"], ["9091102", "9091101"])
        self.assertTrue(event_archive.mission_is_available(player, "9091102"))
        self.assertTrue(event_archive.mission_is_available(player, "9091101"))
        self.assertFalse(event_archive.mission_is_available(player, "9091104"))

    def test_series_boss_ext_quests_have_their_own_release_dates(self):
        cleared = [mission for checkpoint, missions in CHECKPOINTS if checkpoint < date(2022, 1, 13)
                   for mission in missions]
        player = SimpleNamespace(data={"progress": {"cleared_missions": cleared}})
        row = {"area": "909", "name": "Series Boss Battle", "group": "other",
               "missions": ["9091118", "99460101", "99580101"]}
        visible = event_archive.filter_events_by_story([row], player)
        self.assertEqual(visible[0]["missions"], ["9091118"])
        self.assertTrue(event_archive.mission_is_available(player, "9091118"))
        self.assertFalse(event_archive.mission_is_available(player, "99460101"))
        self.assertFalse(event_archive.mission_is_available(player, "99580101"))

    def test_unknown_dated_event_fails_closed_but_permanent_content_remains(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": []}})
        rows = [
            {"area": "7777", "name": "Undated event", "group": "other", "missions": []},
            {"area": "225", "name": "Permanent chamber", "group": "permanent", "missions": []},
        ]
        self.assertEqual([row["area"] for row in event_archive.filter_events_by_story(rows, player)],
                         ["225"])

    def test_launch_era_daily_vortex_areas_remain_available(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": []}})
        rows = [
            {"area": "218", "name": "Cactuar Dunes", "group": "other", "missions": []},
            {"area": "219", "name": "Gil Snapper's Cave", "group": "other", "missions": []},
            {"area": "1038", "name": "Daily Gil Hunt", "group": "other", "missions": []},
        ]
        self.assertEqual([row["area"] for row in event_archive.filter_events_by_story(rows, player)],
                         ["218", "219", "1038"])

    def test_only_present_enhance_areas_are_kept_open(self):
        self.assertIn("228", event_archive.enhance_areas())
        spec = {"0xkoNP8U": [
            {"uv60hgDW": "228", "VjJQ51uG": "2000-01-01 00:00:00",
             "m8ivD4NX": "2000-01-02 00:00:00"},
            {"uv60hgDW": "970", "VjJQ51uG": "2000-01-01 00:00:00",
             "m8ivD4NX": "2000-01-02 00:00:00"},
        ]}
        out = exvius_events.keep_present_areas_open(spec, event_archive.enhance_areas(), now=1_767_398_400)
        self.assertEqual(len(out["0xkoNP8U"]), 2)
        self.assertNotEqual(out["0xkoNP8U"][0]["m8ivD4NX"], "2000-01-02 00:00:00")
        self.assertEqual(out["0xkoNP8U"][1], spec["0xkoNP8U"][1])
        self.assertEqual(spec["0xkoNP8U"][0]["m8ivD4NX"], "2000-01-02 00:00:00")

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

    def test_removed_evergreen_summons_are_hidden_and_not_unlocked(self):
        player = SimpleNamespace(data={"progress": {"cleared_missions": []}})
        removed = [
            {"id": "9", "name": "Rare Summon"},
            {"id": "24", "name": "Premium 10+1 Summon"},
            {"id": "33", "name": "5★ Guaranteed 10+1 Summon"},
            {"id": "45", "name": "5+1 Ticket Summon"},
            {"id": "46", "name": "5+1 Ticket Summon"},
            {"id": "60001", "name": "EXVIUS Summon"},
            {"id": "60002", "name": "NV EXVIUS Summon"},
        ]
        standard = {"id": "1", "name": "Standard Summon", "type": "friend"}
        self.assertEqual(gacha_archive.filter_banners_for_story(player, removed + [standard]), [standard])
        self.assertTrue(gacha_archive.banner_unlocked(player, standard))
        self.assertTrue(all(not gacha_archive.banner_unlocked(player, banner) for banner in removed))


if __name__ == "__main__":
    unittest.main()
