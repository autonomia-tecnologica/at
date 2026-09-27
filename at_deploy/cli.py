"""`at-deploy`'s command line: the surface that reaches §7 whole.

It is the same shape as `at-cli`'s `cli` and a smaller list, because this artifact
owns one subject: the environment. `services` is the whole of it — bring the
environment up, take it down, say what is standing, move the folder between the
two paths, and prove the delivery — and the Wizard of §7 (item 27's third slice)
is the screen that walks a person through the same steps, every one of them
reachable from here, because §5's one-way rule does not bend for a second
artifact.

**The folder comes first, and it is the same folder.** Every invocation confirms
the Working Folder exactly as `at-cli` does, through the same `boot`: the two
artifacts share the folder's STATE and not an API, and nothing here may assume a
folder the other one has not made — or make one this one would not recognise.

Exit codes: `0` success · `1` refused or failed · `2` usage error.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from at import __version__
from at.core import actors, boot, files, gate, install, licenses, paths, tables
from at.i18n import tr

from at_deploy import environment, tree
from at_deploy.environment import HOSTED, INSTALL, UP

# What a person answers with, injected so a test can answer without a terminal —
# the same shape `boot` and `at-cli`'s `cli` take. The credential's door takes two
# readers, because one of them reads WITHOUT ECHO (the account's own shape,
# `at-cli admin`).
Ask = Callable[[str], str]

# The words of `services`, read off the tree that OFFERS them — the declaration
# is `tree.py`'s and this is the same list, so a word can never dispatch without
# being offered nor the other way round (§5's one-way rule).
_SERVICES = tree.find("services")
WORDS = tuple(node.name for node in _SERVICES.children) if _SERVICES else ()

# The one word that takes an argument, and it is a NAME: the gate asserts a name
# and the `users.yml` it derives is keyed by one (§7b). The tree carries what a
# word IS and not how it is spelled after it, which is why this is said here.
ARGUMENT = "credential"

# The two acts of `ca`, read off the tree that offers them, for the reason the
# `services` words are: a word can never dispatch without being offered (§5). The
# ALVOS are the argument — a closed vocabulary of stores —, and the tree does not
# carry them for the same reason it does not carry the name of `credential`.
_CA = tree.find("ca")
CA_WORDS = tuple(node.name for node in _CA.children) if _CA else ()

# The exit codes, and they are the product's: one `cli` answers like the other.
OK = 0
REFUSED = 1
USAGE = 2


def main(argv: Sequence[str] | None = None) -> int:
    """The process's whole life. Returns the exit code; `__main__` raises it."""
    words = list(sys.argv[1:] if argv is None else argv)

    # The same two words run before the folder is confirmed here, and for the
    # same reason `at-cli` gives them: they are about the FILE and where it is
    # found, and not about the folder the file happens to sit in.
    if words[:1] in (["install"], ["uninstall"]):
        return _installed(words[0], words[1:])

    if not boot.ensure_working_folder():
        return REFUSED

    if not words:
        # THE `Tk` STEPS ASIDE FOR NOW, and it is the same decision `at-cli` took
        # in item 9. The Wizard of §7 is a screen for whoever does not type
        # commands, and it is the least urgent of the slices: the door is the
        # `cli` — §5's one-way rule says everything of the screen is reachable
        # from here — and the screen is how somebody who does not type reaches it.
        #
        # So `at_deploy/wizard.py` stays in the code with NO CALLER until the
        # slice that brings the `Tk` back, and what a wordless command answers is
        # the help, exactly like the other artifact. Until then, a machine with
        # no display and a machine with one behave the same way, which is the
        # point: nothing here opens a window.
        print(tree.as_text())
        return OK

    word, rest = words[0], words[1:]

    if word in ("help", "--help", "-h"):
        if rest:
            return _reject(word)
        print(tree.as_text())
        return OK

    if word in ("version", "--version", "-V"):
        if rest:
            return _reject(word)
        print(tr("deploy.version.line", version=__version__))
        return OK

    if word == "license":
        return _license(rest)

    if word == "services":
        return services(rest)

    if word == "ca":
        return ca(rest)

    print(tr("deploy.error.unknown_word", word=word))
    print(tr("deploy.error.usage"))
    return USAGE


