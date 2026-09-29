"""at's own door into the notifier's topic — the push the clock fires on its
own, with no `at_deploy` between the WebApp and ntfy (§4, item 29's second
slice, item 50).

**Reading TASK-146 answered the question this module opens with.** The WebApp's
container mounts the Working Folder itself (`Mirror`, `at_deploy/environment
.py`), so `App/services/notifier/token` is already there to read — nothing new
has to be mounted, and nothing new has to be sealed. What travels is the
DERIVED key alone (§4, item 50), read once at boot and kept in memory
(`at.ui.webapp.keys.notifier_key`) — the very key `at_deploy.notifier` already
derives to seal the same file (`notifier.VAULT_SCOPE`), so opening the envelope
here re-derives nothing and reseals nothing.

**`at` does not import `at_deploy`, so the file's PATH is built from the same
piece both sides already share (`at.core.paths.services_dir`) and not read off
the other package.** The constants below — the scope's name, the file's name,
the topic — are the same words `at_deploy/notifier.py` spells, kept apart the
way `GATE_ENV` is kept apart on both sides of that same line: two definitions
of one small fact cost less than a dependency the layering forbids.

**The ADDRESS is the one thing this module cannot know on its own.** A
container's `127.0.0.1` is itself and nobody else (`gate.portal`'s own
argument), so the notifier's address on the network the two containers share is
handed over by the environment, in `NETWORK_ENV` — and a process that never got
the variable has no address to publish to, which is the CLOSED answer and not a
guess at the host's loop.

**Delivery is best-effort, exactly as `at_deploy.notifier.push` already is.** A
network that does not answer, a key this boot does not hold, a token the
folder has not drawn yet — every one of them is a push that does not go out,
and none of them is an exception the clock's round has to survive by name
(`at.ui.ask.remind` catches broadly, the way `tick` does).
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request

from pathlib import Path

from at.core import paths
from at.encryption import vault

# The scope the Main Key derives this key under, and the file it opens — the
# same two words `at_deploy/notifier.py` spells (`VAULT_SCOPE`, `TOKEN_FILE`),
# kept apart rather than imported across the line `at` does not cross.
NOTIFIER = "notifier"
TOKEN_FILE = "token"

# The topic AT's credential is scoped to write-only — `at_deploy.notifier
# .TOPIC`, spelled again for the same reason as the two above.
TOPIC = "at"

# The variable the environment hands the WebApp: the notifier's address on the
# network the two containers share (`container(NOTIFIER)`, `NOTIFIER_PORT`, on
# the `at_deploy` side). Named here because this is the module that READS it —
# the same rule `webapp.keys` and `core.gate`'s `GATE_ENV` are named by.
NETWORK_ENV = "AT_NOTIFIER"

# What every alert announces itself with — `at_deploy.notifier`'s own three,
# repeated for the reason above: silence at the default priority is a push
# nobody notices, and the tag gives it an icon.
TITLE = "AT"
PRIORITY = "high"
TAGS = "bell"

# How long a POST waits for the notifier before the round moves on.
TIMEOUT = 10.0


def token_file() -> Path:
    """`App/services/notifier/token` — the same file `at_deploy.notifier
    .token_file` names, built from the one piece both sides share."""
    return paths.services_dir() / NOTIFIER / TOKEN_FILE


def _held() -> str | None:
    try:
        kept = token_file().read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return kept or None


def token(key: bytes | None) -> str | None:
    """The credential's clear value, opened with the DERIVED key this boot
    holds — or `None` when there is nothing to open it with.

    The file may still carry the value in clear (a folder from before the
    seal, migrated by `at_deploy.notifier.provision` the next time the
    environment comes up) — a text with no envelope in it IS the value, the
    same reading `at_deploy/notifier.py:_value` gives it.
    """
    text = _held()
    if not text:
        return None
    if not vault.envelopes(text):
        return text
    if key is None:
        return None
    return vault.unseal(text, key) or None


def target() -> str | None:
    """Where the topic is, on the network this container shares with the
    notifier's — or `None` when the environment handed over no address.

    **No fallback to the host's loop.** A WebApp running loose, or a folder
    that came up without the notifier's container beside it, has no such
    variable — and answering with a guess would be `gate.portal`'s own mistake,
    named there: a port is a port, and reading one that happens to be open as
    the notifier would be worse than a push that does not go out.
    """
    held = os.environ.get(NETWORK_ENV, "").strip()
    return f"http://{held}/{TOPIC}" if held else None


def publish(title: str, body: str, key: bytes | None) -> tuple[bool, str]:
    """POST one alert to the topic. `(ok, detail)` — and the detail is never
    the token.

    Two ways of having nothing to send with, and both answer the same shape
    as a refusal the notifier itself gave: no address means the environment
    never told this process where the notifier is, and no token means the
    folder has not drawn one yet or this boot cannot open the one it has.
    Neither is raised — the caller decides what a push that did not go out
    is worth (`at.ui.ask.remind`).
    """
    where = target()
    if where is None:
        return False, "no_address"
    held = token(key)
    if held is None:
        return False, "no_token"
    request = urllib.request.Request(where, data=body.encode("utf-8"), method="POST")
    request.add_header("Title", title)
    request.add_header("Priority", PRIORITY)
    request.add_header("Tags", TAGS)
    request.add_header("Authorization", f"Bearer {held}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return 200 <= response.status < 300, str(response.status)
    except urllib.error.HTTPError as error:
        code = str(error.code)
        error.close()
        return False, code
    except (urllib.error.URLError, OSError) as error:
        return False, str(getattr(error, "reason", error))
