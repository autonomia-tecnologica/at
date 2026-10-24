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

from at import __version__, convert, i18n
from at.core import (
    actors,
    assist,
    audit,
    backup,
    boot,
    files,
    install,
    jobs,
    licenses,
    migrations,
    paths,
    permissions,
    secrets,
    tables,
)
from at.data import schema
from at.i18n import tr
from at.prose import listing as prose
from at.ui import ask as door
from at.ui.ask import OK, REFUSED, USAGE
from at.ui.cli import jsonout, tree

# What a person answers with, injected so a test can answer without a terminal —
# the same shape `boot.ensure_working_folder` takes.
Ask = Callable[[str], str]


def main(argv: Sequence[str] | None = None) -> int:
    """The process's whole life. Returns the exit code; `__main__` raises it."""
    words = list(sys.argv[1:] if argv is None else argv)
    if jsonout.FLAG in words:
        # `--json` is global: it swaps what is PRINTED, in any position, and
        # nothing about what runs (`jsonout`).
        return jsonout.run([w for w in words if w != jsonout.FLAG], _dispatch)
    return _dispatch(words)


def _dispatch(words: list[str]) -> int:
    # `install` and `uninstall` run BEFORE the Working Folder is confirmed, and
    # they are the only words that do. Every other word is ABOUT the folder —
    # what it holds, how it is spoken — and the folder belongs to the binary, so
    # no word could run before the folder is AT's. These two are about the FILE
    # and where it is found, and the folder is only where the file happens to
    # be: confirming one, or worse, creating one so the install has somewhere to
    # write, is exactly what §3's first run asks before and never assumes.
    if words[:1] in (["install"], ["uninstall"]):
        return _installed(words[0], words[1:])

    if not words:
        # The Control Panel is a screen for whoever does not type commands
        # (§5) — and it is this one now (TASK-169, fatia 1/3): the wordless
        # command opens the browser on the app itself, on a port nobody
        # types and behind a token nobody but that browser ever saw.
        # Managing AT stays in the `cli`, where a person and a machine reach
        # the same door — `help` still prints the tree this used to.
        #
        # **And it runs BEFORE `ensure_working_folder`, on purpose** (TASK-169,
        # fatia 2/3): that gate asks in the TERMINAL, and the wordless command
        # is exactly the one with none to ask in. A folder that does not exist
        # yet is not refused here — the browser asks instead, the same
        # question, on the one screen this mode has (`webapp.entry_payload`'s
        # `folder`, `/api/folder`).
        from at.ui.webapp import local

        return local.run()

    if not boot.ensure_working_folder():
        return REFUSED

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
        jsonout.attach("version", __version__)
        # A completion written for zsh is not on its `fpath` until the person's
        # `.zshrc` puts it there — `install` said it once, and there is no
        # terminal-free way to know it was read, let alone acted on. `version`
        # is asked often enough to carry the reminder until the inherited
        # `$FPATH` says it was (`install.fpath_needed`'s own heuristic).
        folder = install.fpath_needed(paths.ARTIFACT)
        if folder is not None:
            print(tr("install.completion.fpath", folder=folder))
        return OK

    if word == "license":
        return _license(rest)

    if word == "webapp":
        return _webapp(rest)

    if word == "backup":
        return _backup(rest)

    if word == "convert":
        return _convert(rest)

    if word == "admin":
        return _admin(rest)

    if word == "lang":
        return _lang(rest)

    if word == "assist":
        return _assist(rest)

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


# ----------------------------------------------------------------- the backup ---

def _backup(rest: list[str], secret: Ask | None = None) -> int:
    """`at-cli backup make|restore` — the copy that survives the machine (item 51).

    The Main Key is read WITHOUT ECHO, the same way `admin`'s credential
    is — it does not travel through the command line, so it never lands in
    the shell's history nor anybody's `ps`. It is read LAZILY: `core.backup`
    calls the reader itself, once its own cheap checks already passed, so a
    destination with no tool to reach it or a folder `restore` refuses never
    gets as far as asking a person to type it.
    """
    if len(rest) != 2:
        return _reject("backup")
    action, target = rest[0], rest[1]
    if action not in (backup.MAKE, backup.RESTORE):
        return _reject("backup")
    if secret is None:
        secret = _readers()[1]
    if secret is None:
        print(tr("backup.no_tty"))
        return REFUSED

    def phrase() -> str:
        return secret(tr("backup.phrase"))

    try:
        outcome = backup.make(phrase, target) if action == backup.MAKE \
            else backup.restore(phrase, target)
    except secrets.SecretsError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    except OSError as error:
        print(tr("backup.error.io", reason=str(error)))
        return REFUSED

    # The wording lives in the door (`ask.backup_message`) because the clock's
    # own round reads it too — the terminal line and the phone's notice are the
    # same fact and must not be two sentences.
    print(door.backup_message(action, outcome, target))
    return OK if outcome.state in (backup.MADE, backup.RESTORED) else REFUSED


# --------------------------------------------------------------- the convert ---

