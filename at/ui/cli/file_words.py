"""The words about files and the artifact: `backup`, `convert`, `license`, `install`."""

from __future__ import annotations

from at import convert
from at.core import backup, files, install, licenses, paths, secrets
from at.i18n import tr
from at.prose import listing as prose
from at.ui import ask as door
from at.ui.ask import OK, REFUSED
from at.ui.cli import tree
from at.ui.cli.common import Ask
from at.ui.cli.common import readers as _readers
from at.ui.cli.common import reject as _reject

# ----------------------------------------------------------------- the backup ---

def _backup(rest: list[str], secret: Ask | None = None) -> int:
    """`at-cli backup make|restore` — the copy that survives the machine (item 51).

    The Main Key is read WITHOUT ECHO, the same way `admin`'s credential
    is — it does not travel through the command line, so it never lands in
    the shell's history nor anybody's `ps`. It is read LAZILY: `core.backup`
    calls the reader itself, once its own cheap checks already passed, so a
    destination with no tool to reach it or a folder `restore` refuses never
    gets as far as asking a person to type it.
    """
    if len(rest) != 2:
        return _reject("backup")
    action, target = rest[0], rest[1]
    if action not in (backup.MAKE, backup.RESTORE):
        return _reject("backup")
    if secret is None:
        secret = _readers()[1]
    if secret is None:
        print(tr("backup.no_tty"))
        return REFUSED

    def phrase() -> str:
        return secret(tr("backup.phrase"))

    try:
        outcome = backup.make(phrase, target) if action == backup.MAKE \
            else backup.restore(phrase, target)
    except secrets.SecretsError as error:
        print(error)
        return REFUSED
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    except OSError as error:
        print(tr("backup.error.io", reason=str(error)))
        return REFUSED

    # The wording lives in the door (`ask.backup_message`) because the clock's
    # own round reads it too — the terminal line and the phone's notice are the
    # same fact and must not be two sentences.
    print(door.backup_message(action, outcome, target))
    return OK if outcome.state in (backup.MADE, backup.RESTORED) else REFUSED


def _convert(rest: list[str]) -> int:
    """`at-cli convert <arquivo> --to pdf|docx` (TASK-165, fatia 2/4).

    `<arquivo>` is read the way `Arquivos/` is always addressed — a path
    relative to it, resolved and validated by `prose.inside`/`prose.read`, the
    same door the WebApp's own file route reads through: a path outside the
    tree or a file that is not text is refused with the SAME sentence the page
    already shows for it, and not a second one invented here.
    """
    if len(rest) != 3 or rest[1] != "--to":
        return _reject("convert")
    rel, _, fmt = rest
    if fmt not in convert.FORMATS:
        return _reject("convert")
    info = prose.read(rel)
    if info is None:
        print(tr("prose.not_served"))
        return REFUSED
    # A conversion is of TEXT — a PDF, an image or a video opens in the page
    # (`open`), and none of them is a markdown to convert.
    if info["open"] != "text":
        print(tr(info["reason"] or "prose.not_supported"))
        return REFUSED
    where = prose.inside(rel)
    assert where is not None  # `prose.read` above already served this path
    try:
        target = convert.convert(where, fmt)
    except files.ReadOnly as error:
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
    print(tr("convert.done", path=target.name))
    return OK


# ---------------------------------------------------------------- the licence ---

def _license(rest: list[str], texts: bool = False) -> int:
    """`at-cli license` — what this artifact carries from outside, and its terms.

    The word is the notices' only door: the artifact is ONE file, so there is no
    folder beside it for a third party's licence to sit in, and what the licence
    demands has to come out of the artifact itself. What comes out by default is
    the summary — what the AT is licensed as, and one line per component —,
    because the vendors' texts are tens of kilobytes of legalese and nobody
    asking what the binary carries is asking to read them; `--include-texts` is
    how whoever needs them reaches them, and the help says the flag, like every
    other flag of the product.

    Nothing here is about the Working Folder, so there is no permission and no
    folder to read: the same place `version` and `help` answer from.
    """
    for flag in rest:
        if flag == "--include-texts":
            texts = True
            continue
        return _reject("license")
    print(licenses.report(paths.ARTIFACT, texts=texts))
    return OK


def _installed(word: str, rest: list[str]) -> int:
    """`at-cli install` and `at-cli uninstall` — the file, where commands are found.

    What the word takes is `--bin <directory>`, and that is the whole of it:
    the artifact is not fetched and not copied, and a new one arrives by the
    file in the folder being replaced, which the link follows (§3).

    Both artifacts answer through the same core (`core/install.py`), because
    where a command is found is one rule and not one per artifact — and the two
    are two installs all the same: neither installs the other, which is the
    same cut §3 makes between `at-cli` and `at-deploy`.

    A `uninstall` that found nothing to take back is not a failure: what the
    person asked for is the state, and the state is already it.
    """
    flag, ok = install.parse(rest)
    if not ok:
        return _reject(word)
    try:
        if word == "install":
            outcome = install.act(paths.ARTIFACT, paths.artifact_file(),
                                  tree.completion(), bin_flag=flag)
            return OK if outcome in (install.DONE, install.ALREADY) else REFUSED
        outcome = install.undo(paths.ARTIFACT, paths.artifact_file(), bin_flag=flag)
        return OK if outcome in (install.REMOVED, install.NOTHING) else REFUSED
    except files.ReadOnly as error:
        # The link and the record are both writes, and the read-only switch is
        # the one writer's rule — the same answer every engine gives (§3).
        print(tr("cli.error.read_only", where=error.where))
        return REFUSED
