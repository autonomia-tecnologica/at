"""The service manager of the HOST environment (TASK-190): `systemctl --user`,
and no other.

The container path's runtime is Podman (`podman.py`); the host path's is
whatever already runs the person's session, because systemd `--user` is what a
Linux login already carries — nothing to install, nothing to ask about. This
file is that runtime's side of the decision: the binary AT looks for, and the
single seam every call goes through, the same shape `podman.py` already set.

**One seam, and it is a function.** `run()` is the only place AT touches
`systemctl`, so every unit AT ever writes or starts is provable on a machine
that has none at all — the suite's own — by swapping this one function out,
exactly how `podman.run` is swapped in `at_deploy/tests/test_environment.py`.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from typing import Any

# The word on the PATH, and the only one AT knows.
BINARY = "systemctl"


def found() -> str | None:
    """Where `systemctl` is, or `None` — the host environment's whole check."""
    return shutil.which(BINARY)


def present() -> bool:
    return found() is not None


def run(args: Sequence[str], **kw: Any) -> subprocess.CompletedProcess:
    """One call to the manager, always for THIS person's session (`--user`) —
    the host environment never touches the system's own units.

    The binary is resolved HERE and never by the caller, the same rule
    `podman.run` follows and for the same reason: nothing outside this
    function has to know where `systemctl` is.
    """
    return subprocess.run(  # noqa: S603 — the manager's own binary, resolved above
        [found() or BINARY, "--user", *(str(part) for part in args)],
        capture_output=True,
        text=True,
        **kw,
    )


def ok(args: Sequence[str]) -> bool:
    """Whether the manager accepted that call — `enable --now`, `restart`,
    `daemon-reload`, every one of which is a yes or a no."""
    return run(args).returncode == 0
