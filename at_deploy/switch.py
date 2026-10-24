"""The switch between the two paths — and it is transactional or it is nothing.

path.md declares the whole of it in a paragraph, and this file is the paragraph
executed. Going from one path to the other is a **switch**: AT runs the set of
actions and, if any of them does not end successfully, everything goes back to
the previous state — "o ambiente não fica pela metade, e o que existia antes
continua funcionando". So there is no half-done state to fall into: the commit is
the LAST line, and every line before it either closes or is undone.

**The Forms stays on until the gate is PROVED in front of AT.** That is the
rule the order exists for: it is not "the container came up", it is AT
RECEIVING the identity it expects — through the real path, carrying the gate
secret the Caddy attaches and the provider never sees. Only then does the folder
record that its authenticator is the gate, and only then does the WebApp stop
asking its own Forms. Until that instant the folder is exactly what it was, and a
failure anywhere in the middle leaves it there.

**The proof is four probes, and each one answers a sentence.** The site through
the edge must answer with the GATE's refusal and not with AT's page — that is
"the gate stands in front". AT, asked directly, must take the identity the
Caddy seals — that is "AT receives what it expects". The SAME identity without
the secret must be refused (`webapp.gate_refused`) — that is the M2M being more
than a header somebody wrote. And **the PORTAL must answer**, on the address the
gate sends the browser to — because a gate that redirects every request to a
page nobody serves is a door that opens onto a wall, and the three probes above
say nothing about it: the first one only ever asked whether the edge answers
`302`, and a redirect to nowhere answers `302` too. That is the defect the
fourth probe exists for (`portal`). A probe that cannot reach anything is a
failure like any other, because "could not tell" is not "proved".

**The proof is asked ONCE per claim, and the sentence names the one that
failed.** `unproved` walks the four in the order the person meets them and
answers with the sentence of the first that did not close; `proved` is the same
walk collapsed to a boolean. The portal failing is NOT "the gate is unproved" —
that sentence blames the provider for an edge that never routes it — so it has
words of its own (`services.switch.noportal`). **And so does the first question
with no answer at all** (`services.switch.unresolved` and
`services.switch.unreachable`): "could not tell" is not "refused", and the name
this machine does not resolve and the environment that is not up are fixed in
two different places.

**Where each probe stands is the PATH's and not a preference.** The two that
speak to the EDGE — the site in front, and the portal it sends the browser to —
are asked from the HOST, because the host is what reaches the edge, which is
where the browser stands too. The other two ask AT directly, and on the
container path "directly" means from INSIDE the network: the WebApp answers
there and nowhere else (§7c), so the deploy asks through a throwaway container
of its own (`environment.inside`), on the network the edge and the app share. A
probe standing on the host would reach nothing and would read "the identity was
not taken" from a gate that is working — which is why the road is written down
here instead of left to whoever calls.

**The switch lives in `at-deploy` and not in `at-cli`.** It is an environment act
and the transactional one is the environment's (item 27); what `at-cli` keeps is
the other half of the same record — reading `authenticator` and refusing to serve
behind a gate that fell (`core/gate.py`), with the deploy artifact absent. The
record itself is ONE file, and `gate.remember` is the one door that writes it.
"""

from __future__ import annotations

import socket

from at.core import actors, files, gate, migrations
from at.i18n import tr
from at.services import caddy
from at_deploy import environment

# The outcomes, and the `cli` is what turns them into an exit code. `SWITCHED`,
# `ALREADY` and `FORMS` are answers; `FAILED` is the one that undid itself.
SWITCHED = "switched"     # the folder is on the container path now
ALREADY = "already"       # it was already where it was asked to go
FORMS_OUTCOME = "forms"   # back to the hosted path, Forms on
FAILED = "failed"         # a step did not close, and everything went back

# The statuses that mean the EDGE answered and AT did not: Authelia's own
# refusal (401) and the redirect to its portal (302 family). Anything else —
# AT's 200 page, or an edge with nobody to ask — is not the gate standing in
# front, and it is not proved.
IN_FRONT = (401, 302, 303, 307, 308)
# The status that means AT took the identity it was handed — and the one that
# means the PORTAL answered: the same number for the two claims it closes,
# because both are "the page the person needed came back".
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
    """The address the person reaches AT on — through the edge (§6).

    It is the ENVIRONMENT's site and not a constant of this file: the edge
    serves the private network's name when the machine is on one (§7e), and the
    proof, the message that closes the switch and the address a person types all
    have to be the same name or the proof is about an address nobody reaches.
    """
    return caddy.address(environment.site_host(), environment.PORT)


