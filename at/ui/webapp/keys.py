"""The WebApp's derived keys — read once from the environment, kept in memory.

§4, item 50: the Vault Key never leaves the one instant `at_deploy.environment
.bring_up` derives it in — that function is the only place a process ever holds
it, and only what is DERIVED from it travels. Its `_webapp_env` hands this
container one scope's key at a time, base64'd, each in its own environment
variable — the same shape `at.core.gate.GATE_ENV` and `at.core.paths.ROOT_ENV`
already use to tell a container something the folder decided.

**A key is read from `os.environ` exactly once, at `boot`, and it is gone from
there the moment it is.** `os.environ` is inherited for the whole life of the
process — a child spawned later would see it forever if `boot` left it
standing — so the read POPS the variable instead of merely getting it. What
survives is the derived key alone, held here and nowhere else: not in a file,
not in a second variable, not spread across the callers that need it.

**A process that never got a variable has no key, and asking for one answers
`None` instead of refusing to boot.** `at-cli webapp` run loose, a test, an
environment whose folder was already fully sealed and had nothing to open this
round (`environment.unlock` answers `None, None` there too) — none of them
carries these variables, and a reader that depended on one says there is none
rather than take the process down.
"""

from __future__ import annotations

import base64
import os

# The two variables `at_deploy.environment._webapp_env` may hand this
# container — named here because this is the module that READS them, the same
# rule `gate.GATE_ENV` and `paths.ROOT_ENV` are named by their own readers
# under.
WEBAPP_KEY_ENV = "AT_WEBAPP_KEY"
NOTIFIER_KEY_ENV = "AT_NOTIFIER_KEY"

_ENV_VARS = (WEBAPP_KEY_ENV, NOTIFIER_KEY_ENV)

_keys: dict[str, bytes] = {}


def boot() -> None:
    """Read every derived key this process was handed — once, and never again.

    Called at `webapp.run`'s start and nowhere else. A variable that does not
    decode — shorter, longer, not base64 at all — is skipped rather than
    raised over: a boot is not the place to fail on a key nothing will miss
    until something asks for it (`get`).
    """
    for variable in _ENV_VARS:
        raw = os.environ.pop(variable, None)
        if not raw:
            continue
        try:
            _keys[variable] = base64.urlsafe_b64decode(raw.encode("ascii"))
        except (ValueError, UnicodeError):
            continue


def webapp_key() -> bytes | None:
    """The WebApp's own derived key, kept since `boot` — or `None`."""
    return _keys.get(WEBAPP_KEY_ENV)


def notifier_key() -> bytes | None:
    """The notifier's derived key — the same one `at_deploy.notifier` seals
    and opens its credential with — kept since `boot`, or `None`."""
    return _keys.get(NOTIFIER_KEY_ENV)
