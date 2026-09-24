"""The gate, as the folder records it and as the app reads it.

The container path's authenticator is an external identity provider in front of
everything (§7b), and the APP's half of it is only this: knowing which
authenticator this folder is on, and refusing to serve when a committed gate
stops answering. **That half belongs to `at-cli` and stays with it** — a folder on
the container path is served by `at-cli` with the deploy artifact absent, closing
when the gate falls (item 27) — while the drawing, the containers and the
transactional switch that COMMITS the record belong to `at-deploy`, which
writes it and which is the only one that can.

**The boundary between the two artifacts is the folder's state, not an API.** The
deploy tool writes the record; `at-cli` reads the same file. So the two halves of
what this module is about are one home each: `mode`, `on_gate` and `remember`
read and write `authenticator` in `App/settings.json`, and `portal` and
`standing` ask the provider that the environment named through `AT_GATE`.

**A value the release does not know reads as `FORMS`**, which is the safe side
and the truthful one: a folder that has never proved a gate IS the hosted path,
and a folder whose record nobody can read is a folder that has proved nothing.
It is read on every request, and a folder whose settings are broken must not take
the WebApp down request by request.

**The probe is here and not in the deploy because it is the APP that asks it.**
`standing` is the question a committed folder makes of its own portal on every
request, from inside the container the WebApp runs in — a container that cannot
see the host's loop, and that reaches the provider by the name the environment
handed it. The switch asks a different question from the other side (the site
through the edge, from the host); the two share the transport below and nothing
else.
"""

from __future__ import annotations

import os
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable

from at.core import settings

# The two authenticators, and the key the folder records the choice under. `App/
# settings.json` holds what is neither translation nor table, and this is an
# adjustment of the installation — the same shelf `basic_auth` sits on, and for
# the same reason: it is a decision about this folder, not a credential.
FORMS = "forms"
GATE = "gate"
KEY = "authenticator"

# The variable the environment hands the WebApp so it can find its gate (§7c). A
# container has no host's loop to ask — `127.0.0.1` inside it is the WebApp's own
# — so the environment is what says which name to use.
GATE_ENV = "AT_GATE"

# How long a probe waits for an answer. Long enough for a container to take a
# connection, short enough that a request is not left waiting on a portal that is
# never going to answer.
PROBE = 5.0

# What a probe answers with: the status, or `None` when nothing answered at all.
# Injected the way every other seam of the product is, and for the same reason — a
# suite proves the whole switch and the whole check without a socket, which is
# what "no test touches the network" means here.
Answer = Callable[[str, dict[str, str]], int | None]


# ------------------------------------------------------------- the folder ---

def mode() -> str:
    """Which authenticator this folder is on: `forms`, or the gate."""
    try:
        held = settings.get(KEY)
    except settings.SettingsError:
        return FORMS
    return GATE if held == GATE else FORMS


def on_gate() -> bool:
    """Whether the Forms is OFF — the switch is committed (§6)."""
    return mode() == GATE


def remember(value: str) -> None:
    """Record where the folder's authenticator is — the COMMIT of the switch.

    The write lives here, beside the read, because they are one declaration: the
    key and its two values are this module's, and the deploy's switch is what
    decides WHEN to write it — the last line of a transaction that undoes itself
    if it does not close (§6).
    """
    settings.save({**settings.load(), KEY: value})


# --------------------------------------------------------------- the portal ---

def portal() -> str | None:
    """Where the WebApp asks whether its authenticator is answering — or `None`.

    It is the name the environment handed over (`GATE_ENV`, §7c), and NOTHING
    when nothing handed one over. The portal is reached by the name the two
    containers share, and a WebApp running outside the environment has no such
    name — falling back to the host's loop address was tried and is worse than
    nothing: a port is a port, this machine has a Transmission answering on
    `127.0.0.1:9091`, and a WebApp that read that as its gate would serve a
    folder whose portal could be down. No answer is the CLOSED answer, and it
    costs nothing: the hosted path has no gate to ask (its `mode` is `forms`), so
    the only way to arrive here with nothing is a folder on the container path
    being served by something other than its own container — which is exactly the
    case that must close.
    """
    held = os.environ.get(GATE_ENV, "").strip()
    return f"http://{held}" if held else None


class _Unfollowed(urllib.request.HTTPRedirectHandler):
    """A redirect that stays a status.

    A probe asks WHAT answers, and a redirect followed would answer with the page
    it led to — the portal's own login screen returning 200 would read as "AT
    answered", which is the one thing the answer must not be mistaken for. So the
    302 family is read where it lands, like every other status here.
    """

    def redirect_request(self, *args: object, **kw: object) -> None:
        return None


def real(url: str, headers: dict[str, str]) -> int | None:
    """The real probe: one GET, and a status or nothing.

    The TLS carries AT's own certificate, which no machine's trust store knows
    — §3's declared price — so the probe does not verify it, and it is not a hole
    here: what is being asked is whether the provider answers at all, and a
    certificate nobody has been told about is exactly what a person clicking
    through the warning sees too. A refusal is an HTTP status (the answer), and
    everything else — no route, no name, nothing listening — is `None`.
    """
    request = urllib.request.Request(url, headers=headers, method="GET")
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(
        _Unfollowed(), urllib.request.HTTPSHandler(context=context)
    )
    try:
        with opener.open(request, timeout=PROBE) as got:
            return got.status
    except urllib.error.HTTPError as refused:
        return refused.code
    except (urllib.error.URLError, OSError, ValueError):
        return None


def ask(url: str, headers: dict[str, str], answer: Answer | None = None) -> int | None:
    """One probe, through the seam — the one way both artifacts ask."""
    return (real if answer is None else answer)(url, headers)


def standing(answer: Answer | None = None) -> bool:
    """Whether the portal answers — what a committed folder depends on (§6).

    It asks the PORTAL and not the edge, and it is asked from the WebApp, which
    is the one place that cannot ask the edge: the WebApp runs in a container on
    the environment's network, and the edge is on the host's. A WebApp with no
    portal to ask (`portal`) is not a WebApp whose gate is standing.
    """
    url = portal()
    return url is not None and ask(url, {}, answer) is not None