def _installed(word: str, rest: list[str]) -> int:
    """`at-deploy install` and `at-deploy uninstall` — the second artifact, put
    where commands are found.

    The same word as `at-cli`'s and the same core (`core/install.py`), because
    where a command is found is one rule (§3, item 28) — and a different
    artifact all the same: this one installs itself and never the other, which
    is §3's cut read from the side of §7. Whoever stays on the hosted path never
    needs this binary, and installing it is the act of whoever does not.
    """
    flag, ok = install.parse(rest)
    if not ok:
        return _reject(word)
    try:
        if word == "install":
            outcome = install.act(paths.DEPLOY, paths.deploy_file(),
                                  tree.completion(), bin_flag=flag)
            return OK if outcome in (install.DONE, install.ALREADY) else REFUSED
        outcome = install.undo(paths.DEPLOY, paths.deploy_file(), bin_flag=flag)
        return OK if outcome in (install.REMOVED, install.NOTHING) else REFUSED
    except files.ReadOnly as error:
        # Both the link and the record are writes, and the read-only switch is
        # the one writer's rule — the same answer every engine gives (§3).
        print(tr("deploy.error.read_only", where=error.where))
        return REFUSED


def services(
    rest: list[str],
    ask: Ask | None = None,
    secret: Ask | None = None,
    answer: gate.Answer | None = None,
) -> int:
    """`at-deploy services` — the container environment (§7a).

    The Wizard is the screen that installs services, and it reads THIS door and
    no other (`at_deploy/wizard.py` walks it one word at a time): §5's rule is
    that everything of the Wizard is reachable from the `cli`, and the way to
    make that a property instead of a promise is for the screen to have no other
    road. So this is the door for the environment — `up` brings it up, `down`
    takes it down, and `status` says what is standing, which is also what the
    wordless `services` answers.

    Two of the words are not about the environment at all, and they live here
    because this is the surface §6 says reaches them: `switch` is the
    TRANSACTIONAL change from the hosted path to the container one, and `forms`
    is the way back — both local, which is the whole point of the return existing
    (`at_deploy/switch.py`).

    `notify` is §7f's, and it is the one word that proves the delivery by hand:
    one alert, through the credential `up` created, to the topic — §5's rule that
    what the Wizard does is reachable from the `cli`.

    **The last two are the OPERATOR's acts** (item 27), and they are here
    because the environment is what they are about. `phone` draws the phone's
    credential — the other end of §7f's per-topic ACL — and prints it once,
    because it has to reach the phone. `credential` is §7b's: it gives a person
    the credential the gate proves, and it is the one word of this surface that
    takes an ARGUMENT, because the thing it changes is a NAME.

    **Os dois do §7f — `notify` e `phone` — pedem a Frase de Acesso** (item 50):
    o que a pasta guarda das duas credenciais é o envelope do cofre, e quem o
    abre é a Chave daquele ato. É por isso que o `secret` deste surface chega a
    eles: a mesma porta sem eco por onde o `up` e o `credential` já a leem.

    The Podman is checked by the ENVIRONMENT and not here: the two ways out of a
    machine without it are §7a's sentence, and they are composed where the
    environment is (`at_deploy/environment.py`). What this surface does is read
    the answer and turn it into an exit code — the `no_answer` of a terminal
    that could not ask being the one that decided nothing.

    `ask` and `secret` are injectable the way `boot` takes its own: a test walks
    the whole offer, and the whole credential conversation, without a terminal.
    And `answer` is the SEAM of the phone's proof — the same `gate.Answer` the
    switch asks through —, so that the whole act, proof included, is provable
    without a socket.
    """
    from at_deploy import notifier, switch

    word = rest[0] if rest else "status"
    args = rest[1:]
    if word not in WORDS:
        return _reject("services")
    if word == ARGUMENT:
        if len(args) > 1:
            return _reject("services")
        if not args:
            # The word needs to know WHOSE credential, and saying which words
            # exist would not say that: the usage is this word's own.
            print(tr("deploy.services.credential.ask"))
            return USAGE
    elif args:
        return _reject("services")

    if word == "status":
        environment.status()
        return OK
    if word == "down":
        environment.down()
        return OK
    if word == "notify":
        # §7f's delivery, proved from the outside: the alert goes out the same
        # way a real one does — the credential on the file and the POST to the
        # topic — and a delivery that did not happen is a refusal (§7f's own
        # "the alert is the best-effort part"; the thing itself is not lost).
        #
        # **E ele pede a Frase de Acesso** (item 50): o que a pasta guarda é o
        # envelope, e quem o abre é a Chave desta entrega — a mesma porta da
        # subida (`environment.unlock`). Sem terminal não se pergunta, e sem a
        # Frase o alerta não sai; é o preço declarado, e ele é o de §7f.
        outcome = notifier.push(tr("services.notifier.test.title"),
                                tr("services.notifier.test.body"),
                                secret if secret is not None else _secret())
        return OK if outcome == notifier.SENT else REFUSED
    if word == "phone":
        # §7f's other end, and the person's act: the phone's credential is drawn
        # by the notifier, kept at `0600` SEALED, and PRINTED ONCE — it has to
        # reach the phone, and the only road there is the person's eyes. A second
        # run does not print it again (`notifier.subscribe`). **E o ato prova a
        # leitura pelo NOME**, com o token e sem ele: um token que existe num
        # arquivo não é um celular que lê, e a palavra promete a leitura
        # (`PHONE_UNPROVED`).
        #
        # **A Frase entra aqui porque o ato SELA e porque ele ABRE** (§4, item
        # 50): o valor sorteado vai para a pasta como envelope, e a prova de uma
        # segunda rodada abre o que está lá — as duas coisas pedem a Chave, e é
        # o mesmo leitor sem eco da subida.
        outcome = notifier.subscribe(
            answer, secret if secret is not None else _secret())
        return OK if outcome in (notifier.PHONE_DRAWN, notifier.PHONE_HELD) else REFUSED
    if word == ARGUMENT:
        return _credential(args[0], ask, secret)
    try:
        if word == "switch":
            outcome = switch.to_gate(
                ask if ask is not None else _reader(),
                secret=secret if secret is not None else _secret(),
            )
            # The environment's own answers come back through the switch
            # unchanged, and they mean here what they mean there.
            return OK if outcome in (
                switch.SWITCHED, switch.ALREADY, INSTALL, HOSTED,
            ) else REFUSED
        if word == "forms":
            # The return is the person's act and never a side effect of anything
            # else (§6): nothing about it needs a Podman, because a folder whose
            # environment vanished is exactly the folder that needs this door.
            return OK if switch.to_forms() in (
                switch.FORMS_OUTCOME, switch.ALREADY,
            ) else REFUSED
        outcome = environment.up(
            ask if ask is not None else _reader(),
            secret if secret is not None else _secret(),
        )
    except files.ReadOnly as error:
        # The pin and the services' files are written by `up`, and the read-only
        # switch is the one writer's rule — the same answer `at-cli`'s table route
        # and every other engine give (§3).
        print(tr("deploy.error.read_only", where=error.where))
        return REFUSED
    # A person who chose either way out, or an environment that came up, is not
    # a failure. What failed is a machine that could not be asked, and a service
    # that did not come up.
    return OK if outcome in (UP, INSTALL, HOSTED) else REFUSED


