"""A auditoria das três portas até cada permissão do catálogo (TASK-186,
fatia 3/4) — o `cli`, o `web` e a frase (`llm`, a leitura do interpretador,
Jev incluso).

**Por que isto existe.** As fatias 1/4 e 2/4 fecharam o CATÁLOGO — toda ação
de toda palavra da CLI tem uma permissão —, mas nada ainda cruzava essa lista
fechada com as portas de fato: uma permissão podia nascer no catálogo e nunca
ganhar rota nenhuma, nem na CLI, nem no WebApp, nem na frase, sem que ninguém
visse — até alguém tropeçar nela em produção, perguntando por que um papel que
a carrega não consegue fazer nada com ela. `reach` é a resposta a essa
pergunta, por permissão; `orphans` é a lista do que não tem resposta nenhuma.

**O que cada marca quer dizer.**
- `CLI` — o terminal alcança. Toda ação de uma TABELA DECLARADA chega por ele,
  sempre: o despacho genérico (`at.ui.cli._table`) cobre o motor
  (`tables.ACTIONS`) mapeado pela narrowing de cada tabela, e os atos
  PRÓPRIOS de um objeto (o `run`/`approve`/`refuse` do `job`, o `scan` do
  `secret`, o `due` do `reminder`) são lidos do mesmo catálogo
  (`permissions.actions`) pelas portas que os despacham. As palavras que não
  são tabela (`webapp`, `backup`, `admin`, `help`...) vêm de
  `tree.WORD_PERMISSIONS` — a mesma lista que a fatia 1/4 já prova contra
  `tree.WORDS`, lida aqui e não copiada de novo.
- `WEB` — uma rota de `at/ui/webapp/app.py` checa esta permissão por nome
  (`_may`/`_legal`). Não há como descobrir isso sem ler o despacho: uma rota
  HTTP é código, não uma declaração. `WEB_PERMISSIONS`, abaixo, é essa leitura
  feita à mão — o preço de auditar uma superfície que não é dado. A rota
  genérica de tabela soma a isso: toda LEITURA (`list`) e as duas escritas que
  ela oferece hoje (`create`, `edit` — `at.ui.webapp.app.TABLE_WRITES`); um
  fechamento e uma exclusão não têm rota ainda, e não é desta auditoria
  inventar uma só para fechar um buraco que é da página.
- `LLM` — a frase alcança: o que `at.nlu.matcher` consegue PROPOR a partir do
  vocabulário embalado (`at.nlu.vocabulary`), sem perguntar nada ao Jev — uma
  leitura ESTÁTICA, como a fatia pede. Só os verbos que o vocabulário hoje
  nomeia como canônico de um `tables.ACTIONS` entram (`create`, `edit`,
  `list`, `view`, hoje); um `cancel`/`delete` não tem gíria nenhuma que os
  proponha, e nenhuma tabela os alcança por aqui enquanto isso for verdade.

**O que isto NÃO garante** — a ressalva da própria fatia: as três portas não
precisam bater para toda ação. Uma ação só pelo REST (ou só pela CLI, ou só
pela frase) é uma marca de UMA porta, nunca um erro. O que este módulo recusa
é o SILÊNCIO — uma permissão sem marca nenhuma, e fora da lista nomeada
abaixo (`NO_INTERFACE_YET`).
"""

from __future__ import annotations

from at.core import permissions, tables
from at.data import schema
from at.nlu import vocabulary
from at.ui.cli import tree

CLI = "cli"
WEB = "web"
LLM = "llm"

# As permissões que uma rota de `at/ui/webapp/app.py` checa POR NOME — lidas
# do arquivo (`_may`/`_legal`, cada ocorrência) e não de um catálogo, porque
# não existe um: a rota é código, e o nome que ela passa é o fato inteiro.
# Manter esta lista é o preço de auditar uma superfície que não é dado; uma
# rota nova que esta lista esquece é um buraco que esta auditoria cala, e uma
# que muda o nome que checa é uma que tirou esta lista da verdade.
WEB_PERMISSIONS: tuple[str, ...] = (
    "setting:read",
    "setting:edit",
    "project:list",
    "project:view",
    "task:list",
    "role:list",
    "prose:read",
    "prose:edit",
    "nlu:ask",
    "assist:ask",
    "strongbox:read",
    "notifier:read",
    "actor:create",
    "actor:edit",
)

# As duas escritas que a rota genérica de tabela oferece hoje
# (`at.ui.webapp.app.TABLE_WRITES`) — um `cancel`/`delete` não tem rota, então
# nenhuma tabela alcança essas duas permissões pelo `web`, só pelo `cli`.
_TABLE_WEB_WRITES = ("create", "edit")


