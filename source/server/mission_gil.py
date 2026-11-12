"""Pay the Gil listed as a mission's clear reward, which the phone does not award itself."""
from __future__ import annotations

import os

LEDGER = "exvius_mission_gil"


def enabled() -> bool:
    return os.environ.get("EXVIUS_MISSION_GIL", "1").strip().lower() not in ("0", "off", "false", "no")


def amount(mid) -> int:
    from player_state import _load_ndjson
    row = _load_ndjson("F_MISSION_MST.ndjson", "qo3PECw6").get(str(mid)) or {}
    value = row.get("7UR4J2SE")
    if value in (None, ""):
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        print(f"mission-gil: mission {mid} has invalid clear Gil {value!r}; not paid", flush=True)
        return 0


def pay(spec, mid, plaintext):
    from ffbe_config import RESULT_TAG
    from ffbe_state import State
    player = State.player
    if (not enabled() or player is None or player.mode == "frozen" or not mid or not isinstance(spec, dict)
            or RESULT_TAG not in spec):
        return spec
    gil = amount(mid)
    if gil <= 0:
        return spec
    from first_clear import _succeeded
    attempt = player.data.get("exvius_repeat", {}).get("attempt", {})
    if attempt.get("mid") != str(mid):
        attempt = {}
    mark = [str(mid), attempt.get("sequence")]
    ledger = player.data.get(LEDGER) or {}
    if ledger.get("last") == mark or not _succeeded(player, str(mid), plaintext):
        return spec
    before = int(player.currencies.get("gil", 0))
    if player.add_currency("gil", gil) == before:
        print(f"mission-gil: mission {mid} clear Gil could not be credited", flush=True)
        return spec
    player.data[LEDGER] = dict(ledger, last=mark)
    player.dirty = True
    State.state_dirty = True
    print(f"mission-gil: mission {mid} paid {gil} clear gil", flush=True)
    import copy
    spec = copy.deepcopy(spec)
    for result in spec.get(RESULT_TAG, []):
        if isinstance(result, dict):
            shown = str(result.get("16LQuC5r") or "0")
            result["16LQuC5r"] = str((int(shown) if shown.isdigit() else 0) + gil)
    return spec
