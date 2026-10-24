"""The portão of the Handler: the LOCAL MODE's token (`_local_gate`), who this
request proved (`_asks`, `_in`, `_opened`, `_proved`, `_sealed`, `_forged`,
`_challenge`), the gate itself and the ceiling (`_gate`, `_may`, `_legal`,
`_actor`), and the three doors above the gate: the Working Folder's
confirmation, the first administrator and the Forms entrance (`_post_folder`,
`_post_first`, `_post_session`).

Moved out of `app.py` (B-6) without a change of behaviour. `GateRoutes` is a
mixin (no `__init__`) the `Handler` inherits: it reads `_json`, `_body`, `_local`
and the request from the `Handler` and its siblings. The names only these read
(`BASIC_KEY`, `REALM`, `LOCAL_COOKIE`, `GATE_IDENTITY`, `basic_allowed`,
`basic_pair`, `_cookie_named`, `_UNASKED`) came along; `app.py` imports them
back. This module does not import `app` at the top.
"""

from __future__ import annotations

import base64
import secrets
from typing import Callable, cast
from urllib.parse import parse_qs, urlparse

from at import i18n
from at.core import actors, boot, gate, permissions, settings, tables
from at.data import store
from at.services import caddy
from at.ui.webapp import session
from at.ui.webapp.routes_base import RouteBase

# The permission that lets an actor come in through Basic (§3, Configurações
# gerais). It is a KEY of `settings.json` and never a credential: the file holds
# permission and adjustment, and what a person proves lives hashed in their own
# row. Off is the default, because Basic puts the credential on the wire on
# every request.
BASIC_KEY = "basic_auth"

# The realm a refused Basic attempt is challenged with. It is a MACHINE word —
# the browser prints it, and it names the thing being entered, which is AT in
# every language (§3: the brand is not translated).
REALM = "AT"

# The cookie the LOCAL MODE's one-time token becomes, once a request has shown
# it (TASK-169, fatia 1/3; `at.ui.webapp.local`). It is its OWN cookie and not
# `session.COOKIE`: that one answers for an ACTOR Forms proved, and the local
# mode proves no actor at all — Forms is off in it — it proves the MACHINE,
# once, with a value drawn at boot and never written to disk.
LOCAL_COOKIE = "at_local"

# The header the gate asserts the identity on. It is the provider's own word for
# it (Authelia's answer to the Caddy's `forward_auth`, copied onto the request
# by the Caddy's `copy_headers`) and it is a MACHINE word, like the realm: it
# names the field of a protocol and not a screen. What makes it an identity is
# the secret travelling beside it (`services/caddy.py`, §7b).
GATE_IDENTITY = "Remote-User"

# --------------------------------------------------------- the transport ---

def basic_allowed() -> bool:
    """Whether a person may come in through Basic (§3, Configurações gerais).

    It is a PERMISSION in the settings and never a secret: the file holds
    permission and adjustment, and no credential lives in it. Only a literal
    `true` turns it on — a value that is not one is a setting nobody made, and
    the folder answers with the safe side, which is off. A folder that has
    never chosen says nothing at all, and is off for the same reason.
    """
    return settings.get(BASIC_KEY, False) is True


def basic_pair(value: str) -> tuple[str, str] | None:
    """The name and the credential an `Authorization: Basic` header carries.

    Read by hand and never raising: a stranger may send anything in a header,
    and `base64`'s refusal has to be a refusal and not a request thread taken
    down. The pair is `name:credential`, split on the FIRST colon — a credential
    may carry one, and cutting it here would be this door deciding what the
    person meant (the comparison keeps every byte, `actors.authenticate`). A
    header with no colon at all is not a pair, and answers `None`.
    """
    try:
        raw = base64.b64decode(value.strip(), validate=True).decode("utf-8")
    except ValueError:
        # `binascii.Error` and `UnicodeDecodeError` are both `ValueError`, and
        # both mean the same thing here: what travelled was not a Basic pair.
        return None
    name, found, credential = raw.partition(":")
    return (name, credential) if found else None


def _cookie_named(header: str | None, name: str) -> str | None:
    """A cookie's value by NAME, read by hand — the same guard `session.token_of`
    already keeps (a stranger's `Cookie` header is never let raise), for the one
    more cookie this file owns (`LOCAL_COOKIE`)."""
    if not header:
        return None
    for piece in header.split(";"):
        key, _, value = piece.strip().partition("=")
        if key == name:
            return value.strip() or None
    return None