def _grammar_actions() -> frozenset[str]:
    """Os verbos de `tables.ACTIONS` que o vocabulário embalado nomeia como
    canônico de alguma expressão, em QUALQUER idioma que ele carregue.

    Leitura estática — nenhuma chamada ao Jev, nenhuma rede: é o mesmo
    `vocabulary.of` que o interpretador lê para casar uma frase, perguntado
    aqui pelo conjunto e não por uma expressão. Hoje responde `{create, edit,
    list, view}`; o dia que uma gíria nomear `cancel` ou `delete`, esta função
    cresce com ela, sem precisar ser reescrita.
    """
    found: set[str] = set()
    for language in vocabulary.languages():
        found |= set(vocabulary.of(language).values())
    return frozenset(found) & frozenset(tables.ACTIONS)


def reach() -> dict[str, frozenset[str]]:
    """Para CADA permissão do catálogo, o conjunto de portas que chegam nela —
    o vazio (`frozenset()`) quando nenhuma chega.

    A chave existe sempre: a resposta é sobre o catálogo inteiro, e uma
    permissão sem marca é um VALOR VAZIO, não uma chave ausente — é o que deixa
    `orphans` (e o teste desta fatia) perguntarem "quantas portas a alcançam?"
    para toda permissão, sem um `in` que confunda "não achei" com "não existe".
    Uma marca para um nome que o catálogo não tem é DESCARTADA aqui: uma rota
    que exija um nome desconhecido é outro defeito (o espelho deste), provado
    por `WEB_PERMISSIONS ⊆ all_permissions()` no teste, e não um fantasma a
    mais nesta resposta.
    """
    found: dict[str, set[str]] = {p: set() for p in permissions.all_permissions()}

    def mark(permission: str, interface: str) -> None:
        if permission in found:
            found[permission].add(interface)

    grammar = _grammar_actions()
    for declared in schema.declared():
        table = str(declared["id"])
        for action in permissions.actions(table):
            permission = permissions.needed(table, action)
            mark(permission, CLI)
            if action == "list" or action in _TABLE_WEB_WRITES:
                mark(permission, WEB)
            if action in grammar:
                mark(permission, LLM)

    for names in tree.WORD_PERMISSIONS.values():
        for permission in names:
            mark(permission, CLI)

    for permission in WEB_PERMISSIONS:
        mark(permission, WEB)

    return {permission: frozenset(marks) for permission, marks in found.items()}


# As permissões que UMA ROTA de `at/ui/webapp/app.py` demanda por nome, e que
# o catálogo precisa conhecer — a checagem que a mão de `WEB_PERMISSIONS` pede:
# uma rota que exija um nome que o catálogo não tem falha FECHADO (recusa o
# administrador), então este cruzamento é um defeito de verdade e não um
# detalhe da auditoria. `reach()` descarta o fantasma; este predicado o aponta.
def unknown_web_permissions() -> list[str]:
    """Os nomes de `WEB_PERMISSIONS` que o catálogo não conhece — vazio quando
    a lista à mão está de acordo com o catálogo."""
    catalogued = set(permissions.all_permissions())
    return [p for p in WEB_PERMISSIONS if p not in catalogued]


# As permissões sem porta nenhuma, por DESENHO, com o porquê de cada uma — a
# lista de exceções nomeadas que a fatia pede. Não é um silêncio: é uma decisão
# já tomada, a mesma que `permissions.py`'s própria `EXTRA` já registra ("reached
# by NO route yet... the screens that move them... are what will demand them").
# Uma permissão que ganha uma porta SAI desta tupla — o teste desta fatia falha
# se ela continuar aqui e for alcançada —, e esta auditoria não a perdoa por
# esquecimento: seu nome está escrito, um por um, por causa.
#
# - `service:*`, `plugin:*` — §4 declara os dois entre os objetos, mas as telas
#   que os movem (itens 13, 15 e 16) ainda não existem: nenhuma rota, nenhuma
#   palavra da CLI, nenhuma gíria da frase os nomeia hoje. É a MESMA razão que
#   `EXTRA` já escreve para os três — hoje só o `at-deploy` (§7) toca serviços, e
#   ele não lê este catálogo.
# - `vocabulary:*` — idem: a tela que edita o vocabulário é item 16, ainda por
#   vir; declarar a permissão hoje é o que impede uma tela futura nascer num
#   catálogo que teria de crescer sob um papel vivo.
NO_INTERFACE_YET: tuple[str, ...] = (
    "service:read",
    "service:edit",
    "plugin:read",
    "plugin:edit",
    "vocabulary:read",
    "vocabulary:edit",
)


def orphans() -> list[str]:
    """As permissões do catálogo que nenhuma porta alcança e que não estão na
    lista nomeada — o buraco que esta fatia existe para apontar.

    Lê `reach()` inteiro (toda permissão tem uma chave, vazia quando ninguém
    chega) e devolve as de conjunto vazio fora de `NO_INTERFACE_YET`, na ordem
    do catálogo. Lista vazia é o estado saudável.
    """
    return [
        permission
        for permission, marks in reach().items()
        if not marks and permission not in NO_INTERFACE_YET
    ]
