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

**The credential is AT's, drawn by AT, and it lives in a `0600` file — SEALED.**
A token is a SECRET, and the vault (§4) took the file over: what it keeps is the
ENVELOPE the Access Phrase seals, at `0600`, **never in the argv and never
printed**. ntfy keeps only the HASH — its `user.db`, inside the state folder the
container mounts — so the plaintext exists in exactly one place, and that one
place is unreadable in a copy of the folder. **E a cópia continua servindo**: a
credencial volta a ser lida com a Frase, e é isso que faz uma pasta copiada
publicar de novo (§3, a promessa do backup).

**Quem lê o valor claro é o `at-deploy`, de FORA, e é ele que pede a Frase.**
Nenhum container lê as duas pontas — o notificador monta só o `server.yml`, e a
fatia 2 do item 50 mediu isso —, então o diretório de execução não é o lugar
delas: quem as lê é o processo que roda o `up`, o `notify` e o `notify creds`, e
nenhum dos três compartilha a Chave de outro. Cada leitura abre o envelope com a Frase
do PRÓPRIO ato — a mesma porta da subida (`environment.unlock`, e `sealing_key`
para quem SELA) —, e **um alerta sem Frase não sai**. A alternativa era pior das
duas formas: deixar em claro um valor numa pasta que é copiada sem criptografia,
ou mandar o envelope no cabeçalho e deixar o notificador recusar o
`Authorization`. E o preço é o de §7f, dito: a entrega é a parte de melhor
esforço, e um alerta que não sai é um alerta que não sai.

**Where the value may travel, and where it may not.** The account ntfy demands
has a password, so AT draws one and hands it over on the STDIN of `podman exec
-i` — never in the argv, which the whole machine reads through `ps`. The token
itself is drawn BY ntfy inside the container and comes back on STDOUT, which is
the one place AT ever reads it; the argv never carries it. And AT's own
credential is never printed: the messages name the FILE, `status` says whether
it exists, and the delivery says what the notifier answered.

**The phone's credential is printed on demand, with the Frase de Acesso as the
door.** The ACL has two ends, and §7f names the other one: AT publishes, the
phone reads. That credential is the PERSON'S, and there is no way for it to
reach a phone except through the person's eyes — but "reach a phone" happens
more than once in a credential's life (a new phone, a re-installed app, a
person who did not save the scrollback), so a value sealed behind the same
Frase that opens every other secret this vault keeps does not need a
print-once rule on TOP of the seal. **`at-deploy services notify creds`**
opens it exactly like `push` opens AT's own token: the Frase is asked, the
envelope is unsealed, and what comes back is the value — every time, not the
first time (2026-09-28, replacing the earlier once-only rule). Its scope is
the mirror of AT's — `read-only` on the topic, and nothing else — so the two
credentials §6 declares neither serve for the other's work nor for anything
beyond the topic.

**Duas credenciais para o celular, e não uma** (2026-09-28): o app do ntfy não
tem campo para um token cru — o login dele pede usuário e senha, e o campo do
usuário não aceita ficar vazio, que é a forma de que o truque do ntfy
(`Authorization` via Basic com usuário vazio) precisa. Então a senha da conta
`phone`, que `_draw` sempre sorteou e que antes se jogava fora, agora fica —
selada do mesmo jeito que o token —, e o app loga com a conta de verdade:
usuário `phone`, esta senha. O token continua existindo para quem tem como
mandar um cabeçalho (`reached`, a prova deste arquivo).

**E o selo não fica no meio da impressão.** O envelope é escrito no arquivo, e o
que vai para a tela é o valor DESTA abertura — sorteado agora, ou lido de volta
com a Frase, tanto faz: quem tem a Frase já provou quem é, e reler não é um
segredo maior do que sortear. A única coisa que não sai em claro é o arquivo:
o que fica na pasta é sempre o envelope, e é a Chave desta chamada que o abre
(`subscribe`).

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
from at.encryption import vault
from at.i18n import tr
from at_deploy import environment, podman

# The topic, and the account AT's credential belongs to. The topic is the
# NAME and not the brand: the phone subscribes to it and AT publishes to it,
# and it is the subject §3's per-topic scope is written about.
TOPIC = "at"
USER = "at"

# What ntfy writes on the token's line, so that whoever reads it later knows
# whose it is. The file carries the ENVELOPE of the value and nothing beside it.
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

