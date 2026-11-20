"""One-time story catch-up rewards when a historical Trial checkpoint is cleared."""
from __future__ import annotations

from copy import deepcopy


LEDGER = "checkpoint_story_catchup"
SIDEQUEST_LEDGER = "checkpoint_sidequest_catchup"
ZONE_REWARD_LEDGER = "checkpoint_zone_reward_settlement"
SECRET_ZONE_LEDGER = "checkpoint_secret_zone_unlocks"
SECRET_DUNGEON_GATES = (("12301", "10047003", "10047002"),
                        ("13251", "10076008", "10075500"))


def _story_missions(checkpoint):
    from trial_progression import (_story_order_and_context, mission_is_within_story_limit,
                                   story_limit_for_checkpoint)

    order, _context = _story_order_and_context()
    limit = story_limit_for_checkpoint(checkpoint)
    if limit is None or limit not in order:
        raise ValueError(f"no shipped story endpoint for checkpoint {checkpoint.isoformat()}")
    return [mission for mission in order if mission_is_within_story_limit(mission, limit, order)]


def _switch_requirement_met(expression, switches):
    expression = str(expression or "").strip()
    if not expression or expression == "0":
        return True
    return any(all(switch.strip() in switches for switch in clause.split(",") if switch.strip())
               for clause in expression.split("|"))


def _story_map_switches(switches, story_missions):
    from player_state import _load_ndjson

    available = set(switches)
    rows = _load_ndjson("F_STORY_SUB_MST.ndjson", "6a9TDRcj")
    missions = _load_ndjson("F_MISSION_MST.ndjson", "qo3PECw6")
    dungeons = _load_ndjson("F_DUNGEON_MST.ndjson", "U9iHsau3")
    areas = _load_ndjson("F_AREA_MST.ndjson", "uv60hgDW")
    towns = _load_ndjson("F_TOWN_MST.ndjson", "Gh92V3Tx")
    worlds = _load_ndjson("F_WORLD_MST.ndjson", "9Pb24aSy")
    story_dungeons = {str((missions.get(mid) or {}).get("U9iHsau3") or "") for mid in story_missions}
    story_dungeons.discard("")
    story_areas = {str((dungeons.get(dungeon) or {}).get("uv60hgDW") or "") for dungeon in story_dungeons}
    story_areas.discard("")

    def location_reachable(location):
        location = str(location or "")
        if location in towns:
            town = towns[location]
            world = worlds.get(str(town.get("9Pb24aSy") or "")) or {}
            return (world.get("dw2nvP3r") == "1"
                    and _switch_requirement_met(town.get("juA0Z4m7"), available))
        if location in dungeons:
            dungeon = dungeons[location]
            area_id = str(dungeon.get("uv60hgDW") or "")
            area = areas.get(area_id) or {}
            return (area_id in story_areas
                    and _switch_requirement_met(dungeon.get("juA0Z4m7"), available)
                    and _switch_requirement_met(area.get("juA0Z4m7"), available))
        if location in areas:
            area = areas[location]
            return location in story_areas and _switch_requirement_met(area.get("juA0Z4m7"), available)
        return False

    while True:
        added = set()
        for row in rows.values():
            requirement = str(row.get("juA0Z4m7") or "")
            if (not requirement or requirement == "0" or not location_reachable(row.get("6uIYE15X"))
                    or not _switch_requirement_met(requirement, available)):
                continue
            for switch in str(row.get("dIPkNn61") or "").split(","):
                switch = switch.strip()
                if switch and switch != "0" and switch not in available:
                    added.add(switch)
        if not added:
            break
        available.update(added)

    for dungeon_id, gate_switch, prerequisite in SECRET_DUNGEON_GATES:
        dungeon = dungeons.get(dungeon_id) or {}
        area_id = str(dungeon.get("uv60hgDW") or "")
        if area_id in story_areas and prerequisite in available:
            available.add(gate_switch)
    return available


