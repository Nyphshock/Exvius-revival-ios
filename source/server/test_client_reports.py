import json
import os
import unittest
from unittest.mock import patch

import client_reports


class ClientReportsTests(unittest.TestCase):
    def setUp(self):
        with client_reports._REQUESTED_LOCK:
            client_reports._REQUESTED_PROFILES.clear()

    def test_report_is_requested_once_on_home_update_not_during_login(self):
        spec = {"existing": [{"value": "kept"}]}
        payload = json.dumps({"LhVz6aD2": [{"9Tbns0eI": "300000001"}]})

        with patch.dict(os.environ, {"EXVIUS_CLIENT_REPORTS": "1"}):
            login_reply = client_reports.handle(spec, "OTX6Fmvu", payload)
            home_reply = client_reports.handle(spec, "Daud71Hn", payload)
            repeated_home_reply = client_reports.handle(spec, "Daud71Hn", payload)

        self.assertNotIn(client_reports.REPORT_BACK_GROUP, login_reply)
        self.assertIn(client_reports.REPORT_BACK_GROUP, home_reply)
        self.assertNotIn(client_reports.REPORT_BACK_GROUP, repeated_home_reply)
        self.assertNotIn(client_reports.REPORT_BACK_GROUP, spec)


if __name__ == "__main__":
    unittest.main()