"""The door's risk and ceiling: who may, who waits, and the line a refusal owes.
"""

from __future__ import annotations

from at import nlu
from at.core import (
    actors,
    audit,
    permissions,
    risk,
    versioning,
)


def ceiling(actor: dict | None, proposal: nlu.Proposal) -> str | None:
    """The permission this proposal needs that the actor's role does not carry, or
    `None` when the act is the actor's to make (§5).

    It is `actors.may` and no rule of its own: the actor's row points at the role,
    the catalogue says what the role carries, and the permission asked is the one
    the proposal NAMES — `table:action`, the same form the routes demand, because
    the interpreter's proposal is a table action like any other. It returns the
    NAME and not a bool so the refusal can say which permission was missing, in
    the catalogue's own label.

    A sentence the interpreter did not read never gets here — there is no proposal
    to ask about — and neither does a folder asking nobody: no actor is no ceiling,
    and the door keeps answering as it always did.

    The permission is `permissions.needed` and not the action's own name written
    out here: a table may narrow itself (`secret` answers `read` and `edit`), and
    a ceiling that composed the name its own way would refuse an act the role
    carries.
    """
    if actor is None:
        return None
    needed = permissions.needed(proposal.table, proposal.action)
    return None if actors.may(actor, needed) else needed


def holds(measured: float, *, actor: dict | None, via: str) -> bool:
    """Whether this demand WAITS for a person: at or above the bar, and nobody
    present to answer (§4, item 15).

    **Who waits is about presence, not about type.** An act a person types or
    clicks never waits: the act IS the approval, and asking again would be
    theatre. An act that runs on its own waits at or above the threshold,
    because the one who cannot ask is the one who waits — and the two marks of
    that absence are the via `engine`, which is AT acting by itself, and an
    actor that is a MACHINE, which is what the `agent` of §4 is.

    **A folder asking nobody is a person at the terminal**, so `None` waits for
    nothing: §3's loopback with no credential is a person in front of the
    machine, and the `cli` is local by construction — the same reading that
    gives an act typed there the first admin as its actor.

    It reads `risk.waits` for the number and nothing of its own: the boundary is
    §4's (at or above it waits), the boundary the ruler draws on the page, and a
    second comparison here would be the one that drifts.
    """
    return risk.waits(measured) and not present(actor, via)


def present(actor: dict | None, via: str) -> bool:
    """Whether a PERSON is present in this act — whoever can answer it.

    The engine's via is AT acting on its own, and an actor whose `type` is not
    `person` is the machine of §4: neither is somebody who can be asked, and
    both are therefore what the filter holds. A row a hand edited to a type
    nobody declares is read as a machine for the same reason every strange
    declaration fails closed — the absence of a person is what waits, and only
    the word `person` says one is there.
    """
    if via == audit.ENGINE:
        return False
    return actor is None or actor.get("type") == "person"


def denied(
    table: str,
    action: str,
    *,
    actor: dict | None = None,
    via: str = audit.ENGINE,
    reason: str,
    saying: str,
) -> None:
    """A refusal the CEILING made, recorded — the line a wall owes (§3).

    It is called where an act is refused BEFORE the engine sees it — the
    interpreter's ceiling, and the page's route — because the engine's own
    refusals are recorded by `run`, which is where they are raised. `saying` is
    the sentence the surface printed, so the version the line ends in is named by
    the words the person read.
    """
    _line(table, action, actor, via, audit.REFUSED, reason, saying)


def _line(
    table: str,
    action: str,
    actor: dict | None,
    via: str,
    status: str,
    reason: str | None,
    saying: str,
    *,
    threshold: float | None = None,
) -> None:
    """The line, and the version it ends in — the two halves of one write.

    They belong together because a line nothing versions is a folder left dirty
    (§4, item 30), and the version is named by the sentence the surface printed:
    one wording for the person, the log and `git log`.

    `threshold` is the bar the demand faced, read when it ARRIVED (`_arrival`),
    and handed in because one demand moves it: `setting:edit` on
    `risk_threshold` changes the number the line is about.
    """
    audit.log(
        table, action, actor=actor, via=via, status=status, reason=reason,
        threshold=threshold,
    )
    versioning.commit(saying)


def _arrival() -> float:
    """The bar in force when the demand arrived — the one it is measured against.

    Read once, at the door, before anything runs: it is the core that measures a
    demand and never whoever asks (§4), and a bar read after the act would be the
    bar the act left behind instead of the one that governed it.
    """
    return risk.threshold()
