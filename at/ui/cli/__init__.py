"""The command line: the surface that reaches everything AT can do (§5).

Dispatch is deliberately small and hand-rolled. A framework would put the word
list in a decorator, and the word list has one home already — `tree.py`, which
the help reads too. The table words are not here either: they are generated from
`data/schema/`, every invocation.

Exit codes: `0` success · `1` refused or failed · `2` usage error.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from at import __version__, i18n
from at.core import actors, boot, files, migrations, tables
from at.data import schema
from at.i18n import tr
from at.ui import ask as door
from at.ui.ask import OK, REFUSED, USAGE
from at.ui.cli import tree

# What a person answers with, injected so a test can answer without a terminal —
# the same shape `boot.ensure_working_folder` takes.
Ask = Callable[[str], str]


def main(argv: Sequence[str] | None = None) -> int:
    """The process's whole life. Returns the exit code; `__main__` raises it."""
    words = list(sys.argv[1:] if argv is None else argv)

    # Every invocation confirms the Working Folder first — including `help` and
    # `--version`. The folder belongs to the binary, not to the word, so there
    # is no word that could run before the folder is AT's.
    if not boot.ensure_working_folder():
        return REFUSED

    if not words:
        # The Control Panel is a screen for whoever does not type commands, and
        # it is not built yet: the wordless command answers with the help, which
        # is the shape §5 already declares for it. Managing AT stays in the
        # `cli`, where a person and a machine reach the same door.
        print(tree.as_text())
        return OK

    word, rest = words[0], words[1:]

    if word in ("help", "--help", "-h"):
        if rest:
            return _reject(word)
        print(tree.as_text())
        return OK

    if word in ("version", "--version", "-V"):
        if rest:
            return _reject(word)
        print(tr("cli.version.line", version=__version__))
        return OK

    if word == "webapp":
        return _webapp(rest)

    if word == "admin":
        return _admin(rest)

    if word == "lang":
        return _lang(rest)

    # The interpreter's word is read off the tree, so a switch that turns it off
    # takes it out of the dispatch and out of the help in the same breath.
    if word in tree.ask_words():
        return _ask(rest)

    if schema.of(word) is not None:
        return _table(word, rest)

    print(tr("cli.error.unknown_word", word=word))
    print(tr("cli.error.usage"))
    return USAGE


