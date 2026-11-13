import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import event_archive
import ios_art
import ios_tables


class VortexArtVersionTests(unittest.TestCase):
    def test_changed_banners_get_higher_persistent_pack_and_table_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            folder = root / "en" / "sd" / "area"
            folder.mkdir(parents=True)
            (folder / "Ver5_spdungeon1.cpk").write_bytes(b"source")
            (folder / "event_703.png").write_bytes(b"orbonne")
            cache = Path(tmp) / "cache"
            cache.mkdir()

            def fake_build(src, adds, out):
                Path(out).write_bytes(b"pack" + b"".join(Path(path).read_bytes() for _, path in adds))
                return {"files": len(adds), "added": len(adds), "size": os.path.getsize(out)}

            with patch.object(ios_art, "art_names", return_value=["event_703.png", "event_704.png"]), \
                    patch.object(ios_art, "build", side_effect=fake_build):
                first = ios_art.built_pack(str(cache), str(root))
                self.assertIsNotNone(first)
                self.assertEqual(ios_art.built_pack(str(cache), str(root)), first)
                with patch.object(ios_tables, "art", return_value=first):
                    first_versions = [ios_tables.table_bump(spec) for spec in
                                      (ios_tables.RESOURCE_VERSION, ios_tables.RESOURCE_CHECKSUM)]

                (folder / "event_704.png").write_bytes(b"second banner")
                second = ios_art.built_pack(str(cache), str(root))
                self.assertIsNotNone(second)
                self.assertGreater(second[1], first[1])
                with patch.object(ios_tables, "art", return_value=second):
                    second_versions = [ios_tables.table_bump(spec) for spec in
                                       (ios_tables.RESOURCE_VERSION, ios_tables.RESOURCE_CHECKSUM)]
                self.assertTrue(all(new > old for old, new in zip(first_versions, second_versions)))
                self.assertEqual(ios_art.built_pack(str(cache), str(root)), second)

            self.assertGreater(first[1], 5 + 1999)
            self.assertGreater(first_versions[0], ios_tables.sound_bump() + 2999)
            self.assertGreater(first_versions[1], 1999)

    def test_server_fetches_and_builds_before_opening_listeners(self):
        path = Path(__file__).resolve().parents[2] / "ios-server" / "serve.py"
        spec = importlib.util.spec_from_file_location("ios_serve_test", path)
        server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server)
        calls = []

        def stop_before_listening(*args):
            calls.append("tls")
            raise RuntimeError("stop before opening listeners")

        with patch.object(server, "configure_engine"), patch.object(server, "start_engine"), \
                patch.dict(sys.modules, {"certs": SimpleNamespace(ensure=lambda path: {})}), \
                patch.object(event_archive, "fetch_added_art", side_effect=lambda **kw: calls.append("fetch")), \
                patch.object(ios_tables, "art", side_effect=lambda: calls.append("build")), \
                patch.object(server.threading, "Thread"), \
                patch.object(server.ssl, "SSLContext", side_effect=stop_before_listening):
            with self.assertRaisesRegex(RuntimeError, "stop before opening listeners"):
                server.main()
        self.assertEqual(calls, ["fetch", "build", "tls"])


if __name__ == "__main__":
    unittest.main()
