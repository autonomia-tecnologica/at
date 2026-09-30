"""§7f's delivery: AT talking TO the notifier — the credential, and the push.

Slice a of §7f put the notifier on its feet and shut the door on whoever brings
no token: `auth-default-access: deny-all`, and nothing else decides what a token
may do (`services/environment.py`). This is the other half, and it is the half
§3 asks a SCOPE for. §3's sentence is about a service that talks to AT and gets
a delimited role; **the mirror of it is here** — AT talks to the SERVICE, and
the credential it carries publishes AND reads the topic — one account, because
the edge is now what decides who reaches it at all (see below). Measured
against the image at the pin: with `ntfy access at at read-write`, the account
answers `200` on the topic `at`, and `403` on any other — the scope the gate
mirrors.

**Basic on the notifier's own name is what changed this** (the gate now fronts
it — `at_deploy/environment.py`'s `_caddy_conf`). Authelia's forward-auth takes
an `Authorization: Basic` header on the request itself instead of redirecting,
so the person's own admin account — the SAME Chave Principal that logs into
`at.local` — is what proves a phone at `ntfy.at.local` too: no second ntfy
account for it, and no credential of its own to print. Once the edge has
proved the person, it swaps whatever `Authorization` the client sent for the
M2M credential below and hands the request straight to the notifier — the
notifier never sees the person's own credential, only AT's.

**The credential is AT's, drawn by AT, and it lives in a `0600` file — SEALED.**
A token is a SECRET, and the vault (§4) took the file over: what it keeps is the
ENVELOPE the Main Key seals, at `0600`, **never in the argv and never
printed**. ntfy keeps only the HASH — its `user.db`, inside the state folder the
container mounts — so the plaintext exists in exactly one place, and that one
place is unreadable in a copy of the folder. **E a cópia continua servindo**: a
credencial volta a ser lida com a Chave Principal, e é isso que faz uma pasta
copiada publicar de novo (§3, a promessa do backup).

**Quem lê o valor claro é o `at-deploy`, de FORA, e é ele que pede a Chave
Principal.** Nenhum container lê a credencial — o notificador monta só o
`server.yml`, e a fatia 2 do item 50 mediu isso —, então o diretório de execução
não é o lugar dela: quem a lê é o processo que roda o `up` e a entrega
(`notify`), e nenhum dos dois compartilha a chave derivada do outro. Cada
leitura abre o envelope com a Chave Principal do PRÓPRIO ato — a mesma porta da
subida (`environment.unlock`) —, e **um alerta sem Chave Principal não sai**. A
alternativa era pior das duas formas: deixar em claro um valor numa pasta que é
copiada sem criptografia, ou mandar o envelope no cabeçalho e deixar o
notificador recusar o `Authorization`. E o preço é o de §7f, dito: a entrega é
a parte de melhor esforço, e um alerta que não sai é um alerta que não sai.

**Where the value may travel, and where it may not.** The account ntfy demands
has a password, and AT draws one too — but not here: it is the SAME value
Caddy already carries in its own config, drawn once before any container
exists (`environment.draw_notify_gate`), because the manifest starts Caddy
before the notifier and nothing here can wait for ntfy to hand one back. This
module only recovers it (`environment.notify_gate_password`) and hands it to
`podman exec -i`'s STDIN — never in the argv, which the whole machine reads
through `ps`. The token itself is drawn BY ntfy inside the container and comes
back on STDOUT, which is the one place AT ever reads it. And AT's own
credential is never printed: the messages name the FILE, `status` says whether
it exists, and the delivery says what the notifier answered.

**The service's own folder is where the token sits, and the container sees it.**
That is the same place the configuration AT wrote for ntfy already lives, and
the same shape as the identity provider's session secret beside its own
`configuration.yml`; what a compromise of the notifier gains from it is a
credential that can publish to the topic that notifier already serves, and
nothing else — which is the scope above doing its job.
"""

from __future__ import annotations

import base64
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from at.core import files
from at.encryption import vault
from at.i18n import tr
from at_deploy import environment, podman