def _webapp(rest: list[str]) -> int:
    """`at webapp` opens the app, and `--include-caddy` exposes it.

    This is the hosted path: loopback, in HTTP, and nothing leaves it until a
    person authenticates (§3, Acesso e exposição). The flag is the exception the
    same rule makes — the Caddy that came inside the binary terminates the TLS
    and publishes AT, and the WebApp keeps listening on the loop behind it
    (§6, §12). The container is the other path, where the Caddy at the edge
    carries the TLS and the gate (§7b, §7c).

    `--host` is the address AT answers on, and it means two different things
    with and without the flag: without it, the loop it binds and the only
    address it accepts — anything else is refused, because exposure without TLS
    is what §3 forbids. With it, the NAME the certificate is issued for, which
    is why the one address a name cannot be is refused there.

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
    host = None
    include_caddy = False

    while args:
        flag, args = args[0], args[1:]
        if flag == "--include-caddy":
            include_caddy = True
            continue
        if flag not in ("--port", "--porta", "--host") or not args:
            return _reject("webapp")
        value, args = args[0], args[1:]
        if flag == "--host":
            if not value or value.startswith("-"):
                return _reject("webapp")
            host = value
            continue
        if not value.isdigit():
            return _reject("webapp")
        port = int(value)
        if not 0 < port < 65536:
            return _reject("webapp")

    return webapp.run(port, host=host, include_caddy=include_caddy)


# ------------------------------------------------------------ the first admin ---

def _admin(
    rest: list[str],
    ask: Ask | None = None,
    secret: Ask | None = None,
) -> int:
    """`at admin` — the first administrator, asked for and never seeded.

    The credential is read WITHOUT ECHO (`getpass`): it does not travel through
    the command line, so it stays out of the shell's history and out of anybody's
    `ps`. It is read twice because a credential is not recovered — there is no
    "forgot the password" in a folder on your own disk.

    The two readers are injectable, the way `boot.ensure_working_folder` takes
    its `ask`: a test covers both the refusal without a terminal and the whole
    conversation without one.
    """
    if rest:
        return _reject("admin")
    if ask is None and secret is None:
        ask, secret = _readers()
    if ask is None or secret is None:
        # The same refusal the first run makes (`boot`): a credential typed
        # where nobody could answer is not a credential.
        print(tr("admin.no_tty"))
        return REFUSED

    try:
        existing = actors.admins()
        if existing:
            raise actors.AdminError(
                "exists", name=tables.title("actor", existing[0])
            )
        name = ask(tr("admin.name")).strip()
        credential = secret(tr("admin.credential"))
        if credential != secret(tr("admin.credential.again")):
            raise actors.AdminError("error.mismatch")
        row = actors.create_admin(name, credential)
    except (actors.AdminError, tables.TableError) as refused:
        print(refused)
        return REFUSED

    print(tr("admin.created", name=tables.title("actor", row)))
    return OK


def _readers() -> tuple[Ask | None, Ask | None]:
    """A line reader and a no-echo reader, when there is a terminal to use."""
    if not sys.stdin.isatty():
        return None, None
    import getpass

    return (lambda question: input(question), getpass.getpass)


# ------------------------------------------------------------ the language ---

def _lang(rest: list[str], ask: Ask | None = None) -> int:
    """`at lang` — the language AT speaks, and the choice of it.

    With no argument it SHOWS the active code and where it came from, which the
    resolution already knows (`i18n.active_origin`): a person who sees the wrong
    language reads why it is that one before choosing another.

    With a code it CHOOSES: the file the folder keeps is written, and every
    surface answers in it from then on — this process at once, the WebApp on the
    next request — because neither the `cli` nor the server holds a language of
    its own. The folders are offered the rename in the SAME run, and the reason
    is that this is the one place the question can be asked: it needs a
    terminal, and whoever just chose the language is sitting in front of one.

    **`--include-app-folders` answers that question before it is asked**: the
    rename runs in this same run with nobody to ask, which is what makes the
    command usable where there is no terminal. It decorates a CHOICE — the flag
    without a code is a usage error, because there is no language for the folders
    to take the names of.

    The `ask` is injectable the way `boot.ensure_working_folder` takes its own,
    so a test covers the offer without a terminal.
    """
    words = list(rest)
    include_folders = "--include-app-folders" in words
    if include_folders:
        words.remove("--include-app-folders")
    if len(words) > 1:
        return _reject("lang")
    if not words:
        if include_folders:
            return _reject("lang")
        print(tr(
            "cli.lang.line",
            code=i18n.active_code(),
            origin=tr(f"cli.lang.origin.{i18n.active_origin()}"),
        ))
        return OK

    code = words[0]
    if code not in i18n.SUPPORTED:
        # Refused, never ignored: a code nobody speaks would otherwise write the
        # file and change nothing, which is the answer that teaches nobody.
        print(tr("cli.lang.error.unsupported", code=code, codes=", ".join(i18n.SUPPORTED)))
        return USAGE

    i18n.write_active(code)
    print(tr("cli.lang.chosen", code=code))
    migrations.offer_language(ask if ask is not None else _readers()[0],
                             include_folders=include_folders)
    return OK


# ---------------------------------------------------------- the interpreter ---

def _ask(rest: list[str]) -> int:
    """`at ask "..."` — one sentence becomes one proposal, and runs.

    The sentence is ONE argument: it is a phrase, and a phrase the shell split in
    two is two phrases. `pedir` is the same door, and `ask pedir` is that door
    written out — the spelling the derived document carries.

    The door itself is `at.ui.ask`, which the WebApp's box reads too: what a
    person reads, in order, is the proposal and then the answer — the proposal so
    the reading can be checked, and the answer in the ENGINE's own words, because
    the engine is the one that validated and wrote. This surface invents no
    second sentence for either.
    """
    args = rest[1:] if rest[:1] == ["pedir"] else rest
    if len(args) != 1:
        return _reject("ask")
    result = door.ask(args[0])
    # A question and a refusal have no proposal to check — nothing was proposed
    # and nothing was written — and they are the one sentence the result carries.
    if result.proposal:
        print(result.proposal)
    print(result.text)
    return result.code


# --------------------------------------------------------------- tables ---

def _table(table: str, rest: list[str]) -> int:
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in tables.ACTIONS:
        print(tr("table.error.unknown_action", action=action))
        return USAGE
    try:
        code, answer = door.run(table, action, args)
    except tables.TableError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    print(answer)
    return code


# ----------------------------------------------------------------- args ---

def _reject(word: str) -> int:
    print(door.rejected(word))
    return USAGE