def _grant_story_map_switches(player, switches, story_missions):
    from player_state import switch_position

    available = _story_map_switches(switches, story_missions)
    for switch in available - set(switches):
        position = switch_position(switch)
        if position:
            player.grant_switch(*position)
    return available


def _sidequest_missions(checkpoint, story_missions, story_switches):
    from event_archive import MISSION_RELEASE_OVERRIDES, checkpoint_date_for_mission, events, quest_dates
    from exvius_field_treasures import _exploration_dungeon
    from player_state import _load_ndjson

    missions = _load_ndjson("F_MISSION_MST.ndjson", "qo3PECw6")
    dungeons = _load_ndjson("F_DUNGEON_MST.ndjson", "U9iHsau3")
    areas = _load_ndjson("F_AREA_MST.ndjson", "uv60hgDW")
    worlds = _load_ndjson("F_WORLD_MST.ndjson", "9Pb24aSy")
    story_dungeons = {str(((missions.get(mission) or {}).get("U9iHsau3") or ""))
                      for mission in story_missions}
    story_dungeons.discard("")
    story_areas = {str((dungeons.get(dungeon) or {}).get("uv60hgDW") or "") for dungeon in story_dungeons}
    story_areas.discard("")
    event_missions = {str(mission) for event in events() for mission in event.get("missions") or []}
    mission_dates = quest_dates().get("missions") or {}
    available_switches = set(story_switches)
    selected = []
    story_mission_set = set(story_missions)
    pending = {str(mid) for mid, row in missions.items() if str(mid).isdigit()
               and str(mid) not in story_mission_set
               and str((worlds.get(str(row.get("9Pb24aSy") or "")) or {}).get("dw2nvP3r")) == "1"
               and _exploration_dungeon(mid) is not None and str(mid) not in event_missions}

    while pending:
        added = []
        for mid in sorted(pending, key=int):
            mission = missions[mid]
            dungeon_id = str(mission.get("U9iHsau3") or "")
            dungeon = dungeons.get(dungeon_id) or {}
            area_id = str(dungeon.get("uv60hgDW") or "")
            area = areas.get(area_id) or {}
            dungeon_gate = str(dungeon.get("juA0Z4m7") or "")
            area_gate = str(area.get("juA0Z4m7") or "")
            if (not _switch_requirement_met(dungeon_gate, available_switches)
                    or not _switch_requirement_met(area_gate, available_switches)):
                continue
            map_reachable = (area_id in story_areas or dungeon_gate not in ("", "0")
                             or area_gate not in ("", "0"))
            if not map_reachable or not _switch_requirement_met(mission.get("juA0Z4m7"), available_switches):
                continue
            release = (checkpoint_date_for_mission(mid) or MISSION_RELEASE_OVERRIDES.get(mid)
                       or mission_dates.get(mid))
            if release:
                try:
                    from datetime import date
                    if date.fromisoformat(str(release)[:10]) > checkpoint:
                        continue
                except ValueError:
                    continue
            added.append(mid)

        if not added:
            break
        for mid in added:
            pending.remove(mid)
            selected.append(mid)
            for switch in str(missions[mid].get("dIPkNn61") or "").replace("|", ",").split(","):
                if switch.strip() and switch.strip() != "0":
                    available_switches.add(switch.strip())
    return selected


