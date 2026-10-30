"""Migrations eighteen to thirty: the clock, the strongbox, the services, the
reminders, the hooks and the notes.

Split from `at.core.migrations`, which re-exports everything here.
"""

from __future__ import annotations

from pathlib import Path

from at.core import (
    paths,
    permissions,
    tables,
)
from at.core.migrations_base import Ask, Report
from at.core.migrations_engine import _extend, _hand_over
from at.data import schema, store

# What THIS release adds to a declaration that is ALREADY on disk — migration
# eighteen, and the same shape migrations nine, fifteen and seventeen write.
#
# **The `job` gains the state the CLOCK drives** (§4, item 24): a folder born
# before the clock declares four states, and a job that comes round on its own
# has a fifth. The value is the last one in the enum and not the first, and that
# is not cosmetic — the merge only ever ADDS, so a value inserted before `done`
# would be an edit to the person's file, while appended it is the same list the
# bundled declaration now carries.
CLOCK: dict[str, dict] = {
    "job": {
        "fields": {
            "status": {
                "enum": {"scheduled": "table.job.field.status.scheduled"},
            }
        },
    },
}


def _clock(ask: Ask | None) -> list[Report]:
    """Migration eighteen: the `job` gains the state that says it rounds on its own.

    A folder that already exists is the one this is for: its declaration was
    written when a job could only WAIT, and the new state is what the engine
    reads to know which jobs the clock drives. Nothing about the rows changes —
    a job is `waiting` until a person answers it, and only a job DECLARED with a
    `when` is ever `scheduled` —, and nothing outside the folder points at the
    declaration (§3, migration).

    It does not ask, for the reason `_tags` gives: a declaration of the
    product's own.
    """
    return _extend(CLOCK)


# O que a seção do Cofre (TASK-156) demanda, e nenhum papel nascido antes
# desta versão teve a CHANCE de carregar — a mesma razão de `GROWN` e `ADDED`.
#
# **O valor acompanha o catálogo de HOJE, não o do dia em que esta migração
# nasceu.** `_hand_over` já é "o papel alcança o que o catálogo tem agora" —
# uma pasta que só roda esta migração nesta versão (uma que nunca tinha
# chegado até aqui) tem de ganhar `strongbox:read`, porque é esse o nome que
# o catálogo de hoje conhece. Uma pasta que já rodou esta migração sob o
# nome antigo (`cofre:read`) não passa por aqui de novo — ela é a migração
# vinte e cinco, abaixo, que resolve.
STRONGBOX_GRANTED = ("strongbox:read",)


def _strongbox_permission(ask: Ask | None) -> list[Report]:
    """Migration vinte: `strongbox:read`, que a seção do Cofre (TASK-156) demanda.

    A mesma forma de `_catalogue` e `_objects`: só o administrador, só o que
    falta, e não pergunta — o ganho é só leitura de uma lista de nomes.
    """
    return _hand_over(STRONGBOX_GRANTED)


def _strongbox_folder(ask: Ask | None) -> list[Report]:
    """`Cofre/` — a pasta que sela sozinha, chega numa pasta que já existia
    (TASK-152, TASK-154).

    A mesma forma de `_harness_folder`: nasce nomeada e vazia, e o impacto de
    fora é nulo — nada aponta para ela ainda —, então não pergunta.
    """
    target = paths.strongbox_dir()
    if target.exists():
        return []
    target.mkdir(parents=True, exist_ok=True)
    return [("boot.migration.folders.born", {"names": target.name})]


def _strongbox_permission_renamed(ask: Ask | None) -> list[Report]:
    """Migration vinte e cinco: `cofre:read` → `strongbox:read`, em todo papel
    que já carregava o nome antigo.

    **Só o código mudou de nome — a pasta de quem já tinha o administrador
    de pé continua com `cofre:read` escrito em `role.jsonl`,** porque a
    migração vinte já rodou para ela sob esse nome e não roda de novo. Sem
    este passo, o catálogo de hoje (que só conhece `strongbox:read`) deixa de
    reconhecer o que o papel carrega, e a seção do Cofre, que a pessoa já
    usava, fecharia para ela — não por decisão de ninguém, por um nome que o
    código trocou por debaixo do papel.

    Troca o token dentro da lista de permissões, nunca a lista inteira:
    o que mais o papel carrega continua exatamente como estava.
    """
    renamed: list[str] = []
    for row in store.load("role"):
        carried = permissions.carried(row)
        if "cofre:read" not in carried:
            continue
        number = store.number_of(row)
        if number is None:
            continue
        updated = ["strongbox:read" if p == "cofre:read" else p for p in carried]
        tables.edit("role", number, {"permissions": ",".join(updated)})
        renamed.append(tables.title("role", row))
    if not renamed:
        return []
    return [("boot.migration.strongbox.renamed", {"names": ", ".join(renamed)})]