# The topic, and the account AT's credential belongs to. The topic is the
# NAME and not the brand: the phone reaches it through the edge now (the
# module's docstring), and it is the subject §3's per-topic scope is written
# about.
TOPIC = "at"
USER = "at"

# What ntfy writes on the token's line, so that whoever reads it later knows
# whose it is. The file carries the ENVELOPE of the value and nothing beside it.
LABEL = "at"

# §3's delimited scope, in ntfy's own word for it: the account publishes AND
# reads, and reaches no other topic. It is `read-write` and not `write-only`
# because it is now the ONE account the edge's M2M credential authenticates
# as (the module's docstring) — everybody who reaches the topic from outside
# does so through it, proved first by the Chave Principal at the edge.
SCOPE = "read-write"

# Where the credential lives: the service's own state folder (`environment.state`),
# which is the one folder the container mounts and the one the backup covers.
TOKEN_FILE = "token"

# O escopo da chave do cofre que sela a credencial (§4: uma chave por serviço
# ou finalidade). É o nome do SERVIÇO dono do valor — o mesmo com que o
# `environment` sela todo valor de um serviço.
VAULT_SCOPE = environment.NOTIFIER

# How much password Caddy's M2M credential draws — read by `environment
# .draw_notify_gate`, named here because this is the module that turns it back
# into the account's password (`decode_m2m`).
M2M_BYTES = 32

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

# The outcomes of `provision` and of `push`. The `cli` is what turns the
# push's into an exit code.
DRAWN = "drawn"       # AT had none, and made one
HELD = "held"         # AT already had one, and it was left alone
SENT = "sent"         # the notifier took the alert
NO_TOKEN = "no_token"  # nothing to authenticate with
FAILED = "failed"     # it was asked and did not happen


def encode_m2m(password: str) -> str:
    """`user:password`, base64 — the shape an `Authorization: Basic` header
    carries, and the value Caddy's M2M credential IS (`environment
    .draw_notify_gate`).

    **It is computed once, at DRAW time, and never at read time.** Opening a
    sealed envelope only ever replaces the sealed text with the clear one
    (`environment._opened`) — it cannot wrap what comes out in `user:` and
    base64 it afterwards. So what gets sealed is already this shape, and the
    Caddyfile embeds it exactly as read.
    """
    return base64.b64encode(f"{USER}:{password}".encode("ascii")).decode("ascii")


def decode_m2m(value: str) -> str:
    """The raw password a drawn M2M value carries — what `ntfy user add` takes.

    The reverse of `encode_m2m`, and the only place it runs: once, when the
    notifier stands and `provision` creates the account with the SAME
    password Caddy already has in its own config.
    """
    return base64.b64decode(value).decode("ascii").split(":", 1)[1]


def token_file() -> Path:
    """`App/services/notifier/token` — where the credential lives (§7f).

    Beside the `server.yml` AT wrote for the same service and inside the same
    state folder, which is §7's sentence that a service's state lives under
    `App/services/<service>/` — and what makes the credential survive a backup.
    """
    return environment.state(environment.NOTIFIER) / TOKEN_FILE


def _held(path: Path) -> str | None:
    """O TEXTO que um arquivo guarda: o envelope, ou o valor em claro.

    An empty file is nobody's credential and not a credential that is the empty
    string: the caller has to be able to tell "there is none" from "there is
    one" (`has_token`, `token`). **E é o TEXTO e não o valor**: o que a pasta
    guarda é o envelope, e quem o abre é `_value` — a mesma separação do
    `environment`, onde o arquivo da pasta é o selo e o diretório de execução é
    o valor.
    """
    try:
        kept = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return kept or None


def _value(text: str | None, key: bytes | None) -> str | None:
    """O VALOR claro que um arquivo guarda, aberto com a chave derivada (§4).

    **Uma pasta que nasceu antes do selo guarda o valor em claro** — é o corte
    `f` do item 50 que a migra —, e é por isso que um texto sem envelope É o
    valor: a leitura não pode depender de o selo já ter acontecido.

    Sem Chave um envelope não abre, e `unseal` responde `None` — a mesma
    resposta de uma Chave Principal errada, e a certa para quem lê: o chamador fica sem o
    que autenticar, em vez de mandar o envelope no cabeçalho e deixar o
    notificador recusar o `Authorization`.
    """
    if not text:
        return None
    if not vault.envelopes(text):
        return text
    if key is None:
        return None
    # `or None` e não só o retorno: um envelope vazio é ninguém, como um arquivo
    # vazio — a mesma regra de `_held`, dita do lado de dentro do selo.
    return vault.unseal(text, vault.derived_key(key, VAULT_SCOPE)) or None


