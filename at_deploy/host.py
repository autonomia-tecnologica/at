"""`at-deploy host up|update` (TASK-190): the hosted path's own two processes,
kept standing across a REBOOT by `systemd --user`.

**The gap this closes is exactly one.** The hosted path's Authelia already
survives a restart of `at-cli webapp` on its own — TASK-177 starts it as a
subprocess the `finally` of `webapp.run` deliberately does NOT stop, and the
next `webapp` run reuses it through `authelia.standing()` (the person's open
sessions live in it, and only the person restarts it). What an orphan
subprocess cannot survive is the MACHINE rebooting: nothing is left to bring
it, or the WebApp itself, back up. `host up` writes one `systemd --user` unit
for each of the two and enables both for real — `WantedBy=default.target`,
which is what makes a unit come back after a reboot and not just after this
shell closes.

**No vendoring happens here, and no network either.** Authelia already
travels vendorized inside this very binary (`at.services.authelia`, TASK-177)
— the same tarball `at-cli webapp --include-caddy` already unpacks into
`App/authelia/` the first time it runs. `host up` calls the exact same
`ensure()`, so a folder that already ran the bundle once has nothing left to
unpack, and one that never did gets it unpacked here instead.

**ntfy is not part of this** (TASK-187's follow-up, 2026-10-03): it left the
product the same day this slice was asked for — the notifier is the PWA's own
Web Push now (`at.core.push`), and there is no second process, vendored or
not, for this file to manage.

**The Authelia unit is the one the WebApp unit depends on, and readiness is
IN the unit, not polled from here.** `ExecStartPost` on the Authelia unit
blocks until its port answers (or a few seconds pass), and systemd keeps a
unit in `activating` for exactly as long as `ExecStartPost` runs — so
`Requires=`/`After=` on the WebApp unit is a real readiness order and not a
guess about how long a fork takes. The WebApp's own `run()` is unchanged: it
asks `authelia.standing()` as it always has, finds the systemd-started one
already listening on the port this file remembered, and never spawns a
second.

**`update` does not restart what did not change** (the same promise
`environment.update`'s own Redis exception makes, for the same reason): a
unit whose content is byte-for-byte what was already on disk, and which is
already active, is left running — restarting Authelia drops every open
session (no Redis on this path, TASK-184's own decision, never revisited
here), and a `host update` that runs because the WEBAPP's code changed must
not pay that price for a service it did not touch.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from at.core import files, paths
from at.i18n import tr
from at.services import authelia
from at.ui.webapp.app import DEFAULT_PORT, GATE_LOOPBACK_NAME

from at_deploy import environment, systemd

Ask = Callable[[str], str]

# The outcomes — the same shape the container environment answers `up` and
# `update` with (`environment.UP`, `.UPDATED`, `.PROVISIONED`, `.FAILED`).
UP = "up"
UPDATED = "updated"
PROVISIONED = "provisioned"
FAILED = "failed"
NO_SYSTEMD = "no_systemd"

# The names systemd answers by. `at-` is the same prefix every AT-owned name
# on a machine already carries (`environment.PREFIX`).
AUTHELIA_UNIT = "at-authelia.service"
WEBAPP_UNIT = "at-webapp.service"

# The default a bare `at-deploy host up` answers with — the same default
# `at-cli webapp --include-caddy` already uses with no `--host` of its own,
# read off that module and not copied, so the two can never drift apart.
DEFAULT_HOST = GATE_LOOPBACK_NAME


def unit_dir() -> Path:
    """`~/.config/systemd/user/` — the `--user` manager's own search path,
    honouring `XDG_CONFIG_HOME` the way every tool that writes there does."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "systemd" / "user"


def provisioned() -> bool:
    """Whether a previous `host up` already wrote both units."""
    where = unit_dir()
    return (where / AUTHELIA_UNIT).is_file() and (where / WEBAPP_UNIT).is_file()


def _quoted(value: str) -> str:
    """One argv entry, in the one quoting systemd's own line splitter reads
    (`systemd.service(5)`, "Command lines"): double quotes around a value
    that might carry a space, like a folder a person named with one."""
    escaped = str(value).replace('"', '\\"')
    return f'"{escaped}"'