# O que o motor offline compara (TASK-162, fatia 1): o `edited_at` que a
# engine restampa em toda escrita da tarefa (`tables._touch`), esteja ou não o
# `status` entre o que mudou — o que `modifications[].at` já não cobre (§
# `at/core/offline.py`).
EDITED_AT: dict[str, dict] = {
    "task": {
        "fields": {
            "edited_at": {
                "label": "table.task.field.edited_at",
                "type": "instant",
                "hide": ["project", "orphans"],
                "touch": True,
            }
        },
    },
}


def _edited_at(ask: Ask | None) -> list[Report]:
    """Migration vinte e um: a tarefa carrega o instante que o motor offline
    compara para decidir quem venceu (TASK-162).

    Mesma forma de `_tags` e `_clock` — e não enche nenhuma linha existente: a
    engine só restampa `edited_at` na PRÓXIMA escrita de cada linha, e uma
    linha nunca escrita de novo não tem conflito nenhum para reconciliar
    ainda.
    """
    return _extend(EDITED_AT)


def _convert_folder(ask: Ask | None) -> list[Report]:
    """`Convertidos/` — onde o `at/convert/` pousa o que gerou, chega numa
    pasta que já existia (TASK-165).

    Mesma forma de `_strongbox_folder` e `_harness_folder`: nasce nomeada e vazia,
    e o impacto de fora é nulo — nada aponta para ela ainda —, então não
    pergunta.
    """
    target = paths.convert_dir()
    if target.exists():
        return []
    target.mkdir(parents=True, exist_ok=True)
    return [("boot.migration.folders.born", {"names": target.name})]


# O que esta troca acrescenta a declarações que JÁ estão no disco — migração
# vinte e três. Mesma forma de `EXTENDED` (nove) e `EDITED_AT` (vinte e um), e
# pelo mesmo motivo: são campos que trocas ANTERIORES acrescentaram ao produto
# sem carregar migração nenhuma, e o `seed` escreve só a declaração AUSENTE —
# a destas tabelas já estava na pasta.
#
# Cada um custa de um jeito, e é isso que decide que os três entram juntos:
#
# - **`reminder.notified` é o guarda do round do relógio.** É o campo que
#   `at.ui.ask.remind` escreve depois de um push que SAIU, e é ele que impede o
#   mesmo lembrete de ser empurrado a cada passagem do relógio (§`at/core/
#   reminder.py`). Sem o campo na declaração da pasta, `tables.edit` recusa o
#   nome (`error.unknown_field`), a marca nunca é escrita — e o push que já
#   saiu se repete a cada cadência, dez minutos, para sempre. O push entrega
#   antes da marca: é a marca que falha, e é o silêncio dela que dói.
# - **`role.permissions` e `actor.role` carregam `risk: 0.95`** (item 15): o
#   preço que editar quem-pode-o-quê levanta. Sem ele a demanda cai no piso
#   (`risk.raised` lê a ausência como o piso) e a edição de um papel não espera
#   por uma pessoa — a declaração velha baixa a barra de quem já existe sem
#   ninguém ter mexido nela.
#
# As adições são DATEADAS — o que 286b206 (24/09, o risco por argumento) e
# ce99afe (28/09, o lembrete que dispara sozinho) mudaram em silêncio —, e uma
# migração publicada nunca é editada: a próxima troca que crescer uma
# declaração traz o próprio passo e a própria lista.
SILENT_ADDITIONS: dict[str, dict] = {
    "reminder": {
        "fields": {"notified": {"label": "table.reminder.field.notified", "filterable": True}},
    },
    "actor": {
        "fields": {"role": {"risk": 0.95}},
    },
    "role": {
        "fields": {"permissions": {"risk": 0.95}},
    },
}