# The phone's ACCOUNT PASSWORD, kept where the token is (2026-09-28). ntfy's own
# apps do not offer a way to log a subscription in with a bare token — the
# Login dialog asks for a username and a password, and the username field
# cannot be left blank there, which is the one shape ntfy's basic-auth-as-token
# trick needs (MEASURED: `curl -u ':<token>'` answers `200`, `curl -u
# 'x:<token>'` answers `401` — the username field is not ignored, it has to be
# EMPTY, and an app's form that refuses an empty field cannot send that). So the
# password `_draw` used to draw and forget is kept too, sealed the same way as
# the token: the app logs in with the real account, `phone` and this password,
# instead of routing the token through a form that cannot carry it.
PHONE_PASSWORD_FILE = "phone-password"

# O escopo da chave do cofre que sela as duas pontas (§4: uma chave por serviço
# ou finalidade). É o nome do SERVIÇO dono do valor — o mesmo com que o
# `environment` sela todo valor de um serviço —, e não um nome novo: as duas
# credenciais são do notificador, e é sob ele que a Frase as abre.
VAULT_SCOPE = environment.NOTIFIER

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

# How much password AT draws for the account it creates. AT's own account
# still has nobody who logs in with it — the credential that matters there is
# the token — but the phone's is kept (`PHONE_PASSWORD_FILE`), so this only has
# to be a value nobody can guess, not one a person types.
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
PHONE_DRAWN = "phone_drawn"  # the phone had none, and got one — shown
PHONE_HELD = "phone_held"    # the phone already had one — shown again, with the Frase
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
    """O VALOR claro que um arquivo guarda, aberto com a Chave do Cofre (§4).

    **Uma pasta que nasceu antes do selo guarda o valor em claro** — é o corte
    `f` do item 50 que a migra —, e é por isso que um texto sem envelope É o
    valor: a leitura não pode depender de o selo já ter acontecido.

    Sem Chave um envelope não abre, e `unseal` responde `None` — a mesma
    resposta de uma Frase errada, e a certa para quem lê: o chamador fica sem o
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
    valor; quem o abre é quem tem a Frase.
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


def has_phone() -> bool:
    """Se a pasta guarda o token do celular — sem abri-lo (`has_token`)."""
    return _held(phone_file()) is not None


def phone_token(key: bytes | None) -> str | None:
    """O valor do token do celular, aberto com a Chave desta leitura.

    It IS printable, and it is printed in exactly one place (`subscribe`) — e de
    lá sai o valor SORTEADO, nunca uma segunda leitura. O que esta porta responde
    é o que a prova da leitura precisa, e `status` diz o arquivo.
    """
    return _value(_held(phone_file()), key)


def write_phone_token(value: str, key: bytes) -> Path:
    """Keep the phone's credential beside AT's, sealed at the same `0600`."""
    return _sealed(phone_file(), value, key)


def phone_password_file() -> Path:
    """`App/services/notifier/phone-password` — the account ntfy's own app logs in with.

    Beside the token, in the same folder, for the same reason (`phone_file`):
    the two are the phone's whole ACL end, and a copied folder carries both.
    """
    return environment.state(environment.NOTIFIER) / PHONE_PASSWORD_FILE


def has_phone_password() -> bool:
    """Se a pasta guarda a senha da conta `phone` — sem abri-la (`has_phone`)."""
    return _held(phone_password_file()) is not None


def phone_password(key: bytes | None) -> str | None:
    """O valor claro da senha da conta `phone`, aberto com a Chave desta leitura."""
    return _value(_held(phone_password_file()), key)


def write_phone_password(value: str, key: bytes) -> Path:
    """Keep the phone's account password sealed, beside its token."""
    return _sealed(phone_password_file(), value, key)


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


def reached(answer: gate.Answer | None = None, key: bytes | None = None) -> bool:
    """Com o token do celular, o tópico responde pelo nome — a primeira metade.

    O token viaja no cabeçalho e nunca no argv, a mesma regra que a entrega
    segue, e o que se lê é o STATUS — a resposta que o ntfy dá ao app. Um
    "nada respondeu" (`None`) não é nem um nem outro: é "não deu para saber", e
    é por isso que a comparação é com `READ` e não com "diferente de erro".

    **`key` é a Chave do Cofre desta leitura** (§4): o que a pasta guarda é o
    envelope, e a prova precisa do valor que o celular guardou. Sem ela um token
    selado não abre, e a metade não fecha — que é a resposta honesta de quem não
    abriu o que a pasta guarda.
    """
    held = phone_token(key)
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


def unproved(answer: gate.Answer | None = None,
             key: bytes | None = None) -> str | None:
    """A sentença da metade que não fechou — ou `None` quando as duas fecham.

    As duas são perguntadas na ordem em que o celular as encontra, e a caminhada
    PARA na primeira que não fecha: perguntar a segunda depois de o token não
    ler seria perguntar sobre uma porta que já não se sabe fechada.
    """
    if not reached(answer, key):
        return "services.notifier.phone.unread"
    if not turned_away(answer):
        return "services.notifier.phone.unrefused"
    return None