def _sealed(path: Path, value: str, key: bytes) -> Path:
    """Write a credential SEALED at `0600` — what the folder keeps (§4, item 50).

    The mode is the writer's (`files.atomic_write_text`), because the value is
    only unreadable if the permission is set on the file that is about to carry
    it, and not after. O que ele grava é o ENVELOPE, no escopo do serviço dono do
    valor; quem o abre é quem tem a Chave Principal.
    """
    ring = vault.derived_key(key, VAULT_SCOPE)
    files.atomic_write_text(path, f"{vault.seal(value.strip(), ring)}\n",
                            mode=0o600)
    return path


def has_token() -> bool:
    """Se a pasta guarda a credencial do AT — sem abri-la.

    É a pergunta de quem só precisa saber que ela existe: o relatório de estado
    a faz, e quem vai SORTEAR também — um sorteio não se repete por cima do que
    já está lá. Quem precisa do VALOR pede a Chave (`token`).
    """
    return _held(token_file()) is not None


def token(key: bytes | None) -> str | None:
    """O valor da credencial do AT, aberto com a Chave desta leitura.

    Nothing here prints or returns it beyond the caller: the value is read at the
    moment of the POST and never travels through a message (§ the module's
    docstring). `None` é "não há com o que autenticar" — um arquivo que não
    existe, e também um envelope que esta Chave não abre.
    """
    return _value(_held(token_file()), key)


def write_token(value: str, key: bytes) -> Path:
    """Keep AT's credential SEALED — never printed, read only by the POST."""
    return _sealed(token_file(), value, key)


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


def publish(title: str, body: str,
            key: bytes | None = None) -> tuple[bool, str]:
    """POST one alert to the topic. `(ok, detail)` — and the detail is never the token.

    The one HTTP call this product makes to a service, and it is deliberately
    plain: the address is the loop, so an alert does not depend on the internal
    DNS, on the edge or on AT's own certificate — if any of the three falls,
    the alert still goes out. **`key` é a Chave desta leitura**: o que a pasta
    guarda é o envelope, e o que vai no cabeçalho é o valor que ele abriu. Um
    envelope que não abriu não vira cabeçalho — o notificador recusaria, e
    mandá-lo assim mesmo seria mandar um segredo por engano.
    """
    request = urllib.request.Request(target(), data=body.encode("utf-8"),
                                     method="POST")
    request.add_header("Title", title)
    request.add_header("Priority", PRIORITY)
    request.add_header("Tags", TAGS)
    held = token(key)
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


def push(title: str, body: str, secret: environment.Ask | None = None) -> str:
    """What actually pushes an alert: the credential, the POST, and AT's words.

    It is the ONE door for whoever has something to say, and §7f names its first
    caller: the approval of a demand that passed the risk threshold arrives
    through the notifier (§3, item 15). A network that did not answer is a fact
    to report and never an exception — an alert that failed is not a crash, it
    is an alert that failed, and whoever called this decides what to do about it.

    **E ele PEDE a Chave Principal** (§4, item 50): o que a pasta guarda é o
    envelope, e quem o abre é a Chave desta leitura — a mesma porta da subida
    (`environment.unlock`), porque nenhum dos dois atos compartilha a Chave do
    outro. Sem terminal não se pergunta, e sem a Chave Principal o alerta NÃO sai: é o
    preço, dito, e é o de §7f — a entrega é a parte de melhor esforço, e um
    alerta que não sai é um alerta que não sai. Pior seria o contrário: uma
    credencial em claro numa pasta que é copiada sem criptografia, ou o envelope
    indo no cabeçalho para o notificador recusar.

    **A credencial que não existe é dita ANTES da Chave Principal**: quem ainda não tem a
    do notificador precisa ouvir qual arquivo falta e qual comando o cria, e não
    uma pergunta sobre um valor que não há.
    """
    if not has_token():
        print(tr("services.notifier.no_token", where=token_file(), topic=TOPIC))
        return NO_TOKEN
    key, refusal = environment.unlock(secret)
    if refusal is not None:
        return FAILED
    ok, detail = publish(title, body, key)
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