def _silent_additions(ask: Ask | None) -> list[Report]:
    """Migração vinte e três: o que trocas anteriores acrescentaram a uma
    declaração que já estava no disco, sem migração para carregar.

    Não pergunta, pela mesma razão da nove: é declaração do próprio produto,
    nada fora da pasta aponta para ela, e o corpo só ACRESCENTA — o que a
    pessoa escreveu por cima ganha o nome no relato e fica onde está.
    """
    return _extend(SILENT_ADDITIONS)


PROJECT_DESC_LIMIT = {
    "project": {
        "fields": {"desc": {"max_length": 200}},
    },
}


def _project_desc_limit(ask: Ask | None) -> list[Report]:
    """Migração vinte e quatro: a descrição do projeto ganha o teto que a
    task não tem — o resumo é dela, a prosa é da task (§3).
    """
    return _extend(PROJECT_DESC_LIMIT)


# Os serviços que o caminho HOSPEDADO espalhava pela raiz de `App/`, e a casa
# única que o §7 lhes dá: `App/services/<serviço>/`, a mesma dos serviços do
# caminho container. O Caddy já forçava o encontro — `caddy.directory()` e
# `environment.state("caddy")` são a MESMA pasta, e o arquivo do portão que os
# dois desenham vive nela —, e esta migração é o resto deles alcançando a casa.
SERVICES: tuple[str, ...] = ("caddy", "authelia", "push", "gitleaks")


# O que é um ARQUIVO e não uma pasta: o cache do Jev, que era `App/jev-cache.json`
# e passa a ser `App/services/jev/cache.json` (o Jev é uma API externa, e ainda
# assim é um serviço — §4).
JEV_CACHE = ("jev-cache.json", "jev", "cache.json")


def _merge_into(target: Path, source: Path) -> list[str]:
    """Move o que `source` tem para dentro de `target`, sem sobrescrever nada.

    Devolve os nomes das entradas que o destino JÁ carregava e que por isso
    ficaram onde estavam. Uma pasta que chegou primeiro — o `App/services/caddy/`
    de quem andou pelo caminho container — mantém o que tinha, e só os nomes que
    ela não carrega é que vão. Depois de mover, a pasta de origem se apaga; se
    sobrou alguma entrada recusada, ela fica (e o motivo é dito), porque apagar a
    origem com algo dentro seria perder o que o destino recusou.
    """
    target.mkdir(parents=True, exist_ok=True)
    kept: list[str] = []
    for entry in sorted(source.iterdir()):
        destination = target / entry.name
        if destination.exists():
            kept.append(entry.name)
            continue
        entry.rename(destination)
    try:
        source.rmdir()
    except OSError:
        pass
    return kept


def _services_under_their_house(ask: Ask | None) -> list[Report]:
    """Migração vinte e seis: cada serviço passa a morar sob `App/services/` (§7).

    O caminho hospedado espalhava os serviços dele pela raiz de `App/` — o
    Caddy, o Authelia, o push, o gitleaks e o cache do Jev —, enquanto o caminho
    container já guardava TUDO sob `App/services/<serviço>/`. São os MESMOS
    serviços, e a casa é uma só: esta migração traz os do caminho hospedado para
    dentro dela, e a raiz de `App/` fica só com o que não é serviço (os ajustes,
    os contadores, o registro da instalação, o carimbo das migrações, o idioma).

    Não pergunta: é a pasta do PRÓPRIO AT (§3, migration) — nada de fora aponta
    para `App/caddy/` —, e o movimento nunca sobrescreve: um destino que já
    existe fica com o que tinha, e o que sobrou é dito. O Authelia que está DE
    PÉ não é reiniciado por isto: ele guarda os caminhos antigos, e quem o
    reinicia é a pessoa, depois.
    """
    house = paths.services_dir()
    root = paths.app_dir()
    moved: list[str] = []
    collided: list[str] = []
    for name in SERVICES:
        source = root / name
        if not source.is_dir():
            continue
        kept = _merge_into(house / name, source)
        moved.append(name)
        collided += [f"{name}/{entry}" for entry in kept]
    loose, jev_folder, jev_name = JEV_CACHE
    source = root / loose
    if source.is_file():
        destination = house / jev_folder / jev_name
        if destination.exists():
            collided.append(loose)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            moved.append(loose)
    report: list[Report] = []
    if moved:
        report.append(("boot.migration.services.moved", {"names": ", ".join(moved)}))
    if collided:
        report.append(("boot.migration.services.collision", {"names": ", ".join(collided)}))
    if not report:
        report.append(("boot.migration.services.kept", {}))
    return report


