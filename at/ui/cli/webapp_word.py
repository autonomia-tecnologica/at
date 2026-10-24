"""`at-cli webapp` — the app opened with the bundle in front."""

from __future__ import annotations

from at.ui.cli.common import reject as _reject


def _webapp(rest: list[str]) -> int:
    """`at-cli webapp` opens the app with the bundle in front; `--no-caddy` keeps it on the loop.

    The bundle is the hosted path's own gate, and it is the DEFAULT (since
    TASK-177's follow-up, 02/10/2026): the Caddy that came inside the binary
    terminates the TLS and publishes AT, fronted the same way by Authelia,
    vendorized the same way the Caddy is — no container, no isolamento
    por raio de explosão (nota `A` and not `S`, `rules.md` §3). `--no-caddy` is
    the one way out of it, back to loopback-only HTTP with nothing leaving it
    until a person authenticates (§3, Acesso e exposição) — the shape a quick
    local run wants, and the shape the test suite's own throwaway folders want.
    The container path is the other one, where the Caddy at the edge carries
    the TLS and the gate from inside its own orchestration instead (§7b, §7c).

    `--host` is the address AT answers on, and it means two different things
    with and without `--no-caddy`: with the bundle up, it is the NAME the
    certificate is issued for, which is why the one address a name cannot be is
    refused there; with `--no-caddy`, it is the loop it binds and the only
    address it accepts — anything else is refused, because exposure without TLS
    is what §3 forbids.

    `--public-port` is the ONE escape hatch for a front door this process does
    not run: something else out there — `tailscale serve`, typically — already
    terminates TLS on a port of its own and proxies here, to a LOCAL port this
    process picked to dodge that front door's OWN bind on the same port. Left
    unsaid, it is `--port` itself, which is the right answer whenever nothing
    sits in front — the standard way this very repository is checked, `at-cli
    webapp --port 12399`, included. Said, it is what Authelia's portal tells
    the browser — never the local bind, which the one in front already hid.

    The WebApp's own authenticator is up (item 10): Forms asks for the
    credential at the entrance, Basic carries the same one in an
    `Authorization` header while `settings.json` permits it, and the machine
    credential proves itself with its Bearer token. The fourth way in is the
    gate's (item 13): the identity provider asserts the name through the Caddy,
    and AT takes it only with the gate secret beside it (`core/gate.py`, §7b).
    """
    from at.ui.webapp import app as webapp

    args = rest[1:] if rest[:1] == ["run"] else rest
    port = webapp.DEFAULT_PORT
    public_port = None
    host = None
    include_caddy = True

    PORT_FLAGS = ("--port", "--porta")
    PUBLIC_PORT_FLAGS = ("--public-port", "--porta-publica")

    while args:
        flag, args = args[0], args[1:]
        if flag == "--no-caddy":
            include_caddy = False
            continue
        if flag not in (*PORT_FLAGS, *PUBLIC_PORT_FLAGS, "--host") or not args:
            return _reject("webapp")
        value, args = args[0], args[1:]
        if flag == "--host":
            if not value or value.startswith("-"):
                return _reject("webapp")
            host = value
            continue
        if not value.isdigit():
            return _reject("webapp")
        chosen = int(value)
        if not 0 < chosen < 65536:
            return _reject("webapp")
        if flag in PUBLIC_PORT_FLAGS:
            public_port = chosen
        else:
            port = chosen

    return webapp.run(port, public_port=public_port, host=host,
                      include_caddy=include_caddy)
