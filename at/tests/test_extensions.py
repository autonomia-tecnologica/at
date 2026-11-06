"""Extensions, slice 1 (§8): manifest, canonical hash, review and blockers."""

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, extensions
from at.data import schema


class ExtensionsTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.env = mock.patch.dict(
            os.environ, {"AT_ROOT": str(self.scratch.name), "AT_LANG": "pt_BR"}
        )
        self.env.start()
        i18n.reset()
        schema.reset()
        with redirect_stdout(StringIO()):
            boot.create_working_folder()
        self.base = extensions.extensions_dir()

    def tearDown(self):
        self.env.stop()
        schema.reset()
        self.scratch.cleanup()

    def make(self, name, manifest=None, files=None):
        folder = self.base / name
        folder.mkdir(parents=True)
        if manifest is not None:
            body = {
                "id": name,
                "name": "X",
                "version": "1",
                "author_note": "n",
                **manifest,
            }
            (folder / "manifest.json").write_text(json.dumps(body), encoding="utf-8")
        for rel, data in (files or {}).items():
            path = folder / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return folder

    def data_ext(self, name="slang", **extra):
        return self.make(
            name, {"class": "data", "alters": ["words:alter"], **extra}, {"a.json": b"{}"}
        )

    def frontend(self, permissions, name="front"):
        return self.make(
            name,
            {"class": "frontend", "contract": "1", "permissions": permissions},
            {"index.html": b"<p>x</p>"},
        )

    # hash

    def test_hash_is_stable_without_mtime_or_empty_folders(self):
        folder = self.data_ext()
        first = extensions.inspect("slang")["hash"]
        os.utime(folder / "a.json", (1, 1))
        (folder / "empty").mkdir()
        self.assertEqual(first, extensions.inspect("slang")["hash"])

    def test_hash_changes_with_one_byte(self):
        folder = self.data_ext()
        first = extensions.inspect("slang")["hash"]
        (folder / "a.json").write_bytes(b"{ }")
        self.assertNotEqual(first, extensions.inspect("slang")["hash"])

    def test_hash_does_not_confuse_file_split(self):
        one = self.make("one", None, {"a": b"bc"})
        two = self.make("two", None, {"ab": b"c"})
        self.assertNotEqual(extensions.digest(one), extensions.digest(two))

    # review

    def test_install_records_hash_review_and_instant(self):
        self.data_ext()
        entry = extensions.install("slang", "read")
        stored = json.loads(extensions.state_file().read_text(encoding="utf-8"))
        self.assertEqual(stored["slang"], entry)
        self.assertEqual(entry["review"], "read")
        self.assertEqual(entry["hash"], extensions.inspect("slang")["hash"])
        self.assertTrue(entry["at"])
        self.assertEqual(extensions.inspect("slang")["review"], "read")

    def test_changed_byte_invalidates_review(self):
        folder = self.data_ext()
        extensions.install("slang", "trust")
        (folder / "a.json").write_bytes(b"[]")
        self.assertIsNone(extensions.inspect("slang")["review"])

    def test_install_refuses_unknown_review_and_extension(self):
        self.data_ext()
        with self.assertRaises(extensions.ExtensionError):
            extensions.install("slang", "maybe")
        with self.assertRaises(extensions.ExtensionError):
            extensions.install("ghost", "read")

    def test_install_refuses_blocked_extension(self):
        self.make("bad")
        with self.assertRaises(extensions.ExtensionError):
            extensions.install("bad", "read")
        self.assertFalse(extensions.state_file().exists())

    def test_data_and_valid_frontend_have_no_blockers(self):
        self.data_ext()
        self.frontend(["setting:list"] if schema.of("setting") else [self.some_table() + ":list"])
        self.assertEqual([e["blockers"] for e in extensions.scan()], [[], []])

    def some_table(self):
        return schema.declared()[0]["id"]

    # blockers

    def test_blocker_missing_manifest(self):
        self.make("bare", None, {"a": b"x"})
        self.assertEqual(extensions.inspect("bare")["blockers"], [extensions.MISSING_MANIFEST])

    def test_blocker_invalid_manifest(self):
        folder = self.make("broken", None)
        (folder / "manifest.json").write_text("{nope", encoding="utf-8")
        self.assertEqual(extensions.inspect("broken")["blockers"], [extensions.INVALID_MANIFEST])
        self.make("wrongid", {"class": "data", "alters": [], "id": "other"})
        self.assertEqual(extensions.inspect("wrongid")["blockers"], [extensions.INVALID_MANIFEST])

    def test_blocker_js_file(self):
        folder = self.data_ext()
        (folder / "sub").mkdir()
        (folder / "sub" / "x.js").write_bytes(b"1")
        self.assertEqual(extensions.inspect("slang")["blockers"], [extensions.SCRIPT])

    def test_blocker_unknown_class(self):
        self.make("odd", {"class": "backend"})
        self.assertEqual(extensions.inspect("odd")["blockers"], [extensions.UNKNOWN_CLASS])

    def test_blocker_unknown_table(self):
        self.frontend(["nonexistent_table:list"])
        self.assertEqual(extensions.inspect("front")["blockers"], [extensions.UNKNOWN_TABLE])

    def test_blocker_invalid_action(self):
        self.frontend([self.some_table() + ":edit"])
        self.assertEqual(extensions.inspect("front")["blockers"], [extensions.INVALID_ACTION])

    def test_data_class_asks_no_read_permission(self):
        self.data_ext()
        self.assertNotIn("permissions", extensions.inspect("slang")["manifest"])
        self.assertEqual(extensions.inspect("slang")["blockers"], [])

    def test_scan_empty_when_no_folder(self):
        self.assertEqual(extensions.scan(), [])


if __name__ == "__main__":
    unittest.main()
