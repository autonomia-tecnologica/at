"""The deploy's word tree — the single declaration its surfaces read.

It is the same shape as `at-cli`'s (`at/ui/words.py`) and a different list: the
environment of §7 is this artifact's, and the words that reach it left `at-cli`'s
tree with it (item 27). One declaration, read by the help and by the dispatch at
once — a word can never dispatch without being offered, nor the other way round.
"""

from __future__ import annotations

from at import __version__
from at.i18n import tr
from at.ui.words import Node, completion_words, section, width


# The environment's words, at the ROOT (2026-09-28: `services` is gone — the
# seven used to be its children, and the parent bought a word to type without
# changing what any of them DO). `up` is the FIRST time, `update` every time
# after (the release that already replaced the binary), `down` and `status` are
# the environment's own report and its way down.
# `switch` is §6's TRANSACTIONAL change from the hosted path to the container
# one and `forms` is the way back — both local, which is the whole point of the
# return existing (`at_deploy/switch.py`).
#
# `credential` is the OPERATOR's act (item 27), and it is here for the same
# reason it was under the parent: the credential §7b's gate proves. It takes an
# argument — a NAME (`at_deploy/cli.py`).
_ENVIRONMENT: tuple[Node, ...] = (
    Node("up", "deploy.up.about"),
    Node("update", "deploy.update.about"),
    Node("down", "deploy.down.about"),
    Node("status", "deploy.status.about"),
    Node("switch", "deploy.switch.about"),
    Node("forms", "deploy.forms.about"),
    Node("credential", "deploy.credential.about"),
)


WORDS: tuple[Node, ...] = (
    *_ENVIRONMENT,
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
    return next((node for node in roots() if node.name == name), None)


def environment_words() -> tuple[str, ...]:
    """The names of the eight root words the environment offers.

    Read off `_ENVIRONMENT` and not off `WORDS`, so `cli.py`'s dispatch group
    can never drift from what this declaration actually offers at the root.
    """
    return tuple(node.name for node in _ENVIRONMENT)


def completion() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Every word the completion offers — which is every word the help does."""
    return completion_words(roots())


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
