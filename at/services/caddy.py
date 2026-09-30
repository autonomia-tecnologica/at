"""The Caddy the binary carries — the TLS that exposure demands (§3, §6).

The rule this file answers is one sentence of §3: exposing demands
authentication **and** TLS, the TLS is Caddy's, and Caddy travels inside the
binary. So `at-cli webapp --include-caddy` is what turns a loopback WebApp into an
exposed one, and the four things that happen are these, in this order: the Caddy
is unpacked into the instance folder, the Caddyfile AT generates is written,
the Caddy is put in front of the WebApp, and the WebApp stays exactly where it
always was — `127.0.0.1`. What leaves the loop is the Caddy's port, never the
WebApp's.

**The certificate is AT's own, and nothing here delivers HSTS.** Caddy's
`tls internal` issues against a local CA instead of a public one, because AT
does not depend on a public domain and cannot promise a trusted certificate; the
browser's warning is the honest price of that. HSTS would turn that warning into
an error with no way out, which is why §3 forbids it — the person can click
through a warning, and cannot click through a pinned failure.

**The payload is the vendor's tarball, byte for byte.** Caddy's version is the
binary's (§3, Dependência externa), so there is no version to pin here and none
is written: the tarball's own name carries the release, and the code finds it by
the platform it serves. Unpacking happens into `App/` and only when the platform
stamp does not match, which is what makes a folder carried from one system to
another re-unpack what no longer serves there — and what makes a folder whose
extracted Caddy was deleted unpack it again instead of refusing to run (§3: what
was extracted lives in the folder, and the folder is the backup).

**The gate secret is item 13's, and its absence is not an error.** §7b says AT
draws a secret per installation, writes it into the Caddyfile it generates,
Caddy attaches it to every request carrying an identity, and AT refuses
whoever does not bring it. That is the container path's M2M: the Caddyfile
carries both lines when the secret is there — the `header_up` that attaches it
and the `forward_auth` that asks the identity provider who is calling. The
hosted path has no gate, so the file is absent and the two lines are too.

**The secret is READ here and DRAWN there.** `gate_secret` and `gate_file` are
below because the file is this Caddy's own (`App/caddy/gate`), and both
artifacts read them: `at-cli` refuses the identity that arrives without it, and
the WebApp's check is what turns the M2M into a door. The DRAWING is the
environment's installation act and belongs to `at-deploy` (§7b, item 27) —
the deploy tool is the one that writes the environment's state, and `at-cli` is
the one that reads it with the deploy artifact absent.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from platform import machine

from at.core import files, paths
from at.i18n import tr

# Where the payload travels: `at/vendor/caddy/`, and the same arithmetic
# `app.py` uses for its own payload — the frozen loader sets `__file__` to
# `<sys._MEIPASS>/at/services/caddy.py`, which is where `at-cli.spec` lands it.
PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "caddy"

# The instance folder the unpacking goes to: `App/caddy/`. It is `App/` and not
# the person's folders because it is what AT wrote to run, and it holds the
# four things the Caddy needs to live inside the folder: the binary, the stamp
# that says which platform it serves, the Caddyfile AT generates, and the
# Caddy's OWN storage — its local CA and the certificates issued against it —
# which is redirected here so that the folder's copy still brings everything
# back (§3, the backup promise).
FOLDER = "caddy"

# Inside that folder. The stamp is the platform word, and the Caddyfile keeps
# Caddy's own name so that the adapter is inferred from it.
BINARY = "caddy"
STAMP = "platform"
CADDYFILE = "Caddyfile"
STORAGE = "storage"

# Where the Caddy reaches its backend when nobody says otherwise: the loop, and
# it is the right answer exactly when the Caddy and the WebApp are the same
# machine — the hosted path. On the container path they are two containers, and
# a container's `127.0.0.1` is itself, so the address is passed in (`caddyfile`,
# §7c).
LOOPBACK = "127.0.0.1"

# The header Caddy attaches to the requests it carries an identity on, and the
# file the secret is drawn into. The file sits beside the Caddyfile that is the
# only thing reading it — the Caddy's own folder, and not `App/services/`, which
# is where the state of the SERVICES of the container path lives (§7); this
# Caddy is a process of the folder that has no container around it.
GATE_HEADER = "X-AT-Gate"
GATE_FILE = "gate"

# A variável com que o AMBIENTE diz onde está a cópia do portão, quando o
# arquivo da pasta não é o que se lê (item 50). O container monta o portão
# materializado fora da pasta — a pasta de estado é a FONTE e o que o WebApp
# monta é a cópia que serve a subida (`at_deploy/environment.py`) —, e a
# variável é o nome que o `at-deploy` diz, do mesmo jeito que já diz o nome do
# provedor (`AT_GATE`). Fora do container nada é entregue, e o que se lê é o
# arquivo da pasta.
GATE_PATH_ENV = "AT_GATE_FILE"

# How much secret AT draws. It is a value no person types and no person
# remembers — a header carries it — so it costs what `token_urlsafe` carries in
# bytes, and it says nothing about the folder it belongs to.
GATE_BYTES = 32

# Where the identity provider is asked, and what the ask is: §7b's
# forward-auth. `uri` is Authelia's own endpoint for it, and the four headers
# are the ones it answers with — `Remote-User` is the identity AT reads
# (`ui/webapp/app.py`), and the other three travel because Authelia's answer
# carries them, not because anything here reads them.
AUTH_URI = "/api/authz/forward-auth"
AUTH_HEADERS = ("Remote-User", "Remote-Groups", "Remote-Name", "Remote-Email")

# The portal's own path on the site, and it is the one thing that keeps the gate
# from looping over itself. **The gate authenticates by REDIRECT**: an
# unauthenticated request is answered with a 302 to the portal, and the browser
# comes back to the portal's URL. While that URL was the site's root, it went
# through `forward_auth` like any other path — so the edge asked the provider
# about the portal, the provider answered with another 302 appending `rd=`,
# and the loop rewrote the URL until the request died in `431 Request Header
# Fields Too Large`. Measured against the container, and nobody could get in.
#
# So the portal has a path of its own, and the edge routes it STRAIGHT to the
# provider — before the ask, never through it. The provider is told the same
# path (`server.address`, `_identity_conf`), and it is what its `authelia_url`
# carries, so the redirect, the page and its assets all agree on one address.
PORTAL = "/authelia"

# The port HTTPS is served on when nobody says otherwise, and the ONE port a URL
# does not spell: `https://at.local` and `https://at.local:443` are the same
# address, and the first is what a person types. Caddy reads a site address with
# no port the same way, so the omission is one on both sides of the file.
HTTPS = 443

# The vendor's own word for each platform, which is what its release assets are
# named with. `sys.platform` first, then the machine: a pair that is not here is
# a platform whose Caddy this artifact does not carry, and that is said instead
# of guessed (§9: Windows and macOS build on their own runners).
SYSTEMS = {"linux": "linux", "darwin": "darwin", "win32": "windows"}
MACHINES = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


class CaddyError(Exception):
    """The artifact carries no usable Caddy for this platform."""


def platform_name() -> str | None:
    """The vendor's word for this platform — `linux_amd64`, `darwin_arm64`.

    `None` when the pair is not one the release names, which is a real answer and
    not a failure: the build froze a Caddy for one system, and this is another.
    """
    system = SYSTEMS.get(sys.platform)
    machine = MACHINES.get(_machine())
    if system is None or machine is None:
        return None
    return f"{system}_{machine}"


def _machine() -> str:
    """This machine, in lower case — `x86_64` on Linux, `AMD64` on Windows."""
    return machine().lower()


def label() -> str:
    """What to call this platform when it has no Caddy: the pair, in the words
    the system uses, so the refusal names what was looked for."""
    return f"{sys.platform}/{machine()}"


def payload() -> Path | None:
    """The vendor's tarball for this platform, or `None` when there is none.

    Found by the platform and not by a version: the version is the binary's, so
    the name is the vendor's to spell (§3, Dependência externa).
    """
    name = platform_name()
    if name is None:
        return None
    found = sorted(PAYLOAD.glob(f"caddy_*_{name}.tar.gz"))
    if len(found) != 1:
        # None, and not the first of many: two Caddies for one platform is a
        # build that does not know which one it carries, and picking one would
        # be AT deciding what the artifact is made of.
        return None
    return found[0]


def directory() -> Path:
    """`App/caddy/` — where everything this file writes lives."""
    return paths.app_dir() / FOLDER


def binary() -> Path:
    """The unpacked Caddy, inside the folder."""
    return directory() / BINARY


def stamp_file() -> Path:
    """The platform the unpacked Caddy serves, written at unpacking time."""
    return directory() / STAMP


def caddyfile_path() -> Path:
    """The Caddyfile AT generates — rewritten on every start."""
    return directory() / CADDYFILE


def storage_dir() -> Path:
    """The Caddy's own storage, inside the folder: the local CA and the
    certificates issued against it. Left outside, a copied folder would come
    back with a certificate nobody's browser had ever been told about."""
    return directory() / STORAGE