def _draw(user: str, label: str, scope: str, password: str) -> str | None:
    """The four calls that make ONE credential in the notifier, in this order.

    1. **the account starts clean.** `user remove` first, because the only way a
       credential is ever re-drawn is a token file that went away, and that is a
       rotation: removing the account takes its tokens with it, so the credential
       that was replaced stops working instead of staying valid in a database
       nobody looks at. A missing account is a failure here and not an error.
    2. **the account.** ntfy refuses a user with no password, so AT hands one
       over on STDIN — never in the argv. `password` is not drawn here: it is
       Caddy's OWN M2M credential (`environment.notify_gate_password`), because
       the two have to agree on the same value or the edge's Basic auth fails
       against the account this creates.
    3. **the scope.** §3 asks least privilege for whoever reaches AT, and the
       mirror of it is this line: the account reaches the topic with the scope
       its own work needs and does nothing else.
    4. **the token**, drawn by ntfy itself and read off its own line. AT never
       invents the value, so it never has to write it into an argv. It is not
       what the edge authenticates with — that is the password above — but the
       delivery still uses it (`push`), so it is drawn all the same.

    `None` is a step that refused, and it has already been said in the caller's
    own word for WHICH call failed (`provision`).
    """
    _inside("user", "remove", user)
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


def provision(key: bytes | None) -> str:
    """Create AT's credential in the notifier — the environment's own act (§7f).

    Made when the notifier comes up, by the four calls `_draw` names, and kept
    in a `0600` file beside the notifier's own state — **selado**, porque um
    valor que o AT sorteia vai para a pasta como o envelope do cofre (§4, item
    50). `key` é a chave derivada desta subida, e ela vem do `up`, que a pediu
    antes de qualquer container: o que falta aqui é exatamente o que faz o `up`
    pedir a Chave Principal (`environment`).

    **The account's password is not drawn here — it is READ.** Caddy's own M2M
    credential was drawn before ANY container, because the manifest starts
    Caddy before the notifier and nothing here could wait for ntfy to hand one
    back (`environment.draw_notify_gate`). This is where that same value
    becomes the account ntfy actually holds — the one act that makes the edge's
    Basic auth and the notifier's own user table agree.

    An environment that already has a credential is left exactly as it is: the
    file is the truth, and whoever wants a new one deletes it and brings the
    environment up again — the same rule the gate's secret follows (`caddy`).

    **A credencial que nasceu em CLARO é a exceção, e é a migração** (item 50,
    corte `f`): a pasta que nasceu antes do selo guarda o valor sem envelope, e
    a subida o re-sorteia como faria com um que faltasse — a conta antiga sai
    primeiro (`_draw`), então o valor que já pode ter sido copiado deixa de
    autenticar. Uma credencial SELADA é deixada como está, que é a regra de
    cima.
    """
    held = _held(token_file())
    if held is not None and vault.envelopes(held):
        return HELD
    if key is None:
        # Um sorteio SELA, e sem Chave não há selo: gravar o valor em claro seria
        # o que este item existe para não haver. É a mesma recusa do `draw_gate`,
        # dita em vez de estourada.
        print(tr("services.notifier.unsealed", where=token_file()))
        return FAILED
    if not _ready():
        print(tr("services.notifier.not_ready",
                 where=f"{environment.NOTIFIER_DATA}/{environment.NOTIFIER_AUTH}"))
        return FAILED

    password = environment.notify_gate_password(key)
    if password is None:
        print(tr("services.notifier.unsealed", where=environment.notify_gate_file()))
        return FAILED

    token = _draw(USER, LABEL, SCOPE, password)
    if token is None:
        return FAILED

    write_token(token, key)
    print(tr("services.notifier.drawn", where=token_file(), topic=TOPIC,
             scope=SCOPE))
    return DRAWN
