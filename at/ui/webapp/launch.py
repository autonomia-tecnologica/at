"""The launch (§3, §4): `run`, which puts AT on a port (in HTTP, or behind the
Caddy's TLS), and everything that sits between `make_server` and the process's
entry that only `run` uses — the address the folder answers on (`chosen_host`),
the probe of whoever already holds the port, the `spelling-checker` beside the
server and the SIGTERM turned into Ctrl-C.

Moved out of `app.py` (B-6) without a change of behaviour. `loopback` and
`GATE_LOOPBACK_NAME` stay in `app.py` (the `Handler` reads the first, the
deploy the second) and `run` asks for them there, inside the function: this
module does not import `app` at the top. `app.py` imports the names back.
"""

from __future__ import annotations

import errno
import json
import os
import urllib.request
from typing import Callable

from at import __version__, i18n
from at.core import actors, gate, paths, settings, spelling
from at.services import authelia, caddy, spelling_checker
from at.ui.webapp import keys
from at.ui.webapp.clock import start_clock
from at.ui.webapp.serve import DEFAULT_PORT, HOST, make_server

# The key of `settings.json` that carries the address the folder answers on. It
# is the same shelf `basic_auth` sits on — an adjustment of the installation and
# never a credential — and it is the door for the person who wants AT to listen
# somewhere else: `127.0.0.1` is the default and what this product recommends,
# and what leaving it costs is the environment's security note's to say.
HOST_KEY = "webapp_host"


def chosen_host() -> str:
    """The address the folder answers on — `HOST` when it chose none.

    `HOST_KEY` holds it, and it is an ADJUSTMENT of the installation: no
    credential, nothing proved. A folder that never wrote it answers on
    `127.0.0.1`, which is the default and what this product recommends; a person
    who wants AT somewhere else says it there, or says it for one run with
    `--host`.

    **A record nobody can read answers the default**, the same way `gate.mode`
    reads a broken one as the safe side: a settings file that will not parse is
    not a folder that moved its address, and a value that is not a name is not a
    name. What is NOT asked here is whether the address is the loop — that
    question has no answer this module could act on (the docstring says why),
    and asking it would be inventing a rule to enforce.
    """
    try:
        held = settings.get(HOST_KEY)
    except settings.SettingsError:
        return HOST
    return held.strip() if isinstance(held, str) and held.strip() else HOST


# How long `run` waits for whoever already holds the port to answer
# `/api/session` before giving up on knowing who it is. Local and fast: the
# instance on the other end is on THIS machine's loopback (or reached the same
# way the person reaches it), never a wait worth making a person sit through.
INSTANCE_PROBE_TIMEOUT = 0.5


def _instance_version(where: str, port: int) -> str | None:
    """The version of whoever already answers on that port, or `None`.

    Asked over HTTP and never guessed from HOW the thing was started: a loose
    `at-cli webapp`, a machine service and the container of §7c all answer the
    same `/api/session` the same way, so ONE probe covers every case this
    product can meet on a port — nothing here has to tell them apart. `None`
    covers everything that is not that answer: a closed port that only took
    the handshake, a page that is not AT's, a body the session payload never
    takes this shape in.
    """
    request = urllib.request.Request(f"http://{where}:{port}/api/session")
    try:
        with urllib.request.urlopen(request, timeout=INSTANCE_PROBE_TIMEOUT) as answer:
            payload = json.loads(answer.read())
    except (OSError, ValueError):
        return None
    version = payload.get("version") if isinstance(payload, dict) else None
    return version if isinstance(version, str) else None


def _version_order(version: str) -> tuple[int, ...]:
    """A version as the numbers in it, for the one comparison this needs:
    which of two is ahead.

    The same rule `at_deploy/environment.py:order` reads image pins by — but
    not imported from there: `at` does not depend on `at_deploy` (that half
    needs the machine and elevation, this one does not), so the few lines are
    repeated instead of reached for across the line that separates them.
    """
    numbers: list[int] = []
    for part in version.replace("-", ".").replace("_", ".").split("."):
        digits = "".join(character for character in part if character.isdigit())
        if digits:
            numbers.append(int(digits))
    return tuple(numbers)


