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


WORDS: tuple[Node, ...] = (
    # The environment of the container path, and everything a person does with
    # one. `up` is the FIRST time, `update` every time after (2026-09-28: the
    # release that already replaced the binary), `down` and `status` are the
    # environment's own report and its way down, and the wordless `services`
    # answers with the status.
    # `switch` is §6's TRANSACTIONAL change from the hosted path to the
    # container one and `forms` is the way back — both local, which is the whole
    # point of the return existing (`at_deploy/switch.py`).
    # `notify` is §7f's, and it is the one word that proves the delivery by hand:
    # one alert, through the credential `up` created, to the topic.
    #
    # `notify` and `credential` are the OPERATOR's acts (item 27), and they are
    # the environment's because the two things they change are: §7f's other end
    # of the topic's ACL, and the credential §7b's gate proves. `credential`
    # takes an OPEN argument — a NAME; `notify` takes an OPTIONAL closed one —
    # with none it sends the test alert, and with `creds` it shows the phone's
    # credential instead (`at_deploy/cli.py`).
    Node(
        "services",
        "deploy.services.about",
        (
            Node("up", "deploy.services.up.about"),
            Node("update", "deploy.services.update.about"),
            Node("down", "deploy.services.down.about"),
            Node("status", "deploy.services.status.about"),
            Node("switch", "deploy.services.switch.about"),
            Node("forms", "deploy.services.forms.about"),
            Node("notify", "deploy.services.notify.about"),
            Node("credential", "deploy.services.credential.about"),
        ),
    ),
    # A CA do AT no cofre que o navegador DESTA máquina lê (item 49). É a outra
    # metade do que o §7a abriu com `cert.at.local`: lá a CA chega ao aparelho
    # que não lê o disco, aqui ela entra no NSS de quem navega daqui. Os dois
    # atos são `install` e `uninstall` porque um cofre que só cresce é um cofre
    # que ninguém audita, e os ALVOS — os cofres — são argumento e não palavra:
    # os dois nomes do meio (firefox, chromium) são o vocabulário fechado, e a
    # `cli` os diz quando o ato vem sozinho (`at_deploy/trust.py`).
    Node(
        "ca",
        "deploy.ca.about",
        (
            Node("install", "deploy.ca.install.about"),
            Node("uninstall", "deploy.ca.uninstall.about"),
        ),
    ),
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
