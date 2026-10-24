"""The edge (§7a, §7e): the name the site is served at, the Caddyfile, the port
it publishes and the certificates it no longer serves.
"""

from __future__ import annotations

import shutil

from at.services import caddy as caddy_service
from at_deploy import vpn
from at_deploy.environment_base import (
    ALL,
    CADDY,
    CADDY_DATA,
    CADDY_STORAGE,
    FALLBACK_HOST,
    IDENTITY,
    IDENTITY_PORT,
    LOOP,
    PORT,
    WEBAPP,
    WEBAPP_PORT,
)
from at_deploy.environment_models import Port
from at_deploy.environment_paths import container, state


def site_host() -> str:
    """The NAME the environment's edge serves the site at (TASK-187).

    §7e is what this reads: with a private network up, the name is the one it
    gives the machine (`vpn.name`) — a name Tailscale's own MagicDNS already
    resolves for every device on it, so the environment needs no DNS of its
    own to be reached by it. With none, the fallback is `FALLBACK_HOST`, which
    every browser resolves to the loop on its own, no resolver asked — the
    same fallback the hosted bundle already carries (`at.services.authelia.
    valid_cookie_domain`). Either way it is a NAME and not an address, for the
    two measurements this piece always had to answer: the gate refuses a
    cookie domain without a dot that is not an IP, so the word `localhost` is
    out; and TLS needs a NAME for the SNI — a client connecting to an ADDRESS
    sends none, and the Caddy answers the handshake with `internal error`
    because it has no certificate it can serve.

    **It is a function and not a constant for the same reason as before, and
    one more now**: the private network is measured when the environment
    comes up — a value read at import would stop being true the moment the
    person joined one —, and every file that has to agree on the name — the
    Caddyfile, the identity provider's access rule and its cookie, and the URL
    the switch says — is written at that same moment.
    """
    return vpn.name() or FALLBACK_HOST


def portal_url() -> str:
    """Where the portal is reached — the site, plus the portal's own path (§7b).

    **ONE place decides it, and three read it**: the provider's `authelia_url`,
    the edge's routing of the portal and the switch's fourth probe. They have to
    name the same address or the redirect lands somewhere the edge does not
    serve, and the drift between "where the gate sends the person" and "what the
    proof asks" is exactly the kind of difference a proof passes through
    (`caddy.PORTAL`). It is a function for the same reason `site_host` is: the
    name is measured when the environment comes up.
    """
    return f"{caddy_service.address(site_host(), PORT)}{caddy_service.PORTAL}/"


def names() -> tuple[str, ...]:
    """Every name the environment answers for — one, since TASK-187.

    It stayed its own function, and not a bare call to `site_host`, because
    `_prune_names` reads it to know which of the Caddy's own certificates are
    stale: the name changes between a subida on a private network and one
    without it, and a certificate issued for yesterday's name is a private key
    the backup would carry for nothing.
    """
    return (site_host(),)


def _caddy_conf() -> str:
    """The Caddyfile the container's Caddy runs.

    The same generator the hosted path reads, because it is the same Caddy: the
    site, the TLS of AT's own certificate, the admin endpoint off and the
    storage — the one line that is a path and not a decision (§7a). The two
    lines of the gate come along when there is a secret, and §7b is what draws
    it: the Caddy asks the identity provider who is calling, and tells the
    WebApp that the request came through here. **And the portal's way around
    the ask comes with them**, because `auth` is here: the provider's own path
    is routed straight to it, so the redirect that sends the browser to the
    portal does not become another question (`caddy.PORTAL`).

    **Four things are the container path's and not the hosted path's**, and each
    is an address that means something else on this side of the network. The
    backend is the WebApp's NAME on the network and not the host's loop, which
    the edge cannot see. The provider is reached the same way, for the same
    reason. The site BINDS everything the container has, because the name the
    certificate carries is not an address this container holds — what makes the
    site reachable is the port the container publishes (§7e). And the site is
    the site: `site_host` is §7a's, and it is the same on both paths.
    """
    return caddy_service.caddyfile(
        site_host(), PORT, WEBAPP_PORT,
        gate=caddy_service.gate_secret(),
        storage=CADDY_DATA,
        auth=f"{container(IDENTITY)}:{IDENTITY_PORT}",
        bind=ALL,
        upstream=container(WEBAPP),
    )


def _caddy_ports() -> tuple[Port, ...]:
    """A porta do site (§7e, TASK-187).

    É a porta que um navegador alcança. Ela publica no endereço da REDE PRIVADA
    quando há uma — a mesma expressão que `site_host` usa — e no laço quando não
    há, que é o estado suportado e não um degradado. **Não é `0.0.0.0`**: uma
    porta publicada em todo endereço é uma porta na LAN, e o que §7a mede e este
    produto promete é que nada do AT fica exposto ali fora, exceto a borda, na
    rede que a pessoa escolheu.

    É uma função e não uma constante pela mesma razão que `site_host`: o
    endereço é medido quando o ambiente sobe, e um valor lido na importação
    deixaria de ser verdade no instante em que a pessoa entrasse numa rede.
    """
    where = vpn.address() or LOOP
    return (Port(PORT, address=where),)


def _prune_names() -> tuple[str, ...]:
    """Tira do storage do Caddy o certificado dos nomes que a borda já não serve.

    **O conjunto de nomes é do AT e não do Caddy** (`names`): quando o ambiente
    deixa de servir um nome, o Caddy não tem como sabê-lo — ele guarda o
    certificado daquele nome e a chave privada ao lado dele para sempre, e o que
    sobra é uma chave em claro que o portão do backup barraria sem motivo. É por
    isso que a poda é do `up`: a limpeza não é um ato à parte que a pessoa teria
    de lembrar de pedir, ela é o preço de o nome ter mudado, e ele já foi pago na
    subida seguinte.

    **É o ÚNICO ato do AT dentro do que o container encheu, e ele é estreito de
    propósito**: só os diretórios de `certificates/local` cujo nome não está no
    `names()` saem — um por nome, e o nome do diretório é o nome servido —, e o
    diretório da CA (`pki/`) nunca é tocado. O que o container escreveu de um
    nome que AINDA é servido continua byte a byte como ele deixou
    (`TheStorageOutOfReach`).
    """
    where = caddy_service.certificates_dir(state(CADDY) / CADDY_STORAGE)
    if not where.is_dir():
        return ()
    served = set(names())
    stale = sorted(
        entry for entry in where.iterdir()
        if entry.is_dir() and entry.name not in served
    )
    for entry in stale:
        shutil.rmtree(entry)
    return tuple(entry.name for entry in stale)