def _inside(path: str, headers: dict[str, str],
            answer: gate.Answer | None = None) -> int | None:
    """Ask the WebApp from INSIDE the network — the two probes of the sealed identity.

    **The road is this piece's other half, and it is measured.** The WebApp
    answers on the network and on nothing else (§7c): a probe standing on the
    host reaches nothing at all, and "reached nothing" is not a status — reading
    it as "the identity was not taken" would blame a gate that is working. So
    the probe stands where the edge stands, and the environment is what knows how
    to stand there (`environment.inside`, which asks a throwaway container on the
    same network).

    The URL is AT's own name on the network. It is built HERE because the PATH is
    what this file knows; the host is the environment's declaration, and reading
    it from there is what keeps the two from drifting.
    """
    url = (f"http://{environment.container(environment.WEBAPP)}"
           f":{environment.WEBAPP_PORT}{path}")
    return gate.ask(url, headers, answer or environment.inside)


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
    secret is the folder's own (`App/services/caddy/gate`, drawn at installation, §7b),
    and the name has to be a row AT can resolve (`actors.asserted`).

    **O segredo é lido como o CONTAINER o lê** (`environment.gate_opened`), e
    não do arquivo da pasta: o da pasta é o envelope que o selo deixou (item
    50), e uma prova que mandasse o envelope acusaria o portão de não aceitar a
    identidade que ele aceita. Sem cópia no diretório de execução não há prova —
    o ambiente não está de pé.
    """
    secret = environment.gate_opened()
    if secret is None:
        return None
    for row in actors.admins():
        name = str(row.get("name", "")).strip()
        if name and actors.may(row, PROBE_PERMISSION):
            return name, secret
    return None


def reaches(host: str) -> bool:
    """Whether this machine resolves `host` — the seam of the question below.

    **A name that does not resolve and a road with nothing behind it are two
    different failures with two different owners**, and the sentence the switch
    prints is the one that says which way to look: the DNS of the environment is
    §7a's, and pointing the machine at it is the person's act; an environment
    that is down is AT's to bring up. It is a function so that the suite can take
    the resolver away, the way it takes the agent away (`vpn.run`): a test that
    asked the machine's real DNS would answer differently on the machine where
    the name happens to resolve.
    """
    try:
        socket.getaddrinfo(host, None)
    except OSError:
        return False
    return True


def edge_status(answer: gate.Answer | None = None) -> int | None:
    """The ONE probe of the first claim: what the SITE answers through the edge.

    It is called once and only once per walk — `unproved` reads the status —, because the two
    sentences of a failed first claim are told apart BY this number: `None` is
    the road, and anything else is the gate.
    """
    return gate.ask(f"{site()}/api/session", {}, answer)


def sealed(answer: gate.Answer | None = None) -> bool:
    """Whether AT TAKES the identity the Caddy seals — the proof's core."""
    who = witness()
    if who is None:
        return False
    name, secret = who
    status = _inside("/api/state",
                     {IDENTITY_HEADER: name, caddy.GATE_HEADER: secret}, answer)
    return status == TAKEN


def unsealed(answer: gate.Answer | None = None) -> bool:
    """Whether the SAME identity without the secret is refused (§7b).

    It is the half that makes the secret worth drawing: a name alone is a header
    somebody wrote, and AT answers it with the gate's own sentence.
    """
    who = witness()
    if who is None:
        return False
    name, _ = who
    return _inside("/api/state", {IDENTITY_HEADER: name}, answer) == REFUSED


def portal(answer: gate.Answer | None = None) -> bool:
    """Whether the PORTAL answers — the fourth claim (§7b).

    It is asked through the SAME edge the person uses, and from the host, which
    is where the browser stands: the address is the one the gate redirects to
    (`environment.portal_url`), and the answer has to be the portal's own page.
    A `302` here is the loop showing itself — the edge sending the portal back
    through the ask — and a `431` is the loop after a few turns; neither is the
    page, so only `200` closes the claim.

    **It is what the first probe cannot see.** `in_front` is satisfied by the
    redirect itself, so the gate counted as standing while the browser bounced
    between the redirect and the ask until the URL died (`caddy.PORTAL`). Asking
    the destination is the difference between "something stands in front" and
    "what stands in front can be used".
    """
    return gate.ask(environment.portal_url(), {}, answer) == TAKEN