def _convert(rest: list[str]) -> int:
    """`at-cli convert <arquivo> --to pdf|docx` (TASK-165, fatia 2/4).

    `<arquivo>` is read the way `Arquivos/` is always addressed — a path
    relative to it, resolved and validated by `prose.inside`/`prose.read`, the
    same door the WebApp's own file route reads through: a path outside the
    tree or a file that is not text is refused with the SAME sentence the page
    already shows for it, and not a second one invented here.
    """
    if len(rest) != 3 or rest[1] != "--to":
        return _reject("convert")
    rel, _, fmt = rest
    if fmt not in convert.FORMATS:
        return _reject("convert")
    info = prose.read(rel)
    if info is None:
        print(tr("prose.not_served"))
        return REFUSED
    # A conversion is of TEXT — a PDF, an image or a video opens in the page
    # (`open`), and none of them is a markdown to convert.
    if info["open"] != "text":
        print(tr(info["reason"] or "prose.not_supported"))
        return REFUSED
    where = prose.inside(rel)
    assert where is not None  # `prose.read` above already served this path
    try:
        target = convert.convert(where, fmt)
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    print(tr("convert.done", path=target.name))
    return OK


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
    "forgot the password" in a folder on your own disk — and the person is told
    that where they read it, before typing it the second time: a rule the person
    meets only in the refusal is a rule they learn by paying for it.

    **The price comes BEFORE the reader, and it is the sentence the refusal
    would say.** `admin.error.short` is the one string that says what the Main
    Key costs — 16 characters, and it is a phrase —, and this door prints it
    once, before the first read, instead of holding a second sentence that could
    drift from the rule the engine enforces (`actors.check_credential`). The
    number is NOT written here either: it is `actors.MIN_CREDENTIAL`, which is
    the vault's own floor (§4, item 176) — whoever asks does not decide the
    rule, and does not spell it again.

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
        # The price, before the person types: the same sentence the refusal
        # uses, and the floor out of the engine — never a 16 spelled here.
        print(tr("admin.error.short", min=actors.MIN_CREDENTIAL))
        credential = secret(tr("admin.credential"))
        # Why twice, said before the second read: the string is not recovered,
        # and a typo would cost exactly what it sealed.
        print(tr("admin.credential.twice"))
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


# -------------------------------------------------------------- the assist ---

def _assist(rest: list[str], secret: Ask | None = None) -> int:
    """`at-cli assist "<frase>"` — what Jev would propose, without running
    it (TASK-180, fatia 2/3).

    The sentence is ONE argument, the same rule `ask` already holds to: a
    phrase the shell split in two is two phrases.

    The Main Key is read WITHOUT ECHO, the same way `backup` and `admin`
    already read theirs: it does not travel through the command line, so it
    never lands in the shell's history nor anybody's `ps`. It is read lazily
    — only once the cheap check already passed — so a folder with the switch
    off never gets as far as asking a person to type it.
    """
    if len(rest) != 1:
        return _reject("assist")
    if not assist.enabled():
        print(tr("assist.preview.off"))
        return REFUSED
    if secret is None:
        secret = _readers()[1]
    if secret is None:
        print(tr("assist.preview.no_tty"))
        return REFUSED
    main_key = secret(tr("assist.preview.phrase"))
    code, answer = door.assist_preview(rest[0], main_key=main_key)
    print(answer)
    return code


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
    """`at-cli job list|view|run|approve|refuse|declare|disable` — the demand
    that waits, and the round the clock drives on its own (§4, item 24).

    The seven words are the object's OWN, read from the catalogue the way a
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

# The acts that are a TABLE's own — read the folder or the store and write no
# row, so none of them walks `run` and none of them is one of `tables.ACTIONS`.
# `secret scan` is the one item 51 gave; `secret install_hooks` is its own
# second act, writing two files and no row either; `reminder due` is item 29's
# first slice. A fourth one is a fourth entry, not a fourth `if`.
_OWN_ACTS: dict[tuple[str, str], Callable[[list[str]], tuple[int, str]]] = {
    (permissions.SECRET, permissions.SCAN): door.scan,
    (permissions.SECRET, permissions.INSTALL_HOOKS): door.install_hooks,
    (permissions.REMINDER, permissions.DUE): door.reminder_due,
}


def _table(table: str, rest: list[str]) -> int:
    action = rest[0] if rest else "list"
    args = rest[1:] if rest else []
    if action not in tables.ACTIONS:
        # An act the engine does not have is the object's OWN, and it does not
        # walk `run`: `secret scan` reads the folder and writes nothing, so it
        # records no line and versions nothing. `_OWN_ACTS` is the closed list of
        # them, held to the same names `permissions.actions` answers with.
        #
        # The engine's own words keep dispatching exactly as they always did,
        # including the ones a narrowed table does not answer: `audit delete`
        # reaches the engine and is refused by it, and the attempt is a line
        # (§3). A word the table does not answer is a refusal to RECORD, and a
        # dispatch that turned it into a usage error would be a wall with no
        # trail behind it.
        own = _OWN_ACTS.get((table, action))
        if own is None:
            print(tr("table.error.unknown_action", action=action))
            return USAGE
        code, answer = own(args)
        print(answer)
        return code
    jsonout.attach("table", table)
    try:
        # The actor of an act typed here is the first admin, and the via is the
        # terminal's: what the door records is WHO and HOW, and the `cli` is the
        # one surface where both are facts of the folder rather than of a request
        # (§3, item 15).
        code, answer, row, _, _ = door.run(
            table, action, args, actor=actors.first_admin(), via=audit.CLI
        )
        jsonout.attach("row", row)
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
