"""The lint gate (B-5): `ruff` and `mypy` come back clean, or the suite fails.

Both are development tools (`pip install -e '.[dev]'`) and both read their
configuration from `pyproject.toml` — the rules live there and not here. A tool
that is not installed in the `.venv` skips its test with the reason, instead of
failing the suite on a machine that only runs the product.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT = 600


def available(tool: str) -> bool:
    probe = subprocess.run(  # noqa: S603 — this interpreter, asking for a module
        [sys.executable, "-m", tool, "--version"],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    return probe.returncode == 0


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 — this interpreter, running a dev tool
        [sys.executable, "-m", *args],
        capture_output=True, text=True, cwd=ROOT, timeout=TIMEOUT, check=False,
    )


class TheLintGate(unittest.TestCase):
    def test_ruff_is_clean(self):
        if not available("ruff"):
            self.skipTest("ruff is not installed in this .venv (pip install -e '.[dev]')")
        done = run("ruff", "check", ".", "--no-cache", "--output-format", "concise")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_mypy_is_clean(self):
        if not available("mypy"):
            self.skipTest("mypy is not installed in this .venv (pip install -e '.[dev]')")
        done = run("mypy")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
