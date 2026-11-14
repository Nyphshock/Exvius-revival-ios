"""Per-profile historical trial checkpoints for dated content."""
from datetime import date


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
FINAL_CONTENT_DATE = date(2024, 10, 30)


def _cleared_missions(player) -> set[str]:
    data = getattr(player, 'data', None) or {}
    progress = data.get('progress') or {}
    return {str(mission) for mission in progress.get('cleared_missions') or []}


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