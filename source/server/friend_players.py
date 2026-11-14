"""Optional synthetic Arena opponents. Not used by the Friend list or helper system.

When explicitly enabled, this module adds a crowd to Arena rival lists:

    * EXVIUS_PLAYERS (default 0) optional accounts with gaming/anime handles, ids 910000001 and up, a Rank each;
  * each one lends a different unit every week (Sunday rollover, same week as the summon rotation). With
    the historical replay on, only units already released by then are lent (replay.released_by);

Real registered players are used for friendship and support units.
"""
from __future__ import annotations

import os
import random
import time

ID_BASE = 910000000

_PARTS_A = [
    "Moogle", "Chocobo", "Cactuar", "Tonberry", "Kupo", "Mako", "Lapis", "Limit", "Esper", "Mithril",
    "Phoenix", "Crystal", "Ultima", "Omega", "Zodiac", "Behemoth", "Malboro", "Bomb", "Ahriman", "Coeurl",
    "Senpai", "Kaiju", "Shonen", "Sakura", "Kitsune", "Ronin", "Shinobi", "Mecha", "Neko", "Oni",
    "Tsundere", "Isekai", "Ramen", "Bento", "Mochi", "Tanuki", "Kawaii", "Sensei", "Chibi", "Yokai",
    "Pixel", "Turbo", "Combo", "Critical", "Rare", "Rainbow", "Gacha", "Speedrun", "Respawn", "Loot",
]
_PARTS_B = [
    "Main", "Slayer", "Knight", "Sage", "Blade", "Hunter", "Dreamer", "Kun", "Chan", "Sama",
    "Prime", "Zero", "Rising", "Breaker", "Lord", "Rider", "Mage", "Ninja", "Bard", "Tamer",
    "Whale", "Fan", "Pilot", "Smith", "Fist", "Storm", "Fang", "Heart", "Soul", "Star",
]
_HANDLES = [
    "LimitBreakLu", "ChainItAll", "PullForNoctis", "XxDarkFinaxX", "RainbowRain", "TrustMeBro",
    "NoLapisNoLife", "SummonAddict", "KupoKupoKupo", "MogKingFan", "OnlyChains", "DualcastDan",
    "GilSnapper", "BraveShifter", "TMRhunter", "VortexVet", "ArenaAce", "ExpeditionEd",
    "OneMorePull", "SaltyRNG", "PityTimer", "GuaranteedGG", "WhaleWatcher", "F2Pforever",
    "MasterTrust", "SevenStarSam", "SoulCrystal", "MegacrystalM", "AwakenedAmy", "PrismPrince",
    "CrystalChaser", "ElementalEli", "KillerChains", "MultiCaster", "TankNTaunt", "CoverGod",
    "StopKillers", "BreakerBob", "AilmentAndy", "EvokerEve", "BlueMageBo", "BardicBella",
    "SamuraiSoul", "DragoonDash", "JumpingJin", "NinjaNoodle", "MonkMode", "PaladinPam",
    "DarkKnightDK", "SpellbladeSi", "ChemistKai", "ThiefTaro", "TimeMageTia", "GeomancerGo",
    "OtakuOracle", "ShonenJump", "MechaPilot", "IsekaiIvy", "KawaiiKaiju", "SenpaiNotice",
    "RamenRonin", "NekoNinja", "ChibiChamp", "AnimeAlex", "MangaMax", "CosplayCam",
    "PixelPaladin", "RetroRyu", "SpeedrunSol", "ComboCarl", "FrameDataFi", "HitboxHana",
]


def enabled() -> bool:
    return _count() > 0


def _count() -> int:
    try:
        return max(0, min(999, int(os.environ.get("EXVIUS_PLAYERS", "0"))))
    except ValueError:
        return 0


def names(count: int | None = None) -> list[str]:
    """`count` unique handles of at most 12 characters, the same every time."""
    count = _count() if count is None else count
    out, seen = [], set()
    for name in _HANDLES:
        if len(name) <= 12 and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    rng = random.Random("exvius-players")
    combos = [a + b for a in _PARTS_A for b in _PARTS_B if len(a + b) <= 12]
    rng.shuffle(combos)
    for name in combos:
        if len(out) >= count:
            break
        if rng.random() < 0.25:
            name += str(rng.randint(1, 99))
            if len(name) > 12:
                continue
        if name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    order = list(range(len(out)))
    random.Random("exvius-players-order").shuffle(order)
    return [out[i] for i in order][:count]


def _week() -> int:
    try:
        import gacha_rotation
        return gacha_rotation.week()[0]
    except Exception:  # noqa: BLE001 -- ISO week as a fallback
        return int(time.strftime("%G%V"))


def _unit_pool(rank: int) -> list[tuple[str, int]]:
    """(unit id, level) choices for a player of this rank: base forms with an English name, released by
    this week's point in history when the replay is on."""
    from player_state import named_unit_ids, unit_roots_by_rarity
    cutoff = None
    try:
        import replay
        cutoff = replay.pool_cutoff()
    except Exception:  # noqa: BLE001
        cutoff = None
    named = named_unit_ids()
    roots = unit_roots_by_rarity()
    levels = {"4": 60, "5": 80, "7": 99}
    rarities = ["5", "7"] if rank >= 100 else ["4", "5"] if rank < 40 else ["4", "5", "7"]
    out = []
    for rarity in rarities:
        for uid in roots.get(rarity, []):
            if uid.startswith("9") or (named and uid not in named):
                continue
            if cutoff is not None:
                import replay
                if not replay.released_by(uid, cutoff):
                    continue
            out.append((uid, levels[rarity]))
    return out


_POOLS: dict = {}


_PLAYERS: dict = {}


def player(index: int) -> dict:
    """Player `index` (1-based) as an Arena-only entry, with this week's unit. Cached per week."""
    week = _week()
    key = (index, week)
    if key not in _PLAYERS:
        if len(_PLAYERS) > 4 * _count():
            _PLAYERS.clear()
        _PLAYERS[key] = _player(index, week)
    return _PLAYERS[key]


def _player(index: int, week: int) -> dict:
    from ffbe_friends import _entry
    rng = random.Random(f"exvius-player-{index}")
    rank = rng.choice([rng.randint(8, 40), rng.randint(40, 120), rng.randint(120, 250), rng.randint(60, 180)])
    pool_key = (week, min(rank // 40, 3))
    if pool_key not in _POOLS:
        _POOLS.clear() if len(_POOLS) > 8 else None
        _POOLS[pool_key] = _unit_pool(rank)
    pool = _POOLS[pool_key] or [("100000102", 1)]
    uid, level = random.Random(f"exvius-player-{index}-week-{week}").choice(pool)
    raw = {"display_name": names()[index - 1], "friend_id": ID_BASE + index, "rank": rank, "emblem_id": 0,
           "unit": {"master_id": uid, "level": level}}
    try:
        return _entry(index, raw)
    except ValueError:
        raw["unit"]["level"] = 1  # a form whose cap is lower than the rarity's usual one
        return _entry(index, raw)


def by_id(friend_id) -> dict | None:
    try:
        index = int(friend_id) - ID_BASE
    except (TypeError, ValueError):
        return None
    if 1 <= index <= _count():
        return player(index)
    return None
