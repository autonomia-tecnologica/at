"""at's own door into the notifier's topic — the push the clock fires on its
own, and the read the page asks for, with no `at_deploy` between the WebApp and
ntfy (§4, item 29's second slice, item 50; TASK-176, fatia 3/3).

**Reading TASK-146 answered the question this module opens with.** The WebApp's
container mounts the Working Folder itself (`Mirror`, `at_deploy/environment
.py`), so `App/services/notifier/token` is already there to read — nothing new
has to be mounted, and nothing new has to be sealed. What travels is the
DERIVED key alone (§4, item 50), read once at boot and kept in memory
(`at.ui.webapp.keys.notifier_key`) — the very key `at_deploy.notifier` already
derives to seal the same file (`notifier.VAULT_SCOPE`), so opening the envelope
here re-derives nothing and reseals nothing.

**`at` does not import `at_deploy`, so the file's PATH is built from the same
piece both sides already share (`at.core.paths.services_dir`) and not read off
the other package.** The constants below — the scope's name, the file's name,
the topic — are the same words `at_deploy/notifier.py` spells, kept apart the
way `GATE_ENV` is kept apart on both sides of that same line: two definitions
of one small fact cost less than a dependency the layering forbids.

**The ADDRESS is the one thing this module cannot know on its own.** A
container's `127.0.0.1` is itself and nobody else (`gate.portal`'s own
argument), so the notifier's address on the network the two containers share is
handed over by the environment, in `NETWORK_ENV` — and a process that never got
the variable has no address to publish to, which is the CLOSED answer and not a
guess at the host's loop.

**Delivery is best-effort, exactly as `at_deploy.notifier.push` already is.** A
network that does not answer, a key this boot does not hold, a token the
folder has not drawn yet — every one of them is a push that does not go out,
and none of them is an exception the clock's round has to survive by name
(`at.ui.ask.remind` catches broadly, the way `tick` does).

**The READ is the other end of the ACL, and it is the PHONE's credential**
(TASK-176, fatia 3/3). ntfy's access is per ACCOUNT and per topic, so the one
AT holds cannot be `write-only` and `read-only` at the same time — the write
end (`token`) and the read end (`phone-token`) are two accounts, and §7f names
both. What the WebApp reads the topic WITH is therefore the phone's credential,
and it is the choice the item left open because the alternative would have been
a THIRD account drawn for the page: that drawing is the environment's act and it
asks the Main Key, which no WebApp holds — so a credential of its own is one
this process could never make, and reusing the end that already exists is the
only road that does not need one.

**And it is not a new envelope.** `phone-token` is sealed under the same scope
the WebApp's key is derived from (`VAULT_SCOPE` is the notifier's own name), so
the key this boot holds opens it exactly as it opens AT's — the same file,
opened by somebody who already could (§ container.md's own sentence about the
write end). Nothing here reseals, redraws or prints anything; the value goes
into the `Authorization` header of one GET and nowhere else, and the person's
own phone keeps logging in with the account password it was given.

**The read is PAGED the way the phone reads**: ntfy answers `poll=1` with what
its memory holds and closes the connection — the same `json?poll=1` the phone's
app asks on open, and the same shape `at_deploy.notifier.reached` proves the
ACL with. It is not a stream: this door answers a request that was made and
never holds a connection open, which is what keeps a page refresh from being a
subscription.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from pathlib import Path

from at.core import paths
from at.encryption import vault

# The scope the Main Key derives this key under, and the two files it opens —
# the same words `at_deploy/notifier.py` spells (`VAULT_SCOPE`, `TOKEN_FILE`,
# `PHONE_FILE`), kept apart rather than imported across the line `at` does not
# cross.
NOTIFIER = "notifier"
TOKEN_FILE = "token"
PHONE_FILE = "phone-token"

# The topic AT's credential is scoped to write-only — `at_deploy.notifier
# .TOPIC`, spelled again for the same reason as the two above.
TOPIC = "at"

# A leitura, no vocabulário do PRÓPRIO ntfy: um `poll` do tópico devolve o que
# está na memória dele e fecha (`at_deploy.notifier.POLL`, the same string the
# phone's app asks with).
POLL = "json?poll=1"

# O que uma mensagem É, do lado de fora: os campos que a página desenha, e só
# eles. O ntfy responde mais do que isto (`event`, `click`, `actions`, o
# `raw` do corpo) — e o que não é desenhado não viaja, porque uma página que
# recebesse o objeto inteiro estaria lendo um vocabulário que não é do AT.
FIELDS = ("id", "time", "title", "message", "priority", "tags")

# The variable the environment hands the WebApp: the notifier's address on the
# network the two containers share (`container(NOTIFIER)`, `NOTIFIER_PORT`, on
# the `at_deploy` side). Named here because this is the module that READS it —
# the same rule `webapp.keys` and `core.gate`'s `GATE_ENV` are named by.
NETWORK_ENV = "AT_NOTIFIER"

# What every alert announces itself with — `at_deploy.notifier`'s own three,
# repeated for the reason above: silence at the default priority is a push
# nobody notices, and the tag gives it an icon.
TITLE = "AT"
PRIORITY = "high"
TAGS = "bell"

# How long a POST waits for the notifier before the round moves on.
TIMEOUT = 10.0


def token_file() -> Path:
    """`App/services/notifier/token` — the same file `at_deploy.notifier
    .token_file` names, built from the one piece both sides share."""
    return paths.services_dir() / NOTIFIER / TOKEN_FILE


def phone_file() -> Path:
    """`App/services/notifier/phone-token` — the READ end of the ACL (§7f).

    The same folder and the same file name `at_deploy.notifier.phone_file`
    names, for the reason above — and, like the write end, this process only
    ever opens it, never draws one.
    """
    return paths.services_dir() / NOTIFIER / PHONE_FILE


def _held(where: Path) -> str | None:
    try:
        kept = where.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return kept or None


def _value(text: str | None, key: bytes | None) -> str | None:
    """O VALOR claro que um arquivo guarda, aberto com a chave derivada (§4).

    The file may still carry the value in clear (a folder from before the
    seal, migrated by `at_deploy.notifier.provision` the next time the
    environment comes up) — a text with no envelope in it IS the value, the
    same reading `at_deploy/notifier.py:_value` gives it.
    """
    if not text:
        return None
    if not vault.envelopes(text):
        return text
    if key is None:
        return None
    return vault.unseal(text, key) or None


def token(key: bytes | None) -> str | None:
    """The write credential's clear value, opened with the DERIVED key this
    boot holds — or `None` when there is nothing to open it with."""
    return _value(_held(token_file()), key)


def phone_token(key: bytes | None) -> str | None:
    """The READ credential's clear value — the phone's, opened with the SAME
    derived key.

    **One key, two files, and that is the whole of the decision** (the module's
    docstring): both ends of the ACL belong to the notifier and are sealed
    under its scope, so the key the WebApp was handed at `up` opens the read
    end exactly as it opens the write one. A `None` here is the same answer
    `token` gives: this boot cannot open what the folder keeps, or the folder
    has not had a phone credential drawn yet — neither of which is an
    exception, and both of which make the read answer nothing.
    """
    return _value(_held(phone_file()), key)


def target() -> str | None:
    """Where the topic is, on the network this container shares with the
    notifier's — or `None` when the environment handed over no address.

    **No fallback to the host's loop.** A WebApp running loose, or a folder
    that came up without the notifier's container beside it, has no such
    variable — and answering with a guess would be `gate.portal`'s own mistake,
    named there: a port is a port, and reading one that happens to be open as
    the notifier would be worse than a push that does not go out.
    """
    held = os.environ.get(NETWORK_ENV, "").strip()
    return f"http://{held}/{TOPIC}" if held else None


def publish(title: str, body: str, key: bytes | None) -> tuple[bool, str]:
    """POST one alert to the topic. `(ok, detail)` — and the detail is never
    the token.

    Two ways of having nothing to send with, and both answer the same shape
    as a refusal the notifier itself gave: no address means the environment
    never told this process where the notifier is, and no token means the
    folder has not drawn one yet or this boot cannot open the one it has.
    Neither is raised — the caller decides what a push that did not go out
    is worth (`at.ui.ask.remind`).
    """
    where = target()
    if where is None:
        return False, "no_address"
    held = token(key)
    if held is None:
        return False, "no_token"
    request = urllib.request.Request(where, data=body.encode("utf-8"), method="POST")
    request.add_header("Title", title)
    request.add_header("Priority", PRIORITY)
    request.add_header("Tags", TAGS)
    request.add_header("Authorization", f"Bearer {held}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return 200 <= response.status < 300, str(response.status)
    except urllib.error.HTTPError as error:
        code = str(error.code)
        error.close()
        return False, code
    except (urllib.error.URLError, OSError) as error:
        return False, str(getattr(error, "reason", error))


def _messages(body: object) -> list[dict]:
    """O que o tópico respondeu, reduzido aos campos que a página desenha.

    An answer that is not the list ntfy promises is an EMPTY topic here and
    never a raise: what the notifier says is its business, and a page asking
    what arrived is not the place to fail over a shape. An entry that is not
    an object is dropped for the same reason, and a field the message does not
    carry is simply absent — `None` would be the page drawing an empty title
    it did not receive.
    """
    if not isinstance(body, list):
        return []
    return [
        {name: entry[name] for name in FIELDS if name in entry}
        for entry in body
        if isinstance(entry, dict)
    ]


def read(key: bytes | None) -> tuple[list[dict], str]:
    """O que o tópico está segurando AGORA: `(mensagens, recusa)`.

    It is the `poll` the phone asks on open (the module's docstring), read
    with the phone's credential and never with AT's — the write end cannot read
    its own topic back, and that is measured (§7f).

    **A read that did not happen is not an empty topic**, so the two come back
    told apart: `recusa` is the empty string when the notifier answered, and
    otherwise it is AT's own word for what stopped it (`no_address`,
    `no_token`) or the notifier's/network's own answer. The caller decides what
    to draw — this door raises nothing, exactly as `publish` does, because a
    notifier that is down is a fact about the environment and not a bug here.
    """
    where = target()
    if where is None:
        return [], "no_address"
    held = phone_token(key)
    if held is None:
        return [], "no_token"
    request = urllib.request.Request(f"{where}/{POLL}")
    request.add_header("Authorization", f"Bearer {held}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        code = str(error.code)
        error.close()
        return [], code
    except (urllib.error.URLError, OSError) as error:
        return [], str(getattr(error, "reason", error))
    try:
        body = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        # A resposta que não é o JSON que o ntfy promete é uma resposta que não
        # se sabe ler — o mesmo "não deu para saber" que um endereço ausente, e
        # nunca um estouro no meio de um pedido da página.
        return [], "unreadable"
    return _messages(body), ""