def proved(answer: gate.Answer | None = None,
           key: bytes | None = None) -> bool:
    """Se o celular lê o notificador pelo nome — as duas metades de uma vez."""
    return unproved(answer, key) is None


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

    **E ele PEDE a Frase de Acesso** (§4, item 50): o que a pasta guarda é o
    envelope, e quem o abre é a Chave desta leitura — a mesma porta da subida
    (`environment.unlock`), porque nenhum dos dois atos compartilha a Chave do
    outro. Sem terminal não se pergunta, e sem a Frase o alerta NÃO sai: é o
    preço, dito, e é o de §7f — a entrega é a parte de melhor esforço, e um
    alerta que não sai é um alerta que não sai. Pior seria o contrário: uma
    credencial em claro numa pasta que é copiada sem criptografia, ou o envelope
    indo no cabeçalho para o notificador recusar.

    **A credencial que não existe é dita ANTES da Frase**: quem ainda não tem a
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


def _draw(user: str, label: str, scope: str) -> tuple[str, str] | None:
    """The four calls that make ONE credential in the notifier, in this order.

    1. **the account starts clean.** `user remove` first, because the only way a
       credential is ever re-drawn is a token file that went away, and that is a
       rotation: removing the account takes its tokens with it, so the credential
       that was replaced stops working instead of staying valid in a database
       nobody looks at. A missing account is a failure here and not an error.
    2. **the account.** ntfy refuses a user with no password, so AT draws one,
       hands it over on STDIN — never in the argv.
    3. **the scope.** §3 asks least privilege for whoever reaches AT, and the
       mirror of it is this line: the account reaches the topic with the scope
       its own work needs and does nothing else.
    4. **the token**, drawn by ntfy itself and read off its own line. AT never
       invents the value, so it never has to write it into an argv.

    Returns `(token, password)`, and not the token alone (2026-09-28): the
    caller decides what to keep. AT's own account still has nobody who logs in
    with it (`provision` throws the password away, as it always did); the
    phone's does, because ntfy's own apps have no field for a bare token
    (`PHONE_PASSWORD_FILE`'s comment).

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
    return found.group(0), password


def provision(key: bytes | None) -> str:
    """Create AT's credential in the notifier — the environment's own act (§7f).

    The write end of the ACL, and it is the environment that draws it: it is
    made when the notifier comes up, by the four calls `_draw` names, and kept
    in a `0600` file beside the notifier's own state — **selado**, porque um
    valor que o AT sorteia vai para a pasta como o envelope do cofre (§4, item
    50). `key` é a Chave do Cofre desta subida, e ela vem do `up`, que a pediu
    antes de qualquer container: o que falta aqui é exatamente o que faz o `up`
    pedir a Frase (`environment`).

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

    drawn = _draw(USER, LABEL, SCOPE)
    if drawn is None:
        return FAILED

    token, _password = drawn
    write_token(token, key)
    print(tr("services.notifier.drawn", where=token_file(), topic=TOPIC,
             scope=SCOPE))
    return DRAWN


def _close(answer: gate.Answer | None, key: bytes | None) -> bool:
    """Diz a prova da leitura, e responde se ela fechou.

    **Uma prova que não alcança nada não é uma prova.** `unproved` nomeia qual
    das duas metades não fechou, e o veredito sai com a estrada inteira à mostra
    — a URL, o tópico e o arquivo da CA —, porque quem lê isto está com o
    celular na mão e o que ele precisa saber é o que conferir no aparelho.
    `key` é a Chave desta leitura: o token da pasta é o envelope, e é com ela que
    a metade que lê abre o que o celular guardou.
    """
    reason = unproved(answer, key)
    if reason is None:
        print(tr("services.notifier.phone.proved", url=phone_url(),
                 topic=TOPIC))
        return True
    print(tr(reason, url=phone_url(), topic=TOPIC,
             host=environment.notifier_host(),
             authority=environment.authority_file(),
             code=NO_TOKEN_REFUSED))
    return False