# What THIS release adds to a declaration that is ALREADY on disk — migration
# twenty-seven, the same shape nine, fifteen, seventeen and eighteen write.
#
# **O `at` de um lembrete declara que seus itens são HORAS** (`"items": "time"`).
# A lista já guardava horas (`["09:00"]`) desde que nasceu; o que faltava era a
# declaração DIZER isso — sem a chave, o tipo `list` não conta nada sobre os
# itens, e a gramática não tinha por onde ler `18h` de uma frase.
REMINDER_HOUR: dict[str, dict] = {
    "reminder": {
        "fields": {
            "at": {"items": "time"},
        },
    },
}


def _reminder_hour(ask: Ask | None) -> list[Report]:
    """Migration twenty-seven: o `at` do lembrete diz que seus itens são horas.

    Não pergunta, e não enche linha nenhuma: é declaração do produto, e o valor
    que já estava lá (`["09:00"]`) sempre foi uma hora — o que muda é só a
    gramática poder lê-la de uma frase.
    """
    return _extend(REMINDER_HOUR)


# O que ESTA troca acrescenta a uma declaração que JÁ está no disco — migração
# vinte e oito, a mesma forma de nove, dezessete, vinte e sete.
#
# **O `on_date` de um lembrete passa a ser obrigatório quando `freq` é `once`.**
# Um lembrete de uma vez sem data NUNCA ocorre (`reminder.occurs` exige
# `on_date` para o `once`), e nada o barrava: a linha nascia morta e calada —
# o Jev marca a data de uma frase ("hj") como `day_span`, a palavra-campo é
# plantada, mas o `read_day` da gramática não lê a gíria, o `on_date` cai como
# resíduo e o `once` fica sem data, para nunca tocar. O portão é do motor
# (`tables._require` lê o `required_when` da própria declaração), e vale para
# toda porta — CLI, WebApp e a frase.
ONCE_NEEDS_A_DAY: dict[str, dict] = {
    "reminder": {
        "fields": {
            "on_date": {"required_when": {"freq": "once"}},
        },
    },
}


def _once_needs_a_day(ask: Ask | None) -> list[Report]:
    """Migração vinte e oito: o `once` do lembrete exige a data.

    Não pergunta, pela mesma razão da vinte e sete: é declaração do produto, e
    o que ela faz é impedir uma linha que já não podia funcionar de nascer. As
    linhas que já existem não são tocadas — quem as tiver, e quiser, decide.
    """
    return _extend(ONCE_NEEDS_A_DAY)


# The permission THIS release grows the catalogue by — what migration
# twenty-nine grants. It is the `secret`'s second own act
# (`permissions.NARROWED`), the same shape migration sixteen already handed
# over for `secret:scan`: a role born before this swap carries none of it,
# because it was built from the catalogue of its own day.
HOOKS_PERMISSIONS = ("secret:install-hooks",)


def _hooks(ask: Ask | None) -> list[Report]:
    """Migração vinte e nove: `secret install-hooks`, e o teto sobre ele.

    A mesma razão da dezesseis: a linha é do AT, e a troca só ADICIONA
    (`_hand_over`). Nada mais na pasta muda — o ato escreve dois arquivos fora
    de qualquer tabela, num `.git/hooks/` que nem é parte da pasta.
    """
    return _hand_over(HOOKS_PERMISSIONS)


# A TABELA DAS NOTAS (TASK-196) — e, na MESMA migração, o nome que o lembrete
# perdeu. As duas coisas andam juntas porque a palavra "nota" nomeia UMA coisa:
# a tabela nova. O `reminder` tinha um campo com esse nome, e uma palavra que
# nomeia duas não nomeia nenhuma — o interpretador recusa a frase que diz as
# duas (`nlu.error.two_tables`).
NOTES = ("note",)


