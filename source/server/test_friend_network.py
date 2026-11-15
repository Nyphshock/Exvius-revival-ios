import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import ffbe_state as st
import friend_network


class _Profiles:
    def player_ids(self):
        return ["300000001", "300000002", "300000003"]


class _HelperProfile:
    data = {
        "identity": {"user_id": "300000002", "handle_name": "Player Two"},
        "rank": {"level": 42},
        "profile": {"player_emblem_id": 0},
        "exvius_friends": {},
    }

    def party_instance_ids(self):
        return ["lead", "second"]

    def roster_row(self, instance_id):
        return {"instance_id": instance_id, "master_id": "100000102", "level": 120,
                "lb_level": 5, "lb_exp": 0, "equipment": {1: "301000001"}}


class FriendNetworkTests(unittest.TestCase):
    def setUp(self):
        self.previous = (st.State.player, getattr(st, "PROFILE_MANAGER", None))
        st.State.player = SimpleNamespace(data={"identity": {"user_id": "300000001"}})
        st.PROFILE_MANAGER = _Profiles()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file_patch = patch.object(friend_network, "NETWORK_FILE",
                                       str(Path(self.temp.name) / "friend_network.json"))
        self.file_patch.start()
        self.addCleanup(self.file_patch.stop)
        self.addCleanup(self._restore)

    def _restore(self):
        st.State.player, st.PROFILE_MANAGER = self.previous

    def test_request_is_incoming_for_recipient_and_acceptance_is_mutual(self):
        self.assertTrue(friend_network.send_request("300000001", "300000002"))
        self.assertEqual(friend_network.relation_type("300000001", "300000002"), 2)
        self.assertEqual(friend_network.relation_type("300000002", "300000001"), 3)
        self.assertTrue(friend_network.accept_request("300000002", "300000001"))
        self.assertEqual(friend_network.relation_type("300000001", "300000002"), 1)
        self.assertEqual(friend_network.relation_type("300000002", "300000001"), 1)
        self.assertEqual(friend_network.friend_ids("300000001", relation=1), ["300000002"])

    def test_recipient_can_refuse_and_sender_can_send_again(self):
        self.assertTrue(friend_network.send_request("300000001", "300000002"))
        self.assertTrue(friend_network.refuse_request("300000002", "300000001"))
        self.assertEqual(friend_network.relation_type("300000001", "300000002"), 0)
        self.assertTrue(friend_network.send_request("300000001", "300000002"))

    def test_reciprocal_requests_accept_friendship(self):
        self.assertTrue(friend_network.send_request("300000001", "300000002"))
        self.assertTrue(friend_network.send_request("300000002", "300000001"))
        self.assertEqual(friend_network.relation_type("300000001", "300000002"), 1)

    def test_unknown_and_self_requests_are_rejected(self):
        self.assertFalse(friend_network.send_request("300000001", "300000001"))
        self.assertFalse(friend_network.send_request("300000001", "999999999"))

    def test_public_friend_uses_the_active_party_lead(self):
        with patch.object(friend_network, "player_for", return_value=_HelperProfile()), \
                patch("ffbe_friends._entry", side_effect=lambda _index, raw: raw):
            friend = friend_network.friend_profile("300000002")

        self.assertEqual(friend["display_name"], "Player Two")
        self.assertEqual(friend["friend_id"], "300000002")
        self.assertEqual(friend["unit_instance_id"], "lead")
        self.assertEqual(friend["unit"]["master_id"], "100000102")

    def test_public_friend_preserves_equipment_slots(self):
        import ffbe_friends

        profile = _HelperProfile()
        profile.roster_row = lambda _iid: {
            "instance_id": "lead", "master_id": "100000102", "level": 120,
            "lb_level": 5, "lb_exp": 0, "materia": ["200100001", "200100002", "0", "0"],
            "equipment": {1: "sword", 5: "armor"},
        }
        with patch.object(friend_network, "player_for", return_value=profile), \
            patch("ffbe_friends.unit_stats", return_value=(100, 10, 20, 30, 40, 50)), \
            patch("ffbe_friends.limit_burst", return_value=None):
            friend = friend_network.friend_profile("300000002")
            reinforcement_row = ffbe_friends._reinforce_row(friend)

        self.assertEqual(friend["unit"]["equipment"], ["sword", "0", "0", "0", "armor", "0"])
        self.assertEqual(friend["unit"]["abilities"], ["200100001", "200100002", "0", "0"])
        self.assertEqual(reinforcement_row["80NUYFMJ"], "1-200100001@2-200100002@3-0@4-0")

    def test_public_friend_uses_companion_settings_by_tab_not_regular_party_lead(self):
        profile = _HelperProfile()
        profile.data = {
            "identity": {"user_id": "300000002", "handle_name": "Player Two"},
            "rank": {"level": 42}, "profile": {"player_emblem_id": 0},
            "party": {"special": {"7": {"active_deck": 0, "decks": [{"id": 0, "members": [
                {"disp_order": 0, "instance_id": "vivi"},
                {"disp_order": 1, "instance_id": "event1"},
                {"disp_order": 2, "instance_id": "event2"},
                {"disp_order": 3, "instance_id": "nemesis1"},
                {"disp_order": 4, "instance_id": "nemesis2"},
            ]}]}}},
        }
        units = {
            "vivi": {"instance_id": "vivi", "master_id": "100004605", "level": 120},
            "event1": {"instance_id": "event1", "master_id": "100004403", "level": 120},
            "event2": {"instance_id": "event2", "master_id": "212000103", "level": 120},
            "nemesis1": {"instance_id": "nemesis1", "master_id": "205000203", "level": 120},
            "nemesis2": {"instance_id": "nemesis2", "master_id": "209000204", "level": 120},
            "regular-lead": {"instance_id": "regular-lead", "master_id": "100000102", "level": 120},
        }
        profile.party_instance_ids = lambda: ["regular-lead"]
        profile.roster_row = lambda instance_id: units.get(instance_id)
        with patch.object(friend_network, "player_for", return_value=profile), \
                patch("ffbe_friends._entry", side_effect=lambda _index, raw: raw):
            favorite = friend_network.friend_profile("300000002", support_tab=1)
            event_1 = friend_network.friend_profile("300000002", support_tab=2)
            event_2 = friend_network.friend_profile("300000002", support_tab=3)
            nemesis_1 = friend_network.friend_profile("300000002", support_tab=4)
            nemesis_2 = friend_network.friend_profile("300000002", support_tab=5)

        self.assertEqual([favorite["unit"]["master_id"], event_1["unit"]["master_id"],
                          event_2["unit"]["master_id"], nemesis_1["unit"]["master_id"],
                          nemesis_2["unit"]["master_id"]],
                         ["100004605", "100004403", "212000103", "205000203", "209000204"])
        self.assertEqual(favorite["unit_instance_id"], "vivi")
        self.assertEqual(nemesis_2["support_tab"], 5)

    def test_public_friend_includes_esper_linked_to_companion_slot(self):
        import ffbe_friends

        profile = _HelperProfile()
        profile.data = {
            "identity": {"user_id": "300000002", "handle_name": "Player Two"},
            "rank": {"level": 42}, "profile": {"player_emblem_id": 0},
            "beasts": [{"esper_id": "12", "rarity": 4, "level": 55}],
            "party": {"special": {"7": {
                "active_deck": 0,
                "decks": [{"id": 0, "members": [
                    {"disp_order": 0, "instance_id": "favorite"},
                    {"disp_order": 1, "instance_id": "event1"},
                ]}],
                "beast_decks": {"0": [99, 12, 0, 0, 0, 0]},
            }}},
        }
        profile.roster_row = lambda instance_id: {
            "instance_id": instance_id, "master_id": "100000102", "level": 120,
            "lb_level": 5, "equipment": {},
        }

        with patch.object(friend_network, "player_for", return_value=profile), \
                patch("ffbe_friends.unit_stats", return_value=(100, 10, 20, 30, 40, 50)), \
                patch("ffbe_friends.limit_burst", return_value=None), \
                patch("ffbe_friends.beast_stats", return_value=(11, 12, 13, 14, 15, 16)):
            friend = friend_network.friend_profile("300000002", support_tab=2)
            row = ffbe_friends._reinforce_row(friend)

        self.assertEqual(friend["unit"]["esper"], 12)
        self.assertEqual(friend["unit"]["esper_rarity"], 4)
        self.assertEqual(friend["unit"]["esper_level"], 55)
        self.assertEqual(row["XZ4Kh7Ic"], "12,4,55,11,12,13,14,15,16")

    def test_public_profile_validation_preserves_requested_support_tab(self):
        profile = _HelperProfile()
        profile.data["party"] = {"special": {"7": {"active_deck": 0, "decks": [{"id": 0, "members": [
            {"disp_order": 3, "instance_id": "nemesis1"},
        ]}]}}}
        profile.roster_row = lambda _iid: {"master_id": "100000102", "level": 120}
        with patch.object(friend_network, "player_for", return_value=profile), \
                patch("ffbe_friends.unit_stats", return_value=(100, 10, 20, 30, 40, 50)), \
                patch("ffbe_friends.limit_burst", return_value=None):
            friend = friend_network.friend_profile("300000002", support_tab=4)

        self.assertEqual(friend["support_tab"], 4)

    def test_native_friend_request_routes_to_real_profile_handler(self):
        import exvius_actions

        handler = exvius_actions._all_handlers()["j0A5vQd8"]

        self.assertEqual(handler.__module__, "exvius_actions_arena")

    def test_friend_list_separates_incoming_and_outgoing_requests(self):
        import ffbe_friends
        st.State.player = SimpleNamespace(
            data={"identity": {"user_id": "300000001"}, "counts": {"friend": 0}},
            mode="live", dirty=False)
        with patch.object(ffbe_friends, "all_friends", return_value=[]), \
                patch.object(friend_network, "current_id", return_value="300000001"), \
                patch.object(friend_network, "friend_ids", side_effect=lambda _owner, relation: {
                    1: [], 2: ["300000002"], 3: ["300000003"],
                }[relation]), \
                patch.object(ffbe_friends, "_request_list_row",
                             side_effect=lambda target, category, _now:
                             {"m3Wghr1j": target, "K3BV17gk": str(category)}), \
                patch.object(ffbe_friends, "_suggestion_rows", return_value=[]):
            reply = ffbe_friends.serve_friends({}, ffbe_friends.FRIENDLIST_REPLY)

        self.assertEqual(reply["9Qt5cI0n"], [{"m3Wghr1j": "300000003", "K3BV17gk": "3"}])
        self.assertEqual(reply["hZR64mDe"], [{"m3Wghr1j": "300000002", "K3BV17gk": "2"}])

    def test_new_friend_list_has_no_preloaded_fake_accounts(self):
        import ffbe_friends
        import friend_players
        with patch.dict("os.environ", {"EXVIUS_PLAYERS": "0"}):
            self.assertEqual(friend_players._count(), 0)
            self.assertFalse(friend_players.enabled())
            self.assertEqual(ffbe_friends.all_friends(), [])

    def test_friend_list_refresh_syncs_accepted_count_before_projection(self):
        import ffbe_friends
        st.State.player = SimpleNamespace(
            data={"identity": {"user_id": "300000001"}, "counts": {"friend": 0}},
            mode="live", dirty=False)
        with patch.object(friend_network, "current_id", return_value="300000001"), \
                patch.object(friend_network, "friend_ids", return_value=["300000002", "300000003"]):
            self.assertIsNone(ffbe_friends.sync_friend_count(None, ffbe_friends.FRIENDLIST_REPLY))

        self.assertEqual(st.State.player.data["counts"]["friend"], 2)
        self.assertTrue(st.State.player.dirty)

    def test_reinforcement_reply_contains_only_accepted_real_friend_helpers(self):
        import ffbe_friends
        st.State.player = SimpleNamespace(
            data={"identity": {"user_id": "300000001"}, "counts": {"friend": 1}},
            mode="live", dirty=False)
        friend = {"friend_id": 300000002, "display_name": "Player Two",
                  "unit": {"vision_card": ""}}
        with patch.object(ffbe_friends, "all_friends", return_value=[friend]), \
            patch.object(ffbe_friends, "all_support_profiles", return_value=[friend]), \
                patch.object(ffbe_friends, "_reinforce_row",
                             return_value={"m3Wghr1j": "300000002", "og2GHy49": "unit-lead"}), \
                patch.object(ffbe_friends, "_friend_list_row",
                             return_value={"m3Wghr1j": "300000002"}), \
                patch.object(ffbe_friends, "_suggestion_rows", return_value=[]):
            reply = ffbe_friends.serve_friends({}, ffbe_friends.REINFORCE_REPLY)

        self.assertEqual(reply[ffbe_friends.REINFORCE_CLEAR_TAG], [
            {"m3Wghr1j": "300000002", "og2GHy49": "unit-lead"}])
        self.assertNotIn(ffbe_friends.REINFORCE_TAG, reply)
        self.assertEqual(reply[ffbe_friends.FRIENDLIST_TAG], [
            {"m3Wghr1j": "300000002", "8zE6w9RP": "0"}])

    def test_reinforcement_reply_serves_only_requested_companion_tab(self):
        import ffbe_friends
        st.State.player = SimpleNamespace(
            data={"identity": {"user_id": "300000001"}, "counts": {"friend": 1}},
            mode="live", dirty=False)
        profiles = [{"friend_id": 300000002, "support_tab": tab, "unit": {"vision_card": ""}}
                    for tab in range(1, 6)]
        with patch.object(ffbe_friends, "all_friends", return_value=[profiles[0]]), \
                patch.object(ffbe_friends, "all_support_profiles",
                             side_effect=lambda tab: [p for p in profiles if p["support_tab"] == tab]), \
                patch.object(ffbe_friends, "_reinforce_row",
                             side_effect=lambda friend: {"m3Wghr1j": str(friend["friend_id"]),
                                                        "Y58ENcB4": str(friend["support_tab"])}), \
                patch.object(ffbe_friends, "_friend_list_row", return_value={"m3Wghr1j": "300000002"}), \
                patch.object(ffbe_friends, "_suggestion_rows", return_value=[]):
            for tab in range(1, 6):
                request = json.dumps({"I53AVzSo": [{"Y58ENcB4": str(tab)}]})
                reply = ffbe_friends.serve_friends({}, ffbe_friends.REINFORCE_REPLY, request)
                rows = reply[ffbe_friends.REINFORCE_CLEAR_TAG]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["Y58ENcB4"], str(tab))

    def test_native_friend_request_saves_pending_and_returns_friend_row(self):
        import exvius_actions_arena
        from ffbe_player import score_quest_action

        previous = st.State.player
        st.State.player = SimpleNamespace(
            data={"identity": {"user_id": "300000001"}, "counts": {"friend": 0}},
            mode="live", dirty=False)
        catalog = {"300000002": {"friend_id": 300000002, "unit": {"master_id": 100000102}}}
        state = {"relations": {"300000002": {"type": 0, "favorite": 0}}}
        try:
            with patch.object(exvius_actions_arena, "_friends", return_value=(catalog, state)), \
                    patch.object(friend_network, "current_id", return_value="300000001"), \
                    patch.object(friend_network, "send_request", return_value=True) as send_request, \
                    patch.object(friend_network, "relation_type", return_value=2), \
                    patch.object(friend_network, "friend_profile", return_value=catalog["300000002"]), \
                    patch.object(exvius_actions_arena, "_friend_row",
                                 return_value={"m3Wghr1j": "300000002", "K3BV17gk": "2"}), \
                    patch.object(exvius_actions_arena, "_friend_reply",
                                 side_effect=lambda spec, tag, rows: {tag: [row for _friend, row in rows]}), \
                    patch("ffbe_player.score_quest_action") as score:
                reply = exvius_actions_arena.friend_request(
                    {}, {"I53AVzSo": [{"m3Wghr1j": "300000002"}]})
        finally:
            st.State.player = previous

        send_request.assert_called_once_with("300000001", "300000002")
        score.assert_called_once_with("14")
        self.assertEqual(reply["2vuhy0Ex"], [{"m3Wghr1j": "300000002", "K3BV17gk": "2"}])
        self.assertEqual(reply["I53AVzSo"][0]["H4zD2IQ5"], "-1")

    def test_native_agree_accepts_incoming_request_and_updates_friend_count(self):
        import exvius_actions_arena

        previous = st.State.player
        st.State.player = SimpleNamespace(
            data={"identity": {"user_id": "300000002"}, "counts": {"friend": 0}},
            mode="live", dirty=False)
        recipient = st.State.player
        catalog = {"300000001": {"friend_id": 300000001, "unit": {"master_id": 100000102}}}
        state = {"relations": {"300000001": {"type": 3, "favorite": 0}}}
        try:
            with patch.object(exvius_actions_arena, "_friends", return_value=(catalog, state)), \
                    patch.object(friend_network, "current_id", return_value="300000002"), \
                    patch.object(friend_network, "accept_request", return_value=True) as accept, \
                    patch.object(friend_network, "friend_profile", return_value=catalog["300000001"]), \
                    patch.object(exvius_actions_arena, "_friend_row",
                                 return_value={"m3Wghr1j": "300000001", "K3BV17gk": "1"}), \
                    patch.object(exvius_actions_arena, "_friend_reply",
                                 side_effect=lambda spec, tag, rows: {tag: [row for _friend, row in rows]}):
                reply = exvius_actions_arena.friend_agree(
                    {}, {"I53AVzSo": [{"m3Wghr1j": "300000001"}]})
        finally:
            st.State.player = previous

        accept.assert_called_once_with("300000002", "300000001")
        self.assertEqual(st.State.player, previous)
        self.assertEqual(recipient.data["counts"]["friend"], 1)
        self.assertEqual(reply["2vuhy0Ex"], [{"m3Wghr1j": "300000001", "K3BV17gk": "1"}])


if __name__ == "__main__":
    unittest.main()