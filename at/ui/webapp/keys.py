"""The WebApp's derived keys — read once from the environment, kept in memory.

§4, item 50: the Main Key never leaves the one instant `at_deploy.environment
.bring_up` reads it in — that function is the only place a process ever holds
it, and only what is DERIVED from it travels. Its `_webapp_env` hands this
container one scope's key at a time, base64'd, each in its own environment
variable — the same shape `at.core.gate.GATE_ENV` and `at.core.paths.ROOT_ENV`
already use to tell a container something the folder decided.

**The hosted path has no `_webapp_env`, and the Vault's key cannot depend on
it existing.** Neither the systemd unit (`at_deploy/host.py`) nor a loose
`at-cli webapp` ever hands over `AT_STRONGBOX_KEY` — only the container path
derives and delivers that variable. So `boot` derives the Vault's key itself,
straight from this boot's Main Key — through the ONE door that reaches the
Vault from the core's side, `core.secrets.key_of` (§4: no screen touches
`vault` directly, and this is a screen). The scope is just a name, and the
Main Key recovers the derived key on any path, not only the one that already
has the variable.

**A key is read from `os.environ` exactly once, at `boot`, and it is gone from
there the moment it is.** `os.environ` is inherited for the whole life of the
process — a child spawned later would see it forever if `boot` left it
standing — so the read POPS the variable instead of merely getting it. What
survives is the derived key alone, held here and nowhere else: not in a file,
not in a second variable, not spread across the callers that need it.

**A process that never got a variable has no key, and asking for one answers
`None` instead of refusing to boot.** `at-cli webapp` run loose, a test, an
environment whose folder was already fully sealed and had nothing to open this
round (`environment.unlock` answers `None, None` there too) — none of them
carries these variables, and a reader that depended on one says there is none
rather than take the process down.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from at.core import secrets, strongbox

# The two variables `at_deploy.environment._webapp_env` may hand this
# container — named here because this is the module that READS them, the same
# rule `gate.GATE_ENV` and `paths.ROOT_ENV` are named by their own readers
# under.
WEBAPP_KEY_ENV = "AT_WEBAPP_KEY"
NOTIFIER_KEY_ENV = "AT_NOTIFIER_KEY"
# TASK-154: o Cofre sela com a chave derivada do escopo `cofre`
# (`at.core.strongbox.SCOPE` — o valor congelado continua `"cofre"`, só o
# módulo e a variável abaixo são `strongbox`), pela mesma porta.
STRONGBOX_KEY_ENV = "AT_STRONGBOX_KEY"

_ENV_VARS = (WEBAPP_KEY_ENV, NOTIFIER_KEY_ENV, STRONGBOX_KEY_ENV)

# A CHAVE PRINCIPAL que o WebApp guarda EM MEMÓRIA para a vida do processo.
#
# O caminho container nunca a tem (só as derivadas acima). O caminho HOSPEDADO a
# recebe no `boot`, do ambiente (`AT_MAIN_KEY`) — a mesma grade S de §4: quem a
# digita quando o AT começa não a vê voltar, e nada em disco a guarda. O que fica
# é esta cópia, que morre com o processo; é ela que abre o Cofre (a credencial
# do Jev incluída) para todo pedido, sem pedir a Chave de novo a cada mensagem.
MAIN_KEY_ENV = "AT_MAIN_KEY"

# O ARQUIVO da máquina onde a pessoa guarda a Chave Principal, fora de qualquer
# pasta de trabalho: `~/.config/at/AT_MAIN_KEY`. O host lê dele quando a
# variável não veio no ambiente — é o que faz o AT subir JÁ com a Chave em
# memória, sem ninguém digitá-la a cada pedido. Não é dado da instância e não
# entra no backup (não está na Pasta de Trabalho); é da pessoa, para a máquina.
MAIN_KEY_FILE = (".config", "at", "AT_MAIN_KEY")

_keys: dict[str, bytes] = {}
_main: str | None = None


def boot() -> None:
    """Read every derived key this process was handed — once, and never again.

    Called at `webapp.run`'s start and nowhere else. A variable that does not
    decode — shorter, longer, not base64 at all — is skipped rather than
    raised over: a boot is not the place to fail on a key nothing will miss
    until something asks for it (`get`).

    **A Chave Principal vem do ambiente OU do arquivo da máquina** — o
    ambiente primeiro, o arquivo depois (`MAIN_KEY_FILE`). Um host que sobe
    sem nenhum dos dois não tem a Chave, e o que depende dela (o Cofre, o Jev)
    diz que não tem em vez de estourar.

    **And the Vault's key is DERIVED here when nobody handed over a ready
    one.** The container path already arrives with `AT_STRONGBOX_KEY` in the
    environment (above); the hosted one has no such door and only has the
    Main Key — so, missing the variable, it is derived straight from it
    (`_derive_strongbox_key`), instead of leaving the Vault without a key
    over an accident of which path raised the process.
    """
    keep_main_key(os.environ.pop(MAIN_KEY_ENV, None) or _main_key_from_file())
    for variable in _ENV_VARS:
        raw = os.environ.pop(variable, None)
        if not raw:
            continue
        try:
            _keys[variable] = base64.urlsafe_b64decode(raw.encode("ascii"))
        except (ValueError, UnicodeError):
            continue
    _derive_strongbox_key()


def _derive_strongbox_key() -> None:
    """The Vault's key, straight from the Main Key, when no ready one arrived.

    Only fills in what `_ENV_VARS` left empty: a container's
    `AT_STRONGBOX_KEY` is never overwritten by a derivation nobody asked
    for. A Main Key too short (or none at all, from a host with neither the
    variable nor the file) leaves the key absent — the same answer a
    process that never got one gives, never a boot that blows up.
    """
    if STRONGBOX_KEY_ENV in _keys or _main is None:
        return
    try:
        _keys[STRONGBOX_KEY_ENV] = secrets.key_of(strongbox.SCOPE, _main)
    except secrets.SecretsError:
        pass


def _main_key_from_file() -> str | None:
    """A Chave Principal que `MAIN_KEY_FILE` guarda — ou `None`.

    Uma leitura que falha (o arquivo não existe, não é texto) é `None`, nunca
    um estouro: não ter a chave é uma resposta, e é a mesma de um host que
    ninguém a deu.
    """
    try:
        read = Path.home().joinpath(*MAIN_KEY_FILE).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    return read.strip() or None


def keep_main_key(value: str | None) -> None:
    """Guarda a Chave Principal desta subida — em memória, e só aqui.

    O valor vem do ambiente no `boot` e é POPSADO de lá (uma variável de
    ambiente é herdada por todo filho; deixá-la de pé seria espalhar a Chave).
    Ela não é escrita em lugar nenhum, e um processo que nunca a recebeu
    responde `None` (`main_key`).
    """
    global _main
    _main = value or None


def main_key() -> str | None:
    """A Chave Principal desta subida, ou `None` — e nenhuma cópia em disco."""
    return _main


def webapp_key() -> bytes | None:
    """The WebApp's own derived key, kept since `boot` — or `None`."""
    return _keys.get(WEBAPP_KEY_ENV)


def notifier_key() -> bytes | None:
    """The notifier's derived key — the same one `at_deploy.notifier` seals
    and opens its credential with — kept since `boot`, or `None`."""
    return _keys.get(NOTIFIER_KEY_ENV)


def strongbox_key() -> bytes | None:
    """The Vault's derived key — what `core.strongbox.Watcher.tick` seals a
    settled write with — kept since `boot`, or `None`."""
    return _keys.get(STRONGBOX_KEY_ENV)
