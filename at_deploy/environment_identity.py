"""The identity provider's files (§7b): `configuration.yml` and `users.yml`.
"""

from __future__ import annotations

from at.i18n import tr
from at.services import authelia as authelia_service
from at.services import caddy as caddy_service
from at.services.authelia import _quoted
from at_deploy.environment_base import (
    ALL,
    IDENTITY,
    IDENTITY_CONFIG,
    IDENTITY_DATA,
    IDENTITY_ENCRYPTION,
    IDENTITY_JWT,
    IDENTITY_NOTIFICATIONS,
    IDENTITY_PORT,
    IDENTITY_SESSION,
    IDENTITY_USERS,
)
from at_deploy.environment_edge import portal_url, site_host
from at_deploy.environment_secrets import _kept


def _identity_conf() -> str:
    """Authelia's configuration — the gate, declared by AT (§7b).

    **Everything here was read off a REFUSAL, and that is the point.** The
    provider measures its own configuration and refuses to start without six
    things, none of which is a preference: the storage and the key it encrypts
    its records with; a notifier — an smtp or a file — because it has to be able
    to tell somebody something; the secret it signs an identity-validation token
    with; the access control, which denies by default and names AT's own site as
    `one_factor`, because AT comes in as one more app behind the gate and the
    app not named is the app that does not enter; the session secret; and the
    cookie's DOMAIN, which is the site and which the provider refuses without a
    dot unless it is an IP — and that last one is why the site on the loop is an
    ADDRESS and not the word `localhost` (`site_host`).

    **The portal gets a path, and it is the fourth thing the provider is told.**
    `server.address` carries it and `authelia_url` names it (`portal_url`), so
    the provider serves its page under the same address the edge routes around
    the ask — without it the redirect comes back to the edge, the edge asks
    about the portal, and the two rewrite each other until the request dies in
    `431` (`caddy.PORTAL`). The access control keeps naming the site alone: the
    portal never travels through it, because it never travels through the ask.

    Each secret is drawn once, SEALED, and kept beside this file — by the `up`,
    before this writer runs (`_drawn`) — because they belong to the installation
    and not to a start: one drawn per start would drop every session on the
    floor and make every record it had written unreadable. **O que este arquivo
    carrega é o ENVELOPE delas** (item 50): a pasta é copiada sem criptografia,
    a fonte é ela, e a cópia que o container monta é este mesmo texto com os
    três abertos (`_materialize`). **O caminho do notificador é o do ARQUIVO** —
    o `filename:` abaixo é o mesmo que a montagem do serviço declara com
    `file=True`, porque é assim que o Authelia o abre —, e ele vive na pasta de
    estado, que é a pasta que o backup cobre (§3): um aviso sobrevive a uma pasta
    copiada.

    **A sessão mora na MEMÓRIA do provedor, e é a única coisa que ele tem.**
    O que a PASTA guarda é o `secret` que assina o cookie, e o mesmo segredo
    entre dois restarts mantém o cookie válido — mas o registro que ele nomeia
    não atravessa: um restart do container, de qualquer origem — um crash, uma
    troca de credencial (`restart`), um `update`, um `podman restart` avulso —
    zera a memória, e é a pessoa de volta ao login com um cookie que o provedor
    já não conhece. **Este é o preço aceito, e não um a resolver aqui**: um
    registro que sobrevivesse a um restart seria um serviço de SESSÃO a mais no
    ambiente, e o §7 não o tem.

    **No OIDC provider is declared, and that is a decision and not an omission.**
    §7b has Authelia speaking OIDC with whoever speaks OIDC and forward-auth
    with whoever does not; every app of §7 reaches it by forward-auth, AT
    included, and the one that speaks OIDC is the one the person adds later.
    Authelia refuses a provider with no clients — `clients` has to name one or
    more, and `jwks` an RSA key — so a block written today would be an identity
    provider that does not start, declaring a client that does not exist. The
    provider enters with the first service that speaks OIDC, and it is that
    slice's to write.
    """
    session = _kept(IDENTITY, IDENTITY_SESSION)
    encryption = _kept(IDENTITY, IDENTITY_ENCRYPTION)
    signature = _kept(IDENTITY, IDENTITY_JWT)
    site = site_host()
    lines = [
        f"# {tr('services.identity-provider.file.header')}",
        "---",
        # A paleta do tema ativo (uma das quatro do Authelia); logo e favicon
        # ficam fora do container por ora — o escritor de arquivos aqui é só de texto.
        f"theme: {authelia_service.palette()}",
        # O endereço do container, e não uma publicação: o que sai dele é o que
        # o runtime mapeia (§7a) — e o NOME do serviço é como a borda e o WebApp
        # o alcançam, os dois na mesma rede. **O CAMINHO é o do portal**, e é o
        # que o Authelia lê para servir a página sob ele: sem o caminho, a borda
        # não teria como rotear o portal fora do `forward_auth`, e o portão
        # mandaria a pessoa a uma URL que ele mesmo volta a perguntar.
        "server:",
        f"  address: {_quoted(f'tcp://{ALL}:{IDENTITY_PORT}{caddy_service.PORTAL}')}",
        "log:",
        "  level: info",
        "session:",
        f"  secret: {_quoted(session)}",
        "  cookies:",
        # O domínio é o do SITE, e a URL é a do PORTAL — o nome em que a pessoa
        # está quando o portal lhe entrega o cookie (§7e), e o caminho onde o
        # portão a manda entrar. Um cookie emitido para outro nome é um cookie
        # que o navegador não devolve; e a URL sem o caminho é o redirecionamento
        # que voltava para a borda e era perguntado de novo, dobrando até o 431
        # (`caddy.PORTAL`).
        f"    - domain: {site}",
        f"      authelia_url: {portal_url()}",
        "storage:",
        f"  encryption_key: {_quoted(encryption)}",
        "  local:",
        f"    path: {IDENTITY_DATA}/db.sqlite3",
        "authentication_backend:",
        "  file:",
        f"    path: {IDENTITY_CONFIG}/{IDENTITY_USERS}",
        "access_control:",
        "  default_policy: deny",
        "  rules:",
        f"    - domain: {site}",
        "      policy: one_factor",
        "notifier:",
        "  filesystem:",
        f"    filename: {IDENTITY_CONFIG}/{IDENTITY_NOTIFICATIONS}",
        "identity_validation:",
        "  reset_password:",
        f"    jwt_secret: {_quoted(signature)}",
    ]
    return "\n".join(lines) + "\n"


def _identity_users() -> str:
    """The people of the folder, in the gate's own words (§7b).

    It is where the split §7b declares actually meets: WHO is an actor belongs
    to AT — the row of `actor`, with the role the ceiling is read from — and
    HOW it is proved belongs to the gate. What Authelia's file carries is the
    derivation the row already holds (the `hashed` field, §4), so the credential
    is the same one Forms and Basic prove, and what travels is a value that is
    only ever compared — never a credential, and nothing that could be turned
    back into one. The file lives inside the state folder, inside the folder the
    backup covers (§3).

    An actor with no credential is not in it: an entry with an empty derivation
    would be an account nobody holds and anybody could try. A folder with nobody
    in it gets the empty map — the gate reads it and lets nobody through, which
    is the honest state of a gate no key has been handed to yet.

    The text itself is `at.services.authelia.users_yaml`, the one definition.
    """
    return authelia_service.users_yaml()
