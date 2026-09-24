"""The session — the entrance's own memory (§3, Forms local).

The Forms credential is proved once, at the door (`actors.authenticate`), and
what the requests after it carry is a SESSION: a token the browser holds in a
cookie and the server holds here. It belongs to the TRANSPORT and not to the
core, and that is what keeps the other two transports thin: Basic carries the
same credential and Bearer carries the machine's token, and both prove
themselves on EVERY request — so neither needs the registry. What they answer
with is the same shape, built and forgotten (`from_row`).

**The token is a secret and not a name.** `secrets` draws it and it says nothing
about who is in — the row the registry keeps beside it is the answer — so a
token copied out of a browser is a token that opens the folder while it lives,
and nothing can be read off the token itself.

**The cookie is host-only, and there is no `Domain=` in this file.** That
absence is the guard, not an omission: a page of another name that resolves to
this address (DNS rebinding) cannot carry a cookie it was never given, and the
`Origin` check the writes already do does not cover that case — it compares the
origin against `Host`, and a rebinding matches both. What stops a foreign page's
write is the `Content-Type: application/json` forcing a preflight and no
`do_OPTIONS` answering it.

**`Secure` is absent on purpose.** The hosted path is plain HTTP on loopback
(§3, Acesso e exposição), and a `Secure` cookie simply never comes back — the
door would refuse every request of the person who had just entered. It is the
Caddy of item 12 that carries the TLS, and that is where this flag belongs.
`HttpOnly` keeps the token out of the page's own scripts and `SameSite=Strict`
keeps it out of another site's requests. With no `Max-Age` the session dies with
the browser, and the server's own life bounds the rest: a restart empties the
registry, and the page shows the entrance again.

**The registry belongs to the SERVER and not to the process.** Two servers in
one process are two instances — which is what the suite builds, one per test —
and a shared registry would hand one test's session to another test's folder.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, replace

from at.core import tables
from at.data import store

COOKIE = "at_session"

# How the cookie goes and comes back. `Path=/` because every route of the page is
# a route of the session, and the two attributes are the ones the docstring
# argues. It is said once, in the one place that writes the header.
ATTRIBUTES = "Path=/; HttpOnly; SameSite=Strict"


@dataclass(frozen=True)
class Session:
    """Who is in: the token, and the row it opens for.

    The token is EMPTY for a request that proved itself with a header: there is
    no cookie to answer with and no registry entry to find, and an empty token
    is a token no request can carry back (`token_of` never answers one).
    """

    token: str
    actor: int | None  # the row's number, which item 11 resolves the role from
    name: str


def from_row(row: dict) -> Session:
    """Who is in, read off the row that proved itself — and held by nobody.

    It is the SHAPE the header transports answer with. Forms opens a session
    and keeps it (`Sessions.open`), and Basic and Bearer, which prove on every
    request, build this one and forget it when the request is over.
    """
    return Session(
        token="",
        actor=store.number_of(row),
        name=tables.title("actor", row),
    )


class Sessions:
    """The sessions one server holds, open until it stops."""

    def __init__(self) -> None:
        self._open: dict[str, Session] = {}

    def open(self, row: dict) -> Session:
        """A session for the row that just proved itself.

        The row is read here and not handed on: what a request needs afterwards
        is who is in — the number item 11 will resolve the role from and the
        name the page draws — and not the credential that proved it. The token
        is the registry's, and it is what makes this session the cookie's.
        """
        session = replace(from_row(row), token=secrets.token_urlsafe(32))
        self._open[session.token] = session
        return session

    def get(self, token: str | None) -> Session | None:
        """The session a token names, or `None`.

        A token nobody issued, a token of a session already gone and no token at
        all are the same answer, and that is the point: the door says "not
        signed in" and never which of the three it was.
        """
        if not token:
            return None
        return self._open.get(token)


def token_of(header: str | None) -> str | None:
    """The session token a `Cookie` header carries, or `None`.

    Read by hand, deliberately: `http.cookies.SimpleCookie.load` raises
    `CookieError` on headers a stranger may legitimately send (`a=b; $x=1`), and
    an exception here would take down the request's thread over a cookie this
    server does not even use. A malformed piece is skipped, and the token is
    looked for by name.
    """
    if not header:
        return None
    for piece in header.split(";"):
        name, _, value = piece.strip().partition("=")
        if name == COOKIE:
            return value.strip() or None
    return None


def cookie_header(session: Session) -> str:
    """The `Set-Cookie` of a session that was just opened.

    Written by hand for the same reason it is read by hand, and it is safe for
    one worth naming: the token is `token_urlsafe` — base64 URL-safe and nothing
    else — and NOTHING a person typed ever enters a header. The actor's name
    travels in the JSON body, where `json.dumps` escapes it.
    """
    return f"{COOKIE}={session.token}; {ATTRIBUTES}"
