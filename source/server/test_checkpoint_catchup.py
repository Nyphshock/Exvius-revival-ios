from datetime import date
import unittest
from unittest.mock import patch

import checkpoint_catchup
from trial_progression import CHECKPOINTS


class CatchupPlayer:
    def __init__(self):
        self.data = {"progress": {"cleared_missions": []}}
        self.dirty = False
        self.mode = "live"
        self.currencies = {"lapis_free": 0, "gil": 0}
        self.cleared = {}
        self.paid = {}
        self.inventory = []
        self.beasts = []
        self.switches = set()

    def clear_mission(self, mission):
        self.data["progress"]["cleared_missions"].append(mission)

    def credit_challenge(self, mission, challenge):
        self.cleared.setdefault(mission, set()).add(challenge)
        paid = self.paid.setdefault(mission, set())
        if challenge in paid:
            return False
        paid.add(challenge)
        return True

    def mark_challenge_cleared(self, mission, challenge):
        self.cleared.setdefault(mission, set()).add(challenge)

    def _can_credit(self, _row):
        return True

    def _grant_items(self, rows):
        self.inventory.extend(rows)
        return rows

    def add_currency(self, currency, amount):
        self.currencies[currency] = self.currencies.get(currency, 0) + amount

    def owns_beast(self, esper):
        return any(row["esper_id"] == str(esper) for row in self.beasts)

    def grant_beast(self, esper, rarity=1, level=1):
        row = {"esper_id": str(esper), "rarity": rarity, "level": level}
        self.beasts.append(row)
        return row

    def grant_switch(self, _switch_type, index):
        self.switches.add(index)


