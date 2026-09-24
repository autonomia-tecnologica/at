"""`bill-deploy`'s command line: the surface that reaches §7 whole.

It is the same shape as `bill`'s `cli` and a smaller list, because this artifact
owns one subject: the environment. `services` is the whole of it — bring the
environment up, take it down, say what is standing, move the folder between the
two paths, and prove the delivery — and the Wizard of §7 (item 27's third slice)
is the screen that walks a person through the same steps, every one of them
reachable from here, because §5's one-way rule does not bend for a second
artifact.

**The folder comes first, and it is the same folder.** Every invocation confirms
the Working Folder exactly as `bill` does, through the same `boot`: the two
artifacts share the folder's STATE and not an API, and nothing here may assume a
folder the other one has not made — or make one this one would not recognise.

Exit codes: `0` success · `1` refused or failed · `2` usage error.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from bill import __version__
from bill.core import actors, boot, files, tables
from bill.i18n import tr

from bill_deploy import environment, tree
from bill_deploy.environment import HOSTED, INSTALL, UP

# What a person answers with, injected so a test can answer without a terminal —
# the same shape `boot` and `bill`'s `cli` take. The credential's door takes two
# readers, because one of them reads WITHOUT ECHO (the account's own shape,
# `bill admin`).
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

# The exit codes, and they are the product's: one `cli` answers like the other.
OK = 0
REFUSED = 1
USAGE = 2


def main(argv: Sequence[str] | None = None) -> int:
    """The process's whole life. Returns the exit code; `__main__` raises it."""
    words = list(sys.argv[1:] if argv is None else argv)

    if not boot.ensure_working_folder():
        return REFUSED

    if not words:
        # The Wizard of §7 is the natural front for this artifact (item 27), and
        # it is not built yet: the wordless command answers with the help, which
        # is the shape §5 already declares for the other artifact's too.
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

    if word == "services":
        return _services(rest)

    print(tr("deploy.error.unknown_word", word=word))
    print(tr("deploy.error.usage"))
    return USAGE


def _services(
    rest: list[str],
    ask: Ask | None = None,
    secret: Ask | None = None,
) -> int:
    """`bill-deploy services` — the container environment (§7a).

    The Wizard is the screen that installs services, and it is not built; §5's
    rule is that everything of the Wizard is reachable from the `cli`, and this
    is that door for the environment — `up` brings it up, `down` takes it down,
    and `status` says what is standing, which is also what the wordless
    `services` answers.

    Two of the words are not about the environment at all, and they live here
    because this is the surface §6 says reaches them: `switch` is the
    TRANSACTIONAL change from the hosted path to the container one, and `forms`
    is the way back — both local, which is the whole point of the return existing
    (`bill_deploy/switch.py`).

    `notify` is §7f's, and it is the one word that proves the delivery by hand:
    one alert, through the credential `up` created, to the topic — §5's rule that
    what the Wizard does is reachable from the `cli`.

    **The last two are the OPERATOR's acts** (item 27), and they are here
    because the environment is what they are about. `phone` draws the phone's
    credential — the other end of §7f's per-topic ACL — and prints it once,
    because it has to reach the phone. `credential` is §7b's: it gives a person
    the credential the gate proves, and it is the one word of this surface that
    takes an ARGUMENT, because the thing it changes is a NAME.

    The Podman is checked by the ENVIRONMENT and not here: the two ways out of a
    machine without it are §7a's sentence, and they are composed where the
    environment is (`bill_deploy/environment.py`). What this surface does is read
    the answer and turn it into an exit code — the `no_answer` of a terminal
    that could not ask being the one that decided nothing.

    `ask` and `secret` are injectable the way `boot` takes its own: a test walks
    the whole offer, and the whole credential conversation, without a terminal.
    """
    from bill_deploy import notifier, switch

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
        outcome = notifier.push(tr("services.notifier.test.title"),
                                tr("services.notifier.test.body"))
        return OK if outcome == notifier.SENT else REFUSED
    if word == "phone":
        # §7f's other end, and the person's act: the phone's credential is drawn
        # by the notifier, kept at `0600`, and PRINTED ONCE — it has to reach the
        # phone, and the only road there is the person's eyes. A second run does
        # not print it again (`notifier.subscribe`).
        outcome = notifier.subscribe()
        return OK if outcome in (notifier.PHONE_DRAWN, notifier.PHONE_HELD) else REFUSED
    if word == ARGUMENT:
        return _credential(args[0], ask, secret)
    try:
        if word == "switch":
            outcome = switch.to_gate(ask if ask is not None else _reader())
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
        outcome = environment.up(ask if ask is not None else _reader())
    except files.ReadOnly as error:
        # The pin and the services' files are written by `up`, and the read-only
        # switch is the one writer's rule — the same answer `bill`'s table route
        # and every other engine give (§3).
        print(tr("deploy.error.read_only", where=error.where))
        return REFUSED
    # A person who chose either way out, or an environment that came up, is not
    # a failure. What failed is a machine that could not be asked, and a service
    # that did not come up.
    return OK if outcome in (UP, INSTALL, HOSTED) else REFUSED


def _credential(name: str, ask: Ask | None, secret: Ask | None) -> int:
    """`bill-deploy services credential <name>` — the operator's act (§7b).

    The credential is read WITHOUT ECHO and twice, exactly as the first
    administrator's is (`bill admin`): it does not travel through the command
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
        outcome = environment.set_credential(name, credential)
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


def _reject(word: str) -> int:
    print(tr("deploy.error.rejected_arguments", word=word))
    return USAGE
