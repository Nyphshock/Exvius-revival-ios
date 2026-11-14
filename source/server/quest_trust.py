"""Fixed trust gain for the player's party on every cleared battle.

Each party unit gains 5% (50 points; 1000 = 100%) per clear. The helper unit does not gain trust, and
`PlayerState.gain_trust` enforces each unit's cap and grants its Trust Master reward once.

EXVIUS_QUEST_TRUST (default 1) can disable quest trust. This runs from
`ffbe_battle._credit_mission_rewards`; before/after values go out in `Qic38SuC` for the result screen.
"""
from __future__ import annotations

import os

TRUST_PER_CLEAR = 50


def enabled() -> bool:
    return os.environ.get('EXVIUS_QUEST_TRUST', '1').strip() not in ('0', 'false', 'off', '')


def roll(player, instance_ids) -> dict:
    """Credit fixed 5% trust to every eligible party unit; return before/after values and rewards."""
    out = {'_rewards': []}
    if player is None or not enabled():
        return out
    for iid in instance_ids:
        unit = player.roster_row(iid)
        if unit is None:
            continue
        current = (list(unit.get('affinity_points') or ['']) + [''])[0]
        current = int(current) if str(current).isdigit() else 0
        out[str(iid)] = (current, current)
        result = player.gain_trust(iid, TRUST_PER_CLEAR)
        if result:
            before, after, rewards = result
            out[str(iid)] = (before, after)
            out['_rewards'] += rewards
    return out