class CheckpointCatchupTests(unittest.TestCase):
    def test_settlement_marker_retries_after_story_and_sidequest_ledgers_exist(self):
        checkpoint, group = next((day, group) for day, group in CHECKPOINTS if len(group) > 1)
        prior = {mission for day, missions in CHECKPOINTS if day < checkpoint for mission in missions}
        cleared = prior | set(group)
        completed = {day.isoformat(): {} for day, _missions in CHECKPOINTS if day <= checkpoint}
        zone_rewards = dict(completed)
        zone_rewards.pop(checkpoint.isoformat())
        secret_zones = dict(completed)
        secret_zones.pop(checkpoint.isoformat())
        player = type("Player", (), {})()
        player.mode = "live"
        player.data = {"progress": {"cleared_missions": list(cleared)},
                       checkpoint_catchup.LEDGER: completed,
                       checkpoint_catchup.SIDEQUEST_LEDGER: dict(completed),
                   checkpoint_catchup.ZONE_REWARD_LEDGER: zone_rewards,
                   checkpoint_catchup.SECRET_ZONE_LEDGER: secret_zones}

        with patch.object(checkpoint_catchup, "apply") as apply:
            checkpoint_catchup.apply_completed(player)

        apply.assert_called_once_with(player, checkpoint)

    def test_zone_settlement_includes_quest_unlocked_town_and_exploration_chests_once(self):
        rows = {
            "quest-town-chest": {"town": "quest-town", "switch": "quest-town-switch", "rewards": "20:1:1"},
            "future-town-chest": {"town": "future-town", "switch": "future-town-switch", "rewards": "20:2:1"},
            "story-mission-chest": {"mission": "story-explore", "switch": "mission-switch", "rewards": "20:3:1"},
            "exploration-map-chest": {"resources": ["dungeon-10100"], "switch": "map-switch", "rewards": "20:4:1"},
        }
        tables = {
            "F_TOWN_MST.ndjson": {
                "quest-town": {"9Pb24aSy": "world-1", "juA0Z4m7": "quest-town-switch"},
                "future-town": {"9Pb24aSy": "world-1", "juA0Z4m7": "future-town-switch"},
            },
            "F_WORLD_MST.ndjson": {"world-1": {"dw2nvP3r": "1"}},
        }
        player = CatchupPlayer()
        credited = set()

        def credit(chest_id, _row):
            if chest_id in credited:
                return False
            credited.add(chest_id)
            return True

        with patch("player_state._load_ndjson", side_effect=lambda name, _key=None: tables[name]), \
                patch("exvius_field_treasures.catalogue", return_value=rows), \
                patch("exvius_field_treasures._exploration_dungeon",
                      side_effect=lambda mid: "dungeon-1" if mid == "story-explore" else None), \
                patch("exvius_field_treasures._credit", side_effect=credit), \
                patch("ffbe_state.State.player", player):
            first = checkpoint_catchup._settle_field_treasures(
                player, ["story-explore"], {"quest-town-switch"}
            )
            repeated = checkpoint_catchup._settle_field_treasures(
                player, ["story-explore"], {"quest-town-switch"}
            )

        self.assertEqual(first, 3)
        self.assertEqual(repeated, 0)
        self.assertEqual(credited, {"quest-town-chest", "story-mission-chest", "exploration-map-chest"})

    def test_story_map_switches_follow_only_reachable_prerequisites(self):
        rows = {
            "1": {"6uIYE15X": "town-1", "juA0Z4m7": "story-open", "dIPkNn61": "map-open"},
            "2": {"6uIYE15X": "town-1", "juA0Z4m7": "map-open", "dIPkNn61": "next-map-open"},
            "3": {"6uIYE15X": "future-town", "juA0Z4m7": "future-open", "dIPkNn61": "future-map-open"},
        }
        tables = {
            "F_STORY_SUB_MST.ndjson": rows,
            "F_MISSION_MST.ndjson": {"story-mission": {"U9iHsau3": "dungeon-1"}},
            "F_DUNGEON_MST.ndjson": {"dungeon-1": {"uv60hgDW": "area-1"}},
            "F_AREA_MST.ndjson": {"area-1": {}},
            "F_TOWN_MST.ndjson": {"town-1": {"9Pb24aSy": "world-1", "juA0Z4m7": "0"},
                                   "future-town": {"9Pb24aSy": "world-1", "juA0Z4m7": "future-open"}},
            "F_WORLD_MST.ndjson": {"world-1": {"dw2nvP3r": "1"}},
        }
        with patch("player_state._load_ndjson", side_effect=lambda name, _key=None: tables[name]):
            switches = checkpoint_catchup._story_map_switches({"story-open"}, ["story-mission"])

        self.assertEqual(switches, {"story-open", "map-open", "next-map-open"})

    def test_secret_dungeon_gates_require_their_region_story_switches(self):
        tables = {
            "F_STORY_SUB_MST.ndjson": {},
            "F_MISSION_MST.ndjson": {"story-d1": {"U9iHsau3": "story-d1"},
                                      "story-d2": {"U9iHsau3": "story-d2"}},
            "F_DUNGEON_MST.ndjson": {
                "story-d1": {"uv60hgDW": "area-1"},
                "story-d2": {"uv60hgDW": "area-2"},
                "12301": {"uv60hgDW": "area-1"},
                "13251": {"uv60hgDW": "area-2"},
            },
            "F_AREA_MST.ndjson": {"area-1": {}, "area-2": {}},
            "F_TOWN_MST.ndjson": {},
            "F_WORLD_MST.ndjson": {},
        }
        with patch("player_state._load_ndjson", side_effect=lambda name, _key=None: tables[name]):
            dirnado = checkpoint_catchup._story_map_switches({"10047002"}, ["story-d1"])
            olderion = checkpoint_catchup._story_map_switches(
                {"10047002", "10075500"}, ["story-d1", "story-d2"]
            )

        self.assertIn("10047003", dirnado)
        self.assertNotIn("10076008", dirnado)
        self.assertEqual({"10047003", "10076008"} & olderion, {"10047003", "10076008"})

    def test_sidequest_missions_follow_reachable_exploration_gates_and_cutoff(self):
        mission_rows = {
            "100": {"U9iHsau3": "d1", "9Pb24aSy": "story"},
            "200": {"U9iHsau3": "d1", "9Pb24aSy": "story", "dIPkNn61": "unlock-next"},
            "201": {"U9iHsau3": "d2", "9Pb24aSy": "story", "juA0Z4m7": "unlock-next"},
            "202": {"U9iHsau3": "d3", "9Pb24aSy": "story"},
            "203": {"U9iHsau3": "d1", "9Pb24aSy": "story"},
            "204": {"U9iHsau3": "d1", "9Pb24aSy": "event"},
        }
        tables = {
            "F_MISSION_MST.ndjson": mission_rows,
            "F_DUNGEON_MST.ndjson": {
                "d1": {"uv60hgDW": "a1"},
                "d2": {"uv60hgDW": "a2", "juA0Z4m7": "unlock-next"},
                "d3": {"uv60hgDW": "a1", "juA0Z4m7": "future-switch"},
            },
            "F_AREA_MST.ndjson": {"a1": {}, "a2": {}, "a3": {}},
            "F_WORLD_MST.ndjson": {"story": {"dw2nvP3r": "1"}, "event": {"dw2nvP3r": "2"}},
            "F_STORY_SUB_MST.ndjson": {},
        }
        with patch("player_state._load_ndjson", side_effect=lambda name, _key=None: tables[name]), \
                patch("player_state.is_main_story_mission", side_effect=lambda mid: str(mid) == "100"), \
                patch("exvius_field_treasures._exploration_dungeon",
                      side_effect=lambda mid: "d1" if str(mid) == "100" else "d" + str(int(mid) - 199)), \
                patch("event_archive.events", return_value=[{"missions": []}]), \
                patch("event_archive.quest_dates", return_value={"missions": {"203": "2017-01-01"}}), \
                patch("event_archive.checkpoint_date_for_mission", return_value=None), \
                patch("event_archive.MISSION_RELEASE_OVERRIDES", {}):
            selected = checkpoint_catchup._sidequest_missions(
                date(2016, 8, 25), ["100"], {"unlock-next"}
            )

        self.assertEqual(selected, ["200", "201"])

    def test_town_quest_catchup_grants_completion_switch_and_reward_once(self):
        tables = {
            "F_TOWN_MST.ndjson": {"1101": {"9Pb24aSy": "world-1", "juA0Z4m7": "town-switch"}},
            "F_WORLD_MST.ndjson": {"world-1": {"dw2nvP3r": "1"}},
            "F_QUEST_MST.ndjson": {
                "1000": {"AgoB52Ey": "1", "6uIYE15X": "1101", "juA0Z4m7": "quest-switch",
                          "dIPkNn61": "dependent-quest-switch", "dX6cor8j": ""},
                "1001": {"AgoB52Ey": "1", "6uIYE15X": "1101", "juA0Z4m7": "0",
                         "dIPkNn61": "quest-switch", "dX6cor8j": "quest-reward"},
            },
            "F_QUEST_SUB_MST.ndjson": {
                "100001": {"Z34jU7ue": "1000", "7Svg2kdT": "100001", "Z0EN6jSh": "1",
                           "dIPkNn61": "dependent-step-switch", "89EvGKHx": "0", "siLGXq94": "0"},
                "100101": {"Z34jU7ue": "1001", "7Svg2kdT": "100101", "Z0EN6jSh": "1",
                           "dIPkNn61": "step-switch", "89EvGKHx": "1", "siLGXq94": "1",
                           "25oxcKwN": "step-delivery"},
            },
        }
        player = CatchupPlayer()
        reward = [{"kind": 20, "id": 12345, "count": 1}]
        reward_calls = []
        with patch("player_state._load_ndjson", side_effect=lambda name, _key=None: tables[name]), \
                patch("player_state.switch_position", side_effect=lambda switch: ("101", 1)
                          if switch in {"step-switch", "quest-switch", "dependent-step-switch",
                                        "dependent-quest-switch"} else None), \
                    patch("exvius_actions_expedition._expedition_rewards",
                        side_effect=lambda value: (reward_calls.append(value),
                                         reward if value == "quest-reward" else [])[1]):
            summary = checkpoint_catchup._complete_town_quests(player, {"town-switch"})
            repeated = checkpoint_catchup._complete_town_quests(player, {"town-switch"})

        switches = {"step-switch", "quest-switch", "dependent-step-switch", "dependent-quest-switch"}
        self.assertEqual(summary, {"town_quests": 2, "quest_steps": 2, "quest_reward_rows": 1,
                       "switches": switches})
        self.assertEqual(repeated, {"town_quests": 0, "quest_steps": 0, "quest_reward_rows": 0,
                        "switches": switches})
        self.assertEqual(player.inventory, reward)
        self.assertEqual(reward_calls, ["quest-reward"])
        self.assertEqual(player.switches, {1})
        self.assertEqual(player.data["exvius_map"]["quests"]["100101"]["4kcAD9fW"], "2")

    def test_apply_completed_waits_for_every_trial_in_the_checkpoint_group(self):
        checkpoint, group = next((day, group) for day, group in CHECKPOINTS if len(group) > 1)
        prior = {mission for day, missions in CHECKPOINTS if day < checkpoint for mission in missions}
        cleared = prior | (set(group) - {next(iter(group))})
        completed = {day.isoformat(): {} for day, _missions in CHECKPOINTS if day <= checkpoint}
        zone_rewards = dict(completed)
        zone_rewards.pop(checkpoint.isoformat())
        player = type("Player", (), {})()
        player.mode = "live"
        player.data = {"progress": {"cleared_missions": list(cleared)},
                       checkpoint_catchup.LEDGER: completed,
                       checkpoint_catchup.SIDEQUEST_LEDGER: dict(completed),
                       checkpoint_catchup.ZONE_REWARD_LEDGER: zone_rewards,
                       checkpoint_catchup.SECRET_ZONE_LEDGER: dict(completed)}

        with patch.object(checkpoint_catchup, "apply") as apply:
            checkpoint_catchup.apply_completed(player)
            apply.assert_not_called()
            player.data["progress"]["cleared_missions"].append(next(iter(group & (group - cleared))))
            checkpoint_catchup.apply_completed(player)

        apply.assert_called_once_with(player, checkpoint)

    def test_completes_only_checkpoint_story_and_settles_rewards_once(self):
        player = CatchupPlayer()
        chest_rows = {
            "mission-chest": {"missions": ["story-2"], "towns": [], "resources": []},
            "town-chest": {"missions": [], "towns": ["town-1"], "resources": []},
            "exploration-chest": {"missions": [], "towns": [], "resources": ["dungeon-10100"]},
            "future-chest": {"missions": ["story-3"], "towns": [], "resources": []},
            "event-town-chest": {"missions": [], "towns": ["event-town"], "resources": []},
        }
        credited_chests = set()

        def credit_chest(chest_id, _row):
            if chest_id in credited_chests:
                return False
            credited_chests.add(chest_id)
            return True

        with patch("trial_progression._story_order_and_context",
                   return_value=(("story-1", "story-2", "story-3"), {})), \
                patch("trial_progression.story_limit_for_checkpoint", return_value="story-2"), \
                patch("player_state.mission_open_switch", side_effect={
                    "story-1": "town-1-switch", "story-2": "0", "story-3": "future-town-switch",
                }.get), \
                patch("player_state._main_story_clear_switches", return_value={}), \
                patch("player_state._load_ndjson", side_effect=lambda name, _key=None: {
                    "F_STORY_SUB_MST.ndjson": {},
                    "F_MISSION_MST.ndjson": {"story-1": {"U9iHsau3": "dungeon-1"},
                                              "story-2": {"U9iHsau3": "dungeon-1"}},
                    "F_DUNGEON_MST.ndjson": {"dungeon-1": {"uv60hgDW": "area-1"}},
                    "F_AREA_MST.ndjson": {"area-1": {}},
                    "F_TOWN_MST.ndjson": {
                        "town-1": {"9Pb24aSy": "world-1", "juA0Z4m7": "town-1-switch"},
                        "town-2": {"9Pb24aSy": "world-1", "juA0Z4m7": "future-town-switch"},
                        "event-town": {"9Pb24aSy": "world-event", "juA0Z4m7": ""},
                    },
                    "F_WORLD_MST.ndjson": {"world-1": {"dw2nvP3r": "1"},
                                           "world-event": {"dw2nvP3r": "2"}},
                    "F_QUEST_MST.ndjson": {},
                    "F_QUEST_SUB_MST.ndjson": {},
                }[name]), \
                patch("player_state.story_beast_for_mission", side_effect={
                    "story-1": 1, "story-2": 2, "story-3": 3,
                }.get), \
                patch("ffbe_battle.challenge_table", return_value={
                    "story-1": {"challenge-1": (10, "condition", 0), "challenge-2": (0, "condition", 1)},
                    "story-2": {"challenge-3": (20, "condition", 0)},
                }), \
                patch("ffbe_battle.LAPIS_AWARD", True), \
                patch("first_clear.enabled", return_value=True), \
                patch("first_clear.raw", return_value="reward"), \
                patch("first_clear.rewards", side_effect=lambda mission: [
                    {"kind": 20, "id": int(mission[-1]), "count": 1}]), \
                patch("story_recipes.note_paid"), \
                patch("mission_gil.enabled", return_value=True), \
                patch("mission_gil.amount", return_value=5), \
                patch("lapis_economy.earned", side_effect=lambda amount: amount), \
                patch("exvius_field_treasures.catalogue", return_value=chest_rows), \
                patch("exvius_field_treasures._town_ids",
                      side_effect=lambda row: set(map(str, row.get("towns", [])))), \
                patch("exvius_field_treasures._exploration_dungeon",
                      side_effect=lambda mission: "dungeon-1" if mission == "story-1" else None), \
                patch("exvius_field_treasures._credit", side_effect=credit_chest), \
                patch("ffbe_state.State.state_dirty", False):
            summary = checkpoint_catchup.apply(player, date(2016, 8, 25))
            repeated = checkpoint_catchup.apply(player, date(2016, 8, 25))

        self.assertEqual(player.data["progress"]["cleared_missions"], ["story-1", "story-2"])
        self.assertEqual(player.currencies["lapis_free"], 30)
        self.assertEqual(player.currencies["gil"], 10)
        self.assertEqual(len(player.inventory), 2)
        self.assertEqual(player.cleared, {
            "story-1": {"challenge-1", "challenge-2"},
            "story-2": {"challenge-3"},
        })
        self.assertEqual([(beast["esper_id"], beast["rarity"]) for beast in player.beasts],
                         [("1", 1), ("2", 1)])
        self.assertEqual(credited_chests, {"mission-chest", "town-chest", "exploration-chest"})
        self.assertEqual(summary["missions"], 2)
        self.assertEqual(summary["chests"], 3)
        self.assertIsNone(repeated)


if __name__ == "__main__":
    unittest.main()