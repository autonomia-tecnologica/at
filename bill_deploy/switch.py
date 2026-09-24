"""The switch between the two paths — and it is transactional or it is nothing.

path.md declares the whole of it in a paragraph, and this file is the paragraph
executed. Going from one path to the other is a **switch**: Bill runs the set of
actions and, if any of them does not end successfully, everything goes back to
the previous state — "o ambiente não fica pela metade, e o que existia antes
continua funcionando". So there is no half-done state to fall into: the commit is
the LAST line, and every line before it either closes or is undone.

**The Forms stays on until the gate is PROVED in front of Bill.** That is the
rule the order exists for: it is not "the container came up", it is Bill
RECEIVING the identity it expects — through the real path, carrying the gate
secret the Caddy attaches and the provider never sees. Only then does the folder
record that its authenticator is the gate, and only then does the WebApp stop
asking its own Forms. Until that instant the folder is exactly what it was, and a
failure anywhere in the middle leaves it there.

**The proof is three probes, and each one answers a sentence.** The site through
the edge must answer with the GATE's refusal and not with Bill's page — that is
"the gate stands in front". Bill, asked directly, must take the identity the
Caddy seals — that is "Bill receives what it expects". And the SAME identity
without the secret must be refused (`webapp.gate_refused`) — that is the M2M
being more than a header somebody wrote. A probe that cannot reach anything is a
failure like any other, because "could not tell" is not "proved".

**The switch lives in `bill-deploy` and not in `bill`.** It is an environment act
and the transactional one is the environment's (item 27); what `bill` keeps is
the other half of the same record — reading `authenticator` and refusing to serve
behind a gate that fell (`core/gate.py`), with the deploy artifact absent. The
record itself is ONE file, and `gate.remember` is the one door that writes it.
"""

from __future__ import annotations

from bill.core import actors, files, gate, migrations
from bill.i18n import tr
from bill.services import caddy

from bill_deploy import environment

# The outcomes, and the `cli` is what turns them into an exit code. `SWITCHED`,
# `ALREADY` and `FORMS` are answers; `FAILED` is the one that undid itself.
SWITCHED = "switched"     # the folder is on the container path now
ALREADY = "already"       # it was already where it was asked to go
FORMS_OUTCOME = "forms"   # back to the hosted path, Forms on
FAILED = "failed"         # a step did not close, and everything went back

# The statuses that mean the EDGE answered and Bill did not: Authelia's own
# refusal (401) and the redirect to its portal (302 family). Anything else —
# Bill's 200 page, or an edge with nobody to ask — is not the gate standing in
# front, and it is not proved.
IN_FRONT = (401, 302, 303, 307, 308)
# The status that means Bill took the identity it was handed.
TAKEN = 200
# The status a request with an identity but no secret is owed (§7b).
REFUSED = 403

# The header the Caddy copies onto every request carrying an identity (app.py
# holds the other half, and reads it under its own name for it).
IDENTITY_HEADER = "Remote-User"

# The permission the proof's route demands, and therefore the one the witness
# has to carry: the probe reads `/api/state`, and a role that cannot reach it
# would answer 403 for a reason that has nothing to do with the gate.
PROBE_PERMISSION = "setting:read"


# ------------------------------------------------------------- the folder ---

def site() -> str:
    """The address the person reaches Bill on — through the edge (§6).

    It is the ENVIRONMENT's site and not a constant of this file: the edge
    serves the private network's name when the machine is on one (§7e), and the
    proof, the message that closes the switch and the address a person types all
    have to be the same name or the proof is about an address nobody reaches.
    """
    return caddy.address(environment.site_host(), environment.PORT)


def _loop(path: str) -> str:
    """Bill's own address, on the loop, where only the Caddy reaches it."""
    return f"http://{environment.WEBAPP_HOST}:{environment.WEBAPP_PORT}{path}"


# --------------------------------------------------------------- the proof ---

def witness() -> tuple[str, str] | None:
    """The name the proof speaks as, and the secret it must carry.

    **A person whose role actually reaches the probe's route**, and that is not
    the same thing as "somebody with a credential": the only read the WebApp
    answers below the gate demands `setting:read`, and a role that does not carry
    it answers 403 — a status this proof would read as "the identity was not
    taken" while it was, blaming a gate that is working. `actors.may` is the same
    door the route asks through, so the witness is chosen by the question the
    route is going to make.

    No witness is a real answer, and `to_gate` says it in its own words: the
    secret is the folder's own (`App/caddy/gate`, drawn at installation, §7b),
    and the name has to be a row Bill can resolve (`actors.asserted`).
    """
    secret = caddy.gate_secret()
    if secret is None:
        return None
    for row in actors.admins():
        name = str(row.get("name", "")).strip()
        if name and actors.may(row, PROBE_PERMISSION):
            return name, secret
    return None


def in_front(answer: gate.Answer | None = None) -> bool:
    """Whether the gate answers for Bill — the edge in front, through the site.

    Asked of a route that is ABOVE the gate (`/api/session`, which the entrance
    needs before anybody is in): without the gate in front, Bill answers it with
    its own 200 page; with the gate there, the answer is Authelia's refusal.
    """
    return gate.ask(f"{site()}/api/session", {}, answer) in IN_FRONT


