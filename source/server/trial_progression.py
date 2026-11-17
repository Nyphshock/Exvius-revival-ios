"""Per-profile historical trial checkpoints for dated content."""
import json
from datetime import date
from functools import lru_cache
from pathlib import Path


CHECKPOINTS = (
    (date(2016, 8, 25), frozenset(('8991101',))),
    (date(2016, 11, 24), frozenset(('8991103',))),
    (date(2017, 3, 9), frozenset(('8991106',))),
    (date(2017, 4, 12), frozenset(('8991107',))),
    (date(2017, 6, 8), frozenset(('8993803',))),
    (date(2017, 7, 20), frozenset(('8993903',))),
    (date(2017, 8, 17), frozenset(('9001603',))),
    (date(2017, 9, 29), frozenset(('8980102',))),
    (date(2017, 11, 22), frozenset(('8994003',))),
    (date(2017, 12, 21), frozenset(('8995003',))),
    (date(2018, 1, 25), frozenset(('8980104',))),
    (date(2018, 5, 17), frozenset(('8980106',))),
    (date(2018, 6, 14), frozenset(('8980108',))),
    (date(2018, 6, 21), frozenset(('8993103',))),
    (date(2018, 7, 12), frozenset(('8980110', '9003501'))),
    (date(2018, 7, 19), frozenset(('8993201', '8995303'))),
    (date(2018, 8, 23), frozenset(('8993203',))),
    (date(2018, 8, 30), frozenset(('8980112',))),
    (date(2018, 9, 13), frozenset(('8995503', '8993302'))),
    (date(2018, 9, 27), frozenset(('8980114',))),
    (date(2018, 10, 4), frozenset(('8995603',))),
    (date(2018, 10, 18), frozenset(('8980116',))),
    (date(2018, 11, 22), frozenset(('8980118',))),
    (date(2018, 12, 20), frozenset(('8980120',))),
    (date(2019, 3, 21), frozenset(('8980200', '8993501'))),
    (date(2019, 4, 11), frozenset(('8993601',))),
    (date(2019, 5, 30), frozenset(('8993701',))),
    (date(2019, 6, 27), frozenset(('8995801',))),
    (date(2019, 9, 12), frozenset(('8974001', '9630203'))),
    (date(2020, 2, 20), frozenset(('8996001',))),
    (date(2020, 3, 5), frozenset(('8997001',))),
    (date(2021, 10, 28), frozenset(('8998602',))),
    (date(2022, 1, 13), frozenset(('8998702',))),
    (date(2022, 8, 18), frozenset(('95080105',))),
    (date(2023, 5, 4), frozenset(('90010101',))),
    (date(2023, 7, 13), frozenset(('90010201',))),
    (date(2024, 8, 22), frozenset(('9630703',))),
)
CHECKPOINT_LAPIS_BONUS = 50000
FINAL_CONTENT_DATE = date(2024, 10, 30)