# A autoridade que emite o certificado do AT, dentro de um storage do Caddy.
# **É um caminho do PRÓPRIO Caddy e não uma decisão de AT** — `tls internal`
# emite por nome contra uma CA local, e ele a guarda aqui —, então ele é escrito
# uma vez só, e os dois caminhos o leem do seu storage: o hospedado, que é o
# `App/caddy/storage`, e o container, cujo `/data` é montado da pasta de estado
# do mesmo serviço (§7a).
#
# **Ele é o arquivo que quem precisa CONFIAR no certificado importa**, e é por
# isso que ele é nomeado: um cliente que valida TLS contra a CA pública recusa o
# certificado do AT, que é o preço declarado de não depender de um domínio
# público (§3). Medido: o app do ntfy não usa o cofre de CAs do aparelho, então
# o que o celular importa é ESTE arquivo, na gestão de certificados do app
# (`at_deploy/notifier.py`).
AUTHORITY = Path("pki") / "authorities" / "local" / "root.crt"


def authority_file(root: Path | None = None) -> Path:
    """A CA local do Caddy, dentro de um storage — o de dentro da pasta por
    padrão, e o do container quando quem chama passa a raiz dele.

    A raiz é um parâmetro porque são DOIS storages com o mesmo conteúdo: o
    caminho hospedado usa o do `App/caddy`, e o container usa a pasta de estado
    do serviço (§7a). O que os dois têm em comum é o que o Caddy escreve dentro,
    e é isso que este arquivo nomeia.
    """
    return (root or storage_dir()) / AUTHORITY


