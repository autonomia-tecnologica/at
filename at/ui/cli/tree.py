"""The word tree — the single declaration every surface reads.

Help and dispatch both read this, so a word can never dispatch without being
offered, nor the other way round. A word is declared here once and named nowhere
else.

`about` is an **i18n key**, never the text: the word is the machine's, the
sentence is the person's. The table words are not written here at all — they come
from `data/schema/`, which is what makes a table a table (§4). Add a
declaration and the word appears, with its actions, in the help and in the
dispatch at once. The SETTINGS are the exception, and it is what the exception
proves: they are an object of the catalogue and not a table, so the word is
declared here (`SETTING`) and the actions it answers are still read from the
catalogue, never listed twice.

The SHAPE of the help — the node, the column, the block — is `at/ui/words.py`,
shared with the deploy's tree, which is the other command line of the same
product (item 27).
"""

from __future__ import annotations

from at import __version__, nlu
from at.core import permissions
from at.data import schema
from at.i18n import tr
from at.ui.words import Node, completion_words, scoped, section, width

# The settings' word. The object is NOT a table — there is no schema to generate
# the word from — so it is declared here, beside `lang` and `admin`, which are
# the other words about the folder itself. What it ANSWERS is not written here:
# `list`, `view` and `edit` are read off the catalogue (`permissions.actions`),
# which is where an object that is not a table declares its narrowing, so the
# help and the dispatch offer the same three words the door takes.
SETTING = Node(
    permissions.SETTING,
    "setting.about",
    tuple(
        Node(action, permissions.action_key(action))
        for action in permissions.actions(permissions.SETTING)
    ),
)

WORDS: tuple[Node, ...] = (
    Node("webapp", "cli.webapp.about", (Node("run", "cli.webapp.run.about"),)),
    # The copy that survives the machine (item 51). It is about the FOLDER and
    # not a table, so it is declared here like `webapp` and `admin` are, and
    # not read off `data/schema/` — there is no row behind either of its acts.
    Node("backup", "cli.backup.about", (
        Node("make", "cli.backup.make.about"),
        Node("restore", "cli.backup.restore.about"),
    )),
    # Markdown to DOCX/PDF, into `Convertidos/` (TASK-165). No sub-word: the
    # format travels as `--to`, the same shape `webapp --port` already takes.
    Node("convert", "cli.convert.about"),
    # The `services` word is NOT here, and its absence is the artifact boundary:
    # the environment of §7 left this binary whole and became `at-deploy`
    # (item 27), whose own tree carries it. `at-cli` keeps the folder and the app.
    # The live search over the files and the searchable fields (B-21): reads,
    # writes nothing. The term travels as the one argument.
    Node("search", "cli.search.about"),
    Node("admin", "cli.admin.about"),
    Node("lang", "cli.lang.about"),
    # The dry run of the slang layer (TASK-180, fatia 2/3): what Jev would
    # propose for a phrase, never applied. No child of its own — a child
    # named `ask` would be the very word `ASK` below already is, and the
    # help's `·` line would show two doors under one spelling. Its own switch
    # (`assist.SWITCH`) is a setting, not a condition on this word — unlike
    # `ASK`, which the INTERPRETER's switch does take out of the tree.
    Node("assist", "cli.assist.about"),
    SETTING,
    # The pair that puts the file where commands are found (§3, item 28). They
    # are words like the others here and unlike the others in `cli/main`, which
    # runs them BEFORE the Working Folder is confirmed: what they are about is
    # the file and where it sits, not the folder.
    Node("install", "cli.install.about"),
    Node("uninstall", "cli.uninstall.about"),
    # The last two are about the FILE, like `install` above and unlike everything
    # else here: `version` says which build this is, and `license` says what that
    # build carries from outside and under which terms (§3, item 27). Neither is
    # about the folder, so neither asks a permission — and `license` is the only
    # door the notices have out of a single-file artifact (`at/core/licenses.py`).
    Node("license", "cli.license.about"),
    Node("help", "cli.help.about"),
    Node("version", "cli.version.about"),
)

# The interpreter's word, and the other spelling that answers to it: `ask` is
# the machine's, `pedir` is the one the derived document writes, and they are
# one door — the same way `webapp` answers to `run`.
ASK = Node("ask", "cli.ask.about", (Node("pedir", "cli.ask.pedir.about"),))