# Last main-story mission available while the Trial checkpoint at each date is pending.
# A blank mission name means the latest main-story mission in that zone/dungeon.
STORY_LIMITS = (
    (date(2016, 8, 25), "Dwarves' Forge", "Morphing Flames"),
    (date(2016, 11, 24), "Water Shrine", "Will of the Ferocious"),
    (date(2017, 3, 9), "Invincible Interior", "Center"),
    (date(2017, 4, 12), "Magic Library", "Showdown of Destiny"),
    (date(2017, 6, 8), "Gronoa Shrine Entrance", "A Power of Old"),
    (date(2017, 7, 20), "Forgotten Walls", "Everlasting Darkness"),
    (date(2017, 8, 17), "Forgotten Walls", "Everlasting Darkness"),
    (date(2017, 9, 29), "The Abyss", "Chaotic Darkness"),
    (date(2017, 11, 22), "Rail Bridge", "Hidden Exit"),
    (date(2017, 12, 21), "Aldore Tower Zenith", "Hyoh of the Delta Star"),
    (date(2018, 1, 25), "Aldore Tower Zenith", "Hyoh of the Delta Star"),
    (date(2018, 4, 19), "Energy Transfer Station", "Beast Sealed Away"),
    (date(2018, 6, 14), "Hideaway Lanzatto", "Zolulu and Delulu"),
    (date(2018, 6, 21), "Hideaway Lanzatto", "Zolulu and Delulu"),
    (date(2018, 7, 12), "Hideaway Lanzatto", "Zolulu and Delulu"),
    (date(2018, 7, 19), "Hideaway Lanzatto", "Zolulu and Delulu"),
    (date(2018, 8, 23), "Camp Danacos", "Yego of the Gamma Star"),
    (date(2018, 8, 30), "Rock Pile Hill", "Reunion with Darkness"),
    (date(2018, 9, 13), "Rock Pile Hill", "Reunion with Darkness"),
    (date(2018, 9, 27), "Londell Road", "The Promise"),
    (date(2018, 10, 4), "Londell Road", "The Promise"),
    (date(2018, 10, 18), "Londell Road", "The Promise"),
    (date(2018, 11, 22), "Land of Fading Memories", "Soul Awakened"),
    (date(2018, 12, 20), "Main Colosseum", ""),
    (date(2019, 1, 24), "Magistellus Military Facility", ""),
    (date(2019, 3, 21), "Emperor's Hall", ""),
    (date(2019, 4, 11), "Ancient Glacier", "Separate Ways"),
    (date(2019, 5, 30), "Stargazer's Point", "Battle for the Future"),
    (date(2019, 9, 12), "Grandore Main Block", "Emperor Vlad"),
    (date(2020, 2, 20), "Various Tomorrows", "Vast Skies of Tomorrow"),
    (date(2020, 3, 5), "Verdant Waterfall", "Nearing the Wormhole"),
    (date(2021, 10, 28), "Lapis (Chapter 10)", "Season 3 Finale (The Maidens' Return)"),
    (date(2022, 1, 13), "The Man-Eating Fortress Ruins", "The Wygars"),
    (date(2022, 8, 18), "To Live as a Hero", "A True Hero"),
    (date(2023, 5, 4), "Legend's End", "Sacrifice"),
    (date(2023, 7, 13), "Rovina Ruins", "A Place of Intertwined Fates"),
    (date(2024, 8, 22), "Ultimo stage", ""),
)

CHECKPOINT_MISSION_RESTRICTIONS = {
    date(2016, 8, 25): frozenset(("2110394",)),  # Chamber of Awakening - 5★ Units
}


def _normalise_name(value):
    return " ".join(str(value or "").replace("’", "'").casefold().split())


