"""§7f's delivery: AT talking TO the notifier — the credential, and the push.

Slice a of §7f put the notifier on its feet and shut the door on whoever brings
no token: `auth-default-access: deny-all`, and nothing else decides what a token
may do (`services/environment.py`). This is the other half, and it is the half
§3 asks a SCOPE for. §3's sentence is about a service that talks to AT and gets
a delimited role; **the mirror of it is here** — AT talks to the SERVICE, and
the credential it carries does one thing: publish to the topic. Measured against
the image at the pin: with `ntfy access at at write-only`, the token answers
`200` publishing to `at`, `403` publishing to any other topic, and `403`
reading its own — the three answers the scope is, in that order.

**The credential is AT's, drawn by AT, and it lives in a `0600` file.** A
token is a SECRET, the `secret` table and the master key are item 14 and are not
built, and the honest interim is the one the retired environment already used:
a `0600` file beside the folder's other secrets, **never in the argv and never
printed**, with the vault taking it over when the vault exists. Two facts are
worth saying out loud. ntfy keeps only the HASH — its `user.db`, inside the state
folder the container mounts — so the plaintext exists in exactly one place. And
that file is inside the Working Folder, so a copy of the folder carries the
credential, which is what makes the copied folder able to publish again (§3, the
backup promise).

**Where the value may travel, and where it may not.** The account ntfy demands
has a password, so AT draws one and hands it over on the STDIN of `podman exec
-i` — never in the argv, which the whole machine reads through `ps`. The token
itself is drawn BY ntfy inside the container and comes back on STDOUT, which is
the one place AT ever reads it; the argv never carries it. And AT's own
credential is never printed: the messages name the FILE, `status` says whether
it exists, and the delivery says what the notifier answered.

**The phone's credential is printed, and it is printed exactly once.** The ACL
has two ends, and §7f names the other one: AT publishes, the phone reads. That
token is the PERSON'S, and there is no way for it to reach a phone except
through the person's eyes — so it is the one value this artifact prints, and it
follows the rule item 10's machine credential already follows in the page: a
credential AT hands to somebody is handed over ONCE. Printed when it is drawn
and never again: what is kept is the value the phone kept, the file is where a
person goes to read it a second time, and a value that came out in a scrollback
is not printed a third time to be safe (`subscribe`). Its scope is the mirror of
AT's — `read-only` on the topic, and nothing else — so the two tokens §6
declares neither serve for the other's work nor for anything beyond the topic.

**The road is a NAME, and the certificate on it is AT's own.** §7f's sentence
that the notifier does not go behind the gate is what lets a headless phone
connect at all; §7a's names are what it connects TO. The phone points at
`ntfy.at.local`, on `443`, and the edge serves it with the certificate it issues
per name (`tls internal`). **E quem precisa confiar nesse certificado é o APP e
não o aparelho**, e isso é uma medição: no Android um app moderno ignora a CA
que a pessoa instalou no sistema, e o app do ntfy tem a gestão de certificados
DELE, com certificado próprio desde a v1.22.1. Então o que a pessoa importa é a
CA do AT — `environment.authority_file` é nomeado por causa disto —, e a
mensagem do celular diz qual arquivo é e onde ele se importa. O mesmo endereço
que a pessoa vai digitar é o da prova: `phone_url` é o nome, e não o laço.

**A leitura é PROVADA, e é o que a palavra do celular promete.** `reached` e
`turned_away` são as duas metades — o tópico responde a quem traz o token do
celular, e recusa quem não traz nenhum —, perguntadas pelo nome, na estrada que
o celular vai usar. Uma prova que não alcança nada não é uma prova: `unproved`
nomeia a metade que não fechou, e `subscribe` fecha `PHONE_UNPROVED` quando
alguma não fecha. O token FICA — ele foi sorteado, e o arquivo é dele —, e o que
não fechou é a leitura, dita com a estrada inteira à mostra para quem está com o
celular na mão.

**The service's own folder is where the token sits, and the container sees it.**
That is the same place the configuration AT wrote for ntfy already lives, and
the same shape as the identity provider's session secret beside its own
`configuration.yml`; what a compromise of the notifier gains from it is a
credential that can publish to the topic that notifier already serves, and
nothing else — which is the scope above doing its job.
"""