# What the session of the request being served starts as: nobody asked yet. It
# is a sentinel and not `None` because `None` is an ANSWER — the folder that
# asks nobody, and the request that proved nobody — and the cache in `_in`
# would then never keep anything.
_UNASKED = object()


class GateRoutes(RouteBase):
    # ------------------------------------------------------------ local mode --

    def _local_gate(self) -> bool:
        """The LOCAL MODE's own portão (TASK-169, fatia 1/3) — answering, when
        it does not open.

        Outside that mode `self.server.local_token` is `None` and the question
        is not even asked: this is `at-cli webapp`'s server, with the entrance
        of §3 and nothing of this file's. INSIDE it, Forms is off by the mode's
        own decision — nobody is asked who they are — so this is the one guard
        standing between the loopback and whoever else is on the machine: the
        token the process sorteou at boot, and only the browser the process
        itself opened ever saw it.

        It runs BEFORE `_gate`, over EVERY request this handler answers — the
        page, the look and the API alike, which is a wider reach than `_gate`'s
        own (§3's page is public on purpose; this mode has no public page to
        be, because the whole point of the token is that no OTHER process on
        this machine gets to ask it anything at all.

        The token travels twice and differently: in the URL's `?k=`, the one
        time the browser is handed it (the boot's own `webbrowser.open`), and
        from then on in a cookie THIS request earns the moment it proves the
        query carried the right value — `_send` is what writes it out, because
        a refusal answered here never reaches that far. A cookie already
        correct skips the query — asking the query again on every request
        would be a URL this page would have to keep rewriting into every link
        it draws.
        """
        token = self.server.local_token
        if token is None:
            return True
        carried = _cookie_named(self.headers.get("Cookie"), LOCAL_COOKIE)
        if carried is not None and secrets.compare_digest(carried, token):
            return True
        given = parse_qs(urlparse(self.path).query).get("k", [None])[0]
        if given is not None and secrets.compare_digest(given, token):
            self._local_cookie = f"{LOCAL_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict"
            return True
        self._json({"error": i18n.tr("webapp.local_denied")}, 403)
        return False

    # ---------------------------------------------------------- the entrance --

    def _asks(self) -> bool:
        """Whether this server asks anybody to enter.

        Two facts, and both have to hold. It is `actors.can_expose()` — the
        folder with somebody to enter it — read HERE and not only in `run`: the
        command refusing to take the port says nothing about a server somebody
        built by hand, and a gate that closed over a folder with nothing to
        prove would be a door with no key in it. §3: with no authentication
        configured, AT listens on loopback and asks nothing.

        **And it is whether THIS server draws an entrance at all**
        (`server.asks`). A run from the source tree does not (`run`), and the
        difference is the whole of what "sem forms" means: the folder is still
        the folder, the tables are still the tables, and nobody has to prove who
        they are to read them.
        """
        return self.server.asks and actors.can_expose()

    def _in(self) -> session.Session | None:
        """The session this request carries, or `None`.

        Three transports, in the order they cost: the cookie a Forms entrance
        opened, and then the two headers, which prove themselves on every
        request (`_proved`). With no authenticator at all, `None` — and it is
        then that `_gate` lets the request through: this is the folder that asks
        nothing, and it is exactly where the API answers as it always did.

        **One look per request.** `_gate` asks this before the route runs and
        `_may` asks it again for the ceiling, and for the two header transports
        each ask is a derivation — the price the token-alone door pays, and one
        this request pays once. The answer is kept until `handle_one_request`
        empties it, and that is where the keeping belongs: to the REQUEST.
        """
        if self._held is _UNASKED:
            self._held = self._opened()
        return cast("session.Session | None", self._held)

    def _opened(self) -> session.Session | None:
        """Who this request proved, asked of the transports once.

        **The registry is not consulted when the Forms is off.** The cookie a
        Forms entrance opened is the LOCAL door (§3), and on the container path
        the person's door is the gate's — so with the switch committed
        (`gate.on_gate`) a cookie left over from before proves nothing, and the
        session it names is not read. It is the same sentence the switch is made
        of, one request at a time: Forms off, the gate on.
        """
        if not self._asks():
            return None
        if not gate.on_gate():
            held = self.server.sessions.get(session.token_of(self.headers.get("Cookie")))
            if held is not None:
                return held
        return self._proved()

    def _proved(self) -> session.Session | None:
        """The session a header proves for this request alone.

        The gate first, because it is the transport whose value is a claim and
        not a proof: the name is read only when the secret beside it says the
        request came through the Caddy (`_sealed`), and what it proves is the
        row that name wears (`actors.asserted`) — Authelia proved the person, and
        AT resolves who they are.

        Then `Basic`, a PERSON's name and credential — the Forms credential by
        the other transport, so the door is the engine's
        (`actors.authenticate`) — read only while the folder's permission says
        so. And `Bearer`, a MACHINE's token alone, whose door is the agent's
        (`actors.authenticate_agent`). None of them is looked up in the
        registry: all prove on every request, and what comes back is a session
        held by nobody (`session.from_row`).

        **With the Forms off, Basic goes with it.** It is the same credential by
        another transport (§3), which is exactly why the switch takes it out with
        the Forms: on the container path the person's credential is Authelia's,
        and a folder that kept taking it here would be keeping the door the gate
        replaced. `Bearer` stays, because it is not a person's door at all — it
        is the machine's, and no machine enters by Forms.
        """
        asserted = self.headers.get(GATE_IDENTITY)
        if asserted is not None:
            row = actors.asserted(asserted) if self._sealed() else None
            return session.from_row(row) if row else None
        header = self.headers.get("Authorization")
        if not header:
            return None
        scheme, _, value = header.partition(" ")
        scheme = scheme.lower()
        if scheme == "basic" and basic_allowed() and not gate.on_gate():
            pair = basic_pair(value)
            row = actors.authenticate(*pair) if pair else None
        elif scheme == "bearer":
            row = actors.authenticate_agent(value.strip())
        else:
            return None
        return session.from_row(row) if row else None

    def _sealed(self) -> bool:
        """Whether the gate secret this request carries is the folder's one.

        It is the comparison §7b is made of, and it answers `False` when the
        folder has no gate at all: without a secret drawn there is nothing the
        Caddy could have attached, and a header claiming an identity is a header
        nobody sealed. The comparison is constant-time, because the value is a
        secret and the clock is a way of reading one.
        """
        secret = caddy.gate_secret()
        carried = self.headers.get(caddy.GATE_HEADER) or ""
        return secret is not None and secrets.compare_digest(carried, secret)

    def _forged(self) -> bool:
        """Whether this request asserts an identity the gate did not seal."""
        return self.headers.get(GATE_IDENTITY) is not None and not self._sealed()

    def _challenge(self) -> dict:
        """The `WWW-Authenticate` a refused Basic attempt is owed, if any.

        It answers an ATTEMPT and nothing else. The header is what makes a
        browser open its own dialog, and one travelling with the page's own 401
        would pop that dialog over the entrance AT drew — so the page, which
        sends no `Authorization`, is never challenged. A folder that does not
        take Basic has nothing to offer and challenges nobody either.
        """
        header = self.headers.get("Authorization") or ""
        if not basic_allowed() or header.partition(" ")[0].lower() != "basic":
            return {}
        return {"WWW-Authenticate": f'Basic realm="{REALM}"'}

    def _gate(self) -> bool:
        """Whether this request reaches the API — answering, when it does not.

        Called by BOTH dispatching halves, and that is the whole reason it is a
        method: `do_GET` walks `_route` and `do_POST` dispatches by itself, so a
        gate written into one of them would leave the other's doors open. What
        sits ABOVE it is the page, the look and the entrance — the three things
        that have to answer before anybody is in.

        **The forged identity is refused before the question of session is
        asked**, and it is answered differently on purpose: "you are not in" is
        401 and is what a stranger gets, and "that identity is not one AT
        takes" is 403 and names the gate (§7b). The two are not the same failure
        — the second is what a person sees when the Caddy's secret and the
        folder's stopped agreeing, and it has to say so instead of looking like
        a login that did not happen.

        **And a fallen gate closes AT before either question is asked.** The
        folder is on the container path — the switch committed, and that is a
        fact of the folder and not of this process — so the API answers the
        sentence §6 names and nothing else. It is asked HERE, per request, and
        that is deliberate: the WebApp is a container that comes up BEFORE the
        edge that fronts it (§7a's order), so asking at start-up would make a
        committed folder refuse to come up at all; and a gate that falls while
        the environment is standing is noticed by the request that finds nothing
        answering, never by a container that does not restart itself.
        """
        if gate.on_gate() and not gate.standing():
            print(i18n.tr("services.gate.down"))
            self._json({"error": i18n.tr("services.gate.down")}, 503)
            return False
        if self._forged():
            self._json({"error": i18n.tr("webapp.gate_refused")}, 403)
            return False
        if not self._asks() or self._in() is not None:
            return True
        self._json({"error": i18n.tr("webapp.session_needed")}, 401, self._challenge())
        return False

    def _may(
        self, permission: str, *, owing: Callable[[], None] | None = None
    ) -> bool:
        """Whether the actor this request proved carries `permission` — and the
        refusal, when it does not.

        It is the STRICT ceiling (§4, item 11): what the role carries is what the
        actor reaches, and a permission the role does not name is one the route
        is refused for. The same door caps the person and the machine — the
        machine's token is the credential of a row that wears a role like any
        other — and an actor pointing at no role reaches nothing, because
        `permissions.carries` fails CLOSED.

        **It sits BESIDE `_gate` and answers a different question.** The gate
        refuses the request that proved nobody (401) and this one refuses the
        request that proved itself and carries too little (403). Both are asked
        with the ROUTE, which is why the demand is written where the route is:
        the one route that cannot say it up front — the table write, whose action
        travels in the body — asks it as soon as the action is read.

        The role is resolved from the ACTOR's row here (`actors.role_of`), on
        every request and never from the session: what a role carries is a fact
        of the store, and a session that kept it would hand a request the ceiling
        of a moment ago.

        The folder that asks nobody has no session to read and keeps answering as
        it always did (§3) — which is what `_asks` says, and the reason this is
        not a gate over the whole server.

        **`owing` is what the refusal owes before it is answered**: the table
        write's line (§3, item 15), which its route hands in because `_may` is
        the moment the wall is found. It runs BEFORE the response goes out — a
        line written after the answer is a line a crash can lose, and a refusal
        that was answered and not recorded is exactly the one worth having.
        """
        held = self._in()
        if not self._asks() or held is None:
            return True
        row = self._actor()
        if row is not None and actors.may(row, permission):
            return True
        if owing is not None:
            owing()
        self._json(
            {
                "error": i18n.tr(
                    "permission.denied", permission=permissions.label(permission)
                )
            },
            403,
        )
        return False

    def _legal(self, permission: str) -> bool:
        """Whether the actor this request proved carries `permission` — a QUESTION
        and never a refusal (TASK-120, fatia 1).

        `_may` is a GATE: it answers the same way and writes the 403 a route is
        refused with. A context menu asking what it may show is not a route being
        refused — there is nothing to write, and no owing either, because showing
        nothing is not a demand that failed. Same two hops as `_may`'s ceiling
        (`_asks`, `_actor`, `actors.may`), and none of its response.
        """
        if not self._asks():
            return True
        row = self._actor()
        return row is not None and actors.may(row, permission)

    def _actor(self) -> dict | None:
        """The row this request proved, or `None` — the session's own hop back to
        the store.

        `_in` answers WHO, with the row's NUMBER; the ceiling is read off the ROW,
        and this is the one place that makes the hop. It is what `_may` resolves
        the role from, and what the interpreter's door is handed — one hop, so a
        route imposing a ceiling and the door imposing it cannot disagree.
        """
        held = self._in()
        if not self._asks() or held is None or held.actor is None:
            return None
        return store.find("actor", held.actor)

    def _post_folder(self) -> None:
        """A confirmação da Pasta de Trabalho, pela página (TASK-169, fatia
        2/3) — a MESMA pergunta que `boot.ensure_working_folder` faz no
        terminal, feita aqui porque o modo local não tem um terminal para
        fazê-la.

        **Acima do portão, como `_post_session` e `_post_first`**: não há
        sessão nenhuma a exigir de quem a pasta ainda nem existe para
        guardar — e é a MESMA razão, um passo antes da deles.

        **Confirmando, `boot.create_working_folder()` — sem `ask`.** É a
        mesma chamada que `at-cli` já faz sem terminal: a única pergunta que
        ela poderia fazer (a falta do `git`) já responde sozinha que não há
        onde perguntar, e nada trava por isso.

        **Recusando, nada é escrito.** O que marca a recusa é
        `server.folder_cancelled` — o sinal que `local.run` já espera para
        encerrar a janela, a mesma morte que fechá-la por fora já era.
        """
        if boot.is_configured():
            self._json({"error": "bad request"}, 400)
            return
        payload = self._body()
        if payload is None:
            return
        if payload.get("confirm") is not True:
            self.server.folder_cancelled.set()
            self._json({"cancelled": True})
            return
        boot.create_working_folder()
        self._json({"created": True})

    def _post_first(self) -> None:
        """A primeira subida: o formulário da página cria o primeiro admin.

        **É a MESMA porta de `at-cli admin`** — `actors.create_admin`, com o
        papel criado antes da linha —, e é por isso que ela está ACIMA do
        portão, como `_post_session`: não há sessão a exigir de quem ainda não
        tem com quem entrar, e uma rota que exigisse uma seria uma porta que só
        abre para quem já passou por ela. Pela mesma razão ela é a ÚNICA rota
        de escrita que responde a um pedido sem sessão, e é por isso que ela
        responde ANTES a quem está do outro lado do fio (`_local`): §3 —
        sem ator nenhum o AT não expõe.

        **As regras são as do terminal, e não uma segunda cópia delas.** As
        duas chaves são lidas duas vezes porque não se recuperam, e o
        `admin.error.mismatch` é a recusa quando não são a mesma; o piso é
        `actors.MIN_CREDENTIAL`, que é o do Cofre, e quem recusa por ele é o
        próprio motor (`admin.error.short`, dentro de `create_admin`); e a
        pasta que já tem administrador é recusada pelo nome dele
        (`admin.exists`), que é a mesma pergunta que `at-cli admin` faz. As
        palavras são as do bloco `admin` do catálogo, as mesmas que o
        formulário desenhou (`_first_words`).

        **A sessão abre no fim, e ela é a única coisa que sobra para o
        formulário fazer.** Quem acabou de digitar a Chave Principal já provou
        quem é — a mesma string é o que a linha vai guardar hasheada —, e
        pedir a mesma coisa duas vezes seria a página cobrando de novo o que o
        servidor acabou de aceitar.
        """
        if gate.on_gate():
            self._json({"error": i18n.tr("webapp.forms_off")}, 403)
            return
        if self._forged():
            self._json({"error": i18n.tr("webapp.gate_refused")}, 403)
            return
        if not self._local():
            self._json({"error": i18n.tr("webapp.no_admin")}, 403)
            return
        existing = actors.admins()
        if existing:
            self._json(
                {"error": str(actors.AdminError(
                    "exists", name=tables.title("actor", existing[0])
                ))},
                403,
            )
            return
        payload = self._body()
        if payload is None:
            return
        name = payload.get("name")
        credential, again = payload.get("credential"), payload.get("again")
        if not all(isinstance(value, str) for value in (name, credential, again)):
            self._json({"error": "bad request"}, 400)
            return
        if credential != again:
            self._json({"error": str(actors.AdminError("error.mismatch"))}, 400)
            return
        try:
            row = actors.create_admin(cast(str, name).strip(), cast(str, credential))
        except (actors.AdminError, tables.TableError) as refused:
            self._json({"error": str(refused)}, 400)
            return
        opened = self.server.sessions.open(row)
        self._json(
            {"actor": {"name": opened.name},
             "created": i18n.tr("admin.created",
                                name=tables.title("actor", row))},
            extra={"Set-Cookie": session.cookie_header(opened)},
        )

    def _post_session(self) -> None:
        """The entrance: the credential is proved, and a session opens.

        It is the one write that does not need a session, because it is the one
        that makes one — and it obeys the same body guards as every other write,
        through the same door (`_body`), because it is the same page that sends
        it.

        A refusal is 401 in the catalog's words: the same sentence whether the
        name is unknown or the credential is wrong, so the answer says neither.

        **And on the container path this door does not open at all.** It is the
        Forms entrance, and the Forms is what the switch takes off the path — a
        folder that kept handing out session cookies would be keeping the door
        one switch served to close. It is refused here rather than hidden from
        the page, because the page is not the thing that decides who enters.
        """
        if gate.on_gate():
            self._json({"error": i18n.tr("webapp.forms_off")}, 403)
            return
        payload = self._body()
        if payload is None:
            return
        name, credential = payload.get("name"), payload.get("credential")
        if not isinstance(name, str) or not isinstance(credential, str):
            self._json({"error": "bad request"}, 400)
            return
        row = actors.authenticate(name, credential)
        if row is None:
            self._json({"error": i18n.tr("webapp.session_refused")}, 401)
            return
        opened = self.server.sessions.open(row)
        self._json(
            {"actor": {"name": opened.name}},
            extra={"Set-Cookie": session.cookie_header(opened)},
        )