def _authelia_unit(config: Path, port: int) -> str:
    """The unit that runs the vendored Authelia itself, config and all.

    `ExecStartPost` is the readiness gate the module docstring promises: a
    bounded poll of the LOOPBACK port this Authelia was told to listen on,
    written in `bash` because `/dev/tcp` is a `bash` built-in and not a POSIX
    `sh` one, and `bash` is the one shell this slice can assume on the Linux
    this feature is scoped to.
    """
    probe = (
        f"for i in $(seq 1 100); do "
        f"(exec 3<>/dev/tcp/127.0.0.1/{port}) 2>/dev/null && exit 0; "
        f"sleep 0.1; done; exit 1"
    )
    return (
        "[Unit]\n"
        "Description=AT - Authelia (hosted path's own gate)\n"
        "After=network-online.target\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={_quoted(str(authelia.binary()))} --config {_quoted(str(config))}\n"
        f"ExecStartPost=/bin/bash -c {_quoted(probe)}\n"
        "Restart=on-failure\n"
        "RestartSec=2\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _webapp_unit(argv: tuple[str, ...], workdir: Path) -> str:
    """The unit that runs `at-cli webapp` itself, with the gate it depends on
    ordered — and READY — before it (`Requires=`, `After=`)."""
    command = " ".join(_quoted(part) for part in argv)
    return (
        "[Unit]\n"
        "Description=AT - WebApp (hosted path)\n"
        f"After=network-online.target {AUTHELIA_UNIT}\n"
        f"Requires={AUTHELIA_UNIT}\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={_quoted(str(workdir))}\n"
        f"Environment={paths.ROOT_ENV}={_quoted(str(workdir))}\n"
        f"ExecStart={command}\n"
        "Restart=on-failure\n"
        "RestartSec=2\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _write_if_changed(name: str, content: str) -> bool:
    """Write the unit only when its content actually differs; answer whether
    it did — the one bit `_apply` needs to decide what NOT to restart."""
    where = unit_dir() / name
    try:
        current = where.read_text(encoding="utf-8")
    except FileNotFoundError:
        current = None
    if current == content:
        return False
    where.parent.mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(where, content)
    return True


def _active(name: str) -> bool:
    return systemd.ok(["is-active", "--quiet", name])


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _apply(authelia_content: str, webapp_content: str, config_changed: bool) -> str:
    """Write both units, reload only if either changed, and (re)start only
    what changed or was not already standing — never both at once, and never
    the one that did not need it (module docstring's own promise).

    **`config_changed` is `_prepare`'s, and the unit text alone cannot say
    it.** The Authelia unit's `ExecStart` names a config PATH, not its
    content — a `--host` changed between two `host update`s rewrites
    `configuration.yml`'s cookie domain while the unit file naming that same
    path stays byte-for-byte what it was, and a restart keyed on the unit
    alone would leave the old host signed into every cookie it issues next.
    """
    authelia_unit_changed = _write_if_changed(AUTHELIA_UNIT, authelia_content)
    authelia_changed = authelia_unit_changed or config_changed
    webapp_changed = _write_if_changed(WEBAPP_UNIT, webapp_content)

    if (authelia_changed or webapp_changed) and not systemd.ok(["daemon-reload"]):
        return FAILED

    if not systemd.ok(["enable", AUTHELIA_UNIT]):
        return FAILED
    if (authelia_changed or not _active(AUTHELIA_UNIT)) and not systemd.ok(
        ["restart", AUTHELIA_UNIT]
    ):
        return FAILED

    if not systemd.ok(["enable", WEBAPP_UNIT]):
        return FAILED
    if (webapp_changed or not _active(WEBAPP_UNIT)) and not systemd.ok(
        ["restart", WEBAPP_UNIT]
    ):
        return FAILED

    return UP


def _prepare(host: str, port: int, public_port: int | None) -> tuple[str, str, bool] | None:
    """Everything the two units need, assembled — or `None` without a payload.

    Authelia's config is written here with `at.services.authelia.write`, the
    exact function `at-cli webapp` itself calls on a run with no systemd
    unit in front of it — so a folder this slice provisions and a folder that
    never ran `host up` write the identical `configuration.yml`, and the one
    difference is who starts the binary that reads it. The THIRD thing it
    answers is whether that write actually changed the config or the people
    it derives `users.yml` from — read before the write and compared after,
    because `authelia.write` always rewrites both files and a timestamp is
    not content.
    """
    if authelia.ensure() is None:
        print(tr("authelia.no_payload", platform=authelia.label()))
        return None

    try:
        listen_port = int(authelia.port_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        listen_port = authelia.free_port()

    config_path = authelia.directory() / authelia.CONFIG
    users_path = authelia.directory() / authelia.USERS
    before = (_read(config_path), _read(users_path))

    public = public_port if public_port is not None else port
    config = authelia.write(host, listen_port, public)
    authelia.remember(listen_port)

    after = (_read(config_path), _read(users_path))
    config_changed = before != after

    workdir = paths.working_folder()
    argv = (environment.binary(), "webapp", "--host", host, "--port", str(port))
    if public_port is not None:
        argv += ("--public-port", str(public_port))

    return _authelia_unit(config, listen_port), _webapp_unit(argv, workdir), config_changed


def host_up(host: str | None = None, port: int = DEFAULT_PORT,
            public_port: int | None = None) -> str:
    """`host up` — the FIRST time: write and enable the two units."""
    if not systemd.present():
        print(tr("services.host.no_systemd"))
        return NO_SYSTEMD
    if provisioned():
        print(tr("services.host.up.provisioned"))
        return PROVISIONED
    prepared = _prepare(host or DEFAULT_HOST, port, public_port)
    if prepared is None:
        return FAILED
    return _apply(*prepared)


def host_update(host: str | None = None, port: int = DEFAULT_PORT,
                 public_port: int | None = None) -> str:
    """`host update` — every time after: reapply what changed, touch nothing
    that did not (module docstring)."""
    if not systemd.present():
        print(tr("services.host.no_systemd"))
        return NO_SYSTEMD
    if not provisioned():
        print(tr("services.host.update.unprovisioned"))
        return FAILED
    prepared = _prepare(host or DEFAULT_HOST, port, public_port)
    if prepared is None:
        return FAILED
    outcome = _apply(*prepared)
    if outcome == UP:
        print(tr("services.host.update.done"))
        return UPDATED
    return outcome
