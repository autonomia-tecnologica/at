"""The test suite. Stdlib `unittest` only — a test runner is not a dependency.

    python3 -m unittest discover -t .

From the repository root, and NOT with `-s at/tests`: there are two artifacts
and two suites (item 27), and this one command is what runs both. The split is
`at/tests` for the folder and the app and `at_deploy/tests` for §7, and the
boundary between them is affirmed in `at_deploy/tests/test_boundary.py`.
"""

from __future__ import annotations

from at.core import files
from at.services import caddy

# The gate secret the suite works with when it has to EXIST. The deploy draws it
# at installation (`at_deploy/environment.py`, §7b) and `at` reads it — so a
# test of the READER writes the file, which is exactly the state the deploy
# leaves behind, and never imports the deploy to produce it.
DRAWN_GATE = "segredo-sorteado"


def drawn_gate(secret: str = DRAWN_GATE) -> str:
    """Leave `App/caddy/gate` as `up` would have left it, and answer the secret."""
    where = caddy.gate_file()
    where.parent.mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(where, f"{secret}\n")
    return secret