# Onde o Caddy guarda o certificado de CADA nome, dentro do storage: um
# diretório por nome servido, com o `.crt` e a `.key` dele. **É um caminho do
# PRÓPRIO Caddy e não uma decisão de AT** — `tls internal` emite por nome, e ele
# os guarda aqui —, e é por isso que ele é nomeado uma vez: quem varre o storage
# atrás dos nomes que a borda já não serve precisa saber onde eles moram
# (`environment._prune_names`), e um nome que ninguém serve deixa um certificado
# e uma chave privada para trás.
CERTIFICATES = Path("certificates") / "local"


def certificates_dir(root: Path | None = None) -> Path:
    """O diretório dos certificados POR NOME, dentro de um storage.

    A raiz é um parâmetro pela mesma razão de `authority_file`: são DOIS storages
    com o mesmo conteúdo, e o que eles têm em comum é o que o Caddy escreve
    dentro. Cada entrada é um nome servido, e é o NOME que diz se ele ainda
    serve (`environment.names`).
    """
    return (root or storage_dir()) / CERTIFICATES


def unpacked() -> bool:
    """Whether the folder already carries the Caddy this platform runs."""
    if not binary().is_file() or not stamp_file().is_file():
        return False
    return stamp_file().read_text(encoding="utf-8").strip() == platform_name()


def ensure() -> Path | None:
    """Unpack the Caddy into the instance folder; `None` without a payload.

    It runs only when the stamp and the machine disagree, so the common path is
    one `read_text` and no writing at all.
    """
    if unpacked():
        return binary()

    source = payload()
    if source is None:
        return None

    where = directory()
    where.mkdir(parents=True, exist_ok=True)
    destination = binary()

    # Written beside the target and moved onto it, so a Caddy that is half
    # unpacked is never a Caddy the folder would try to run.
    with tarfile.open(source, "r:gz") as archive:
        try:
            packed = archive.extractfile(BINARY)
        except KeyError as error:
            raise CaddyError(f"{source.name} carries no {BINARY}") from error
        if packed is None:  # pragma: no cover — a member that is not a file
            raise CaddyError(f"{source.name} carries no {BINARY}")
        handle, temporary = tempfile.mkstemp(dir=where, prefix=f".{BINARY}.")
        try:
            with os.fdopen(handle, "wb") as out, packed:
                shutil.copyfileobj(packed, out)
            os.chmod(temporary, 0o755)
            os.replace(temporary, destination)
        except BaseException:
            os.unlink(temporary)
            raise

    files.atomic_write_text(stamp_file(), f"{platform_name()}\n")
    return destination