from __future__ import annotations

import re
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

from at.core import files, gate
from at.i18n import tr
from at_deploy import environment, podman

# The topic, and the account AT's credential belongs to. The topic is the
# NAME and not the brand: the phone subscribes to it and AT publishes to it,
# and it is the subject §3's per-topic scope is written about.
TOPIC = "at"
USER = "at"

# What ntfy writes on the token's line, so that whoever reads it later knows
# whose it is. The file carries the value and nothing beside it.
LABEL = "at"

# §3's delimited scope, in ntfy's own word for it: AT publishes and does
# nothing else — it does not read the topic back, and it does not reach another
# one. Measured (the module's docstring).
SCOPE = "write-only"

# The other end of the ACL (§7f), and it is another ACCOUNT and not another
# token of the same one: ntfy's access is per user and per topic, so one account
# cannot be `write-only` and `read-only` on the same topic at once — and the two
# ends §6 declares are two credentials, each with the scope its own work needs.
PHONE_USER = "phone"
PHONE_LABEL = "phone"
PHONE_SCOPE = "read-only"

# Where the credential lives: the service's own state folder (`environment.state`),
# which is the one folder the container mounts and the one the backup covers.
TOKEN_FILE = "token"
# The phone's, beside it and inside the same folder — so the copied folder comes
# back with BOTH ends of the ACL, which is what §3's backup promise costs.
PHONE_FILE = "phone-token"

# A leitura do celular, no vocabulário do PRÓPRIO ntfy: um `poll` do tópico
# devolve o que está na memória dele e fecha. É o que o app faz ao abrir a
# inscrição, e é por ele que a prova pergunta (`_close`).
POLL = "json?poll=1"

# As duas respostas que a prova lê. Com o token do celular o tópico responde;
# sem token nenhum ele recusa, que é o que `auth-default-access: deny-all`
# promete e o que faz do token a porta. Os dois números são MEDIDOS contra a
# imagem do pino, como o escopo — o docstring do módulo conta a medição.
READ = 200
NO_TOKEN_REFUSED = 403

# How much password AT draws for the account it creates. The value is handed
# over and forgotten — nobody logs in with it, and the credential that matters
# is the token below — so it only has to be a value nobody can guess.
PASSWORD_BYTES = 32

# What every alert announces itself with. At the default priority a message
# arrives silently on the phone, and a message nobody notices is a message not
# delivered; the tag gives it an icon of its own.
TITLE = "AT"
PRIORITY = "high"
TAGS = "bell"

# How long a POST waits for the notifier, and how long the environment waits for
# the notifier's own database to be born (see `_ready`).
TIMEOUT = 10.0

# The shape of a token, for reading it off the CLI's line. ntfy's own rule is
# `tk_` and 32 characters; what this asks is the prefix and a body, so a longer
# alphabet tomorrow still parses instead of silently answering none.
TOKEN_WORD = re.compile(r"tk_[a-z0-9]{10,}")

# The outcomes of `provision`, of `subscribe`, and of `push`. The `cli` is what
# turns the push's into an exit code.
DRAWN = "drawn"       # AT had none, and made one
HELD = "held"         # AT already had one, and it was left alone
PHONE_DRAWN = "phone_drawn"  # the phone had none, and got one — shown once
PHONE_HELD = "phone_held"    # the phone already had one, and it is not shown
PHONE_UNPROVED = "phone_unproved"  # the token is drawn, and the read is not proved
SENT = "sent"         # the notifier took the alert
NO_TOKEN = "no_token"  # nothing to authenticate with
FAILED = "failed"     # it was asked and did not happen