def _complete_town_quests(player, story_switches):
    from exvius_actions_expedition import _expedition_rewards
    from player_state import _load_ndjson, switch_position

    towns = _load_ndjson("F_TOWN_MST.ndjson", "Gh92V3Tx")
    worlds = _load_ndjson("F_WORLD_MST.ndjson", "9Pb24aSy")
    unlocked_towns = set()
    for town_id, town in towns.items():
        world = worlds.get(str(town.get("9Pb24aSy") or "")) or {}
        required = {switch.strip() for switch in str(town.get("juA0Z4m7") or "").split(",")
                    if switch.strip() and switch.strip() != "0"}
        if world.get("dw2nvP3r") == "1" and required.issubset(story_switches):
            unlocked_towns.add(str(town_id))

    quests = _load_ndjson("F_QUEST_MST.ndjson", "Z34jU7ue")
    steps = _load_ndjson("F_QUEST_SUB_MST.ndjson", "7Svg2kdT")
    block = player.data.setdefault("exvius_map", {})
    saved = block.setdefault("quests", {})
    rewarded = set(map(str, block.get("rewarded") or []))
    available_switches = set(story_switches)
    granted_switches = set()
    step_count = reward_count = completed_quest_count = 0
    pending = list(quests.items())
    while pending:
        remaining = []
        progressed = False
        for qid, quest in pending:
            if (str(quest.get("AgoB52Ey")) != "1" or str(quest.get("6uIYE15X") or "") not in unlocked_towns
                    or not _switch_requirement_met(quest.get("juA0Z4m7"), available_switches)):
                remaining.append((qid, quest))
                continue
            quest_steps = sorted((step for step in steps.values() if str(step.get("Z34jU7ue")) == str(qid)),
                                 key=lambda step: int(step.get("Z0EN6jSh") or 0))
            if not quest_steps:
                continue
            progressed = True
            for step in quest_steps:
                sid = str(step["7Svg2kdT"])
                old = saved.get(sid) or {}
                if str(old.get("4kcAD9fW")) != "2":
                    saved[sid] = {"Z34jU7ue": str(qid), "7Svg2kdT": sid,
                                  "4kcAD9fW": "2", "0G7J2vfD": old.get("0G7J2vfD", "")}
                    step_count += 1
                for switch in str(step.get("dIPkNn61") or "").split(","):
                    pos = switch_position(switch.strip())
                    if pos:
                        player.grant_switch(*pos)
                        available_switches.add(switch.strip())
                        granted_switches.add(switch.strip())

            for switch in str(quest.get("dIPkNn61") or "").split(","):
                pos = switch_position(switch.strip())
                if pos:
                    player.grant_switch(*pos)
                    available_switches.add(switch.strip())
                    granted_switches.add(switch.strip())
            if str(qid) not in rewarded:
                reward_text = str(quest.get("dX6cor8j") or "")
                rewards = _expedition_rewards(reward_text) if reward_text else []
                if rewards:
                    if player._grant_items(rewards) != rewards:
                        raise RuntimeError(f"partial town quest reward for {qid}")
                    reward_count += len(rewards)
                rewarded.add(str(qid))
                completed_quest_count += 1
        if not progressed:
            break
        pending = remaining

    block["rewarded"] = sorted(rewarded, key=int)
    return {"town_quests": completed_quest_count, "quest_steps": step_count,
            "quest_reward_rows": reward_count, "switches": granted_switches}


def _settle_field_treasures(player, missions, switches):
    from exvius_field_treasures import _credit, _exploration_dungeon, _town_ids, catalogue
    from player_state import _load_ndjson

    towns = _load_ndjson("F_TOWN_MST.ndjson", "Gh92V3Tx")
    worlds = _load_ndjson("F_WORLD_MST.ndjson", "9Pb24aSy")
    unlocked_towns = set()
    for town_id, town in towns.items():
        required = {switch.strip() for switch in str(town.get("juA0Z4m7") or "").split(",")
                    if switch.strip() and switch.strip() != "0"}
        world = worlds.get(str(town.get("9Pb24aSy") or "")) or {}
        if required and world.get("dw2nvP3r") == "1" and required.issubset(switches):
            unlocked_towns.add(str(town_id))

    explorations = {dungeon for mission in missions
                    if (dungeon := _exploration_dungeon(mission)) is not None}
    chest_count = 0
    for chest_id, row in catalogue().items():
        town_match = bool(_town_ids(row) & unlocked_towns)
        chest_missions = set(map(str, row.get("missions", [])))
        if row.get("mission"):
            chest_missions = {str(row["mission"])}
        mission_match = bool(chest_missions & set(missions))
        map_match = False
        if not chest_missions and not _town_ids(row):
            resources = set(map(str, row.get("resources", [])))
            map_match = any(dungeon + "0100" in resources or str(chest_id).startswith(dungeon)
                            for dungeon in explorations)
        if (town_match or mission_match or map_match) and _credit(str(chest_id), row):
            chest_count += 1
    return chest_count


