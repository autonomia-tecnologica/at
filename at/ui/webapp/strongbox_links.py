"""One-time links to the Vault's clear bytes — minted, used, gone.

**The clear never lands on disk, and the link never opens twice.** Whoever
asks to open a Vault file gets back an address, not its content — the
content only leaves when SOMEBODY navigates to that address, and only once:
`take` erases the token in the same instant it reads it, so a second attempt
with the same token — a browser retrying the request, a tab left open,
somebody who copied the URL — finds the same answer a token that never
existed would.

**And the link dies on its own if nobody ever walks it.** `TTL` is how long
it survives unused: short enough not to be a long-lived secret floating in
browser history or a proxy's log, long enough for the navigation a
confirmation triggers to actually happen. Past that, `take` answers the same
`None` a token that never existed would — the question does not tell the two
reasons apart, because the answer to whoever is asking is the same either
way: there is none.

**The registry belongs to the SERVER and not to the process**, the same
reason `session.Sessions` does: two servers in one process (the suite builds
one per test) must not share a link one minted for the other to open.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

# How many seconds a link survives unused — enough for a confirmation on
# screen and the navigation it triggers, not enough to be a long-lived
# secret anywhere.
TTL = 60.0


@dataclass(frozen=True)
class _Link:
    path: str
    expires: float


class Links:
    """The one-time links one server minted, each alive until the first
    `take` or the `TTL`, whichever comes first."""

    def __init__(self) -> None:
        self._open: dict[str, _Link] = {}

    def open(self, path: str) -> str:
        """A fresh token for `path` — the relative path `strongbox.listed`
        already recognises, never read back off this token: whoever walks it
        gets the clear, not the file's name."""
        token = secrets.token_urlsafe(32)
        self._open[token] = _Link(path, time.monotonic() + TTL)
        return token

    def take(self, token: str | None) -> str | None:
        """The path `token` names — once. An unknown token, one already
        taken and one past its `TTL` are the same answer, and none of the
        three says which of them it was."""
        if not token:
            return None
        link = self._open.pop(token, None)
        if link is None or link.expires < time.monotonic():
            return None
        return link.path
