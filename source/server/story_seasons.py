"""Calendar eras and story checkpoints used by the Vortex and summon archives."""
from datetime import date, datetime


SEASON_IDS = ('season1', 'season2', 'season3', 'season4', 'season5')
SEASON_LABELS = {
    'season1': 'Season 1',
    'season2': 'Season 2',
    'season3': 'Season 3',
    'season4': 'Season 4',
    'season5': 'Season 5',
}

# Each season starts on the day after the preceding season ends.
SEASON_STARTS = {
    'season1': date.min,
    'season2': date(2017, 3, 1),
    'season3': date(2019, 5, 30),
    'season4': date(2021, 5, 10),
    'season5': date(2024, 12, 27),
}

# The mission IDs are the opening story missions in the shipped mission index.
CHECKPOINT_MISSIONS = {
    'season1': ('1110100', '1110101'),
    'season2': ('2000101',),
    'season3': ('3010101',),
    'season4': ('4010101',),
    'season5': ('5000101',),
}


def season_for_date(value):
    """Return the date-based season, or None when the date cannot be read."""
    if isinstance(value, datetime):
        release = value.date()
    elif isinstance(value, date):
        release = value
    else:
        text = str(value or '').strip()
        if len(text) == 4:
            text += '-01-01'
        if len(text) == 7:
            text += '-01'
        try:
            release = date.fromisoformat(text[:10])
        except ValueError:
            return None

    for season in reversed(SEASON_IDS):
        if release >= SEASON_STARTS[season]:
            return season
    return None


def season_unlocked(player, season):
    """Whether a player's completed story missions reach this season's checkpoint."""
    if season not in SEASON_IDS or player is None:
        return True
    unlocked = unlocked_seasons(player)
    return season in unlocked


def unlocked_seasons(player):
    """Unlock all earlier seasons cumulatively when a later opening mission is cleared."""
    if player is None:
        return frozenset(SEASON_IDS)
    data = getattr(player, 'data', None) or {}
    progress = data.get('progress') or {}
    cleared = {str(mission) for mission in progress.get('cleared_missions') or []}
    reached = [index for index, season in enumerate(SEASON_IDS)
               if cleared.intersection(CHECKPOINT_MISSIONS[season])]
    if not reached:
        return frozenset()
    return frozenset(SEASON_IDS[:max(reached) + 1])
