"""Map Tailscale peer addresses to isolated player save files."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import ipaddress
import json
import os
from typing import Iterator

import data_paths
import ffbe_state as st
from ffbe_state import load_state, save_state


class ProfileMapError(RuntimeError):
    """The configured peer-to-profile map is invalid or cannot be loaded."""


class UnregisteredClientError(PermissionError):
    """The peer address is not assigned to a player profile."""


@dataclass
class _ProfileState:
    player: object
    state_dirty: bool
    state_file: str
    state_slot: str


def _player_id(value: object, field: str) -> str:
    if (not isinstance(value, str) or len(value) > 20 or not value.isascii() or not value.isdigit()
            or int(value) <= 0 or str(int(value)) != value):
        raise ProfileMapError(f"{field} must be a positive numeric string")
    return value


def _ip_address(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ProfileMapError(f"{field} must be an IP address")
    try:
        return str(ipaddress.ip_address(value.split("%", 1)[0]))
    except ValueError as exc:
        raise ProfileMapError(f"{field} is not a valid IP address") from exc


def validate_profile_map(raw: object) -> tuple[str, dict[str, str]]:
    if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != 1:
        raise ProfileMapError("profile map must be a version 1 JSON object")
    default_id = _player_id(raw.get("default_player_id"), "default_player_id")
    clients = raw.get("clients")
    if not isinstance(clients, dict):
        raise ProfileMapError("profile map clients must be an object")

    normalized: dict[str, str] = {}
    for peer, player_id in clients.items():
        address = _ip_address(peer, "client address")
        if address in normalized:
            raise ProfileMapError(f"duplicate client address after normalization: {address}")
        normalized[address] = _player_id(player_id, f"clients[{address!r}]")
    return default_id, normalized


class PlayerProfileManager:
    def __init__(self, path: str | None = None, *, auto_create: bool = False):
        self.path = os.path.abspath(path or os.path.join(data_paths.STATE_DIR, "profiles.json"))
        self._required = bool(path)
        self._auto_create = auto_create
        self._mtime_ns: int | None = None
        self._default_id: str | None = None
        self._clients: dict[str, str] = {}
        self._profiles: dict[str, _ProfileState] = {}
        self._enabled = False
        self._reload()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def default_player_id(self) -> str | None:
        return self._default_id

    def _reload(self) -> None:
        try:
            stat = os.stat(self.path)
        except FileNotFoundError as exc:
            if not self._enabled and not self._required:
                if self._auto_create:
                    self._create_default_map()
                    self._reload()
                return
            raise ProfileMapError(f"profile map is unavailable: {self.path}") from exc
        except OSError as exc:
            raise ProfileMapError(f"cannot read profile map {self.path}: {exc}") from exc

        if self._mtime_ns == stat.st_mtime_ns:
            return
        try:
            with open(self.path, encoding="utf-8") as fh:
                default_id, clients = validate_profile_map(json.load(fh))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProfileMapError(f"cannot parse profile map {self.path}: {exc}") from exc

        current_id = str((st.State.player.data.get("identity") or {}).get("user_id", ""))
        if self._default_id is None:
            if current_id != default_id:
                raise ProfileMapError(
                    f"default_player_id {default_id} does not match the loaded save's player ID {current_id!r}")
            self._default_id = default_id
            self._profiles[default_id] = self._snapshot()
        elif default_id != self._default_id:
            raise ProfileMapError("default_player_id cannot change while the server is running")

        self._clients = clients
        self._mtime_ns = stat.st_mtime_ns
        self._enabled = True
        print(f"profiles: {len(clients)} Tailscale address(es) mapped; default player {default_id}", flush=True)

    def _create_default_map(self) -> None:
        default_id = _player_id(
            str((st.State.player.data.get("identity") or {}).get("user_id", "")),
            "loaded save's player ID")
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except OSError as exc:
            raise ProfileMapError(f"cannot create profile map directory for {self.path}: {exc}") from exc
        try:
            fh = open(self.path, "x", encoding="utf-8")
        except FileExistsError:
            return
        except OSError as exc:
            raise ProfileMapError(f"cannot create profile map {self.path}: {exc}") from exc
        try:
            with fh:
                json.dump({"version": 1, "default_player_id": default_id, "clients": {}}, fh, indent=2)
                fh.write("\n")
        except OSError as exc:
            raise ProfileMapError(f"cannot create profile map {self.path}: {exc}") from exc

    @staticmethod
    def _snapshot() -> _ProfileState:
        return _ProfileState(st.State.player, st.State.state_dirty, st.STATE_FILE, st.STATE_SLOT)

    @staticmethod
    def _activate(profile: _ProfileState, player_id: str) -> None:
        st.State.player = profile.player
        st.State.state_dirty = profile.state_dirty
        st.STATE_FILE = profile.state_file
        st.STATE_SLOT = profile.state_slot
        st.PROFILE_ID = player_id

    def _load_profile(self, player_id: str) -> _ProfileState:
        path = os.path.join(data_paths.STATE_DIR, "profiles", f"{player_id}.json")
        existed = os.path.isfile(path)
        previous = self._snapshot()
        previous_runtime_id = st.PROFILE_ID
        persist = st.STATE_PERSIST
        st.State.state_dirty = False
        try:
            st.STATE_FILE = path
            st.STATE_SLOT = player_id
            st.STATE_PERSIST = False
            load_state()
            player = st.State.player
            actual_id = str((player.data.get("identity") or {}).get("user_id", ""))
            if existed and actual_id != player_id:
                raise ProfileMapError(
                    f"save {path} belongs to player {actual_id!r}, not configured player {player_id!r}")
            if not existed:
                player.data.setdefault("identity", {})["user_id"] = player_id
                player.dirty = True
            season = getattr(st, "SEASON", None)
            if season is not None:
                switches = season.switch_sets()
                if switches:
                    player.add_volatile_switches(switches)
            return self._snapshot()
        finally:
            st.STATE_PERSIST = persist
            self._activate(previous, st.PROFILE_ID or self._default_id or "")
            st.PROFILE_ID = previous_runtime_id

    def _next_player_id(self) -> str:
        used = {self._default_id, *self._clients.values()}
        profile_dir = os.path.join(data_paths.STATE_DIR, "profiles")
        try:
            filenames = os.listdir(profile_dir)
        except FileNotFoundError:
            filenames = []
        except OSError as exc:
            raise ProfileMapError(f"cannot inspect profile saves {profile_dir}: {exc}") from exc
        used.update(name[:-5] for name in filenames if name.endswith(".json"))
        candidate = 300000001
        while str(candidate) in used:
            candidate += 1
        if candidate > 300999999:
            raise ProfileMapError("automatic player ID range 300000001-300999999 is exhausted")
        return str(candidate)

    def _save_client_map(self) -> None:
        payload = {
            "version": 1,
            "default_player_id": self._default_id,
            "clients": dict(sorted(self._clients.items())),
        }
        temporary = self.path + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(temporary, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
                fh.write("\n")
            os.replace(temporary, self.path)
            self._mtime_ns = None
        except OSError as exc:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise ProfileMapError(f"cannot save profile map {self.path}: {exc}") from exc

    def _register_client(self, address: str, handle_name: str) -> str:
        if (not isinstance(handle_name, str) or not handle_name.strip() or len(handle_name) > 64
                or not handle_name.isprintable()):
            raise UnregisteredClientError(
                f"CreateUserRequest from {address} did not contain a valid player name")
        
        # Check if this address was already auto-registered
        existing_player_id = self._clients.get(address)
        if existing_player_id:
            # Update the existing profile with the player name
            profile = self._profiles.get(existing_player_id)
            if profile is None:
                profile = self._load_profile(existing_player_id)
            profile.player.data.setdefault("identity", {})["handle_name"] = handle_name.strip()
            profile.player.dirty = True
            self._profiles[existing_player_id] = profile
            print(f"profiles: {address} named their profile {handle_name.strip()!r} (player {existing_player_id})", flush=True)
            return existing_player_id
        
        # New registration (address not in map)
        player_id = self._next_player_id()
        profile = self._load_profile(player_id)
        profile.player.data.setdefault("identity", {})["handle_name"] = handle_name.strip()
        profile.player.dirty = True

        self._clients[address] = player_id
        try:
            self._save_client_map()
        except ProfileMapError:
            del self._clients[address]
            raise
        self._profiles[player_id] = profile
        print(f"profiles: registered {address} as player {player_id} ({handle_name.strip()!r})", flush=True)
        return player_id

    def _auto_register_client(self, address: str) -> str:
        """Auto-register a new device without requiring a name yet. The name will be set when the game sends CreateUserRequest."""
        player_id = self._next_player_id()
        profile = self._load_profile(player_id)

        self._clients[address] = player_id
        try:
            self._save_client_map()
        except ProfileMapError:
            del self._clients[address]
            raise
        self._profiles[player_id] = profile
        print(f"profiles: auto-registered {address} as player {player_id} (awaiting player name)", flush=True)
        return player_id

    @contextmanager
    def activate(self, peer: str, *, registration_name: str | None = None) -> Iterator[str | None]:
        self._reload()
        if not self._enabled:
            yield None
            return

        address = _ip_address(peer, "connected peer")
        if ipaddress.ip_address(address).is_loopback:
            player_id = self._default_id
        else:
            player_id = self._clients.get(address)
        if player_id is None:
            if registration_name is None:
                # Auto-register unknown devices with a new player ID without requiring a name yet
                player_id = self._auto_register_client(address)
            else:
                player_id = self._register_client(address, registration_name)

        previous_id = st.PROFILE_ID or self._default_id
        previous_runtime_id = st.PROFILE_ID
        previous = self._snapshot()
        self._profiles[previous_id] = previous
        if player_id != previous_id:
            profile = self._profiles.get(player_id)
            if profile is None:
                profile = self._load_profile(player_id)
                self._profiles[player_id] = profile
            self._activate(profile, player_id)
        else:
            st.PROFILE_ID = player_id

        try:
            yield player_id
        finally:
            try:
                save_state()
            finally:
                self._profiles[player_id] = self._snapshot()
                if player_id != previous_id:
                    self._activate(previous, previous_id)
                st.PROFILE_ID = previous_runtime_id


__all__ = [
    "PlayerProfileManager",
    "ProfileMapError",
    "UnregisteredClientError",
    "validate_profile_map",
]