# The subcommand words a language spells its own way (`at-cli lang <code>
# --include-subcommands`). Only the spellings the `cli` already answers to are
# here: `ajuda` is `help`, `pedir` is `ask`. `en_US` is the canonical spelling
# and carries none.
SUBCOMMAND_WORDS: dict[str, dict[str, str]] = {
    "pt_BR": {"help": "ajuda", "ask": "pedir"},
    "en_US": {},
}

# The four words that are the artifact's OWN INTERFACE, and not an act on the
# Working Folder — so none of them has a permission to carry (TASK-186, fatia
# 1/4, `help` carved out of it in fatia 3/4 — the person's own call, below).
# Each reason is the code's own, not one invented for this list:
#
# - `install`/`uninstall` run BEFORE the folder is even confirmed (`cli`'s
#   `main`: "the only words that do"), so there is no actor and no role yet to
#   hold a ceiling for them to answer to.
# - `license`'s own docstring says it plainly: "Nothing here is about the
#   Working Folder, so there is no permission and no folder to read: the same
#   place `version` and `help` answer from."
# - `version` prints what the binary is, reading nothing the folder owns.
NAMED_EXCEPTIONS = ("version", "license", "install", "uninstall")

# Every other non-table word's permissions live in `permissions.WORD_PERMISSIONS`
# (the audit in `core` reads them, and `core` cannot import the CLI); re-exported
# here because the words and their permissions are read together.
WORD_PERMISSIONS = permissions.WORD_PERMISSIONS


def words() -> tuple[Node, ...]:
    """The words that are not a table.

    The interpreter's is here while its switch is on, and gone the moment it is
    off: help and dispatch both read this one list, so the word leaves both at
    once — which is what the item means by turning it off taking the word out of
    the tree, and taking nothing else.
    """
    return ((ASK,) if nlu.enabled() else ()) + WORDS


def ask_words() -> tuple[str, ...]:
    """Every word that reaches the interpreter — and nothing at all when it is
    off, so a spelling can never dispatch without the help offering it."""
    if not nlu.enabled():
        return ()
    return (ASK.name, *(child.name for child in ASK.children))


def table_nodes() -> tuple[Node, ...]:
    """One root per declared table, each carrying the actions it answers.

    The action list is read through the catalogue (`permissions.actions`) and not
    copied here: a word that dispatches is a word the help offers, and a table
    that narrows itself — one that answers `read` and `edit` and not the six —
    offers the narrowed list in the help and in the dispatch at once, from the
    one declaration. The KEY of each action is `permissions.action_key` for the
    same reason: the engine's six are named by the engine's block, and the acts
    an object declares of its own — the `job`'s run and its two answers — by the
    catalogue's.
    """
    return tuple(
        Node(
            str(declared["id"]),
            schema.name_key(str(declared["id"]), many=True) or str(declared["id"]),
            tuple(
                Node(action, permissions.action_key(action))
                for action in permissions.actions(str(declared["id"]))
            ),
        )
        for declared in schema.declared()
    )


def roots() -> tuple[Node, ...]:
    return words() + table_nodes()


def find(name: str) -> Node | None:
    return next((node for node in roots() if node.name == name), None)


def completion() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Every word the completion offers — which is every word the help does."""
    return completion_words(roots())


def scoped_text(word: str) -> str | None:
    """The help of one word: only the words under it, in the top help's shape.

    `None` when the word has no subtree to show (a word that takes an argument
    — `search`, `convert`, the interpreter's — keeps `help` as its argument).
    """
    node = find(word)
    if node is None or not node.children or word in ask_words():
        return None
    return scoped(node, "cli.help.title", "cli.help.scoped_usage", "cli.help.words",
                  version=__version__)


def as_text() -> str:
    """The help, in the active language."""
    declared = table_nodes()
    column = width(roots())

    lines = [
        tr("cli.help.title", version=__version__),
        "",
        tr("cli.help.usage"),
        tr("cli.help.json"),
    ]
    if declared:
        lines += section(declared, column, "cli.help.tables")
    lines += section(words(), column, "cli.help.words")
    lines += ["", tr("cli.help.no_args")]
    return "\n".join(lines)