def token_file() -> Path:
    """`App/services/notifier/token` — where the credential lives (§7f).

    Beside the `server.yml` AT wrote for the same service and inside the same
    state folder, which is §7's sentence that a service's state lives under
    `App/services/<service>/` — and what makes the credential survive a backup.
    """
    return environment.state(environment.NOTIFIER) / TOKEN_FILE


def phone_file() -> Path:
    """`App/services/notifier/phone-token` — the phone's credential (§7f).

    The same folder as AT's and for the same reason: the state of a service
    lives under `App/services/<service>/`, so a copied folder carries both ends
    of the ACL and comes back able to publish and to read.
    """
    return environment.state(environment.NOTIFIER) / PHONE_FILE


def _held(path: Path) -> str | None:
    """The value a `0600` file carries, or `None` when it holds nothing.

    An empty file is nobody's credential and not a credential that is the empty
    string: the caller has to be able to tell "there is none" from "there is
    one" (`token`, `phone_token`).
    """
    try:
        kept = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return kept or None


def _keep(path: Path, value: str) -> Path:
    """Write a credential at `0600` — the interim while the vault does not exist.

    The mode is the writer's (`files.atomic_write_text`), because the value is
    only unreadable if the permission is set on the file that is about to carry
    it, and not after.
    """
    files.atomic_write_text(path, f"{value.strip()}\n", mode=0o600)
    return path


def token() -> str | None:
    """The credential, or `None` when AT has none yet.

    Nothing here prints or returns it beyond the caller: the value is read at the
    moment of the POST and never travels through a message (§ the module's
    docstring).
    """
    return _held(token_file())


def write_token(value: str) -> Path:
    """Keep AT's credential — never printed, and read only by the POST."""
    return _keep(token_file(), value)


def phone_token() -> str | None:
    """The phone's credential, or `None` when it has none yet.

    It IS printable, and it is printed in exactly one place (`subscribe`): what
    a person needs here is where it is, and `status` says the file.
    """
    return _held(phone_file())


def write_phone_token(value: str) -> Path:
    """Keep the phone's credential beside AT's, at the same `0600`."""
    return _keep(phone_file(), value)


# ------------------------------------------------------ the phone's read ---

def phone_url() -> str:
    """O endereço que o CELULAR usa — o nome, na borda, e nunca o laço.

    É o que vai para o aparelho (`notifier_public_url`) com o caminho da leitura
    no vocabulário do ntfy (`POLL`). **A prova pergunta AQUI de propósito**: a
    estrada que precisa ser provada é a do celular — o nome, na 443, com o
    certificado da borda —, e o laço é a estrada do AT (`target`), que funciona
    por construção e não diria nada sobre o aparelho.
    """
    return f"{environment.notifier_public_url()}/{TOPIC}/{POLL}"


def _ask(headers: dict[str, str], answer: gate.Answer | None) -> int | None:
    """A pergunta da prova, na estrada do celular e pelo transporte DA BORDA.

    O transporte padrão é o do ambiente (`through_edge`) e não o do portão
    (`gate.real`), e a diferença é MEDIDA: o nome que o celular digita não é
    resolvido pela máquina que roda o comando — o resolver dela não é o do
    aparelho —, então perguntar ao nome pelo `gate.real` responderia "não deu
    para saber" sobre uma borda de pé. O que a estrada do celular tem de seu é o
    NOME no SNI e no `Host`; o endereço da conexão é da rede do ambiente.
    """
    return gate.ask(phone_url(), headers, answer or environment.through_edge)


def reached(answer: gate.Answer | None = None) -> bool:
    """Com o token do celular, o tópico responde pelo nome — a primeira metade.

    O token viaja no cabeçalho e nunca no argv, a mesma regra que a entrega
    segue, e o que se lê é o STATUS — a resposta que o ntfy dá ao app. Um
    "nada respondeu" (`None`) não é nem um nem outro: é "não deu para saber", e
    é por isso que a comparação é com `READ` e não com "diferente de erro".
    """
    held = phone_token()
    if held is None:
        return False
    return _ask({"Authorization": f"Bearer {held}"}, answer) == READ


