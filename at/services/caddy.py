"""The Caddy the binary carries — the TLS that exposure demands (§3, §6).

The rule this file answers is one sentence of §3: exposing demands
authentication **and** TLS, the TLS is Caddy's, and Caddy travels inside the
binary. So `at-cli webapp` turns a loopback WebApp into an exposed one by
default (`--no-caddy` is the one way out), and the four things that happen
are these, in this order: the Caddy is unpacked into the instance folder, the
Caddyfile AT generates is written, the Caddy is put in front of the WebApp,
and the WebApp stays exactly where it always was — `127.0.0.1`. What leaves
the loop is the Caddy's port, never the WebApp's.

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
whoever does not bring it. The Caddyfile carries both lines when the secret is
there — the `header_up` that attaches it and the `forward_auth` that asks the
identity provider who is calling. **A folder with neither an installed
environment nor a running bundle has no gate**, so the file is absent and the
two lines are too — the one case this sentence still describes.

**The secret is READ here, and DRAWN in TWO different places now (TASK-177,
2026-10-02).** `gate_secret` and `gate_file` are below because the file is
this Caddy's own (`App/services/caddy/gate`), and both artifacts read them: `at-cli`
refuses the identity that arrives without it, and the WebApp's check is what
turns the M2M into a door. The container path's draw is `at-deploy`'s
installation act (§7b, item 27, sealed by the Chave Principal because that
state folder is copied into a container with no encryption of its own) — the
deploy tool writes the environment's state, and `at-cli` reads it with the
deploy artifact absent. **The bundle's draw is `draw_gate`, right below**: the
hosted path's own, in the clear, because nothing here ever crosses a
container boundary — the same `App/` the backup already covers.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from platform import machine

from at.core import files, paths
from at.encryption import vault
from at.i18n import tr

# Where the payload travels: `at/vendor/caddy/`, and the same arithmetic
# `app.py` uses for its own payload — the frozen loader sets `__file__` to
# `<sys._MEIPASS>/at/services/caddy.py`, which is where `at-cli.spec` lands it.
PAYLOAD = Path(__file__).resolve().parents[1] / "vendor" / "caddy"

# The instance folder the unpacking goes to: `App/services/caddy/` — the house
# of the services (§7), shared with the container path's Caddy. It is `App/` and not
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
    """`App/services/caddy/` — where everything this file writes lives."""
    return paths.service_dir(FOLDER)


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
# uma vez só, e os dois caminhos o leem do MESMO storage: `App/services/caddy/
# storage` é a pasta do serviço, o hospedado a lê direto e o container a monta
# em `/data` (§7a).
#
# **Ele é a metade PÚBLICA da CA local**, e é por isso que ele é nomeado: um
# cliente que valida TLS contra a CA pública recusa o certificado do AT, que é
# o preço declarado de não depender de um domínio público (§3). **Nada no
# produto o serve nem o importa hoje** (TASK-187): o certificado válido de quem
# alcança o AT de outro aparelho vem do `tailscale serve`, de fora do AT, e o
# `tls internal` da borda fica só para quem a alcança do próprio laço.
AUTHORITY = Path("pki") / "authorities" / "local" / "root.crt"


def authority_file(root: Path | None = None) -> Path:
    """A CA local do Caddy, dentro de um storage — o da pasta por padrão, e o do
    container quando quem chama passa a raiz dele.

    A raiz é um parâmetro porque o container alcança a MESMA pasta do serviço por
    outro caminho — de dentro dele o storage é `/data`, e no host é
    `state(CADDY)/storage` (§7a). O que os dois têm em comum é o que o Caddy
    escreve dentro, e é isso que este arquivo nomeia.
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

    A raiz é um parâmetro pela mesma razão de `authority_file`: o container lê a
    mesma pasta de serviço por outro caminho (`/data` de dentro dele), e o que os
    dois têm em comum é o que o Caddy escreve dentro. Cada entrada é um nome
    servido, e é o NOME que diz se ele ainda serve (`environment.names`).
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
    """`App/services/caddy/gate` — the secret's file, drawn by whoever installs the gate.

    É o arquivo da PASTA, e dois desenhos escrevem nele — nunca os dois na
    mesma pasta. O container path o sela (`at_deploy.environment.draw_gate`,
    item 50, porque aquela pasta de estado é copiada sem criptografia); o
    bundle hospedado o escreve em claro (`draw_gate`, abaixo, logo abaixo
    desta função) — a mesma razão do `App/` nunca precisar do selo: nada
    aqui atravessa fronteira de container. Quem lê pode estar lendo outro
    arquivo (`gate_handed` e `gate_secret`), e é por isso que este nome e a
    leitura são duas coisas.
    """
    return directory() / GATE_FILE


