"""The backup's round as the door answers it (`backup:make` on the clock).
"""

from __future__ import annotations

from at.core import (
    backup,
    clock,
    notifier,
    secrets,
)
from at.i18n import tr
from at.ui.ask_base import OK, USAGE, rejected

# --------------------------------------------------------------- the backup ---


def backup_message(action: str, outcome: backup.Report, target: str) -> str:
    """The sentence one act of `backup` ends in — the ONE home of the wording,
    read by the `cli`'s terminal line and by the push the clock sends when the
    automatic copy did not go out.

    It lived in `at.ui.cli` while the terminal was its only reader; the clock's
    round is the second, and a second sentence for the same fact would be the
    two that drift. `core.backup` answers in facts (a state, a tool) and never
    in words, which is why the composition is here and not there.
    """
    if action == backup.MAKE:
        if outcome.state == backup.MADE:
            return tr("backup.make.done", destination=target)
        if outcome.state == backup.BLOCKED:
            return tr("backup.make.blocked")
        if outcome.state == backup.NO_TOOL:
            return tr("backup.make.no_tool", tool=outcome.tool)
        return tr("backup.make.failed", tool=outcome.tool, destination=target)
    if outcome.state == backup.RESTORED:
        return tr("backup.restore.done")
    if outcome.state == backup.NOT_FOUND:
        return tr("backup.restore.not_found", where=target)
    if outcome.state == backup.NOT_FRESH:
        return tr("backup.restore.not_fresh")
    return tr("backup.restore.wrong_key")


def _main_key() -> str | None:
    """The Main Key in memory this boot, or `None` (§4, item 50) — the natural
    candidate for the phrase nobody types.

    It is read off the HOSTED path's in-memory copy (`at.ui.webapp.keys`), and
    the container path never has it: there it answers `None`, and the round says
    the truth instead of pretending it copied. The import is LAZY — the same
    door `versioning.ways_out` takes to avoid a cycle: the key is only asked for
    when the round is genuinely about to copy. A test injects it the way it
    injects the notifier's: `at.ui.webapp.keys.keep_main_key`.
    """
    from at.ui.webapp import keys  # noqa: PLC0415 — a mesma porta de `ways_out`

    return keys.main_key()


def _backed(action: str) -> tuple[
    int, str, dict | None, tuple[list[str], list[list[str]]] | None, list[str] | None
]:
    """One round of the BACKUP's declared job — the act `backup:make` that runs
    on its own (§4, item 24; TASK-133).

    **The cadence is the backup's own, and it is read before anything else.** The
    clock brings this round every minute; the copy only leaves when the interval
    the folder chose has passed since the last attempt (`backup.due`). A round
    that is not due does nothing, leaves no stamp and says nothing — it asks
    again on the next pass. With no destination declared there is nowhere to
    copy to, and the round is that same silence: an unconfigured backup is not
    an event, and the moment the person declares a destination it starts working.

    **The phrase comes from the Main Key, and the round never fakes it.** A boot
    with no Key in memory — the container path, a host that never brought one —
    does not copy: it marks the attempt and sends ONE notice that the copy did
    not go out, so the person learns it from the phone rather than from a folder
    that quietly stopped protecting itself. The mark is what keeps the notice to
    once per interval instead of every minute. The same one-notice-per-interval
    is what a copy the scan blocked or the tool refused gets.

    **`restore` is never scheduled.** It lays the archive over the current
    folder, and an act shaped like a wipe fired with nobody asking is the loss
    the backup exists to prevent — refused by name, like any act this door does
    not answer.

    The answer is the engine's in both surfaces: what the terminal would print is
    what the notice carries, because both read `backup_message`.
    """
    if action != backup.MAKE:
        return USAGE, rejected(action), None, None, None
    at = clock.now()
    target = backup.destination()
    if not target or not backup.due(at):
        return OK, tr("backup.make.auto.waited"), None, None, None
    key = _main_key()
    if key is None:
        notice = tr("backup.make.no_key")
        notifier.publish(notifier.TITLE, notice)
        backup.attempted(at)
        return OK, notice, None, None, None
    try:
        report = backup.make(lambda: key, target)
    except (secrets.SecretsError, OSError) as error:
        # A Key too short to derive from, a destination the filesystem refused:
        # the round answers it the way the `cli` does — one sentence, no crash —
        # and the notice carries the same words the terminal would.
        notice = tr("backup.make.notice", reason=str(error))
        notifier.publish(notifier.TITLE, notice)
        backup.attempted(at)
        return OK, notice, None, None, None
    if report.state == backup.MADE:
        backup.attempted(at)
        return OK, backup_message(action, report, target), None, None, None
    notice = tr("backup.make.notice", reason=backup_message(action, report, target))
    notifier.publish(notifier.TITLE, notice)
    backup.attempted(at)
    return OK, notice, None, None, None
