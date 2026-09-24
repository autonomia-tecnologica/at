"""The VPN of the container path (§7e): the network the environment is reached on.

§7e is the optional step that changes what the environment is FOR. With no VPN
the environment is a loopback AT — everything it offers is on the machine it
runs on, and the gate in front of it guards an address nobody can reach. With
one, the same environment answers on a private network, and that is what makes
the WebApp reachable "from your phone, anywhere", which is §7e's own sentence.

**The tool is not the name of the file, and that is on purpose.** §7a decided
Podman and `podman.py` carries the brand because the section did; §7e did NOT
decide a tool — it says "here I am using Tailscale", and "Headscale support in
the future" — so what this module is about is the ROLE. The brand lives in
`BINARY` and in nothing else, and the day another agent serves it the rest of
this file does not move.

**Nothing here needs privilege, and that is measured.** The questions asked are
`ip -4` (the address this machine has on the private network) and
`status --json` (the name the network answers for it) — both answered to a plain
user on the machine this was written on, so the VPN is the one part of §7 with
no entry in §3's closed list. What AT does with the answers is CONFIGURE what
it writes for the Caddy and for the DNS: it never brings the network up, never
joins one, and never asks for a key.

**Absent is an answer and not a failure.** §7e is optional: a machine with no
agent, or one that is not up, gets `None` from both questions and the environment
stays exactly what it was — a loopback AT, which is the supported state and not
a degraded one. Whoever wants the phone configures the network; AT only says
where things are.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence

# The word on the PATH that serves the role today. It is the ONLY place the brand
# is written (the module's docstring argues why).
BINARY = "tailscale"

# How long one question waits. These are local questions — the agent is a daemon
# on this machine — and a daemon that does not answer in this long is a daemon
# that is not going to.
TIMEOUT = 10


def run(args: Sequence[str], **kw: object) -> subprocess.CompletedProcess:
    """One question to the agent — the seam, and the only one.

    The binary is resolved here and never by the caller, exactly as
    `podman.run` does it: the orchestration above asks QUESTIONS, and what
    answers them is this file's business. Output is captured, and a failure to
    run at all is the caller's to prevent (`present`) — a missing binary raises
    `FileNotFoundError` like any other `subprocess.run`.
    """
    return subprocess.run(  # noqa: S603 — the agent's own binary, named above
        [BINARY, *(str(part) for part in args)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        **kw,  # type: ignore[arg-type]
    )


# What a question is answered with: the completed call, or `None` when there was
# nobody to ask. Injected the way the environment's `ask` and the switch's
# `answer` are, and for the same reason — a test never runs the machine's agent.
Call = Callable[[Sequence[str]], subprocess.CompletedProcess | None]


def present(call: Call | None = None) -> bool:
    """Whether this machine has the agent at all.

    A question with no answer is the answer: a machine with no VPN is the
    supported, optional, entirely fine state of §7e.
    """
    answer = (call or _call)(["ip", "-4"])
    return answer is not None and answer.returncode == 0


def address(call: Call | None = None) -> str | None:
    """The IPv4 this machine has on the private network, or `None`.

    It is what the environment publishes on when it is there — the Caddy's bind
    and the DNS's answer. The FIRST line is taken and the rest ignored: an agent
    that reports several addresses reports the network's first, and an AT that
    guessed between them would be choosing a network nobody named.
    """
    answer = (call or _call)(["ip", "-4"])
    if answer is None or answer.returncode != 0:
        return None
    lines = [line.strip() for line in answer.stdout.splitlines() if line.strip()]
    return lines[0] if lines else None


def name(call: Call | None = None) -> str | None:
    """The name the private network answers for this machine, or `None`.

    It is what the Caddy is issued a certificate FOR — a certificate names a
    name, never an address (§3) — and what the person types. The agent hands it
    in `status --json`, under a TRAILING DOT that is the DNS root and not part of
    the name: `host.example-tailnet.ts.net.` is the record, and the name is what
    is typed.
    """
    answer = (call or _call)(["status", "--json"])
    if answer is None or answer.returncode != 0:
        return None
    try:
        payload = json.loads(answer.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    node = payload.get("Self")
    held = node.get("DNSName") if isinstance(node, dict) else None
    if not isinstance(held, str):
        return None
    return held.rstrip(".") or None


def _call(args: Sequence[str]) -> subprocess.CompletedProcess | None:
    """The real question, and no answer where there is nobody to ask.

    A missing binary and an agent that is there but not up are the SAME answer
    here on purpose: §7e asks whether this machine is on a private network, and
    neither of those is a machine that is.
    """
    try:
        return run(args)
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
