"""The flags and arguments each permission's act accepts.

Corte de `at.core.permissions` (a fachada); ver o docstring de lá.
"""

from __future__ import annotations

from typing import NamedTuple

from at.core.permissions_base import INSTALL_HOOKS, SCAN, SECRET

# --------------------------------------------------------------- modifiers ---
#
# TASK-186, fatia 2/4: o motor de Actions centralizado. Até aqui o catálogo
# dizia qual permissão um ato demanda; o que ele calava é que vários desses
# atos aceitam um FLAG ou um ARGUMENTO que muda o que o ato faz — `webapp run
# --port`, `backup make <destino>`, `job run <id>` — e essa forma só existia
# no código do despacho (`at/ui/cli/__init__.py`), sem nenhuma declaração ao
# lado de `NARROWED`/`EXTRA` que uma página pudesse ler.


class Modifier(NamedTuple):
    """Um flag ou argumento que o ato de uma permissão aceita — METADADO, não
    código que o despacho lê. `name` é a palavra que a pessoa digita (`--port`,
    `destino`, `id`); `key` é a chave i18n do rótulo; `kind` é `FLAG` ou
    `ARGUMENT`, para a página (fatia 4/4) desenhar os dois de jeito diferente.

    Não é parser nem validador: a CLI (`_webapp`, `_backup`, `_job`, em
    `at/ui/cli/__init__.py`) já decide à mão o que cada um FAZ, e continua
    sendo o único lugar que decide. Um modificador que o código deixa de
    aceitar, ou um que ele passa a aceitar e este dicionário não acompanha, é
    uma inconsistência para a auditoria (fatia 3/4) ou um teste futuro
    pegarem — não esta declaração, que só é lida, nunca checada contra o
    código que ela descreve.
    """

    name: str
    key: str
    kind: str


# As duas formas que um modificador toma, hoje: um FLAG é digitado pelo
# próprio nome (`--port`, `--no-caddy`), com ou sem valor depois; um ARGUMENT
# é digitado no lugar, sem nome próprio (`backup make <destino>`, `job run
# <id>`). A página é quem desenha os dois de jeito diferente; nada aqui força
# uma terceira forma a existir.
FLAG = "flag"
ARGUMENT = "argument"

# Os modificadores que o ato de cada entrada aceita — o MÍNIMO que o prompt
# desta fatia nomeou (backup sem flag, `webapp run`, `secret scan`, as três
# palavras do `job`), não o catálogo inteiro: cobrir toda ação é o ideal, e
# fica para quando a página (fatia 4/4) expuser a lacuna.
#
# `secret:scan` está DENTRO deste dicionário, com nada: `scan` não aceita
# flag nem argumento (`at.ui.cli._table` recusa qualquer `args` que receba), e
# a tupla vazia diz exatamente isso — ausente do dicionário diria a mesma
# coisa por um segundo caminho, que é o segundo lar que este módulo já recusa
# em outro lugar (`narrowed`'s own docstring).
MODIFIERS: dict[str, tuple[Modifier, ...]] = {
    "webapp:run": (
        Modifier("--port", "permission.modifier.webapp.port", FLAG),
        Modifier("--public-port", "permission.modifier.webapp.public_port", FLAG),
        Modifier("--host", "permission.modifier.webapp.host", FLAG),
        Modifier("--no-caddy", "permission.modifier.webapp.no_caddy", FLAG),
    ),
    "backup:make": (
        Modifier("destino", "permission.modifier.backup.destination", ARGUMENT),
    ),
    "backup:restore": (
        Modifier("destino", "permission.modifier.backup.destination", ARGUMENT),
    ),
    f"{SECRET}:{SCAN}": (),
    f"{SECRET}:{INSTALL_HOOKS}": (
        Modifier("--repo", "permission.modifier.secret.install_hooks.repo", FLAG),
    ),
    "job:run": (Modifier("id", "permission.modifier.job.id", ARGUMENT),),
    "job:approve": (Modifier("id", "permission.modifier.job.id", ARGUMENT),),
    "job:refuse": (Modifier("id", "permission.modifier.job.id", ARGUMENT),),
    "job:disable": (Modifier("id", "permission.modifier.job.id", ARGUMENT),),
    "job:declare": (
        Modifier("--when", "permission.modifier.job.when", FLAG),
    ),
}


def modifiers(permission: str) -> tuple[Modifier, ...]:
    """Os flags/argumentos que o ato desta permissão aceita, lidos para a
    página (fatia 4/4) do mesmo jeito que `narrowed`/`actions` já são.

    `()` tanto quando a entrada não está em `MODIFIERS` quanto quando ela
    está lá sem nada (`secret:scan`) — a forma não distingue os dois, do
    mesmo jeito que `carried` não distingue um papel sem permissões de um que
    nunca existiu. Separar os dois casos, se um dia importar, é pergunta da
    página (`permission in MODIFIERS`), não desta função.
    """
    return MODIFIERS.get(permission, ())