def ca(rest: list[str]) -> int:
    """`at-deploy ca` — a CA do AT no cofre que o navegador desta máquina lê (item 49).

    A palavra que liga o §7a ao navegador de quem está NESTA máquina: o
    `cert.at.local` da fatia 1 levou a CA ao aparelho que não lê o disco daqui, e
    o Firefox desta não lê o cofre do sistema — o NSS dele é por perfil. Quem
    escreve nesses bancos é o `certutil`, e o ato inteiro mora em
    `at_deploy/trust.py`.

    **A ordem das palavras é do produto e não do pedido, e vale dizer por quê.**
    O pedido era `ca <alvo> install`; o que saiu foi `ca install [<alvo>]`. A
    regra do §5 é que uma palavra que DESPACHA seja uma palavra que a ajuda
    OFERECE, e a árvore é a declaração única das duas: os ATOS — `install` e
    `uninstall` — são o que despacha, então são eles os filhos de `ca`; os ALVOS
    são um vocabulário fechado de ARGUMENTO, como o nome de
    `services credential <nome>`, e a frase de uso os diz. É o desenho que o
    `at-cli` já segue — `<objeto> <ação> [<argumento>]` —, e sem ele o ato não
    apareceria na ajuda nem no completion.

    O alvo vazio é o PADRÃO: sem ele a palavra cobre os dois cofres que a pessoa
    tem, e nomeá-lo a estreita. Nada aqui pede elevação — os dois bancos são
    arquivos da própria pessoa —, e o cofre do sistema fica de fora de propósito
    (`trust.py`).
    """
    from at_deploy import trust

    if not rest:
        print(tr("deploy.ca.ask", targets=", ".join(trust.TARGETS)))
        return USAGE
    act, alvos = rest[0], rest[1:]
    if act not in CA_WORDS:
        return _reject("ca")

    unknown = [name for name in alvos if name not in trust.TARGETS]
    if unknown:
        print(tr("deploy.ca.unknown", name=unknown[0],
                 targets=", ".join(trust.TARGETS)))
        return USAGE

    outcome = (trust.install(alvos) if act == trust.INSTALL
               else trust.uninstall(alvos))
    return OK if outcome in (trust.INSTALLED, trust.REMOVED) else REFUSED


