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
from at.core import (
    actors,
    audit,
    boot,
    files,
    install,
    jobs,
    licenses,
    migrations,
    paths,
    permissions,
    tables,
)
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

    # `install` and `uninstall` run BEFORE the Working Folder is confirmed, and
    # they are the only words that do. Every other word is ABOUT the folder —
    # what it holds, how it is spoken — and the folder belongs to the binary, so
    # no word could run before the folder is AT's. These two are about the FILE
    # and where it is found, and the folder is only where the file happens to
    # be: confirming one, or worse, creating one so the install has somewhere to
    # write, is exactly what §3's first run asks before and never assumes.
    if words[:1] in (["install"], ["uninstall"]):
        return _installed(words[0], words[1:])

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

    if word == "license":
        return _license(rest)

    if word == "webapp":
        return _webapp(rest)

    if word == "admin":
        return _admin(rest)

    if word == "lang":
        return _lang(rest)

    if word == permissions.SETTING:
        return _setting(rest)

    # The interpreter's word is read off the tree, so a switch that turns it off
    # takes it out of the dispatch and out of the help in the same breath.
    if word in tree.ask_words():
        return _ask(rest)

    # The job's acts are not the engine's six, so the word does NOT walk the
    # table dispatch: `run`, `approve` and `refuse` are the object's own, and the
    # door that takes them is the one above (`door.job`). It reads its actions
    # from the catalogue, so the help and the dispatch still offer one list.
    if word == jobs.JOB:
        return _job(rest)

    if schema.of(word) is not None:
        return _table(word, rest)

    print(tr("cli.error.unknown_word", word=word))
    print(tr("cli.error.usage"))
    return USAGE


def _webapp(rest: list[str]) -> int:
    """`at-cli webapp` opens the app, and `--include-caddy` exposes it.

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


# ---------------------------------------------------------------- the licence ---

def _license(rest: list[str], texts: bool = False) -> int:
    """`at-cli license` — what this artifact carries from outside, and its terms.

    The word is the notices' only door: the artifact is ONE file, so there is no
    folder beside it for a third party's licence to sit in, and what the licence
    demands has to come out of the artifact itself. What comes out by default is
    the summary — what the AT is licensed as, and one line per component —,
    because the vendors' texts are tens of kilobytes of legalese and nobody
    asking what the binary carries is asking to read them; `--include-texts` is
    how whoever needs them reaches them, and the help says the flag, like every
    other flag of the product.

    Nothing here is about the Working Folder, so there is no permission and no
    folder to read: the same place `version` and `help` answer from.
    """
    for flag in rest:
        if flag == "--include-texts":
            texts = True
            continue
        return _reject("license")
    print(licenses.report(paths.ARTIFACT, texts=texts))
    return OK


# ------------------------------------------------------------ the first admin ---

def _admin(
    rest: list[str],
    ask: Ask | None = None,
    secret: Ask | None = None,
) -> int:
    """`at-cli admin` — the first administrator, asked for and never seeded.

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
    """`at-cli lang` — the language AT speaks, and the choice of it.

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


# -------------------------------------------------------------- the install ---

def _installed(word: str, rest: list[str]) -> int:
    """`at-cli install` and `at-cli uninstall` — the file, where commands are found.

    What the word takes is `--bin <directory>`, and that is the whole of it:
    the artifact is not fetched and not copied, and a new one arrives by the
    file in the folder being replaced, which the link follows (§3).

    Both artifacts answer through the same core (`core/install.py`), because
    where a command is found is one rule and not one per artifact — and the two
    are two installs all the same: neither installs the other, which is the
    same cut §3 makes between `at-cli` and `at-deploy`.

    A `uninstall` that found nothing to take back is not a failure: what the
    person asked for is the state, and the state is already it.
    """
    flag, ok = install.parse(rest)
    if not ok:
        return _reject(word)
    try:
        if word == "install":
            outcome = install.act(paths.ARTIFACT, paths.artifact_file(),
                                  tree.completion(), bin_flag=flag)
            return OK if outcome in (install.DONE, install.ALREADY) else REFUSED
        outcome = install.undo(paths.ARTIFACT, paths.artifact_file(), bin_flag=flag)
        return OK if outcome in (install.REMOVED, install.NOTHING) else REFUSED
    except files.ReadOnly as error:
        # The link and the record are both writes, and the read-only switch is
        # the one writer's rule — the same answer every engine gives (§3).
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED


# --------------------------------------------------------------- settings ---

def _setting(rest: list[str]) -> int:
    """`at-cli setting list|view|edit` — the settings through the core (§4).

    §5 says the `cli` reaches everything, and the settings are reachable by one
    road only: the three words are the object's own actions, read from the
    catalogue the way a table's are, and the door is `at.ui.ask.setting`, which
    owns the line and the version. The actor of an act typed here is the first
    admin and the via is the terminal's — the same pair every other word of this
    surface records, and a fact of the folder rather than of a request (§3).

    The action list is `permissions.actions` and not a tuple written here: the
    word the help offers and the word the dispatch accepts are the same list,
    which is what keeps a spelling from dispatching without being offered.
    """
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in permissions.actions(permissions.SETTING):
        print(tr("table.error.unknown_action", action=action))
        return USAGE
    code, answer = door.setting(action, args, actor=actors.first_admin(), via=audit.CLI)
    print(answer)
    return code


# ---------------------------------------------------------- the interpreter ---

def _ask(rest: list[str]) -> int:
    """`at-cli ask "..."` — one sentence becomes one proposal, and runs.

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
    # The ACTOR of an act typed at the terminal is the first admin (§3, item 15):
    # the `cli` is local by construction and whoever is in front of it is the
    # folder's owner. A folder that never made one asks with nobody, which is
    # what it always did.
    result = door.ask(args[0], actor=actors.first_admin())
    # A question and a refusal have no proposal to check — nothing was proposed
    # and nothing was written — and they are the one sentence the result carries.
    if result.proposal:
        print(result.proposal)
    print(result.text)
    return result.code