def _report_taken(where: str, port: int) -> None:
    """The port is somebody else's — and, when that somebody is an AT, which
    version it is and the way out that fits (§3: the pin only moves forward).

    A version this cannot read at all falls back to the plain refusal: named
    port, named way out, nothing guessed about who is holding it. Otherwise
    it is one of three: the SAME version (nothing to do — it is already the
    WebApp this command would have started, loose or as a service, and this
    probe cannot tell which); AHEAD (this at-cli is the one behind, and the
    way out is updating IT); or BEHIND, where the way out is updating the
    instance itself. That word — `at-deploy update` — does not exist yet, so
    this only NAMES the exit and never runs it; once it exists, the missing
    piece is `at-deploy` itself, offered and never fetched, the same way the
    Podman and the `certutil` gaps are (`docs/pt_BR/container.md`).
    """
    url = f"http://{where}:{port}"
    theirs = _instance_version(where, port)
    if theirs is None:
        print(i18n.tr("webapp.port_taken", port=port))
        return
    mine = _version_order(__version__)
    order = _version_order(theirs)
    if order == mine:
        print(i18n.tr("webapp.instance_up", url=url, version=theirs))
    elif order > mine:
        print(i18n.tr("webapp.instance_ahead", url=url, theirs=theirs, mine=__version__))
    else:
        print(i18n.tr("webapp.instance_behind", url=url, theirs=theirs, mine=__version__))
        deploy = paths.deploy_file()
        if not (paths.working_folder() / deploy).is_file():
            print(i18n.tr("webapp.instance_behind_no_deploy", deploy=deploy))


# Who wants to know, AT ONCE, that the server is up: `(url, the announced line)`.
# A surface that says the run as data (`--json`) registers here for the length of
# the run, so the announcement leaves while the server keeps serving.
on_serving: list[Callable[[str, str], None]] = []


def _terminate_as_interrupt() -> Callable[[], None]:
    """Make SIGTERM raise `KeyboardInterrupt` in the main thread; answer the undo."""
    import signal
    import threading

    if threading.current_thread() is not threading.main_thread():
        return lambda: None

    def handler(signum, frame):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, handler)
    def restore() -> None:
        signal.signal(signal.SIGTERM, previous)

    return restore


def _spawn_spelling_checker():
    """Bring the `spelling-checker` up beside the server; `None` when it cannot."""
    from at.i18n import tr

    if not spelling_checker.AUTOSTART:
        return None
    if spelling_checker.platform_name() is None or spelling_checker.payload() is None:
        print(tr("spelling.no_payload", platform=spelling_checker.label()))
        return None
    if not spelling_checker.unpacked():
        print(tr("spelling.unpacking", where=spelling_checker.directory()))
    process = spelling_checker.bring_up()
    if process is None:
        print(tr("spelling.start_failed"))
        return None
    print(tr("spelling.up", port=spelling.port()))
    return process


WARM_TEXT = "Warm up."


def _warm_spelling_checker(process):
    """Warm the checker in the background; returns `(thread, stop)` or `None`.

    LanguageTool loads a language's rules on the FIRST query for it (seconds),
    so the first correction of the chat would pay for it. A daemon thread waits
    for the service and sends one throwaway query per supported language. It
    never blocks the boot, never raises, never writes: a failed warm-up is
    silent, and `stop` (or the process going down) ends it.
    """
    if process is None:
        return None
    import threading

    from at.i18n import SUPPORTED

    stop = threading.Event()

    def work():
        try:
            port = spelling.port()
            if port is None or not spelling_checker.ready(port):
                return
            for language in SUPPORTED:
                if stop.is_set() or process.poll() is not None:
                    return
                spelling.check(WARM_TEXT, language)
        except Exception:  # noqa: BLE001 — warming is never a reason to fail
            return

    thread = threading.Thread(target=work, name="spelling-warmup", daemon=True)
    thread.start()
    return thread, stop