def sealed(answer: gate.Answer | None = None) -> bool:
    """Whether Bill TAKES the identity the Caddy seals — the proof's core."""
    who = witness()
    if who is None:
        return False
    name, secret = who
    status = gate.ask(_loop("/api/state"),
                      {IDENTITY_HEADER: name, caddy.GATE_HEADER: secret}, answer)
    return status == TAKEN


def unsealed(answer: gate.Answer | None = None) -> bool:
    """Whether the SAME identity without the secret is refused (§7b).

    It is the half that makes the secret worth drawing: a name alone is a header
    somebody wrote, and Bill answers it with the gate's own sentence.
    """
    who = witness()
    if who is None:
        return False
    name, _ = who
    return gate.ask(_loop("/api/state"), {IDENTITY_HEADER: name}, answer) == REFUSED


def proved(answer: gate.Answer | None = None) -> bool:
    """Whether the gate is PROVED in front of Bill — all three sentences at once."""
    return in_front(answer) and sealed(answer) and unsealed(answer)


# -------------------------------------------------------------- the switch ---

def to_gate(ask: environment.Ask | None = None,
            answer: gate.Answer | None = None) -> str:
    """Take this folder to the container path — transactionally (§6).

    The order IS the rule, and it is worth reading as one: the environment comes
    up, the gate is proved in front of Bill, and only then is the switch
    recorded. Every step before the commit is undoable, and the one failure that
    is not the person's — the proof — takes the environment down with it, so
    "o que existia antes continua funcionando" is literally true: the folder is
    where it was, the Forms is on, and the hosted WebApp still answers.

    The two ways out of a machine without Podman are the ENVIRONMENT's answers
    and they come back unchanged: neither of them moved anything, so there is
    nothing to undo.
    """
    if gate.on_gate():
        print(tr("services.switch.already"))
        return ALREADY

    # A step that raises is a step that did not close, and the environment is
    # already half up when it does: the rollback is the same one the FAILED
    # return gets, and the exception keeps travelling afterwards — the `cli` is
    # what turns the read-only folder into its own sentence (§3).
    try:
        outcome = environment.up(ask)
    except (files.ReadOnly, OSError):
        _rollback("services.switch.failed")
        raise
    if outcome != environment.UP:
        if outcome == environment.FAILED:
            _rollback("services.switch.failed")
        return outcome

    if witness() is None:
        # Nothing to prove WITH: no row the gate could assert and the probe could
        # read. It is not the gate's fault and it is said as its own thing.
        _rollback("services.switch.nowitness")
        return FAILED

    if not proved(answer):
        _rollback("services.switch.unproved")
        return FAILED

    # The commit, and the only line that changes what this folder IS. A folder
    # that refuses the write — the read-only switch, §3, or a disk that says no —
    # refuses the switch with it, and the environment the swap brought up goes
    # with the rollback: the commit IS the switch, and there is no state where it
    # half-exists.
    try:
        gate.remember(gate.GATE)
    except (files.ReadOnly, OSError):
        _rollback("services.switch.failed")
        raise

    print(tr("services.switch.done", url=site()))
    return SWITCHED


def _rollback(reason: str) -> None:
    """Undo everything the switch did — the environment, and nothing else.

    The mode was never written, so there is nothing to put back there: a folder
    that did not commit is a folder that never left the hosted path. The reason
    is the SWITCH's to say and not the environment's (`down(say=False)`): what the
    person needs to read is that the switch did not close and what that leaves
    them holding.
    """
    print(tr("services.switch.rolling_back"))
    environment.down(say=False)
    print(tr(reason))


def to_forms() -> str:
    """Bring Bill back to Forms mode — the Wizard's and the `cli`'s act (§6).

    It is DELIBERATE and it is the person's, and both halves are the point: the
    environment goes down and the folder records the hosted path again. Nothing
    happens on its own — a fallen gate leaves Bill closed, and reopening Forms
    without anybody deciding would be trading security for convenience. Both
    doors that reach this are LOCAL: the Wizard and the `cli`.
    """
    if not gate.on_gate():
        print(tr("services.forms.already"))
        return ALREADY
    # The record first, and the environment after: a folder that refuses the
    # write (the read-only switch) refuses the return with it, and nothing has
    # moved yet — the environment still stands, and the path is still the one it
    # was, which is the state the person found.
    gate.remember(gate.FORMS)
    environment.down()
    print(tr("services.forms.done"))
    return FORMS_OUTCOME


def missing(ask: environment.Ask | None = None) -> str:
    """§6's question, for a folder whose environment is not there.

    "Foi detectado que você tem um ambiente de infraestrutura configurado nesse
    ambiente, mas o ambiente de infraestrutura não foi encontrado" — the backup
    promise showing up on the screen: the folder came back, and what was missing
    was only the ground. It is asked where the absence of the Podman is noticed
    (`environment.ways_out`), and it is the SWITCH's to ask and not the
    environment's, because the two ways out here are not the same two: this
    folder is on the container path already, so "continue on the hosted path" is
    not a thing that can happen on its own — restoring it IS the second way out,
    and it moves the record.

    A folder that chooses to install gets the same answer the first offer gives;
    a folder that chooses to restore gets its Forms back, which is `to_forms`
    and everything that means.
    """
    if ask is None:
        print(tr("services.missing.no_tty"))
        return environment.NO_ANSWER
    if migrations.is_yes(ask(tr("services.missing.ask"))):
        print(tr("services.no_podman.install"))
        return environment.INSTALL
    to_forms()
    return environment.HOSTED
