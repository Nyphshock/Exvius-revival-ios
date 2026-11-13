import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import capture_server
import data_paths
import ffbe_state as st
import player_profiles
from player_state import PlayerState


class _Player:
    def __init__(self, player_id):
        self.data = {"identity": {"user_id": player_id}}
        self.dirty = False


class PlayerProfileTests(unittest.TestCase):
    def setUp(self):
        self.original = (st.State.player, st.State.state_dirty, st.STATE_FILE, st.STATE_SLOT,
                         st.STATE_PERSIST, st.PROFILE_ID)
        st.State.player = _Player("100000001")
        st.State.state_dirty = False
        st.STATE_FILE = "default.json"
        st.STATE_SLOT = "default"
        st.STATE_PERSIST = True
        st.PROFILE_ID = None
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state_dir = Path(self.temp.name)
        self.profile_dir_patch = patch.object(data_paths, "STATE_DIR", str(self.state_dir))
        self.profile_dir_patch.start()
        self.addCleanup(self.profile_dir_patch.stop)

    def tearDown(self):
        (st.State.player, st.State.state_dirty, st.STATE_FILE, st.STATE_SLOT,
         st.STATE_PERSIST, st.PROFILE_ID) = self.original

    def _manager(self):
        path = self.state_dir / "profiles.json"
        path.write_text(json.dumps({
            "version": 1,
            "default_player_id": "100000001",
            "clients": {
                "100.64.0.1": "100000001",
                "100.64.0.2": "100000002",
            },
        }), encoding="utf-8")
        return player_profiles.PlayerProfileManager(str(path))

    def test_profile_map_validates_and_normalizes_addresses(self):
        default_id, clients = player_profiles.validate_profile_map({
            "version": 1,
            "default_player_id": "100000001",
            "clients": {"100.64.0.2": "100000002", "fd7a:115c:a1e0::1": "100000003"},
        })
        self.assertEqual(default_id, "100000001")
        self.assertEqual(clients["fd7a:115c:a1e0::1"], "100000003")

    def test_profile_map_rejects_duplicate_normalized_addresses(self):
        with self.assertRaises(player_profiles.ProfileMapError):
            player_profiles.validate_profile_map({
                "version": 1,
                "default_player_id": "100000001",
                "clients": {
                    "fd7a:115c:a1e0::1": "100000001",
                    "fd7a:115c:a1e0:0:0:0:0:1": "100000002",
                },
            })

    def test_profiles_are_loaded_separately_and_restored_after_request(self):
        manager = self._manager()
        loaded = []

        def fake_load_state():
            player_id = st.STATE_SLOT
            st.State.player = _Player(player_id)
            st.State.state_dirty = False
            loaded.append(player_id)

        with patch.object(player_profiles, "load_state", side_effect=fake_load_state), \
                patch.object(player_profiles, "save_state", side_effect=lambda: setattr(
                    st.State, "state_dirty", False)):
            with manager.activate("100.64.0.2"):
                self.assertEqual(st.PROFILE_ID, "100000002")
                self.assertEqual(
                    Path(st.STATE_FILE), self.state_dir / "profiles" / "100000002.json")
                st.State.player.data["profile_note"] = "player two"
            self.assertIsNone(st.PROFILE_ID)
            self.assertEqual(st.State.player.data["identity"]["user_id"], "100000001")
            self.assertEqual(st.STATE_FILE, "default.json")

            with manager.activate("100.64.0.2"):
                self.assertEqual(st.State.player.data["profile_note"], "player two")

        self.assertEqual(loaded, ["100000002"])
        self.assertEqual(st.STATE_FILE, "default.json")

    def test_unknown_peers_are_registered_and_keep_their_ids_after_restart(self):
        manager = player_profiles.PlayerProfileManager(auto_create=True)

        def fake_load_state():
            st.State.player = _Player(st.STATE_SLOT)
            st.State.state_dirty = False

        with patch.object(player_profiles, "load_state", side_effect=fake_load_state), \
                patch.object(player_profiles, "save_state"):
            with manager.activate("127.0.0.1") as player_id:
                self.assertEqual(player_id, "100000001")
            for address, expected in (("100.64.0.99", "300000001"),
                                      ("100.64.0.100", "300000002"),
                                      ("100.64.0.99", "300000001")):
                with manager.activate(address) as player_id:
                    self.assertEqual(player_id, expected)
                    self.assertEqual(st.State.player.data["identity"]["user_id"], expected)
            profile_map = json.loads((self.state_dir / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(profile_map["default_player_id"], "100000001")
            self.assertEqual(profile_map["clients"], {
                "100.64.0.99": "300000001", "100.64.0.100": "300000002"})
            manager = player_profiles.PlayerProfileManager(auto_create=True)
            with manager.activate("100.64.0.99") as player_id:
                self.assertEqual(player_id, "300000001")

    def test_new_ids_skip_existing_mappings_and_orphan_saves(self):
        manager = self._manager()
        manager._clients["100.64.0.3"] = "300000001"
        manager._clients["100.64.0.4"] = "999999999"
        profile_dir = self.state_dir / "profiles"
        profile_dir.mkdir()
        (profile_dir / "300000002.json").write_text("{}", encoding="utf-8")
        self.assertEqual(manager._next_player_id(), "300000003")

    def test_removed_mapping_gets_new_id_without_reusing_orphan_save(self):
        manager = self._manager()
        profile_dir = self.state_dir / "profiles"
        profile_dir.mkdir()
        (profile_dir / "300000001.json").write_text("{}", encoding="utf-8")

        def fake_load_state():
            st.State.player = _Player(st.STATE_SLOT)
            st.State.state_dirty = False

        with patch.object(player_profiles, "load_state", side_effect=fake_load_state), \
                patch.object(player_profiles, "save_state"):
            with manager.activate("100.64.0.99") as player_id:
                self.assertEqual(player_id, "300000002")
            self.assertTrue((profile_dir / "300000001.json").exists())

    def test_unknown_client_registers_named_profile_on_create_user(self):
        manager = self._manager()

        def fake_load_state():
            st.State.player = _Player(st.STATE_SLOT)
            st.State.state_dirty = False

        with patch.object(player_profiles, "load_state", side_effect=fake_load_state), \
                patch.object(player_profiles, "save_state"):
            with manager.activate("100.64.0.99", registration_name="Player Two"):
                self.assertEqual(st.PROFILE_ID, "300000001")
                self.assertEqual(st.State.player.data["identity"]["handle_name"], "Player Two")
            profile_map = json.loads((self.state_dir / "profiles.json").read_text(encoding="utf-8"))
            self.assertEqual(profile_map["clients"]["100.64.0.99"], "300000001")
            with manager.activate("100.64.0.99"):
                self.assertEqual(st.PROFILE_ID, "300000001")
                self.assertEqual(st.State.player.data["identity"]["handle_name"], "Player Two")

    def test_registration_rejects_empty_or_nonprintable_names(self):
        manager = self._manager()
        with self.assertRaises(player_profiles.UnregisteredClientError):
            with manager.activate("100.64.0.99", registration_name=" \n"):
                self.fail("invalid registration name must be rejected")

    def test_create_user_request_extracts_the_selected_name(self):
        handler = capture_server.Handler.__new__(capture_server.Handler)
        handler.path = "/actionSymbol/0FK8NJRX.php"
        handler.client_address = ("100.64.0.99", 443)
        raw = (b'{"TEAYk6R1":{"z5hB3P01":"P6pTz4WA"},'
               b'"t7n6cVWf":{"qrVcDe48":"cipher"}}')
        with patch.object(capture_server, "endpoint_for",
                          return_value=({"encode_key": "test-key"}, "test")), \
                patch.object(capture_server, "cbc_decrypt",
                             return_value=b'{"LhVz6aD2":[{"9qh17ZUf":"Player Two"}]}'):
            self.assertEqual(handler._registration_name(raw), "Player Two")

    def test_user_info_reply_uses_the_active_profiles_identity(self):
        player = object.__new__(PlayerState)
        player.data = {"identity": {"user_id": "100000003", "handle_name": "Player Two"}}
        with patch.object(PlayerState, "groups", return_value={}):
            reply = player.apply_to_reply(
                {"LhVz6aD2": [{"9Tbns0eI": "100000001", "9qh17ZUf": "Rain"}]})
        self.assertEqual(reply["LhVz6aD2"][0]["9Tbns0eI"], "100000003")
        self.assertEqual(reply["LhVz6aD2"][0]["9qh17ZUf"], "Player Two")

    def test_map_cannot_reassign_existing_default_save(self):
        path = self.state_dir / "profiles.json"
        path.write_text(json.dumps({
            "version": 1,
            "default_player_id": "100000009",
            "clients": {"100.64.0.1": "100000009"},
        }), encoding="utf-8")
        with self.assertRaises(player_profiles.ProfileMapError):
            player_profiles.PlayerProfileManager(str(path))

    def test_missing_default_map_keeps_single_profile_mode(self):
        manager = player_profiles.PlayerProfileManager()
        with manager.activate("100.64.0.99") as player_id:
            self.assertIsNone(player_id)
        self.assertFalse(manager.enabled)

    def test_auto_create_does_not_replace_missing_explicit_map(self):
        with self.assertRaises(player_profiles.ProfileMapError):
            player_profiles.PlayerProfileManager(str(self.state_dir / "missing.json"), auto_create=True)


if __name__ == "__main__":
    unittest.main()