def _credential(name: str, ask: Ask | None, secret: Ask | None) -> int:
    """`at-deploy services credential <name>` — the operator's act (§7b).

    The credential is read WITHOUT ECHO and twice, exactly as the first
    administrator's is (`at-cli admin`): it does not travel through the command
    line, so it stays out of the shell's history and out of anybody's `ps`, and
    it is read twice because a credential is not recovered — there is no
    "forgot the password" in a folder on your own disk.

    **The rules are the core's, and so are their sentences.** The length is
    `actors.check_credential`'s and the mismatch is the same refusal the first
    administrator's door raises, because it is the same rule and §3 is explicit
    that whoever asks does not get to decide it. What this surface owns is the
    conversation and the outcome: everything the ACT says is the environment's
    (`environment.set_credential`).

    A person nobody names is refused here with the deploy's own word and not as
    an engine error: the name is what the gate asserts and what the `users.yml`
    is keyed by, so a name nobody wears is a gate with nothing to prove.
    """
    if ask is None and secret is None:
        ask, secret = _readers()
    if ask is None or secret is None:
        # The same refusal the first administrator's door makes: a credential
        # typed where nobody could answer is not a credential.
        print(tr("services.credential.no_tty"))
        return REFUSED

    try:
        credential = secret(tr("services.credential.secret"))
        if credential != secret(tr("services.credential.again")):
            raise actors.AdminError("error.mismatch")
        outcome = environment.set_credential(name, credential, secret)
    except (actors.AdminError, tables.TableError) as refused:
        print(refused)
        return REFUSED
    except files.ReadOnly as error:
        # The row is a write of the folder's, and the read-only switch is the
        # one writer's rule — the same answer every other engine gives (§3).
        print(tr("deploy.error.read_only", where=error.where))
        return REFUSED

    if outcome == environment.CREDENTIAL_UNKNOWN:
        print(tr("services.credential.unknown", name=name))
        return REFUSED
    # `CHANGED` did everything it set out to; `PENDING` already said, in its own
    # words, that the folder has the new credential and the gate does not.
    return OK if outcome == environment.CREDENTIAL_CHANGED else REFUSED


def _readers() -> tuple[Ask | None, Ask | None]:
    """A line reader and a no-echo reader, when there is a terminal to use."""
    if not sys.stdin.isatty():
        return None, None
    import getpass

    return (lambda question: input(question), getpass.getpass)


def _reader() -> Ask | None:
    """A line reader, when there is a terminal to ask a YES/NO question in."""
    return _readers()[0]


def _secret() -> Ask | None:
    """A no-echo reader, when there is a terminal to type a secret in.

    Ele é o leitor da Frase de Acesso (§4): o mesmo `getpass` que a credencial
    do primeiro administrador usa, pela mesma razão — o que se digita sem eco
    não fica no histórico do shell nem no `ps` de ninguém.
    """
    return _readers()[1]


def _license(rest: list[str], texts: bool = False) -> int:
    """`at-deploy license` — the same door `at-cli`'s licence word opens.

    It is the same answer and a different list: this artifact carries the
    interpreter, the bootloader and the crypto binding, and none of the WebApp's
    payload — no typeface, no Vue bundle, no Caddy —, so what it declares is what
    it holds. The reading is `at/core/licenses.py`'s, shared by both artifacts,
    and the flag is the same one.
    """
    for flag in rest:
        if flag == "--include-texts":
            texts = True
            continue
        return _reject("license")
    print(licenses.report(paths.DEPLOY, texts=texts))
    return OK


def _reject(word: str) -> int:
    print(tr("deploy.error.rejected_arguments", word=word))
    return USAGE