def gate_file() -> Path:
    """`App/caddy/gate` — the secret's file, drawn by `at-deploy` (§7b).

    É o arquivo da PASTA, e é ele que o `draw_gate` escreve — o desenho tem um
    lugar só. Quem lê pode estar lendo outro arquivo (`gate_handed` e
    `gate_secret`), e é por isso que este nome e a leitura são duas coisas.
    """
    return directory() / GATE_FILE


def gate_handed() -> Path | None:
    """A cópia do portão que o AMBIENTE entregou — ou `None`, fora do container.

    Item 50: o que o container monta é a cópia que o `up` materializou fora da
    pasta, e a pasta guarda a FONTE. O WebApp é o leitor que a recebe, e a
    variável é o nome que o ambiente diz (`GATE_PATH_ENV`). Sem ela — o AT
    rodando da pasta, no caminho hospedado — não há cópia entregue, e o que se
    lê é o arquivo da pasta.
    """
    handed = os.environ.get(GATE_PATH_ENV, "").strip()
    return Path(handed) if handed else None


def gate_secret() -> str | None:
    """The M2M secret between the Caddy and the WebApp, when there is a gate.

    §7b: the secret is drawn by AT at installation, written into the Caddyfile
    AT generates, attached by the Caddy to every request carrying an identity,
    and refused by AT to whoever does not bring it (`ui/webapp/app.py`). The
    line in the Caddyfile is this file's, and it is written only when the secret
    is there — a hosted folder with no gate has no file and gets no line.

    **O que ele lê é a cópia que o ambiente entregou, quando há uma**
    (`gate_handed`), e o arquivo da pasta quando não há: é esta função que faz
    do portão materializado o que o WebApp de dentro do container prova.
    """
    where = gate_handed() or gate_file()
    try:
        secret = where.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return secret or None


# Every way a person says "all of them". None of them can be a site address:
# `tls internal` issues a certificate FOR A NAME, and a wildcard is the absence
# of one — Caddy accepts `https://:443` and then cannot complete a handshake,
# which is a failure that only shows up in the browser (`run` refuses it before
# anything starts, and says what to name instead).
WILDCARDS = ("0.0.0.0", "::", "*")


def wildcard(host: str) -> bool:
    """Whether that address is "every address", which a certificate cannot name."""
    return host in WILDCARDS


def address(host: str, port: int) -> str:
    """The site address Caddy serves: the name the browser will use.

    It is a name and an IP both, because §3's certificate is AT's own: Caddy's
    local CA issues for `localhost`, for a hostname and for an address alike, so
    exposing to the local network means naming the address the person reaches —
    `--host 192.168.1.10` — and not opening every one of them.

    **The default port is not written**: a URL and a Caddyfile both read
    `https://at.local` as the address on `443`, and a `:443` in the middle of it
    is noise that says nothing — the port is there when it is another one, which
    is exactly when a person has to read it.
    """
    return f"https://{host}" if port == HTTPS else f"https://{host}:{port}"