# The permissions the CATALOGUE grows by — the six the engine has, for a table
# that does not narrow itself. It is read off `tables.ACTIONS` and not spelled
# out here, so an action the engine grows is a permission this migration
# already hands over.
NOTE_PERMISSIONS = tuple(f"note:{action}" for action in tables.ACTIONS)


def _notes(ask: Ask | None) -> list[Report]:
    """Migração trinta: a tabela `note`, e o `note` que o lembrete tinha.

    **A tabela nova entra como as outras de sistema** — a declaração é
    empacotada e o `seed` a escreve onde ela está AUSENTE, e uma declaração
    que a pessoa editou continua sendo dela.

    **O campo do lembrete muda de nome**, na declaração e nas linhas: o que a
    palavra "nota" passa a nomear é a TABELA, e o conteúdo que o campo
    carregava vai com ele — um lembrete que tinha uma observação continua
    tendo uma, e com o mesmo texto.

    A renomeação é feita pela porta da DECLARAÇÃO (`schema.rename_field`) e
    pelas LINHAS por baixo: o motor sabe mudar o valor de um campo e não sabe
    TIRAR uma chave de uma linha — e uma renomeação é exatamente isso.
    """
    written = schema.seed(paths.data_dir() / schema.SCHEMA_DIR, only=NOTES)
    report: list[Report] = []
    if written:
        report.append(
            ("boot.migration.declarations.written", {"names": ", ".join(sorted(written))})
        )
    report += _remark_renamed()
    return report + _hand_over(NOTE_PERMISSIONS)


def _remark_renamed() -> list[Report]:
    """O campo `note` do `reminder` vira `remark` — na declaração e nas linhas.

    A DECLARAÇÃO pela porta que a renomeia, e as LINHAS pela loja: cada linha
    que carregava a chave antiga carrega a nova no MESMO lugar da ordem — um
    campo que muda de lugar parece outro campo —, e a chave antiga sai.

    As linhas só andam quando a pasta já fala o nome novo: uma pasta que
    declara os DOIS nomes é uma pasta em que o nome velho ainda existe, e aí
    as linhas ficam como estão.
    """
    schema.rename_field("reminder", "note", "remark")
    if schema.field("reminder", "note") or not schema.field("reminder", "remark"):
        return []

    rows = store.load("reminder")
    moved: list[str] = []
    written: list[dict] = []
    for row in rows:
        if "note" not in row:
            written.append(row)
            continue
        existing = row.get("remark")
        fresh: dict[str, object] = {}
        for name, value in row.items():
            if name == "note":
                fresh["remark"] = existing if existing is not None else value
            elif name == "remark":
                continue  # a chave nova entra no lugar da velha
            else:
                fresh[name] = value
        written.append(fresh)
        moved.append(tables.title("reminder", row))
    if not moved:
        return []
    store.save("reminder", written)
    return [("boot.migration.reminder.renamed", {"names": ", ".join(moved)})]


# O que ESTA troca acrescenta a uma declaração que JÁ está no disco — migração
# trinta e dois, a mesma forma de nove, dezessete, vinte e sete e vinte e oito.
#
# **O lembrete passa a ter UMA instância corrente**, e o campo `closed` é a
# memória dela: a pessoa fecha a ocorrência — o `(dia, hora)` que já passou — e o
# carimbo mora na linha, no mesmo formato de `notified` (`"AAAA-MM-DD HH:MM"`).
# Sem o campo na declaração, o ato de fechar é recusado (`error.unknown_field`)
# e `current` não tem onde ler que a ocorrência já foi resolvida.
REMINDER_CLOSED: dict[str, dict] = {
    "reminder": {
        "fields": {
            "closed": {
                "label": "table.reminder.field.closed",
                "filterable": True,
                "type": "list",
            }
        },
    },
}


def _reminder_closed(ask: Ask | None) -> list[Report]:
    """Migração trinta e dois: o lembrete ganha o campo que guarda os fechamentos.

    A pessoa fecha a ocorrência e o campo guarda os carimbos; a pasta que já
    existe ganha o nome na declaração, sem tocar as linhas — quem nunca fechou
    nada continua com as linhas exatamente como estavam.

    Não pergunta, pela mesma razão da vinte e sete: é declaração do produto, e o
    corpo só ACRESCENTA — o que a pessoa escreveu por cima ganha o nome no
    relato e fica onde está.
    """
    return _extend(REMINDER_CLOSED)
