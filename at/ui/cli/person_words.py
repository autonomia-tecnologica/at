"""The words that talk to a person: `admin`, `lang`, `assist`."""

from __future__ import annotations

from at import i18n
from at.core import actors, assist, migrations, tables
from at.i18n import tr
from at.ui import ask as door
from at.ui.ask import OK, REFUSED, USAGE
from at.ui.cli import tree
from at.ui.cli.common import Ask
from at.ui.cli.common import readers as _readers
from at.ui.cli.common import reject as _reject


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


def _say_subcommand_words(code: str) -> None:
    """`--include-subcommands`: the subcommand words the language spells its own way.

    The table is `tree.SUBCOMMAND_WORDS`, and it holds only the spellings the
    `cli` already answers to (`ajuda`, `pedir`) — a language with none says so.
    """
    spelled = tree.SUBCOMMAND_WORDS.get(code, {})
    if not spelled:
        print(tr("cli.lang.subcommands.none", code=code))
        return
    pairs = ", ".join(f"{word} → {own}" for word, own in spelled.items())
    print(tr("cli.lang.subcommands", code=code, words=pairs))


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
    include_subcommands = "--include-subcommands" in words
    if include_subcommands:
        words.remove("--include-subcommands")
    if len(words) > 1:
        return _reject("lang")
    if not words:
        if include_folders or include_subcommands:
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
    if include_subcommands:
        _say_subcommand_words(code)
    return OK


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