def _drawn_in_the_clear(where: Path) -> str:
    """O valor que um arquivo já guarda, ou um sorteado agora e mantido dali
    em diante — em CLARO, e de propósito (`draw_gate`'s own docstring diz
    por quê). `draw_gate` é a face disto.

    **O nome do arquivo é o mesmo que o caminho container usa**
    (`at_deploy.environment.gate_file`, na mesma `caddy.directory()`), porque
    os dois são a mesma pasta `App/services/caddy/` do mesmo Caddy — só que o caminho
    container SELA o que escreve ali (item 50), e o que está selado não é o
    valor em claro que este caminho lê. Um envelope encontrado aqui não é um
    valor já sorteado — é o OUTRO caminho, e o sorteio é o mesmo de um arquivo
    ausente.
    """
    try:
        held = where.read_text(encoding="utf-8").strip()
        if held and not vault.envelopes(held):
            return held
    except FileNotFoundError:
        pass
    value = secrets.token_urlsafe(GATE_BYTES)
    where.parent.mkdir(parents=True, exist_ok=True)
    files.atomic_write_text(where, f"{value}\n")
    return value


def draw_gate() -> str:
    """O segredo do portão, sorteado uma vez e mantido em CLARO (§6, bundle).

    **Este é o desenho do CAMINHO HOSPEDADO**, e não o do item 50: a pasta
    deste Caddy (`App/services/caddy/`) nunca é copiada para dentro de um container —
    ela é a cópia de trabalho de uma única máquina, já coberta pelo backup —,
    então o valor que o `header_up` carrega não precisa do envelope da Chave
    Principal que o caminho container exige (`at_deploy.environment.
    draw_gate`). Um valor já sorteado não é sorteado de novo: rotacioná-lo
    derrubaria toda sessão que o WebApp já aceitou pelo mesmo Caddy.
    """
    return _drawn_in_the_clear(gate_file())


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
              files: tuple[tuple[str, str], ...] = ()) -> str:
    """The Caddyfile AT generates: TLS in front, the WebApp behind.

    `backend` is the WebApp's own port, and `upstream` is the HOST the Caddy
    reaches it at — the loop by default, and the WebApp's name on the network
    when the Caddy is a container too (§7c): a container's `127.0.0.1` is itself,
    and the app's door is the network. The gate lines exist only when there is a
    secret to carry, and `admin off` is not decoration — an admin endpoint would
    be a local port that rewrites the running configuration with no credential
    at all.

    **`files` is what the edge serves out of a FILE — and it is a file and not a
    folder.** Each pair is a `(name, path)` and each becomes a site of its own,
    with its own certificate and nothing of the gate, outside the ask: whoever
    needs such a file is a device that
    does not trust AT yet, and a `forward_auth` in front of it is a question
    asked by the certificate that would have to answer. **Nothing in the
    product passes it today** — the CA file it served (`cert.at.local`) left
    with the environment's DNS (TASK-187) — and it stays as a capability of
    the generator, with its own tests, for the next site that has to hand out
    a file by name.

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

    **With the ask come the two ways around it, and they are one block.** The
    provider answers every unauthenticated request with a redirect to its
    portal, so the portal itself cannot be asked about — asking is what sends
    the browser there; and the PWA's manifest and icons cannot be asked about
    either, because the browser fetches the manifest WITHOUT credentials and
    never reaches the provider through the ask. The three `handle`s below are
    the whole of it: the PWA's paths go STRAIGHT to the WebApp, the portal's
    path goes STRAIGHT to the provider, and everything else goes through the ask
    and then to the WebApp. Caddy sorts a matched `handle` before the bare one,
    which is the fallback, so the matched paths win where they match and the
    rest of the site is untouched. The `handle`s exist only where there is a
    gate to go around: a folder with no provider writes none of them.

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
        # O UTILITÁRIO DO PWA É PÚBLICO, E TEM QUE SER. O Chrome busca o
        # MANIFESTO sem credenciais (`credentials: omit`, o que a spec manda),
        # e atrás do ask ele nunca chega — sem manifesto lido não existe
        # "Instalar app", por mais ícones que haja. São dois caminhos, e só
        # dois: o manifesto e os ícones — metadado e imagem, nenhum dado da
        # pasta, e nada que a lista de `.enc` ou o claro de um arquivo toque.
        # Vão direto ao WebApp, sem o `forward_auth` e sem o cabeçalho do
        # portão: quem os serve é o `_static`, que não pergunta nada.
        lines += [
            "\t@pwa path /manifest.webmanifest /icons/*",
            "\thandle @pwa {",
            f"\t\treverse_proxy {behind}:{backend}",
            "\t}",
            # The portal comes FIRST and OUTSIDE the ask: it is where the gate sends
            # the browser, so asking the provider about it is what closes the loop
            # (`PORTAL`). The matcher names the path with and without the trailing
            # slash — the redirect lands on `/authelia/`, but a person typing the
            # path without it must not be asked about it either.
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
    files.atomic_write_text(
        where,
        caddyfile(host, port, backend, gate_secret(), auth=auth),
    )
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
