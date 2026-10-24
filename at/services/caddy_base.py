"""Caddy: o que é constante e o que mora em pastas — nomes, caminhos e o storage."""

from __future__ import annotations

import sys
from pathlib import Path

from at.core import paths

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
# The member's name inside the vendor's archive, which is also the unpacked file:
# Windows spells it with the `.exe` its loader needs.
BINARY = "caddy.exe" if sys.platform == "win32" else "caddy"
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


class CaddyError(Exception):
    """The artifact carries no usable Caddy for this platform."""



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
