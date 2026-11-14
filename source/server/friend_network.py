"""Shared real-player friendship state for profiles on this server."""
from __future__ import annotations

import json
import os
import threading

import data_paths
import ffbe_state as st

NETWORK_FILE = os.environ.get("FRIEND_NETWORK_FILE") or os.path.join(data_paths.STATE_DIR, "friend_network.json")
CAPACITY = 100
_LOCK = threading.RLock()


def _player_id(value):
    text = str(value or "")
    return text if text.isascii() and text.isdigit() and int(text) > 0 else ""


def current_id():
    if st.State.player is None:
        return ""
    return _player_id((st.State.player.data.get("identity") or {}).get("user_id"))


def player_ids():
    manager = getattr(st, "PROFILE_MANAGER", None)
    if manager is not None:
        return [_player_id(player_id) for player_id in manager.player_ids() if _player_id(player_id)]
    own = current_id()
    return [own] if own else []


def player_for(player_id):
    player_id = _player_id(player_id)
    if not player_id or player_id not in player_ids():
        return None
    if player_id == current_id():
        return st.State.player
    manager = getattr(st, "PROFILE_MANAGER", None)
    return manager.player_for(player_id) if manager is not None else None


def friend_profile(player_id):
    """Public friend card using the first unit in the player's active party as its helper."""
    player_id = _player_id(player_id)
    player = player_for(player_id)
    if player is None:
        return None
    identity = player.data.get("identity") or {}
    party_ids = player.party_instance_ids()
    helper_id = str((player.data.get("exvius_friends") or {}).get("helper_instance_id") or
                    (party_ids[0] if party_ids else ""))
    if helper_id not in party_ids:
        helper_id = party_ids[0] if party_ids else ""
    unit = player.roster_row(helper_id) if helper_id else None
    if unit is None:
        return None
    equipment = unit.get("equipment") or {}
    if isinstance(equipment, dict):
        equipment = [str(equipment.get(str(slot), equipment.get(slot, "0"))) for slot in range(1, 7)]
    from ffbe_friends import _entry
    try:
        return _entry(0, {
            "display_name": identity.get("handle_name") or f"Player {player_id}",
            "friend_id": player_id,
            "rank": (player.data.get("rank") or {}).get("level", 1),
            "emblem_id": (player.data.get("profile") or {}).get("player_emblem_id", 0),
            "unit_instance_id": helper_id,
            "unit": {
                "master_id": unit.get("master_id"),
                "level": unit.get("level", 1),
                "lb_level": unit.get("lb_level", 0),
                "lb_exp": unit.get("lb_exp", 0),
                "vision_card": unit.get("vision_card", ""),
                "abilities": unit.get("abilities") or [],
                "equipment": equipment,
            },
        })
    except (TypeError, ValueError) as exc:
        print(f"[friends] player {player_id} helper unavailable ({exc})", flush=True)
        return None


def _pair_key(first, second):
    return ":".join(sorted((str(first), str(second)), key=int))


def _read_store():
    try:
        with open(NETWORK_FILE, encoding="utf-8") as source:
            state = json.load(source)
    except FileNotFoundError:
        return {"version": 1, "relations": {}}
    if not isinstance(state, dict) or state.get("version") != 1 or not isinstance(state.get("relations"), dict):
        raise ValueError(f"invalid friend network store: {NETWORK_FILE}")
    return state


def _write_store(state):
    os.makedirs(os.path.dirname(NETWORK_FILE) or ".", exist_ok=True)
    temporary = NETWORK_FILE + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as destination:
            json.dump(state, destination, indent=2)
            destination.write("\n")
        os.replace(temporary, NETWORK_FILE)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def relation_type(owner, target, state=None):
    owner, target = _player_id(owner), _player_id(target)
    if not owner or not target or owner == target:
        return 0
    with _LOCK:
        relations = (state or _read_store())["relations"]
        relation = relations.get(_pair_key(owner, target))
        if not relation:
            return 0
        if relation.get("status") == "accepted":
            return 1
        if relation.get("status") == "pending":
            return 2 if relation.get("requester") == owner else 3
        return 0


def friend_ids(owner, relation=None, _state=None):
    owner = _player_id(owner)
    if not owner:
        return []
    with _LOCK:
        state = _state or _read_store()
    ids = []
    for target in player_ids():
        category = relation_type(owner, target, state)
        if target != owner and (relation is None or category == relation):
            ids.append(target)
    return ids


def _accepted_count(state, owner):
    return len(friend_ids(owner, relation=1, _state=state))


def send_request(owner, target):
    owner, target = _player_id(owner), _player_id(target)
    if not owner or not target or owner == target or target not in player_ids():
        return False
    with _LOCK:
        state = _read_store()
        key = _pair_key(owner, target)
        relation = state["relations"].get(key)
        if relation:
            if relation.get("status") != "pending" or relation.get("requester") == owner:
                return False
            if (_accepted_count(state, owner) >= CAPACITY
                    or _accepted_count(state, relation.get("requester")) >= CAPACITY):
                return False
            relation.update(status="accepted", requester="")
        else:
            if _accepted_count(state, owner) >= CAPACITY:
                return False
            state["relations"][key] = {"status": "pending", "requester": owner}
        _write_store(state)
    return True


def accept_request(owner, target):
    owner, target = _player_id(owner), _player_id(target)
    if not owner or not target or owner == target:
        return False
    with _LOCK:
        state = _read_store()
        key = _pair_key(owner, target)
        relation = state["relations"].get(key)
        if not relation or relation.get("status") != "pending" or relation.get("requester") == owner:
            return False
        requester = relation.get("requester")
        if (_accepted_count(state, owner) >= CAPACITY
            or _accepted_count(state, requester) >= CAPACITY):
            return False
        relation.update(status="accepted", requester="")
        _write_store(state)
    return True


def remove_friend(owner, target):
    owner, target = _player_id(owner), _player_id(target)
    if not owner or not target or owner == target:
        return False
    with _LOCK:
        state = _read_store()
        key = _pair_key(owner, target)
        relation = state["relations"].get(key)
        if not relation or relation.get("status") != "accepted":
            return False
        del state["relations"][key]
        _write_store(state)
    return True


def refuse_request(owner, target):
    owner, target = _player_id(owner), _player_id(target)
    if not owner or not target or owner == target:
        return False
    with _LOCK:
        state = _read_store()
        key = _pair_key(owner, target)
        relation = state["relations"].get(key)
        if not relation or relation.get("status") != "pending" or relation.get("requester") == owner:
            return False
        del state["relations"][key]
        _write_store(state)
    return True