@lru_cache(maxsize=None)
def _localized_names(table):
    try:
        import data_paths
        path = Path(data_paths.TEXT_DIR) / (table + ".ndjson")
        names = {}
        with path.open(encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                if row.get("key") and row.get("v") and row["v"][0]:
                    names.setdefault(_normalise_name(row["v"][0]), set()).add(
                        row["key"].rsplit("_", 1)[-1])
        return {name: frozenset(ids) for name, ids in names.items()}
    except (OSError, ValueError, ImportError):
        return {}


def _name_aliases(value):
    name = _normalise_name(value)
    aliases = {name}
    if " - " in name:
        aliases.add(name.rsplit(" - ", 1)[-1])
    if "(" in name and name.endswith(")"):
        opening = name.rfind("(")
        aliases.add(name[opening + 1:-1].strip())
        aliases.add(name[:opening].strip())
    return aliases


@lru_cache(maxsize=1)
def _story_order_and_context():
    """Return sorted main-story mission ids and their localized zone/dungeon names."""
    try:
        from player_state import _load_ndjson, is_main_story_mission
        missions = _load_ndjson("F_MISSION_MST.ndjson", "qo3PECw6")
        dungeons = _load_ndjson("F_DUNGEON_MST.ndjson", "U9iHsau3")
        mission_ids = sorted((str(mid) for mid in missions if str(mid).isdigit()
                              and is_main_story_mission(mid)), key=int)
    except (OSError, ValueError, KeyError):
        return (), {}
    area_names = _localized_names("F_TEXT_AREA_NAME")
    dungeon_names = _localized_names("F_TEXT_DUNGEON_NAME")
    areas_by_id = {area_id: name for name, ids in area_names.items() for area_id in ids}
    dungeons_by_id = {dungeon_id: name for name, ids in dungeon_names.items() for dungeon_id in ids}
    context = {}
    for mid in mission_ids:
        mission = missions[mid]
        dungeon_id = str(mission.get("U9iHsau3") or "")
        dungeon = dungeons.get(dungeon_id) or {}
        area_id = str(dungeon.get("uv60hgDW") or "")
        context[mid] = {
            "dungeon": dungeon_id,
            "area": area_id,
            "names": {dungeons_by_id.get(dungeon_id, ""), areas_by_id.get(area_id, "")} - {""},
        }
    return tuple(mission_ids), context


def _resolve_story_limit(zone, mission_name):
    order, context = _story_order_and_context()
    if not order:
        return None
    mission_names = _localized_names("F_TEXT_MISSION")
    zone_aliases = _name_aliases(zone)
    area_names = _localized_names("F_TEXT_AREA_NAME")
    dungeon_names = _localized_names("F_TEXT_DUNGEON_NAME")
    zone_areas = set().union(*(area_names.get(alias, ()) for alias in zone_aliases))
    zone_dungeons = set().union(*(dungeon_names.get(alias, ()) for alias in zone_aliases))
    mission_aliases = _name_aliases(mission_name) - {""}
    if mission_name:
        mission_aliases |= _name_aliases(zone + " - " + mission_name) - {""}
    if mission_aliases:
        matching = set().union(*(mission_names.get(alias, ()) for alias in mission_aliases))
        matching = {mid for mid in matching if mid in context}
        in_zone = {mid for mid in matching if context[mid]["dungeon"] in zone_dungeons
                   or context[mid]["area"] in zone_areas
                   or bool(context[mid]["names"] & zone_aliases)}
        candidates = in_zone if zone_areas or zone_dungeons else matching if len(matching) == 1 else set()
    else:
        candidates = {mid for mid in order if context[mid]["dungeon"] in zone_dungeons
                      or context[mid]["area"] in zone_areas
                      or bool(context[mid]["names"] & zone_aliases)}
    return max(candidates, key=int) if candidates else None


def story_limit_for_checkpoint(checkpoint_date):
    """Latest supplied story endpoint on or before a Trial checkpoint date."""
    eligible = [(day, zone, mission) for day, zone, mission in STORY_LIMITS if day <= checkpoint_date]
    if not eligible:
        return None
    _day, zone, mission = eligible[-1]
    return _resolve_story_limit(zone, mission)


def story_mission_is_available(player, mission_id):
    """Allow main-story missions only through the endpoint for the player's pending Trial."""
    checkpoint = next_checkpoint_date(player)
    if player is None or checkpoint is None:
        return True
    limit = story_limit_for_checkpoint(checkpoint)
    if limit is None:
        return True
    order, _context = _story_order_and_context()
    return mission_is_within_story_limit(str(mission_id), limit, order)


def checkpoint_mission_is_available(player, mission_id):
    """Whether a non-story mission is allowed at the player's currently pending Trial checkpoint."""
    checkpoint = next_checkpoint_date(player)
    blocked = CHECKPOINT_MISSION_RESTRICTIONS.get(checkpoint, frozenset())
    return str(mission_id) not in blocked


def mission_is_within_story_limit(mission_id, limit_mission, story_order):
    """Whether `mission_id` is no later than the checkpoint's final permitted story mission."""
    if mission_id not in story_order or limit_mission not in story_order:
        return True
    return story_order.index(mission_id) <= story_order.index(limit_mission)


def _cleared_missions(player) -> set[str]:
    data = getattr(player, 'data', None) or {}
    progress = data.get('progress') or {}
    return {str(mission) for mission in progress.get('cleared_missions') or []}


def newly_completed_checkpoints(cleared_before, cleared_after) -> tuple[date, ...]:
    """Checkpoint dates whose complete trial group became cleared in this transition."""
    before = {str(mission) for mission in cleared_before}
    after = {str(mission) for mission in cleared_after}
    return tuple(day for day, missions in CHECKPOINTS
                 if not missions.issubset(before) and missions.issubset(after))


def next_checkpoint_date(player) -> date | None:
    """The first checkpoint date whose maximum-tier trial group is not fully cleared."""
    if player is None:
        return None
    cleared = _cleared_missions(player)
    return next((day for day, missions in CHECKPOINTS if not missions.issubset(cleared)), None)


def active_checkpoint_missions(player) -> frozenset[str]:
    """Mission IDs for the next checkpoint, which remains playable while later content is closed."""
    day = next_checkpoint_date(player)
    return next((missions for checkpoint, missions in CHECKPOINTS if checkpoint == day), frozenset())


def checkpoint_date_for_mission(mission_id) -> date | None:
    mission_id = str(mission_id)
    return next((day for day, missions in CHECKPOINTS if mission_id in missions), None)


def release_is_available(player, release) -> bool:
    """Dated content must predate the next checkpoint; the checkpoint trial is handled separately."""
    limit = next_checkpoint_date(player)
    if player is None or release is None:
        return True
    if isinstance(release, date):
        day = release
    else:
        try:
            day = date.fromisoformat(str(release)[:10])
        except ValueError:
            return True
    if limit is None:
        return day <= FINAL_CONTENT_DATE
    return day < limit