def run(port: int = DEFAULT_PORT, public_port: int | None = None,
        host: str | None = None, include_caddy: bool = True) -> int:
    """Put AT on a port — in HTTP, or behind the Caddy's TLS.

    **One refusal lives here, and it is not a rule about exposure: it is the
    certificate.** `tls internal` is issued FOR A NAME (§3), and "every address"
    is the absence of one — a Caddy that took `0.0.0.0` would start and never
    finish a handshake. The address itself is the folder's choice
    (`chosen_host`), and the default is the loop; where the address is asked
    about and where it is not is the module docstring's. The raw server is what
    the route tests build, and it is not a hole: it is the folder that asks
    nothing, and `_asks` is where that is decided.

    **`public_port` is the bind port, unless something out there bends that**
    (TASK-187's follow-up): the Caddy right here is not always the one the
    browser's TLS lands on — `tailscale serve` terminates its own and proxies
    to this one, on a LOCAL port picked only to stay out of that front door's
    way. Left as `None`, the two are the same port, which is every run without
    one of those in front, this very repository's own `at-cli webapp --port
    12399` included. Said explicitly, it is what Authelia's portal tells the
    browser — the port it actually reaches, and never the bind the front door
    already swallowed.

    **And the clock starts with it** (§4, item 24): a daemon thread that rounds
    the jobs which have come round, born here and gone with the process. It is
    NOT in `make_server`, and that is the same line the refusal above draws —
    the route tests build a bare server, and nothing of theirs may move with an
    hour the machine chose.

    **And the derived keys are read here, once, before anything else** (§4,
    item 50): whatever `at_deploy.environment._webapp_env` handed this process
    is popped off `os.environ` and kept in `keys` for the life of the process —
    `keys.boot` is idempotent, but a second boot in the same run would just find
    nothing left to read, which is why this is the one call site.
    """
    from at.i18n import tr

    # `loopback` and the gate's name stay in `app.py` (the `Handler` and the
    # deploy read them there); `app` imports this module, so it is asked late.
    from at.ui.webapp.app import GATE_LOOPBACK_NAME, loopback

    keys.boot()

    # The port that reaches the browser, and `port` itself whenever nobody
    # says otherwise — see the docstring on `public_port`.
    public = public_port if public_port is not None else port

    # WHETHER THIS RUN ASKS. A run from the source tree does not: it serves
    # whoever is testing it, on the loop, and the install-time coin of "no actor
    # yet" must not stand between that person and the page. The BUNDLE always
    # asks, and that is the whole rule — `paths.source` is the artifact
    # answering, and there is no flag beside it (`paths.source` says why).
    asks = not paths.source()

    where = host or (GATE_LOOPBACK_NAME if include_caddy else chosen_host())

    # "Sem ator nenhum o AT não expõe" (§3, Acesso e exposição): a folder with
    # nobody to enter it does not open its page. The engine's row does not count
    # — it does not enter, the person does (`actors.can_expose`). It is asked
    # only of a run that ASKS: the refusal is about an entrance, and a run with
    # none is not a run with a door to close.
    #
    # **E ela não RECUSA mais: ela fica no LAÇO** (TASK-176, fatia 3/3). A
    # primeira subida é uma PÁGINA agora, e o formulário que cria o primeiro
    # administrador é uma tela desta casa — para ele existir, este processo tem
    # de estar de pé. O que a regra de §3 compra é o ENDEREÇO, e ele continua
    # comprado: sem ator nenhum o AT não responde fora do laço, nem por
    # `--host`, nem atrás do Caddy (`include_caddy` publica na rede, e é a
    # mesma exposição). O que fica de fora é a população que o terminal já
    # servia: quem está na máquina.
    if asks and not actors.can_expose() and (include_caddy or not loopback(where)):
        print(tr("webapp.no_admin"))
        return 1

    if include_caddy and caddy.wildcard(where):
        print(tr("caddy.address_needs_name", host=where))
        return 1

    # TASK-177: the bundle now always brings the gate beside the TLS, and
    # Authelia refuses a cookie domain this blunt before anything else
    # even unpacks (`authelia.valid_cookie_domain`, measured against the real
    # binary) — said here, before a port is taken or a secret drawn.
    if include_caddy and not authelia.valid_cookie_domain(where):
        print(tr("authelia.cookie_domain", host=where))
        return 1

    # Exposed, the WebApp takes an EPHEMERAL port on the loop and the Caddy holds
    # the port the person reaches: two processes cannot share one, and moving the
    # WebApp is the move that keeps the exposed address the stable one.
    try:
        server = make_server(0 if include_caddy else port,
                             HOST if include_caddy else where, asks=asks)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        # A port somebody else is already serving on is the way this fails in
        # practice — the PoC on 12345, or a second AT — and the bare `OSError:
        # Address already in use` names neither the port nor a way out. When
        # the somebody is an AT, `_report_taken` asks it which version and
        # names the way out that fits; otherwise it falls back to naming just
        # the port and the two generic ways out: another port, or freeing
        # this one.
        _report_taken(where, port)
        return 1

    process = None
    authelia_process = None
    if include_caddy:
        if not caddy.unpacked():
            print(tr("caddy.unpacking", where=caddy.directory()))
        if caddy.ensure() is None:
            server.server_close()
            print(tr("caddy.no_payload", platform=caddy.label()))
            return 1

        # TASK-177: the bundle's other vendored binary, unpacked the
        # same way and with the same refusal — said, not guessed, before
        # either of the two is asked to run.
        if not authelia.unpacked():
            print(tr("authelia.unpacking", where=authelia.directory()))
        if authelia.ensure() is None:
            server.server_close()
            print(tr("authelia.no_payload", platform=authelia.label()))
            return 1

        # O segredo do portão que o Caddyfile abaixo carrega — sorteado uma
        # vez, mantido em claro ao lado da pasta do Caddy (`caddy.draw_gate`'s
        # own docstring diz por quê), e lido de novo em toda subida seguinte
        # em vez de sorteado outra vez.
        caddy.draw_gate()

        # Authelia first: the Caddyfile below names its loopback address, so
        # it has to exist before that file is written.
        # O Authelia FICA DE PÉ entre subidas: se já há um respondendo na porta
        # lembrada, esta subida o REUSA. A sessão da pessoa vive nele, e
        # reiniciar o `at-cli` não pode reiniciá-lo — só a primeira subida (ou
        # uma em que ele caiu) sobe um novo. Quem o reinicia é a pessoa.
        standing = authelia.standing()
        if standing is not None:
            authelia_port, authelia_config = standing
            authelia_process = None
            print(tr("authelia.reused", port=authelia_port))
        else:
            authelia_port = authelia.free_port()
            authelia_config = authelia.write(where, authelia_port, public)
            authelia_process = authelia.start(authelia_config)
            if not authelia.started(authelia_process):
                server.server_close()
                print(tr("authelia.start_failed"))
                return 1
            authelia.remember(authelia_port)

        # `gate.standing`'s own self-check (`_gate`, §6) reads this exactly as
        # the container path's environment hands it over — a bare
        # `host:port`, no scheme — and a folder once committed to the gate on
        # THAT path carries the commitment into this one too, since the two
        # share the same `settings.json`. Left unset, `gate.portal` reads
        # nothing, `standing` is never true, and every request this bundle's
        # own Authelia just proved closes anyway on a 503 that blames a
        # portal which is, in fact, up.
        os.environ[gate.GATE_ENV] = f"{caddy.LOOPBACK}:{authelia_port}"

        # O ntfy saiu: a notificação é o Web Push do próprio PWA
        # (`core.push`), e o Caddy não publica um segundo site. O Caddyfile
        # que sobe tem UM site — o AT —, e a porta que a pessoa alcança é a
        # dele só.
        config = caddy.write_caddyfile(
            where, port, server.server_address[1],
            auth=f"{caddy.LOOPBACK}:{authelia_port}",
        )
        process = caddy.start(config)
        if not caddy.started(process):
            # The Caddy holds the port the person reaches, so its failure is the
            # command's: an AT that answered with a URL here would be announcing
            # an address nothing is on. O Authelia NÃO é parado: ele fica de pé
            # para a próxima subida o reusar (a sessão vive nele).
            server.server_close()
            print(tr("webapp.port_taken", port=port))
            return 1

    url = f"https://{where}:{port}" if include_caddy else f"http://{where}:{port}"
    serving = tr("caddy.serving", url=url) if include_caddy \
        else tr("webapp.serving", url=url)
    print(serving)
    for listener in list(on_serving):
        listener(url, serving)
    # AND WHETHER THIS RUN ASKS, said out loud: a person who expected an
    # entrance and does not find one should not have to guess why — and the
    # sentence is the same fact (`asks`), said once in the language on screen.
    if not asks:
        print(tr("webapp.source_open"))
    # The clock, kept by the process that is already up (§4, item 24). It is a
    # DAEMON: it dies with the server, and nothing has to stop it — the folder
    # that is idle is exactly the one it is here for. `server` travels with it
    # now (TASK-128, fatia 2/3): it is what lets the clock's own page-vigia
    # round reach the `Broadcaster` every open tab's `/api/events` subscribed to.
    # And the backup's own job is declared before it beats once (TASK-133): the
    # round that copies the folder on its own has no other door to be born by.
    start_clock(server)
    # The `spelling-checker` service (§4, §7d), spawned by this process and
    # gone with it. It is never a reason for AT not to be here: when it cannot
    # come up the line below says so, and whoever asks it gets "unavailable".
    checker = _spawn_spelling_checker()
    warming = _warm_spelling_checker(checker)
    # SIGTERM is how a service manager (and `instance-up.sh`) stops this
    # process: without turning it into the Ctrl-C below, the `finally` would not
    # run and the checker's JVM would outlive AT.
    restore = _terminate_as_interrupt()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        # Ctrl-C is how a person stops a server; it is not a failure.
        pass
    finally:
        restore()
        if warming is not None:
            warming[1].set()
        spelling_checker.stop(checker)
        if warming is not None:
            warming[0].join(timeout=1)
        caddy.stop(process)
        # E o Authelia FICA DE PÉ: a sessão da pessoa vive nele, e derrubá-lo
        # aqui seria perdê-la a cada reinício do `at-cli`. Quem o reinicia é a
        # pessoa — a subida seguinte o reusa (`authelia.standing`).
        server.server_close()
    return 0