def unproved(answer: gate.Answer | None = None) -> str | None:
    """The sentence of the claim that did not close — or `None` when all close.

    Each claim is asked ONCE, in the order the person meets them, and the walk
    stops at the first failure: asking the rest would be asking about a gate
    that is already refused. The three that are about AT share one sentence
    ("the gate was not proved"); the portal has its own, because it is not the
    provider that failed — it is the edge that never routes it.

    **A primeira pergunta que não recebe resposta NENHUMA tem frase própria**, e
    por uma razão medida: ela é a que acontece com mais frequência, e as duas
    causas dela se parecem por dentro e não se parecem por fora. O nome pode não
    resolver nesta máquina — e aí o que falta é apontá-la ao DNS do ambiente
    (§7a) —, ou o ambiente pode não estar de pé. Dizer "o portão não foi provado"
    para as duas manda a pessoa procurar no lugar errado, que foi o que custou
    uma rodada de `up` e `switch` a quem escreveu isto.
    """
    status = edge_status(answer)
    if status is None:
        return ("services.switch.unresolved" if not reaches(environment.site_host())
                else "services.switch.unreachable")
    if not (status in IN_FRONT and sealed(answer) and unsealed(answer)):
        return "services.switch.unproved"
    if not portal(answer):
        return "services.switch.noportal"
    return None


def proved(answer: gate.Answer | None = None) -> bool:
    """Whether the gate is PROVED in front of AT — all four claims at once."""
    return unproved(answer) is None


# -------------------------------------------------------------- the switch ---

def to_gate(ask: environment.Ask | None = None,
            answer: gate.Answer | None = None,
            secret: environment.Ask | None = None) -> str:
    """Take this folder to the container path — transactionally (§6).

    The order IS the rule, and it is worth reading as one: the environment comes
    up, the gate is proved in front of AT, and only then is the switch
    recorded. Every step before the commit is undoable, and the one failure that
    is not the person's — the proof — takes the environment down with it, so
    "o que existia antes continua funcionando" is literally true: the folder is
    where it was, the Forms is on, and the hosted WebApp still answers.

    The two ways out of a machine without Podman are the ENVIRONMENT's answers
    and they come back unchanged: neither of them moved anything, so there is
    nothing to undo.

    `secret` é o leitor sem eco, e ele desce para o `bring_up` sem ser lido
    aqui: a Chave Principal é pedida por quem SELA (§4), e a virada é uma das
    portas por onde alguém sobe o ambiente.

    **E é `bring_up`, não `up`** (2026-09-28): a virada não é nem uma primeira
    subida garantida nem uma que `up` recusaria por a pasta já ter ambiente —
    um Forms seguido de uma virada de volta é exatamente essa segunda forma —,
    então ela toma o motor direto, sem a porta que decide qual dos dois nomes
    vale.
    """
    if gate.on_gate():
        print(tr("services.switch.already"))
        return ALREADY

    # A step that raises is a step that did not close, and the environment is
    # already half up when it does: the rollback is the same one the FAILED
    # return gets, and the exception keeps travelling afterwards — the `cli` is
    # what turns the read-only folder into its own sentence (§3).
    try:
        outcome = environment.bring_up(ask, secret)
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

    # The claim that failed is the SWITCH's to name: "not proved" for the gate
    # and its own words for a portal the edge never routes (`unproved`).
    reason = unproved(answer)
    if reason is not None:
        # As duas frases da estrada nomeiam o que a pessoa procura: a URL que
        # não respondeu, e o nome que a máquina não resolve.
        _rollback(reason, url=site(), host=environment.site_host())
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


def _rollback(reason: str, **fields: str) -> None:
    """Undo everything the switch did — the environment, and nothing else.

    The mode was never written, so there is nothing to put back there: a folder
    that did not commit is a folder that never left the hosted path. The reason
    is the SWITCH's to say and not the environment's (`down(say=False)`): what the
    person needs to read is that the switch did not close and what that leaves
    them holding.
    """
    print(tr("services.switch.rolling_back"))
    environment.down(say=False)
    print(tr(reason, **fields))


def to_forms() -> str:
    """Bring AT back to Forms mode — the Wizard's and the `cli`'s act (§6).

    It is DELIBERATE and it is the person's, and both halves are the point: the
    environment goes down and the folder records the hosted path again. Nothing
    happens on its own — a fallen gate leaves AT closed, and reopening Forms
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