def turned_away(answer: gate.Answer | None = None) -> bool:
    """Sem token nenhum, o tópico recusa — a outra metade, e a que faz a porta.

    É o `auth-default-access: deny-all` medido: quem chega sem credencial leva
    `NO_TOKEN_REFUSED`, e é isso que diz que a ACL por tópico é a autenticação
    deste serviço. Um `200` aqui seria o notificador aberto a quem chegasse.
    """
    return _ask({}, answer) == NO_TOKEN_REFUSED


def unproved(answer: gate.Answer | None = None) -> str | None:
    """A sentença da metade que não fechou — ou `None` quando as duas fecham.

    As duas são perguntadas na ordem em que o celular as encontra, e a caminhada
    PARA na primeira que não fecha: perguntar a segunda depois de o token não
    ler seria perguntar sobre uma porta que já não se sabe fechada.
    """
    if not reached(answer):
        return "services.notifier.phone.unread"
    if not turned_away(answer):
        return "services.notifier.phone.unrefused"
    return None


def proved(answer: gate.Answer | None = None) -> bool:
    """Se o celular lê o notificador pelo nome — as duas metades de uma vez."""
    return unproved(answer) is None


def target() -> str:
    """Where an alert goes: the topic, at the address the notifier publishes on.

    Built from the environment's own constants — the loop and the port are the
    ones the `Port` publishes and `server.yml` listens on. **E o laço é de
    propósito**: quem lê o link de dentro do alerta é o celular, e é o
    `base-url` que o monta (`notifier_public_url`); quem PUBLICA é o AT, e ele
    fala com o serviço pelo laço, onde o alerta não depende do DNS interno, da
    borda nem do certificado do AT. Os dois endereços são diferentes porque são
    duas estradas diferentes.
    """
    return f"{environment.notifier_url()}/{TOPIC}"