def subscribe(answer: gate.Answer | None = None,
              secret: environment.Ask | None = None) -> str:
    """The phone's credential — drawn if there is none, shown either way (§7f).

    §6 says it in one line: in `ntfy` the ACL is per topic, **AT publishes and
    the phone reads**, and neither token serves for anything else. The write end
    is `provision`'s and happens with the environment; this is the read end, and
    it is the OPERATOR's act (item 27): the phone is not the machine the
    environment runs on, so nothing here can be decided by bringing the
    environment up.

    **It is shown every time, on demand, and that is the point of the word**
    (`at-deploy services notify creds`, 2026-09-28). The earlier shape of this
    door printed the value once and refused to again — the file was "where a
    person reads it a second time", which meant reading it back by hand, past
    the vault, past the point of the vault existing at all. That is not a
    security property, only friction, and a person who still has the Frase de
    Acesso has already proven who they are — so asking again is the same
    question `unlock` and `sealing_key` already answer, not a second gate.

    **Two values now, and not one.** ntfy's own apps do not have a field for a
    bare token — the Login dialog asks for a username and password, and the
    username cannot be left empty there, which is the one shape ntfy's
    basic-auth-as-token trick needs (`PHONE_PASSWORD_FILE`'s comment). So the
    account's real password is kept too, sealed beside the token: the app logs
    in with `phone` and this password, and the token stays for whoever's client
    DOES take a header (`Authorization: Bearer`, `reached`).

    Two scopes and not one, and it is measured (§ the module's docstring): the
    account may READ the topic and nothing else — it cannot publish to it, and
    it cannot reach another one. An environment that already has BOTH files is
    left alone — no re-draw, no rotation — and the way to a new pair is
    deleting them and running this again, which is the rotation `_draw` starts
    clean for.

    **A pasta que só tinha o token (o formato de antes do par) entra pela mesma
    porta**: falta a senha, e é a MESMA condição de "não há credencial ainda" —
    a rotação que `_draw` sempre começa com `user remove` cuida disso de graça,
    porque o token velho para de valer no mesmo golpe que cria o par novo.
    Nenhuma migração à parte, e nenhum estado onde só uma metade existe.

    **A leitura é PROVADA no fim do ato, e é o que a palavra promete** (§7f): o
    celular não é a máquina onde o ambiente roda, então "o token existe" não é a
    mesma coisa que "o celular lê". As duas metades são perguntadas pelo NOME, na
    borda (`_close`), e o ato termina `PHONE_UNPROVED` quando alguma não fecha —
    o token fica, porque ele foi sorteado, e o que não fechou é a leitura. É a
    mesma regra da entrega: `notify` também recusa quando o alerta não sai.

    **E ele PEDE a Frase de Acesso, porque ele SELA e porque ele ABRE.** O que a
    pasta guarda é o envelope (§4, item 50): o sorteio que sai daqui vai selado,
    e a leitura desta chamada, ou de qualquer outra depois dela, abre o que está
    lá — as duas coisas precisam da Chave, e é por isso que esta porta pergunta
    SEMPRE (`environment.sealing_key`), e não a que pergunta só quando a pasta
    tem o que abrir.
    """
    if not podman.present():
        # A machine with no runtime has no notifier to ask, and there is nothing
        # to wait for: `up` is what names the two ways out, and this word is the
        # operator's and can be reached before the environment ever stood. **E
        # ele vem ANTES da Frase de propósito**: sem runtime a prova não tem por
        # onde ser feita, e perguntar a Frase antes seria pedir o que ainda não
        # faz falta.
        print(tr("services.no_podman.status"))
        return FAILED
    key, refusal = environment.sealing_key(secret)
    if refusal is not None:
        return FAILED
    if has_phone() and has_phone_password():
        # `key` já provou que abre tudo o que a pasta guarda selado
        # (`environment._ask_phrase`, chamado por `sealing_key` acima, confere
        # as DUAS pontas do notificador — `environment._sealed_files`): o que
        # seria uma Frase errada já se recusou lá, antes de chegar aqui.
        token, password = phone_token(key), phone_password(key)
        print(tr("services.notifier.phone.held", token=token, password=password,
                 where=phone_file(), url=environment.notifier_public_url(),
                 topic=TOPIC, authority=environment.authority_file()))
        return PHONE_HELD if _close(answer, key) else PHONE_UNPROVED
    if not _ready():
        print(tr("services.notifier.not_ready",
                 where=f"{environment.NOTIFIER_DATA}/{environment.NOTIFIER_AUTH}"))
        return FAILED

    drawn = _draw(PHONE_USER, PHONE_LABEL, PHONE_SCOPE)
    if drawn is None:
        return FAILED

    token, password = drawn
    write_phone_token(token, key)
    write_phone_password(password, key)
    print(tr("services.notifier.phone.drawn", token=token, password=password,
             topic=TOPIC, scope=PHONE_SCOPE, url=environment.notifier_public_url(),
             authority=environment.authority_file(), where=phone_file()))
    return PHONE_DRAWN if _close(answer, key) else PHONE_UNPROVED
