"""The door's reads and pushes: `remind`, `scan`, `install_hooks`, `reminder_due`, `assist_preview`.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from at import i18n
from at.core import (
    assist,
    clock,
    files,
    hooks,
    jev,
    notifier,
    permissions,
    reminder,
    scanner,
    tables,
)
from at.i18n import tr
from at.services import gitleaks
from at.ui.ask_base import OK, REFUSED, USAGE, rejected
from at.ui.ask_listing import rendered

# --------------------------------------------------------- the reminder's push ---


def remind(
    now: datetime | None = None,
    key: bytes | None = None,
    send: Callable[..., tuple[bool, str]] | None = None,
) -> list[dict]:
    """One round of the clock's OTHER schedule: the reminders THIS PASS is about
    (§4, item 29's second slice — TASK-145).

    **Two schedules share one clock, and they are not the same shape.** A job's
    round faces the bar and moves an instant on at the MINUTE's grain (`tick`);
    a reminder names the HOURS of its day (`at`: `["09:00", "18:00"]` — the
    water six times, the medicine at its two doses) and its grain is the
    (day, HOUR). `reminder.occurs` says the DAY, `reminder.hours` says the
    hours, and this round fires an hour when its pass COVERS it (`_covers`: the
    marked minute and the cadence after it). An hour the round was not up for is
    not owed — a server that was down at 11:00 does not fire the 11:00 at noon.

    **What keeps an hour from pushing on every pass that covers it is
    `reminder.notified`, asked before a send and written only after one that
    WENT OUT (`mark_notified`, per (day, hour)): a push that failed is retried
    on the next pass that covers the hour, the same "not in a loop, but not
    given up on either" the round's own bookkeeping already gives a job that a
    wall or a network refused. The guard is per HOUR and not per day: the 09:00
    of a six-times-a-day reminder must not cover its 11:00.

    **`due` wins the hour's push, `warn` gets its own text.** The two lists
    `reminder.due` answers never share a row for the same occurrence (that
    module's own rule), so a row read here is asked for exactly one of the two
    sentences below.

    **O push agora leva um botão que FECHA a ocorrência dali.** Cada aviso
    carrega, em `data`, qual lembrete e qual instância ele está anunciando, e
    em `actions` o botão `close` com o texto de `reminder.push.close`. Fechar
    pela notificação é o MESMO ato da tela — a mesma rota, a mesma porta, a
    mesma linha de auditoria e a mesma versão —, e não um segundo caminho de
    escrita: o Service Worker só chama a rota que a tela já chama. A instância
    anunciada é `(today, hour)` para uma linha de `due`; para uma de `warn` é a
    ocorrência FUTURA sobre a qual o aviso fala — o primeiro dia de
    `warn_days`, em ordem crescente, em que a recorrência cai —, porque fechar
    o aviso antecipado é fechar a ocorrência que ele anuncia, e não a de hoje.
    Uma ocorrência já em `closed` — a anunciada, que para `due` é a de hoje —
    não é avisada de novo.

    `now` is the instant this pass reads (`datetime.now` when `None`) — the day
    AND the hour come off it, which is why the round can no longer be handed a
    bare calendar — `key` is the derived key this boot holds for the notifier's
    scope (`None` is a boot with nothing to open the credential with, and
    `notifier.publish` answers `no_token` for it rather than sending an envelope
    nobody could read on the other end), and `send` is the seam a test drives
    instead of reaching the network (`notifier.publish` when `None`).

    The rows this pass actually pushed for come back, the way `tick`'s rounded
    rows do, so a caller can say what happened without reading the store back.
    """
    if files.readonly():
        return []
    moment = now if now is not None else datetime.now()
    today = moment.date()
    push = send if send is not None else notifier.publish
    found = reminder.due(today)
    fired: list[dict] = []
    for rows, said, warned in (
        (found["due"], "reminder.push.due", False),
        (found["warn"], "reminder.push.warn", True),
    ):
        for row in rows:
            announced = _announced_day(row, today) if warned else today
            if announced is None:
                continue
            for hour in reminder.hours(row):
                if (
                    not _covers(hour, moment)
                    or reminder.notified(row, today, hour)
                    or reminder.closed(row, announced, hour)
                ):
                    continue
                ok, _ = push(
                    notifier.TITLE,
                    tr(said, text=row.get("text", "")),
                    key=key,
                    data={
                        "reminder": row.get("id"),
                        "instance": f"{announced.isoformat()} {hour}",
                    },
                    actions=[{"action": "close", "title": tr("reminder.push.close")}],
                )
                if ok:
                    reminder.mark_notified(row, today, hour)
                    if row not in fired:
                        fired.append(row)
    return fired


def _announced_day(row: dict, today: date) -> date | None:
    """O dia da ocorrência que um aviso de `warn` anuncia — o primeiro `warn_days`.

    `warn_days` pode ser `[3, 1]`; um aviso vale para a ocorrência MAIS PRÓXIMA
    que a janela alcança, então a leitura é em ordem crescente e para no
    primeiro dia em que a recorrência cai. É esse dia, e não `today`, que o
    botão de fechar deve fechar.
    """
    for days in sorted(reminder._warn_days(row)):
        when = today + timedelta(days=days)
        if reminder.occurs(row, when):
            return when
    return None


def _covers(hour: str, moment: datetime) -> bool:
    """Whether THIS pass covers `hour` (`HH:MM`) — the marked minute and the
    clock's cadence after it, and no later.

    É o que faz "toca às 09:00" valer sem tocar o dia inteiro na primeira
    passada, e o que faz uma hora que passou com o servidor fora simplesmente
    não ser devida: a passada de meio-dia não cobre as onze.
    """
    start = int(hour[:2]) * 60 + int(hour[3:])
    current = moment.hour * 60 + moment.minute
    return start <= current < start + int(clock.CADENCE.total_seconds() // 60)


# -------------------------------------------------------------- the scan ---


# The last answer `scan` read, kept for the surfaces that say the findings as data.
last_scan: scanner.Report | None = None


def scan(args: list[str]) -> tuple[int, str]:
    """`secret scan` — the folder says what it carries that it should not (item 51).

    **The act is the table's own, and it does not walk `run`.** `scan` is not one
    of the engine's six: it reads the folder and rewrites no row of any table, so
    it is no `create`, no `edit` and no `cancel`, and the engine has nothing to
    do for it. What this door owns is the WORDS — the scanner answers in facts (a
    state, the tool, the findings) and what a person reads is composed here, so
    the `cli`, and any surface that comes after it, read one sentence.

    **A read leaves nothing of the person's (§3).** There is no actor and no via
    in the signature because there is no line to write and nothing to version:
    the scan changes nothing of the folder it reads, which is exactly what makes
    it a read. The one thing it can write is AT's own — `App/services/gitleaks/`, where
    the scanner the artifact carries is unpacked the first time it is asked for
    (`scanner.found`) — and that is AT's tool in AT's folder, the same sense
    `App/services/caddy/` is. What it also does not do is decide anything about the
    ceiling: the catalogue names `secret:scan` and the role that carries it, and a
    surface that has to refuse without it — the page's routes — writes that line
    itself, the way every other route does.
    """
    if args:
        return USAGE, rejected(permissions.SCAN)
    answer = scanner.scan()
    # What a surface that says it as data (`at-cli --json`) reads beside the text.
    global last_scan
    last_scan = answer
    if answer.state == scanner.NO_TOOL:
        # The ways out, and the whole of what AT does about a scanner that is not
        # there: it says them and it installs NOTHING (§7a, the Podman the
        # `certutil` word already follows). What failed is the EXTRACTION — the
        # `gitleaks` travels inside the binary —, so the platform is named: it is
        # what tells "this artifact is not mine" from "this folder is not mine".
        return REFUSED, "\n".join(
            (
                tr("secrets.scan.no_tool", platform=gitleaks.label()),
                tr("secrets.scan.ways"),
            )
        )
    if answer.state == scanner.FAILED:
        return REFUSED, tr("secrets.scan.failed")
    # The rule list said out loud: which scanner, and which version of it, stood
    # behind what follows — the only honest answer to "a list that ages".
    lines = [tr("secrets.scan.rules", tool=answer.tool)]
    if answer.state == scanner.CLEAN:
        lines.append(tr("secrets.scan.clean"))
        return OK, "\n".join(lines)
    lines.append(tr("secrets.scan.found"))
    lines += [_shown(finding) for finding in answer.findings]
    return OK, "\n".join(lines)


def _shown(finding: scanner.Finding) -> str:
    """One finding as a person reads it: the rule and WHERE — never the value.

    The commit is cut to its short form because that is the spelling a person
    pastes into `git show`, and the whole hash is noise on a line. A finding the
    files as they are already carry has no commit, and the sentence says less
    because there is less to say.
    """
    where = f"{finding.where}:{finding.line}" if finding.line else finding.where
    if finding.commit:
        return tr(
            "secrets.scan.committed",
            rule=finding.rule,
            where=where,
            commit=finding.commit[:7],
        )
    return tr("secrets.scan.finding", rule=finding.rule, where=where)


def install_hooks(args: list[str]) -> tuple[int, str]:
    """`secret install-hooks` — the varredura becomes `git`'s own portão.

    **The act is the table's own, and it does not walk `run`.** It writes two
    files into a repository's own `.git/hooks/` and no row of any table, so it
    is no `create`, no `edit` and no `cancel` — `core.hooks` is composed the
    same way `core.scanner` already is.

    `--repo <path>` is the one argument: left out, the repository protected is
    the Working Folder running this command (an AT user's own data); said, it
    is ANY repository — chiefly a product checkout, which §3 never lets become
    a Working Folder, so there has to be a way to point this act at one that
    is not.
    """
    repo: Path | None = None
    rest = list(args)
    if rest[:1] == ["--repo"]:
        if len(rest) != 2 or not rest[1]:
            return USAGE, rejected(permissions.INSTALL_HOOKS)
        repo = Path(rest[1])
        rest = []
    if rest:
        return USAGE, rejected(permissions.INSTALL_HOOKS)
    report = hooks.install(repo)
    if report.state == hooks.NOT_A_REPO:
        return REFUSED, tr("secrets.hooks.not_a_repo", where=str(report.target))
    return OK, tr("secrets.hooks.installed", where=str(report.target))


# ----------------------------------------------------------- the reminder ---


def reminder_due(args: list[str]) -> tuple[int, str]:
    """`reminder due` — which reminders a DAY is about (item 29's first slice).

    **The act is the table's own, and it does not walk `run`.** `due` is not one
    of the engine's six: it reads the store and rewrites no row, the way `scan`
    reads the folder and rewrites none — so it is a read on §4's scale, with no
    actor and no via in the signature and no line to leave.

    **The day is `--at`, and it defaults to today — the engine's own, never the
    machine's read a second time here.** A day already past is not refused: the
    fatia this door belongs to is decision, checkable against any day, and the
    push that reaches a phone on the day itself is another slice's work.
    """
    at = reminder.today()
    rest = list(args)
    if rest[:1] == ["--at"]:
        if len(rest) != 2:
            return USAGE, tr("reminder.due.error.arguments")
        try:
            at = date.fromisoformat(rest[1])
        except ValueError:
            return USAGE, tr("reminder.due.error.arguments")
        rest = []
    if rest:
        return USAGE, tr("reminder.due.error.arguments")
    found = reminder.due(at)
    lines = [tr("reminder.due.today", date=at.isoformat())]
    lines.append(
        rendered(reminder.REMINDER, found["due"]) if found["due"] else tr("table.word.empty")
    )
    lines.append("")
    lines.append(tr("reminder.due.warn"))
    lines.append(
        rendered(reminder.REMINDER, found["warn"]) if found["warn"] else tr("table.word.empty")
    )
    return OK, "\n".join(lines)


# -------------------------------------------------------------- the assist ---


def assist_preview(text: str, *, language: str | None = None, main_key: str | None = None) -> tuple[int, str]:
    """`assist "<frase>"` — what Jev would propose for `text`, without ever
    running it (TASK-180, fatia 2/3).

    **The act is a READ, the way `scan` and `reminder_due` already are.**
    Nothing of the folder changes for having asked, so there is no actor, no
    via, and no line or version to leave — what this door owns is the
    SENTENCE, so the `cli` and any surface that comes after it read the same
    one.

    `main_key` is handed in rather than read here: the Vault's credential is
    opened by `at.core.assist`, and a surface that read the vault itself
    would be a second door into it.
    """
    found = assist.preview(text, language=language or i18n.active_code(), main_key=main_key)
    if found is None:
        return REFUSED, tr("assist.preview.none")
    return OK, tr(
        "assist.preview.line",
        action=_jev_label(found.action, is_action=True),
        action_confidence=f"{found.action_confidence:.2f}",
        table=_jev_label(found.table, is_action=False),
        table_confidence=f"{found.table_confidence:.2f}",
        tier=tr(f"assist.preview.tier.{found.tier}"),
    )


def _jev_label(canonical: str, *, is_action: bool) -> str:
    """One of Jev's two answers, in the engine's own words — `jev.NONE` reads
    the same dash a proposal's empty fields already do."""
    if canonical == jev.NONE:
        return tr("table.word.none")
    return tr(f"table.action.{canonical}") if is_action else tables.table_name(canonical)
