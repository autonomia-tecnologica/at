"""Caddy: o Caddyfile que o AT gera — endereço, texto e escrita."""

from __future__ import annotations

from pathlib import Path

from at.core import files
from at.i18n import tr
from at.services.caddy_base import (
    AUTH_HEADERS,
    AUTH_URI,
    GATE_HEADER,
    HTTPS,
    LOOPBACK,
    PORTAL,
    caddyfile_path,
    storage_dir,
)
from at.services.caddy_gate import gate_secret

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
    never reaches the provider through the ask; nor can `/sw.js`, because a
    stale service worker updates itself with no session and would be sent to
    the portal. The three `handle`s below are
    the whole of it: the PWA's paths (`/sw.js`, the manifest, the icons) go STRAIGHT to the WebApp, the portal's
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
        # "Instalar app", por mais ícones que haja. São três caminhos, e só
        # eles: o service worker (`/sw.js`), o manifesto e os ícones — o
        # worker velho do navegador busca a versão nova SEM sessão, e atrás do
        # ask levaria 302 para o portal e nunca se atualizaria. Código estático
        # e imagem, nenhum dado da
        # pasta, e nada que a lista de `.enc` ou o claro de um arquivo toque.
        # Vão direto ao WebApp, sem o `forward_auth` e sem o cabeçalho do
        # portão: quem os serve é o `_static`, que não pergunta nada.
        lines += [
            "\t@pwa path /sw.js /manifest.webmanifest /icons/*",
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