def caddyfile(host: str, port: int, backend: int, gate: str | None = None,
              storage: str | Path | None = None, auth: str | None = None,
              bind: str | None = None, upstream: str | None = None,
              notify: tuple[str, str, str] | None = None,
              files: tuple[tuple[str, str], ...] = ()) -> str:
    """The Caddyfile AT generates: TLS in front, the WebApp behind.

    `backend` is the WebApp's own port, and `upstream` is the HOST the Caddy
    reaches it at — the loop by default, and the WebApp's name on the network
    when the Caddy is a container too (§7c): a container's `127.0.0.1` is itself,
    and the app's door is the network. The gate lines exist only when there is a
    secret to carry, and `admin off` is not decoration — an admin endpoint would
    be a local port that rewrites the running configuration with no credential
    at all.

    **`notify` is §7f's notifier, fronted by the SAME `forward_auth` and a
    different upstream** — `(host, upstream, credential)`, and each becomes a
    site of its own, with its own certificate (`tls internal` issues per name).
    It took a second measurement to get here: the gate authenticates by
    redirect and session cookie, and a headless phone app used to take the 302
    and never connect (`subscribers=0` behind Authelia, `101` without it) — but
    Authelia's forward-auth reads an `Authorization: Basic` header on the
    request itself and skips the redirect when one is there, which is exactly
    the shape a client that always sends its credential has. So this site asks
    too, with no portal to route around (nothing here is a browser), and past
    the ask it reverse-proxies straight to `upstream` — never to the WebApp —
    swapping whatever `Authorization` the client sent for `credential`, the
    M2M value AT drew for this ONE account. The notifier never sees the
    person's own credential.

    **A site of its own and not a host matcher inside the one above**, and the
    reason is the certificate and the `handle`s: two names in one block share
    the ordering that keeps the portal out of the ask, and a name added there
    would be one more thing between the person and the door. Two blocks cannot
    interfere, and the site's block stays exactly what it was.

    **`files` is what the edge serves out of a FILE — and it is a file and not a
    folder.** Each pair is a `(name, path)` and each becomes a site of its own,
    with its own certificate and nothing of the gate: §7a's `cert.at.local` is
    the one that exists, and it is outside the ask for the same reason `notify`
    is not — whoever needs it is a device that does not trust AT yet, and a
    `forward_auth` in front of a CA is a question asked by the certificate that
    CA would have to sign.

    **Every request is rewritten onto the ONE path, and the folder is never
    served.** The path is inside the Caddy's own storage (`AUTHORITY`), which
    holds the CA's certificate **beside its private key** — `root.key`,
    `intermediate.key` —, and a `root` at that folder would hand the key to
    anyone who guessed the name beside the file. Naming the file makes the rest
    of the storage unreachable by construction: there is no path a request can
    carry that is not rewritten onto it.

    **The two gate lines travel together, and both are §7b.** `forward_auth` is
    the Caddy asking the identity provider who is calling, before it hands
    anything to the WebApp; `header_up` is the Caddy telling the WebApp, in the
    secret only it and AT know, that the request came through here. `auth` is
    the provider's address — `host:port`, which on the container path is the
    provider's name on the network and not a published port — and without it
    there is nobody to ask, so the block is not written: a hosted folder with a
    secret but no provider would otherwise ask a question with no answer and
    answer every request with a failure.

    **With the ask comes the portal's way around it, and they are one block.**
    The provider answers every unauthenticated request with a redirect to its
    portal, so the portal itself cannot be asked about — asking is what sends
    the browser there. The two `handle`s below are the whole of it: the portal's
    path goes STRAIGHT to the provider, and everything else goes through the ask
    and then to the WebApp. Caddy sorts a matched `handle` before the bare one,
    which is the fallback, so the portal's path wins where it matches and the
    rest of the site is untouched. The `handle`s exist only where there is a
    gate to go around: a folder with no provider writes neither.

    `storage` is a path and not a decision (§7a), and it is the line that
    differs between the two paths because the folder is the one that does: the
    Caddy unpacked into it keeps its CA and its certificates there (§3, the
    backup promise), and the Caddy running as a container keeps them in the
    container's own data directory, which is a folder of the instance mounted
    into it. **`bind` is an ADDRESS and not a name**, and it exists for the
    container path: the name the certificate carries is the private network's
    (§7e) and the container holds no address of that name, so the site listens
    on everything the container has and what makes it reachable is the port the
    container PUBLISHES. Every other site binds the same way, for the same
    reason.
    """
    behind = upstream or LOOPBACK
    # The portal's way around the ask exists exactly where the ask does, and it
    # is what decides the indentation of everything below it: inside the
    # `handle`s a directive sits one level deeper than at the site's root.
    gated = bool(gate and auth)
    indent = "\t\t" if gated else "\t"

    lines = [
        f"# {tr('caddy.file.header')}",
        "{",
        "\tadmin off",
        # And no autosave either: the running configuration is copied to Caddy's
        # own config directory, which is outside the folder — and the gate secret
        # is IN this file, so a copy of it living under `~/.config` would be the
        # secret leaving the folder and the backup (§3, §7b).
        "\tpersist_config off",
        # AT does not enter the machine's trust store, and that is the same
        # decision as the missing HSTS: the root would have to be installed with
        # elevation, and §3 spends elevation only on an explicit request. The
        # browser keeps warning, which is the declared price of a certificate
        # that is AT's own.
        "\tskip_install_trust",
        # Caddy's automatic HTTPS opens the redirect listener on :80 and refuses
        # to start when it cannot — a privileged port this product never serves.
        # The person reaches the URL AT printed, and nothing redirects to it.
        "\tauto_https disable_redirects",
        f'\tstorage file_system "{storage or storage_dir()}"',
        "}",
        "",
        f"{address(host, port)} {{",
        # The line that says WHERE the site listens, when the name it carries is
        # not an address this process holds. It goes first because it is about
        # the server and not about a request.
        *([f"\tbind {bind}"] if bind else []),
        "\ttls internal",
    ]
    if gated:
        # The portal comes FIRST and OUTSIDE the ask: it is where the gate sends
        # the browser, so asking the provider about it is what closes the loop
        # (`PORTAL`). The matcher names the path with and without the trailing
        # slash — the redirect lands on `/authelia/`, but a person typing the
        # path without it must not be asked about it either.
        lines += [
            f"\t@portal path {PORTAL} {PORTAL}/*",
            "\thandle @portal {",
            f"\t\treverse_proxy {auth}",
            "\t}",
            "\thandle {",
            # AT is ONE MORE APP here and not an exception (§7b): the same block
            # that would stand in front of Sonarr stands in front of AT, and what
            # makes it AT is only the secret on the line below.
            f"\t\tforward_auth {auth} {{",
            f"\t\t\turi {AUTH_URI}",
            f"\t\t\tcopy_headers {' '.join(AUTH_HEADERS)}",
            "\t\t}",
        ]

    proxy = [f"{indent}reverse_proxy {behind}:{backend}"]
    if gate:
        proxy[0] += " {"
        proxy += [f"{indent}\theader_up {GATE_HEADER} {gate}", f"{indent}}}"]
    lines += proxy

    if gated:
        lines.append("\t}")
    lines.append("}")

    # The notifier's own site: the SAME ask, a DIFFERENT upstream, and the M2M
    # credential that replaces whatever `Authorization` the client sent. No
    # portal here — nothing on this road is a browser to route around the ask
    # for — and no gate header either: the notifier does not read it, only
    # Basic.
    if notify is not None and auth:
        notify_host, notify_upstream, notify_credential = notify
        lines += [
            "",
            f"{address(notify_host, port)} {{",
            *([f"\tbind {bind}"] if bind else []),
            "\ttls internal",
            f"\tforward_auth {auth} {{",
            f"\t\turi {AUTH_URI}",
            "\t}",
            f"\treverse_proxy {notify_upstream} {{",
            f'\t\theader_up Authorization "Basic {notify_credential}"',
            "\t}",
            "}",
        ]

    # E os que ela serve de um ARQUIVO: a mesma forma, e o `rewrite` que faz de
    # qualquer pedido o ÚNICO arquivo — a pasta em volta nunca é servida, e é
    # ali que a chave privada da CA mora ao lado do certificado.
    for name, path in files:
        lines += [
            "",
            f"{address(name, port)} {{",
            *([f"\tbind {bind}"] if bind else []),
            "\ttls internal",
            "\troot * /",
            f"\trewrite * {path}",
            "\tfile_server",
            "}",
        ]
    return "\n".join(lines) + "\n"


