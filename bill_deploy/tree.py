"""The deploy's word tree — the single declaration its surfaces read.

It is the same shape as `bill`'s (`bill/ui/words.py`) and a different list: the
environment of §7 is this artifact's, and the words that reach it left `bill`'s
tree with it (item 27). One declaration, read by the help and by the dispatch at
once — a word can never dispatch without being offered, nor the other way round.
"""

from __future__ import annotations

from bill import __version__
from bill.i18n import tr
from bill.ui.words import Node, section, width


WORDS: tuple[Node, ...] = (
    # The environment of the container path, and everything a person does with
    # one. `up`, `down` and `status` are the environment itself, and the
    # wordless `services` answers with the status.
    # `switch` is §6's TRANSACTIONAL change from the hosted path to the
    # container one and `forms` is the way back — both local, which is the whole
    # point of the return existing (`bill_deploy/switch.py`).
    # `notify` is §7f's, and it is the one word that proves the delivery by hand:
    # one alert, through the credential `up` created, to the topic.
    Node(
        "services",
        "deploy.services.about",
        (
            Node("up", "deploy.services.up.about"),
            Node("down", "deploy.services.down.about"),
            Node("status", "deploy.services.status.about"),
            Node("switch", "deploy.services.switch.about"),
            Node("forms", "deploy.services.forms.about"),
            Node("notify", "deploy.services.notify.about"),
        ),
    ),
    Node("help", "deploy.help.about"),
    Node("version", "deploy.version.about"),
)


def roots() -> tuple[Node, ...]:
    return WORDS


def find(name: str) -> Node | None:
    return next((node for node in roots() if node.name == name), None)


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