# ------------------------------------------------------------------ the job ---

def _job(rest: list[str]) -> int:
    """`at-cli job list|view|run|approve|refuse` — the demand that waits (§4).

    The five words are the object's OWN, read from the catalogue the way a
    table's actions are (`permissions.actions`) and not written here, so a word
    the help offers is a word the dispatch accepts and the other way round. What
    they answer is `at.ui.ask.job`, which is the door: the line, the version and
    the ceiling all live there, and this surface only chooses WHERE the words go.

    The actor is the first admin and the via is the terminal's, the same pair
    every other word of this surface records: the `cli` is local by construction,
    and whoever is in front of it is the folder's owner (§3). The approval is
    therefore typed by a person — which is the whole of what it means.
    """
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in permissions.actions(jobs.JOB):
        print(tr("table.error.unknown_action", action=action))
        return USAGE
    try:
        # The door answers its own refusals (a state the act does not answer, a
        # machine trying the approval) as text and a code, like `setting` does;
        # what reaches here is the engine's, raised while the job RUNS.
        code, answer = door.job(
            action, args, actor=actors.first_admin(), via=audit.CLI
        )
    except tables.TableError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    print(answer)
    return code


# --------------------------------------------------------------- tables ---

def _table(table: str, rest: list[str]) -> int:
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in tables.ACTIONS:
        # An act the engine does not have is the object's OWN, and it does not
        # walk `run`: `secret scan` reads the folder and writes nothing, so it
        # records no line and versions nothing. It is the one such act a table
        # declares today, and the catalogue (`permissions.actions`) is the closed
        # list that says so.
        #
        # The engine's own words keep dispatching exactly as they always did,
        # including the ones a narrowed table does not answer: `audit delete`
        # reaches the engine and is refused by it, and the attempt is a line
        # (§3). A word the table does not answer is a refusal to RECORD, and a
        # dispatch that turned it into a usage error would be a wall with no
        # trail behind it.
        if table != permissions.SECRET or action != permissions.SCAN:
            print(tr("table.error.unknown_action", action=action))
            return USAGE
        code, answer = door.scan(args)
        print(answer)
        return code
    try:
        # The actor of an act typed here is the first admin, and the via is the
        # terminal's: what the door records is WHO and HOW, and the `cli` is the
        # one surface where both are facts of the folder rather than of a request
        # (§3, item 15).
        code, answer, _ = door.run(
            table, action, args, actor=actors.first_admin(), via=audit.CLI
        )
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