def publish(title: str, body: str) -> tuple[bool, str]:
    """POST one alert to the topic. `(ok, detail)` — and the detail is never the token.

    The one HTTP call this product makes to a service, and it is deliberately
    plain: the address is the loop, so an alert does not depend on the internal
    DNS, on the edge or on AT's own certificate — if any of the three falls,
    the alert still goes out.
    """
    request = urllib.request.Request(target(), data=body.encode("utf-8"),
                                     method="POST")
    request.add_header("Title", title)
    request.add_header("Priority", PRIORITY)
    request.add_header("Tags", TAGS)
    held = token()
    if held is not None:
        request.add_header("Authorization", f"Bearer {held}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return 200 <= response.status < 300, str(response.status)
    except urllib.error.HTTPError as error:
        # A refusal is an answer and not an exception to the caller — and the
        # error is a file-like, so it is closed here: leaving it to the garbage
        # collector makes the run warn about a handle nobody closed.
        code = str(error.code)
        error.close()
        return False, code
    except (urllib.error.URLError, OSError) as error:
        return False, str(getattr(error, "reason", error))


def push(title: str, body: str) -> str:
    """What actually pushes an alert: the credential, the POST, and AT's words.

    It is the ONE door for whoever has something to say, and §7f names its first
    caller: the approval of a demand that passed the risk threshold arrives
    through the notifier (§3, item 15). A network that did not answer is a fact
    to report and never an exception — an alert that failed is not a crash, it
    is an alert that failed, and whoever called this decides what to do about it.
    """
    held = token()
    if held is None:
        print(tr("services.notifier.no_token", where=token_file(), topic=TOPIC))
        return NO_TOKEN
    ok, detail = publish(title, body)
    if not ok:
        print(tr("services.notifier.undelivered", detail=detail))
        return FAILED
    print(tr("services.notifier.delivered", topic=TOPIC, detail=detail))
    return SENT


def _ready(grace: float | None = None) -> bool:
    """Whether the database the notifier's server writes at startup exists yet.

    MEASURED: the CLI refuses to run before it does — with no database it answers
    `auth-file does not exist; please start the server at least once` and exits —
    so there is nothing AT can create until the container is up AND its server
    has started. Asking `test -f` inside the container is the probe, for the same
    reason the orchestrator asks an address by binding it: the question and the
    failure are the same one.
    """
    where = f"{environment.NOTIFIER_DATA}/{environment.NOTIFIER_AUTH}"
    name = environment.container(environment.NOTIFIER)
    deadline = time.monotonic() + (environment.GRACE if grace is None else grace)
    while True:
        if podman.ok(["exec", name, "test", "-f", where]):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(environment.STEP)


def _inside(*argv: str, **kw: object):
    """One call inside the notifier's container — the CLI, and never the host's.

    Every `ntfy` command is a server command: it reads the very database the
    container's server opened, so it runs where that database is. `input` is the
    only thing that reaches a command on a stream instead of the argv.

    **`-i` is not decoration, and it was measured**: without it the runtime does
    not attach the command's input, and `ntfy user add` — which asks for the
    password — dies with `inappropriate ioctl for device` instead of reading the
    line AT hands it.
    """
    return podman.run(["exec", "-i", environment.container(environment.NOTIFIER),
                       "ntfy", *argv], **kw)


def _draw(user: str, label: str, scope: str) -> str | None:
    """The four calls that make ONE credential in the notifier, in this order.

    1. **the account starts clean.** `user remove` first, because the only way a
       credential is ever re-drawn is a token file that went away, and that is a
       rotation: removing the account takes its tokens with it, so the credential
       that was replaced stops working instead of staying valid in a database
       nobody looks at. A missing account is a failure here and not an error.
    2. **the account.** ntfy refuses a user with no password, so AT draws one,
       hands it over on STDIN — never in the argv — and forgets it.
    3. **the scope.** §3 asks least privilege for whoever reaches AT, and the
       mirror of it is this line: the account reaches the topic with the scope
       its own work needs and does nothing else.
    4. **the token**, drawn by ntfy itself and read off its own line. AT never
       invents the value, so it never has to write it into an argv.

    `None` is a step that refused, and it has already been said in the caller's
    own word for WHICH credential was being made (`subscribe`, `provision`).
    """
    _inside("user", "remove", user)
    password = secrets.token_urlsafe(PASSWORD_BYTES)
    added = _inside("user", "add", "--role", "user", user,
                    input=f"{password}\n{password}\n")
    if added.returncode != 0:
        print(tr("services.notifier.undrawn", call=f"ntfy user add {user}"))
        return None

    scoped = _inside("access", user, TOPIC, scope)
    if scoped.returncode != 0:
        print(tr("services.notifier.undrawn", call=f"ntfy access {user} {TOPIC}"))
        return None

    created = _inside("token", "add", "--label", label, user)
    found = TOKEN_WORD.search(created.stdout or "")
    if created.returncode != 0 or found is None:
        print(tr("services.notifier.undrawn", call=f"ntfy token add {user}"))
        return None
    return found.group(0)


def provision() -> str:
    """Create AT's credential in the notifier — the environment's own act (§7f).

    The write end of the ACL, and it is the environment that draws it: it is
    made when the notifier comes up, by the four calls `_draw` names, and kept
    in a `0600` file beside the notifier's own state.

    An environment that already has a credential is left exactly as it is: the
    file is the truth, and whoever wants a new one deletes it and brings the
    environment up again — the same rule the gate's secret follows (`caddy`).
    """
    if token() is not None:
        return HELD
    if not _ready():
        print(tr("services.notifier.not_ready",
                 where=f"{environment.NOTIFIER_DATA}/{environment.NOTIFIER_AUTH}"))
        return FAILED

    drawn = _draw(USER, LABEL, SCOPE)
    if drawn is None:
        return FAILED

    write_token(drawn)
    print(tr("services.notifier.drawn", where=token_file(), topic=TOPIC,
             scope=SCOPE))
    return DRAWN


def _close(answer: gate.Answer | None) -> bool:
    """Diz a prova da leitura, e responde se ela fechou.

    **Uma prova que não alcança nada não é uma prova.** `unproved` nomeia qual
    das duas metades não fechou, e o veredito sai com a estrada inteira à mostra
    — a URL, o tópico e o arquivo da CA —, porque quem lê isto está com o
    celular na mão e o que ele precisa saber é o que conferir no aparelho.
    """
    reason = unproved(answer)
    if reason is None:
        print(tr("services.notifier.phone.proved", url=phone_url(),
                 topic=TOPIC))
        return True
    print(tr(reason, url=phone_url(), topic=TOPIC,
             host=environment.notifier_host(),
             authority=environment.authority_file(),
             code=NO_TOKEN_REFUSED))
    return False


def subscribe(answer: gate.Answer | None = None) -> str:
    """Draw the phone's credential — the other end of the ACL, and PRINTS IT ONCE.

    §6 says it in one line: in `ntfy` the ACL is per topic, **AT publishes and
    the phone reads**, and neither token serves for anything else. The write end
    is `provision`'s and happens with the environment; this is the read end, and
    it is the OPERATOR's act (item 27): the phone is not the machine the
    environment runs on, so nothing here can be decided by bringing the
    environment up.

    **It is the one value this artifact prints, and it is printed here.** The
    token has to reach the phone, and the only road to a phone is the person's
    eyes — so the value comes out of the container on `token add`'s stdout,
    lands in a `0600` file, and is shown ONCE, in the same breath. A second run
    does not print it: the file is where a person reads it again, and the value
    is the one the phone kept (the module's docstring).

    Two scopes and not one, and it is measured (§ the module's docstring): the
    account may READ the topic and nothing else — it cannot publish to it, and
    it cannot reach another one. An environment that already has the phone's
    credential is left alone, and the way to a new one is deleting the file and
    running this again, which is the rotation `_draw` starts clean for.

    **A leitura é PROVADA no fim do ato, e é o que a palavra promete** (§7f): o
    celular não é a máquina onde o ambiente roda, então "o token existe" não é a
    mesma coisa que "o celular lê". As duas metades são perguntadas pelo NOME, na
    borda (`_close`), e o ato termina `PHONE_UNPROVED` quando alguma não fecha —
    o token fica, porque ele foi sorteado, e o que não fechou é a leitura. É a
    mesma regra da entrega: `notify` também recusa quando o alerta não sai.
    """
    if phone_token() is not None:
        print(tr("services.notifier.phone.held", where=phone_file(),
                 url=environment.notifier_public_url(), topic=TOPIC,
                 authority=environment.authority_file()))
        return PHONE_HELD if _close(answer) else PHONE_UNPROVED
    if not podman.present():
        # A machine with no runtime has no notifier to ask, and there is nothing
        # to wait for: `up` is what names the two ways out, and this word is the
        # operator's and can be reached before the environment ever stood.
        print(tr("services.no_podman.status"))
        return FAILED
    if not _ready():
        print(tr("services.notifier.not_ready",
                 where=f"{environment.NOTIFIER_DATA}/{environment.NOTIFIER_AUTH}"))
        return FAILED

    drawn = _draw(PHONE_USER, PHONE_LABEL, PHONE_SCOPE)
    if drawn is None:
        return FAILED

    write_phone_token(drawn)
    print(tr("services.notifier.phone.drawn", token=drawn, topic=TOPIC,
             scope=PHONE_SCOPE, url=environment.notifier_public_url(),
             authority=environment.authority_file(), where=phone_file()))
    return PHONE_DRAWN if _close(answer) else PHONE_UNPROVED
