"""The container runtime of the container path (§7a): the Podman, and no other.

§7a decides one word: **Podman is the choice**. This file is the runtime's side
of that decision — the binary Bill looks for, and the single seam every call
goes through. The two ways out of a machine that does not have it are the
ENVIRONMENT's (`services/environment.py`), because it is the environment that
needs a runtime; what belongs here is what a runtime is: a name, a lookup and a
command.

**One seam, and it is a function.** `run()` is the only place Bill touches
Podman, so the whole orchestration — the argv of every service, the pin, the
refusal — is provable on a machine that has no Podman at all, which is exactly
this one. That is not a testing convenience: the argv IS where the security
decisions of the environment are readable, because what is mounted, what is
published and on which address is a list of arguments, and nothing else.

**A second runtime is a declaration away, and it is not made here.** Docker
speaks the same verbs for the environment Bill orchestrates, so the day it comes
in it comes in as another word behind this seam — but it does not come in on its
own: Podman is daemonless and rootless by default, and the daemon of the other
one runs as root, which is a decision of §3 (Privilégio) that nobody has taken.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence

# The word on the PATH, and the only one Bill knows.
BINARY = "podman"


def found() -> str | None:
    """Where the Podman is, or `None` — §7a's whole check.

    A path and not a boolean: what a person reads when the runtimes of a machine
    are being told apart is which one was found, and `which` is the same
    question the shell answers.
    """
    return shutil.which(BINARY)


def present() -> bool:
    return found() is not None


def run(args: Sequence[str], **kw: object) -> subprocess.CompletedProcess:
    """One call to the runtime — the seam, and the only one.

    The binary is resolved HERE and never by the caller, so nothing outside this
    function has to know where a Podman is, or that there is one. Output is
    captured: the runtime speaks for whoever is diagnosing, and Bill answers in
    its own words (§3) — an error's text is a machine's, and it is printed where
    the person asked for it, not passed through.

    A missing binary is the caller's to prevent (`present()`): this raises
    `FileNotFoundError` like any `subprocess.run`, and the environment refuses
    the machine long before it gets here.
    """
    return subprocess.run(  # noqa: S603 — the runtime's own binary, resolved above
        [found() or BINARY, *(str(part) for part in args)],
        capture_output=True,
        text=True,
        **kw,  # type: ignore[arg-type]
    )


def ok(args: Sequence[str]) -> bool:
    """Whether the runtime accepted that call — for the questions that are a yes
    or a no, like whether a container is there."""
    return run(args).returncode == 0
