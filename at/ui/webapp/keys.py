"""The WebApp's derived keys — read once from the environment, kept in memory.

§4, item 50: the Main Key never leaves the one instant `at_deploy.environment
.bring_up` reads it in — that function is the only place a process ever holds
it, and only what is DERIVED from it travels. Its `_webapp_env` hands this
container one scope's key at a time, base64'd, each in its own environment
variable — the same shape `at.core.gate.GATE_ENV` and `at.core.paths.ROOT_ENV`
already use to tell a container something the folder decided.

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

# The two variables `at_deploy.environment._webapp_env` may hand this
# container — named here because this is the module that READS them, the same
# rule `gate.GATE_ENV` and `paths.ROOT_ENV` are named by their own readers
# under.
WEBAPP_KEY_ENV = "AT_WEBAPP_KEY"
NOTIFIER_KEY_ENV = "AT_NOTIFIER_KEY"
# TASK-154: o Cofre sela com a chave derivada do escopo `cofre`
# (`at.core.cofre.SCOPE`), pela mesma porta.
COFRE_KEY_ENV = "AT_COFRE_KEY"

_ENV_VARS = (WEBAPP_KEY_ENV, NOTIFIER_KEY_ENV, COFRE_KEY_ENV)

# A CHAVE PRINCIPAL que o WebApp guarda EM MEMÓRIA para a vida do processo.
#
# O caminho container nunca a tem (só as derivadas acima). O caminho HOSPEDADO a
# recebe no `boot`, do ambiente (`AT_MAIN_KEY`) — a mesma grade S de §4: quem a
# digita quando o AT começa não a vê voltar, e nada em disco a guarda. O que fica
# é esta cópia, que morre com o processo; é ela que abre o Cofre (a credencial
# do Jev incluída) para todo pedido, sem pedir a Chave de novo a cada mensagem.
MAIN_KEY_ENV = "AT_MAIN_KEY"

_keys: dict[str, bytes] = {}
_main: str | None = None


def boot() -> None:
    """Read every derived key this process was handed — once, and never again.

    Called at `webapp.run`'s start and nowhere else. A variable that does not
    decode — shorter, longer, not base64 at all — is skipped rather than
    raised over: a boot is not the place to fail on a key nothing will miss
    until something asks for it (`get`).
    """
    keep_main_key(os.environ.pop(MAIN_KEY_ENV, None))
    for variable in _ENV_VARS:
        raw = os.environ.pop(variable, None)
        if not raw:
            continue
        try:
            _keys[variable] = base64.urlsafe_b64decode(raw.encode("ascii"))
        except (ValueError, UnicodeError):
            continue


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


def cofre_key() -> bytes | None:
    """The Cofre's derived key — what `core.cofre.Watcher.tick` seals a
    settled write with — kept since `boot`, or `None`."""
    return _keys.get(COFRE_KEY_ENV)
