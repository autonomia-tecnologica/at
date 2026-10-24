"""The environment's vocabulary: outcomes, constants, names and injected types.

Everything here is a value and nothing is a step. The facade (`environment`)
re-exports every name, so the rest of the product keeps reading them from there.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

# What a person answers with, injected the way `boot` and `lang` take theirs: a
# test asks the same question without a terminal.
Ask = Callable[[str], str]

# What spends an elevation, injected the same way — and the suite MUST inject it:
# a test that ran `sudo` would be a test that asked a person for a password.
Spend = Callable[..., None]


# The outcomes of `up` and `update`, and the CLI is what turns them into an
# exit code.
UP = "up"                 # the environment is standing
UPDATED = "updated"       # `update` re-pinned and recreated, over a folder that
                          # already had an environment
PROVISIONED = "provisioned"  # `up` refused: this folder already has one — the
                             # word for a second time is `update`
INSTALL = "install"       # the person installs the Podman; AT said how
HOSTED = "hosted"         # the folder stays on the hosted path, and nothing moved
NO_ANSWER = "no_answer"   # no terminal to ask in: neither way was taken
FAILED = "failed"         # a service did not come up (or `update` on a folder
                          # with no environment yet — the word for that is `up`)
UNREADABLE = "unreadable"  # the Main Key does not open what the folder keeps
# A pasta de estado tem um caminho com a forma errada — um ARQUIVO onde o
# serviço monta uma pasta, ou o contrário. Não é um serviço que não subiu: é um
# estado que o AT sabe diagnosticar antes de tentar, e a subida recusa com a
# frase em vez de estourar no meio dela.
MALFORMED = "malformed"


class SealedRefused(Exception):
    """Um envelope que esta subida não abriu — e não se monta o que não se abriu.

    Ele guarda contra a única coisa que não pode acontecer em silêncio: o
    envelope indo parar no diretório de execução, onde o container o leria como
    se fosse o valor. A Chave Principal é conferida contra TUDO o que a pasta guarda antes
    de qualquer container (`_not_opened`), então chegar aqui é uma
    inconsistência — a cópia mudou entre a conferência e a montagem, ou alguém
    montou sem Chave Principal nenhuma. A resposta é a mesma nos dois casos, e é a do §4:
    o que não se abriu não se usa.
    """


# The outcomes of the gate's credential change — item 27's operator act (§7b).
# The row is written in all three: what separates them is how far the change
# travelled, and the person is owed exactly that difference.
CREDENTIAL_CHANGED = "changed"   # the row, the derivation and the provider
CREDENTIAL_UNKNOWN = "unknown"   # nobody in this folder wears that name
CREDENTIAL_PENDING = "pending"   # the folder has it; the gate does not yet

# The port the edge is reached on, and it is 443 because that is the port a URL
# does not say: the person types `https://<site_host()>`, and §7f's phone takes
# a URL and nothing more — a `:8443` in the middle of it is a port nobody asked
# to know. The Caddy is the edge, and its port is the FIRST the environment
# publishes outside the loop (§7e).
#
# **It costs its OWN elevation now, and that is the price of there being no
# DNS of the environment's own any more** (TASK-187): a rootless container
# publishes nothing below the kernel's floor, and `443` is itself under it on
# every machine that ships the rule — the floor has to move to `443` for the
# environment to come up at all (`elevate`).
PORT = 443
# Where the WebApp answers inside its container. **The address is the fix of
# this piece, and it is measured**: an app on the container's own loop is
# reached by nobody — the published port lands on the container's network
# address and finds nothing there, and the edge is another container whose
# `127.0.0.1` is itself. So the app answers on the container's addresses, and
# what keeps that from being an exposure is the network and the gate secret
# (`GATE_ENV`, §7b): who reaches it and brings no secret is refused with 403.
#
# The PORT is unchanged, and §7c is why: exposing moves the address the person
# reaches, never the one the WebApp listens on. `test_environment` holds the
# port to the WebApp's OWN constant, so the declaration cannot drift from the
# thing it names.
ALL = "0.0.0.0"
WEBAPP_HOST = ALL
WEBAPP_PORT = 12345

# The environment's network — the one the services of the environment talk over.
# **It is ONE network, and a second one buys almost nothing here**, which is a
# measurement and not a preference: two podman networks do not reach each other
# at all (no route, and the name only resolves inside the network that gave it),
# so what decides a service's network is nothing but WHO IT HAS TO TALK TO. The
# Caddy reaches the WebApp (its `reverse_proxy`), the WebApp reaches the gate
# (its own "is my portal standing"), and the Caddy reaches the gate
# (`forward_auth`) — so those three stand together, and whoever has business
# with them stands with them.
NETWORK = "at"

# The prefix of every container AT creates. A container is named for the
# service it runs, and the name is AT's: `down` removes what the name says,
# and another AT on this machine has other names.
PREFIX = "at-"

# The label every container of this environment carries, for whoever reads the
# runtime by hand and wants to know whose it is.
LABEL = "at.service"

# O DIRETÓRIO DE EXECUÇÃO: o que o container LÊ, materializado fora da Pasta de
# Trabalho (item 50). **A pasta de estado é a FONTE, e ele é a cópia que serve a
# subida** — o `up` o escreve para cada serviço e o `down` o apaga —, e ele mora
# onde morre: o `XDG_RUNTIME_DIR` da máquina quando ele existe (permissão `0700`,
# `tmpfs`, apagado no logout), e o temporário do sistema quando não existe. **É
# por aqui que um arquivo selado volta a ser lido sem a Chave Principal no
# processo**: quem abre o envelope é o `up`, uma vez, com a Chave Principal que a subida
# digitou, e o que o container monta é a cópia clara (`_materialize`).
#
# **O nome carrega o id da pasta e nunca o nome dela**: dois ambientes nesta
# máquina não se cruzam, e o nome da pasta de ninguém aparece num diretório
# compartilhado. O prefixo é o mesmo das imagens e dos containers: `at-`.
RUN_ENV = "XDG_RUNTIME_DIR"
RUN_ID = 12

# A pasta do diretório de execução que espelha a dos serviços, e a do portão.
# O diretório de execução é um `App/` em miniatura — `<run>/services/<serviço>/`
# é o que aquele serviço lê, e `<run>/caddy/gate` é a cópia clara do segredo do
# portão —, e as duas usam o MESMO nome que a pasta usa, para que quem olha um
# reconheça o outro.
RUN_SERVICES = "services"

# A cópia materializada do portão, montada no WebApp (§7b). Ele é o TERCEIRO dos
# leitores que o cofre nomeia e o único que não é o dono do arquivo: o Caddy lê
# o portão dentro do `Caddyfile` que AT escreve, o provedor lê os dele no
# `configuration.yml`, e o WebApp o lê pela pasta INTEIRA que monta (`Mirror`) —
# onde o arquivo é o da PASTA, que o selo vai fechar. Então ele recebe a cópia
# clara como uma montagem própria, e o `at-cli` é TOLD onde ela está pela
# variável que o próprio Caddy declara (`caddy.GATE_PATH_ENV`), exatamente como
# já é told o nome do provedor (`GATE_ENV`).
#
# É um ARQUIVO e não uma pasta: o que o WebApp precisa é de um valor, e a pasta
# em volta não tem nada que lhe sirva.
GATE_DIR = "caddy"
GATE_MOUNT = "/run/at/gate"

# The address a service publishes on when it declares none: the loop, because
# that is what closes the LAN (measured — see the module's docstring).
LOOP = "127.0.0.1"

# The machine's rule about low ports, and the ONE thing §7 asks of it. A user
# process may only bind ports from this floor up, and §7a's edge publishes on
# `443` — which is under it on every machine that ships the rule.
# The name is the DOTTED one the command takes; the file that ANSWERS it spells
# the same thing with slashes, and the two are not interchangeable.
SYSCTL_PORTS = "net.ipv4.ip_unprivileged_port_start"
SYSCTL_FILE = Path("/proc/sys") / SYSCTL_PORTS.replace(".", "/")

# Inside the containers, where each service reads what AT writes for it.
CADDY_CONFIG = "/etc/caddy"
CADDY_DATA = "/data"

# A pasta do SERVIÇO que o Caddy monta em `CADDY_DATA`: o storage dele, com a CA
# local e os certificados emitidos contra ela. Ela é um nome e não a linha do
# `Mount` porque DOIS lugares têm de concordar sobre ela — o que o container
# monta, e onde o Caddy guarda o que emite por nome (`_prune_names`).
CADDY_STORAGE = "storage"
IDENTITY_CONFIG = "/config"
IDENTITY_DATA = "/data"

# The identity provider (§7b), and the name of the service is the ROLE and not
# the brand: Authelia is what serves it today (`SERVICES`), and a product that
# named the brand here would have to rename the service the day another one
# serves it. Its port is Authelia's own default, published on the loop because
# that is where the Caddy's `forward_auth` reaches it from — the Caddy shares
# the host's network and the provider does not need to (§7a's measured rule).
IDENTITY = "identity-provider"
IDENTITY_PORT = 9091

# The three files of its state folder, and all three are the service's: the
# configuration AT generates, the people it writes for it to prove, and the
# session secret drawn once and kept — Authelia signs its cookie with it, and a
# secret drawn per start would drop every session on the floor.
IDENTITY_YAML = "configuration.yml"
IDENTITY_USERS = "users.yml"
IDENTITY_SESSION = "session"

# The other two secrets the provider needs, and they are the same kind of value
# as the session's: they belong to the INSTALLATION and not to a start. The
# first is what it ENCRYPTS its own records with — one drawn per start would
# make everything it had already written unreadable —, and the second is what it
# signs an identity-validation token with.
IDENTITY_ENCRYPTION = "encryption"
IDENTITY_JWT = "jwt"

# Os TRÊS, numa lista, porque dois lugares os nomeiam: quem os SORTEIA — o `up`,
# antes de qualquer escritor, e um a um — e quem os SELA na conferência da
# Chave Principal (`_sealed_files`). O `_identity_conf` continua nomeando cada um no lugar
# do YAML onde ele entra, porque lá a POSIÇÃO é o que importa; aqui é o
# CONJUNTO, e ele é um só.
IDENTITY_SECRETS = (IDENTITY_SESSION, IDENTITY_ENCRYPTION, IDENTITY_JWT)

# Where the provider writes what it has to TELL somebody, and the everyday case
# is an identity validating a second factor. §7 has no smtp to give it, so it is
# a FILE — inside the service's own state folder, which is the folder the backup
# covers (§3) and what makes the notice recoverable instead of lost.
IDENTITY_NOTIFICATIONS = "notifications"

# §7a's edge, by the name the manifest gives it — and by the name the deploy's
# own probes ask the environment for the image they run in (`inside`): it is the
# one image of the manifest that carries an HTTP client, and it is already
# pulled by the time anything asks.
CADDY = "caddy"

# The WebApp as a container (§7c), and what runs inside it is THIS artifact: the
# module's docstring holds the decision, and the test is what keeps it true —
# the folder is mounted at its own path, and the command names the binary the
# person is running.
WEBAPP = "webapp"

# The variable the environment hands the WebApp so it can find its gate. A
# container has no host's loop to ask — `127.0.0.1` inside it is the WebApp's
# own — so the environment is what says which name to use, and the name is the
# provider's on the network the two share (`core/gate.py`, which reads it).
GATE_ENV = "AT_GATE"

# How much secret the identity provider's own drawing carries. The same price
# as the gate's (`caddy.GATE_BYTES`): it is a value a header and a cookie carry,
# never one a person types.
SECRET_BYTES = 32

# O nome do ambiente quando não há rede privada nenhuma — o mesmo truque que o
# bundle hospedado já usa (`at.services.authelia.valid_cookie_domain`), e pela
# mesma medida: todo navegador resolve `*.localhost` para o laço sozinho, sem
# DNS nenhum por trás, e o ponto no meio é o que o portão exige de um domínio
# de cookie (TASK-187 — antes disso o ambiente respondia por um nome PRÓPRIO,
# `at.local`, que só um `dnsmasq` do próprio AT resolvia). Com uma rede privada
# de pé, o nome é o dela (`vpn.name`), e este nunca é usado.
FALLBACK_HOST = "at.localhost"

# How long the orchestrator waits for an address to exist before it gives up on
# publishing there. Long enough for an interface to come up, short enough that a
# person is not left staring at a command that will never start anything.
GRACE = 20.0
STEP = 0.5

# The pin, as §3 spells it: a version and a digest. `sha256:` is the digest the
# registry publishes, and 64 hex characters after it.
PIN_PREFIX = "sha256:"
PIN_DIGITS = 64

# What the folder's pin says about one service, against the binary's (§3).
CURRENT = "current"
OUTDATED = "outdated"
AHEAD = "ahead"

# The three states a container is in, for `status`.
RUNNING = "running"
STOPPED = "stopped"
ABSENT = "absent"

# WHAT A PERSON IS ASKED, and the three words are all of it: is it on this
# machine, and is it on. The container's life — created, stopped, removed — is
# the RUNTIME's vocabulary, and a report that answers in it is answering a
# question nobody asked. The three are checked, not inferred: the image is in
# the machine's store, and the container is running.
INSTALLED = "installed"     # the image is here, and nothing is running
MISSING = "missing"         # the image is not here — it was never brought