def write_caddyfile(host: str, port: int, backend: int,
                    auth: str | None = None) -> Path:
    """Write the Caddyfile the Caddy is started with, and answer where it is."""
    where = caddyfile_path()
    where.parent.mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(where,
                            caddyfile(host, port, backend, gate_secret(), auth=auth))
    return where


def start(config: Path, log: bool = True) -> subprocess.Popen:
    """Run the Caddy in the foreground of this process's terminal.

    Its output is inherited on purpose: Caddy says which addresses it bound and
    what it refuses, and an AT that swallowed it would leave the person with a
    port that answers nothing and no reason why. `log=False` is the suite's: the
    Caddy speaks JSON, line per line, for whoever runs the server and not for
    whoever reads a test's output.
    """
    sink = None if log else subprocess.DEVNULL
    return subprocess.Popen([str(binary()), "run", "--config", str(config)],
                            stdout=sink, stderr=sink)


def started(process: subprocess.Popen, grace: float = 0.3) -> bool:
    """Whether the Caddy survived the blink in which it fails.

    The way it fails is binding a port somebody else already answers on, and it
    fails in milliseconds. AT printing a URL for a port nothing is on would be
    the worst answer available: a promise with no way to tell it was not kept.
    Caddy's own words are on the terminal beside this — its output is inherited —
    and this only decides whether AT gets to announce anything.
    """
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        return True
    return False


def stop(process: subprocess.Popen | None) -> None:
    """Stop the Caddy this process started, and only that one."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
