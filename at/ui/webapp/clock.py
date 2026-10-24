"""The clock's rhythm and the thread that keeps it (§4, item 24): `start_clock`
raises the pre-declared backup job and the daemon thread, and `beat` is the
loop that thread runs (the job round, the reminders, the Vault's `Watcher` and
the page's `vigia`).

Moved out of `app.py` (B-6) without a change of behaviour. Nothing here knows the
`Handler`: the only thing it asks of the server is its `events` broadcaster.
`app.py` imports the names back.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Callable

from at import i18n
from at.core import (
    actors,
    backup,
    clock,
    files,
    jobs,
    paths,
    strongbox,
    tables,
    vigia,
)
from at.data import store
from at.ui import ask as door
from at.ui.webapp import keys

if TYPE_CHECKING:
    from at.ui.webapp.app import Server

# The clock's thread, by name (§4, item 24). It is named because a thread with
# no name is a thread nobody can find: a person reading a dump of the process,
# and the test that proves the RAW server does not start one.
CLOCK_THREAD = "at-clock"


def _declare_backup() -> None:
    """O job do backup, pré-declarado UMA vez, na subida do processo que mantém
    o relógio (§4, item 24; TASK-133).

    **É pré-declarado aqui porque a `cli` que declara um job agendado ainda não
    existe** (TASK-139): enquanto ela não chega, quem põe a linha é a subida, e
    ela é idempotente — uma linha de `backup:make` que já exista NÃO é tocada
    nem recriada, seja qual for o estado em que uma pessoa a tenha deixado
    (desligar de verdade é o verbo da TASK-139, não desta subida).

    **O dono é o primeiro administrador.** §4 diz que o job roda com a autoridade
    de quem o possui, e uma pasta sem pessoa nenhuma não tem a quem dar o job —
    então ela não declara nada, e nada se perde: sem administrador não há a quem
    avisar de um backup que não saiu.

    O `when` inicial é AGORA, e o relógio o reescreve a cada rodada; quem decide
    se a cópia sai é a cadência própria do backup (`backup.due`), nunca o `when`.
    """
    if files.readonly():
        return
    owner = actors.first_admin()
    if owner is None:
        return
    declared = jobs.what(backup.OBJECT, backup.MAKE)
    if any(
        isinstance(row, dict) and row.get(jobs.WHAT) == declared
        for row in store.load(jobs.JOB)
    ):
        return
    tables.create(
        jobs.JOB,
        {
            jobs.WHAT: declared,
            jobs.TABLE: backup.OBJECT,
            jobs.ARGUMENTS: [],
            jobs.ACTOR: store.number_of(owner),
            jobs.WHEN: tables.utc(clock.now()),
            jobs.STATUS: jobs.SCHEDULED,
        },
    )


def start_clock(server: "Server") -> None:
    """O relógio, de pé — o backup pré-declarado e a THREAD daemon que
    `beat` roda nela (§4, item 24).

    **Uma função só porque duas subidas precisam das duas mesmas linhas**:
    `run`, e o modo local (`at.ui.webapp.local`, TASK-169, fatia 1/3) — as
    duas erguem o MESMO relógio, pelo mesmo motivo, e repeti-lo seria a cópia
    que um dia diverge.
    """
    _declare_backup()
    threading.Thread(target=beat, args=(server,), daemon=True, name=CLOCK_THREAD).start()


def beat(server: "Server | None" = None, times: int | None = None,
         pause: Callable[[float], None] = time.sleep) -> None:
    """The clock's rhythm: one pass, then the cadence, over and over (§4, item 24).

    **The WebApp is where the clock lives, and it is the process AT already
    raises.** A job has no clock of its own, and the process that manages it IS
    this one — which is exactly why item 24 puts the clock here, and why the
    clock leaves the day the engine does. It is a THREAD and not a loop inside
    `serve_forever`: the two do not know each other, so a pass neither waits for
    a request nor blocks one.

    **A pass that raises does not take the clock down.** A clock that stopped is
    a folder whose jobs stopped with it, and nobody to say so — so the failure is
    said (in AT's words, with the machine's message inside, because a bug's text
    is the only thing that can be diagnosed from) and the rhythm goes on. The
    reminder's round (§4, item 29's second slice) shares the pass and the same
    guard: the two rounds do not know about each other, so one that raises does
    not take the other down either.

    **The reminder's round is handed the notifier's derived key, read at
    `keys.boot` and kept nowhere but this process's memory** (§4, item 50): a
    boot with no key still rounds — `notifier.publish` answers `no_token`
    rather than sending an envelope nobody here could open.

    **The Vault's round shares the same guard, and its own `Watcher` is born
    once, here** (TASK-154): a `strongbox.Watcher` holds the pasta's retrato
    and the writes still settling between two rounds, so it has to be the
    SAME object across the whole rhythm and not one built fresh inside the
    loop — a fresh one every round would never see a write settle, because
    settling is read against the round before. It rounds on the job clock's
    own cadence and not a faster one of its own: a Vault is not a chat, and
    one more thread with one more rhythm is a cost this fatia does not ask
    for.

    **A quarta rodada é o vigia da página, e só existe com um `server`**
    (TASK-128, fatia 2/3): o que ele vigia é `Arquivos/`
    (`paths.prose_dir()`) — a mesma pasta que `FileTree.vue` relê hoje ao
    cutucar —, e o que ele faz ao ver uma escrita é publicar no
    `Broadcaster` do servidor (`server.events`), que repassa para toda aba
    com uma conexão `/api/events` aberta. `server` é `None` nos testes que
    só provam as outras rodadas (`TheProcess`, abaixo) — sem servidor não há
    `Broadcaster` para publicar em, e a rodada simplesmente não nasce, como
    sempre foi antes desta fatia.

    `times` and `pause` are the seams a test drives: the pass is proven with the
    instant handed to `at.ui.ask.tick`, and these are how the same pass is
    proven without the machine's hour and without sleeping through a cadence.
    """
    watcher = strongbox.Watcher()
    page_vigia = None
    if server is not None:
        page_vigia = vigia.Vigia(paths.prose_dir())
        page_vigia.watch(lambda event: server.events.publish())
    done = 0
    while times is None or done < times:
        try:
            door.tick()
        except Exception as error:  # noqa: BLE001 — the clock does not die of a pass
            print(i18n.tr("webapp.clock_failed", error=error))
        try:
            door.remind(key=keys.notifier_key())
        except Exception as error:  # noqa: BLE001 — same guard, the other round
            print(i18n.tr("webapp.clock_failed", error=error))
        try:
            watcher.tick(keys.strongbox_key())
        except Exception as error:  # noqa: BLE001 — same guard, the third round
            print(i18n.tr("webapp.clock_failed", error=error))
        if page_vigia is not None:
            try:
                page_vigia.scan()
            except Exception as error:  # noqa: BLE001 — same guard, the fourth round
                print(i18n.tr("webapp.clock_failed", error=error))
        done += 1
        if times is None or done < times:
            pause(_rest(clock.CADENCE.total_seconds()))


def _rest(period: float) -> float:
    """The seconds until the next boundary of `period` — the beat lands ON the
    grid instead of drifting a little later with every pass.

    Com a cadência no minuto, um passo que derrapa (a cadência MAIS o trabalho
    da passada, a cada passada) acaba pulando um minuto inteiro — e um lembrete
    marcado para esse minuto não toca. Dormir até a PRÓXIMA borda reseta a
    deriva a cada passada, e é o que faz "toca às 18h00" valer mesmo depois de
    horas de batida.
    """
    return period - (time.time() % period)