def apply(player, checkpoint):
    """Complete the available main story and settle its earned rewards exactly once per checkpoint."""
    from ffbe_state import State

    if player is None or player.mode == "frozen":
        return None
    key = checkpoint.isoformat()
    story_done = key in (player.data.get(LEDGER) or {})
    sidequests_done = key in (player.data.get(SIDEQUEST_LEDGER) or {})
    zone_rewards_done = key in (player.data.get(ZONE_REWARD_LEDGER) or {})
    secret_zones_done = key in (player.data.get(SECRET_ZONE_LEDGER) or {})
    if story_done and sidequests_done and zone_rewards_done and secret_zones_done:
        return None

    story_missions = _story_missions(checkpoint)
    missions = list(story_missions)
    before = deepcopy(player.data)
    dirty_before = player.dirty
    state_dirty_before = State.state_dirty
    try:
        import first_clear
        import mission_gil
        import story_recipes
        from player_state import (_load_ndjson, _main_story_clear_switches, mission_open_switch,
                                  story_beast_for_mission)

        clear_ledger = first_clear.ledger(player)
        first_clear_baseline = set(map(str, clear_ledger.get("baseline") or []))
        first_clear_paid = set(map(str, clear_ledger.get("paid") or []))
        backpaid = bool(clear_ledger.get("backpaid"))
        cleared_before = set(map(str, player.data.get("progress", {}).get("cleared_missions") or []))

        story_switches = set()
        for mission in story_missions:
            for switch in str(mission_open_switch(mission) or "").split(","):
                if switch.strip() and switch.strip() != "0":
                    story_switches.add(switch.strip())
            story_switches.update(_main_story_clear_switches(mission))
            if not story_done:
                player.clear_mission(mission)
        story_switches = _grant_story_map_switches(player, story_switches, story_missions)
        secret_zone_switches = {switch for _dungeon, switch, _parent in SECRET_DUNGEON_GATES
                    if switch in story_switches}

        sidequest_summary = {}
        side_missions = []
        side_switches = set(story_switches)
        town_quest_count = quest_step_count = quest_reward_rows = 0
        while True:
            town_summary = _complete_town_quests(player, side_switches)
            if not sidequests_done:
                town_quest_count += town_summary["town_quests"]
                quest_step_count += town_summary["quest_steps"]
                quest_reward_rows += town_summary["quest_reward_rows"]
            side_switches.update(town_summary["switches"])
            side_switches = _grant_story_map_switches(player, side_switches, story_missions)
            secret_zone_switches.update(switch for _dungeon, switch, _parent in SECRET_DUNGEON_GATES
                                        if switch in side_switches)

            new_missions = [mission for mission in
                            _sidequest_missions(checkpoint, story_missions, side_switches)
                            if mission not in side_missions]
            if not new_missions:
                break
            for mission in new_missions:
                if not sidequests_done:
                    player.clear_mission(mission)
                for switch in str(mission_open_switch(mission) or "").split(","):
                    if switch.strip() and switch.strip() != "0":
                        side_switches.add(switch.strip())
            side_switches = _grant_story_map_switches(player, side_switches, story_missions)
            secret_zone_switches.update(switch for _dungeon, switch, _parent in SECRET_DUNGEON_GATES
                                        if switch in side_switches)
            side_missions.extend(new_missions)

        missions.extend(side_missions)
        if not sidequests_done:
            sidequest_summary = {"missions": len(side_missions), "town_quests": town_quest_count,
                                 "quest_steps": quest_step_count, "quest_reward_rows": quest_reward_rows}

        challenge_lapis = 0
        import ffbe_battle
        challenge_table = ffbe_battle.challenge_table()
        for mission in missions:
            for challenge, (amount, _condition, _order) in challenge_table.get(mission, {}).items():
                if amount and ffbe_battle.LAPIS_AWARD:
                    if player.credit_challenge(mission, challenge):
                        challenge_lapis += amount
                else:
                    player.mark_challenge_cleared(mission, challenge)
        if challenge_lapis:
            from lapis_economy import earned
            player.add_currency("lapis_free", earned(challenge_lapis))

        first_clear_rows = 0
        if first_clear.enabled():
            for mission in missions:
                if mission in first_clear_paid or (backpaid and mission in first_clear_baseline):
                    continue
                if not first_clear.raw(mission):
                    continue
                granted, _skipped = first_clear.grant(player, first_clear.rewards(mission))
                clear_ledger["paid"].append(mission)
                first_clear_paid.add(mission)
                first_clear_rows += len(granted)
                story_recipes.note_paid(player, mission)

        gil = 0
        if mission_gil.enabled():
            gil = sum(mission_gil.amount(mission) for mission in missions
                      if mission not in cleared_before)
            if gil:
                player.add_currency("gil", gil)

        esper_ids = set()
        for mission in missions:
            esper = story_beast_for_mission(mission)
            if esper is not None:
                esper_ids.add(str(esper))
        granted_espers = 0
        for esper in sorted(esper_ids, key=int):
            if not player.owns_beast(esper):
                player.grant_beast(esper, rarity=1, level=1)
                granted_espers += 1

        chest_count = _settle_field_treasures(player, missions, side_switches)

        summary = {"missions": len(missions), "first_clear_rows": first_clear_rows,
                   "challenge_lapis": challenge_lapis, "gil": gil, "chests": chest_count,
                   "espers": granted_espers}
        if not story_done:
            player.data.setdefault(LEDGER, {})[key] = summary
        if not sidequests_done:
            player.data.setdefault(SIDEQUEST_LEDGER, {})[key] = sidequest_summary
        if not zone_rewards_done:
            player.data.setdefault(ZONE_REWARD_LEDGER, {})[key] = {"chests": chest_count}
        if not secret_zones_done:
            player.data.setdefault(SECRET_ZONE_LEDGER, {})[key] = sorted(secret_zone_switches)
        player.dirty = True
        State.state_dirty = True
    except Exception:
        player.data, player.dirty = before, dirty_before
        State.state_dirty = state_dirty_before
        raise

    print(f"checkpoint catch-up: {key}: {summary['missions']} story/side missions, "
          f"{summary['first_clear_rows']} first-clear reward row(s), {summary['challenge_lapis']} challenge lapis, "
          f"{summary['chests']} chest(s), {summary['espers']} esper(s), {summary['gil']} gil", flush=True)
    return summary


def apply_completed(player):
    """Apply any completed Trial checkpoint catch-ups that are not in this save's ledger yet."""
    if player is None or player.mode == "frozen":
        return
    from trial_progression import CHECKPOINTS, _cleared_missions

    cleared = _cleared_missions(player)
    completed = set((player.data.get(LEDGER) or {}).keys())
    sidequests = set((player.data.get(SIDEQUEST_LEDGER) or {}).keys())
    zone_rewards = set((player.data.get(ZONE_REWARD_LEDGER) or {}).keys())
    secret_zones = set((player.data.get(SECRET_ZONE_LEDGER) or {}).keys())
    for checkpoint, group in CHECKPOINTS:
        key = checkpoint.isoformat()
        if (key in completed and key in sidequests and key in zone_rewards and key in secret_zones) \
            or not set(group).issubset(cleared):
            continue
        try:
            apply(player, checkpoint)
        except Exception as exc:
            print(f"checkpoint catch-up: {key} failed ({exc!r}); will retry next mission clear", flush=True)
            return
        completed.add(key)
        sidequests.add(key)
        zone_rewards.add(key)
        secret_zones.add(key)