"""The single writer, and the read-only switch (`at.core.files`).

`atomic_write_text` already gets its coverage through every module that calls
it; what had no test of its own was the counting side — `writes`, `reset_writes`
and `guard` — and `mark_write`, the door a bulk write that does not go through
`atomic_write_text` (a restore's tar extraction) uses to tell the cadence one
write happened all the same.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from at.core import files


class TheCounter(unittest.TestCase):
    def setUp(self):
        files.reset_writes()

    def tearDown(self):
        files.reset_writes()

    def test_it_starts_at_zero(self):
        self.assertEqual(files.writes(), 0)

    def test_mark_write_counts_one(self):
        files.mark_write()
        self.assertEqual(files.writes(), 1)

    def test_two_marks_count_two(self):
        files.mark_write()
        files.mark_write()
        self.assertEqual(files.writes(), 2)

    def test_reset_forgets_the_count(self):
        files.mark_write()
        files.reset_writes()
        self.assertEqual(files.writes(), 0)


class TheSwitch(unittest.TestCase):
    def test_it_reads_the_environment(self):
        for value, expected in (
            ("1", True), ("true", True), ("YES", True), ("on", True),
            ("0", False), ("", False), ("nao", False),
        ):
            with self.subTest(value=value):
                with mock.patch.dict(os.environ, {files.ENV_READONLY: value}):
                    self.assertEqual(files.readonly(), expected)

    def test_unset_is_writable(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(files.ENV_READONLY, None)
            self.assertFalse(files.readonly())

    def test_guard_refuses_only_when_the_switch_is_on(self):
        with mock.patch.dict(os.environ, {files.ENV_READONLY: "1"}):
            with self.assertRaises(files.ReadOnly) as raised:
                files.guard("algum/caminho")
            self.assertEqual(raised.exception.where, "algum/caminho")
        with mock.patch.dict(os.environ, {files.ENV_READONLY: "0"}):
            files.guard("algum/caminho")  # does not raise


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
