"""The deploy's word tree — the single declaration its surfaces read.

It is the same shape as `at-cli`'s (`at/ui/words.py`) and a different list: the
environment of §7 is this artifact's, and the words that reach it left `at-cli`'s
tree with it (item 27). One declaration, read by the help and by the dispatch at
once — a word can never dispatch without being offered, nor the other way round.
"""

from __future__ import annotations

from at import __version__
from at.i18n import tr
from at.ui.words import Node, completion_words, scoped, section, width

# The container environment's words, nested under `container` (2026-10-03: a
# second environment — the host's own systemd, below — arrived, and a word
# typed bare stopped being able to say which one it meant; the eight that
# used to sit at the root moved under this one name, by the same reasoning
# that moved them out from under `services` in the first place, one revision
# ago). `up` is the FIRST time, `update` every time after (the release that
# already replaced the binary), `down` and `status` are the environment's own
# report and its way down.
# `switch` is §6's TRANSACTIONAL change from the hosted path to the container
# one and `forms` is the way back — both local, which is the whole point of the
# return existing (`at_deploy/switch.py`).
#
# `credential` is the OPERATOR's act (item 27), and it is here for the same
# reason it was under the parent: the credential §7b's gate proves. It takes an
# argument — a NAME (`at_deploy/cli.py`).
_CONTAINER: tuple[Node, ...] = (
    Node("up", "deploy.up.about"),
    Node("update", "deploy.update.about"),
    Node("down", "deploy.down.about"),
    Node("status", "deploy.status.about"),
    Node("switch", "deploy.switch.about"),
    Node("forms", "deploy.forms.about"),
    Node("credential", "deploy.credential.about"),
)

# The HOST environment's words (TASK-190): the hosted path's own Authelia,
# already up as a subprocess of `at-cli webapp` since TASK-177, kept standing
# across a REBOOT too — which an orphan subprocess never survives on its own.
# `up` writes the two systemd `--user` units (the WebApp's and Authelia's) the
# FIRST time; `update` is every time after, the mirror of the container path's
# own pair.
_HOST: tuple[Node, ...] = (
    Node("up", "deploy.host.up.about"),
    Node("update", "deploy.host.update.about"),
)


WORDS: tuple[Node, ...] = (
    Node("container", "deploy.container.about", _CONTAINER),
    Node("host", "deploy.host.about", _HOST),
    # The second artifact puts ITSELF where commands are found, and it does not
    # install the first one: §3's cut is the same sentence here — whoever stays
    # on the hosted path never needs this binary, and whoever installs this one
    # has it for §7 alone.
    Node("install", "deploy.install.about"),
    Node("uninstall", "deploy.uninstall.about"),
    # About the FILE, like the pair above and like `at-cli`'s own: this artifact
    # carries the interpreter, the bootloader and the crypto binding, so the
    # licences of those travel inside it too — and this word is the only door
    # they have out of a single file (`at/core/licenses.py`). It answers with
    # what THIS artifact carries, which is not what the other one carries.
    Node("license", "deploy.license.about"),
    Node("help", "deploy.help.about"),
    Node("version", "deploy.version.about"),
)


def roots() -> tuple[Node, ...]:
    return WORDS


def find(name: str) -> Node | None:
    """A root by name, or — one level down, same reach as `completion_words`
    — a child's. `up` names two children now (`container`'s and `host`'s);
    this answers the first `WORDS` carries, which is a lookup's whole job,
    not a disambiguation the dispatch already does by reading the parent."""
    for node in roots():
        if node.name == name:
            return node
        for child in node.children:
            if child.name == name:
                return child
    return None


def environment_words() -> tuple[str, ...]:
    """The names of the seven words the container environment offers.

    Read off `_CONTAINER` and not off `WORDS`, so `cli.py`'s dispatch group
    can never drift from what this declaration actually offers under `container`.
    """
    return tuple(node.name for node in _CONTAINER)


def host_words() -> tuple[str, ...]:
    """The names of the two words the host environment offers — the same
    guarantee `environment_words()` gives the container one."""
    return tuple(node.name for node in _HOST)


def completion() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Every word the completion offers — which is every word the help does."""
    return completion_words(roots())


def scoped_text(word: str) -> str | None:
    """The help of one root word: only the words under it, in the top help's
    shape. `None` for a root with nothing under it."""
    node = next((n for n in roots() if n.name == word), None)
    if node is None or not node.children:
        return None
    return scoped(node, "deploy.help.title", "deploy.help.scoped_usage",
                  "deploy.help.words", version=__version__)


def as_text() -> str:
    """The help, in the active language."""
    lines = [
        tr("deploy.help.title", version=__version__),
        "",
        tr("deploy.help.usage"),
        *section(WORDS, width(WORDS), "deploy.help.words"),
        "",
        tr("deploy.help.no_args"),
    ]
    return "\n".join(lines)
