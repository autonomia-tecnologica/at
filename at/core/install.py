"""`install`: the artifact puts itself where commands are found (§3, item 28).

Using the artifact means keeping the file somewhere and typing its path — or a
shim written by hand to avoid that, which is what the machine this was written
on had, aimed at one checkout and pinning the folder. The product's own answer
is `install`.

**What it creates is a SYMLINK to the artifact inside the Working Folder**, and
nothing is copied. That one decision is the whole of the update story: the next
release replaces the file in the folder and the link follows it, so there is no
copy to find and no second file to leave behind. What the install writes outside
the folder is a link and the shell's completion — and a link is not state.

**The one thing that IS remembered lives in `App/install.json`**: the directory
the person chose, when they chose one. A link needs no memory; a directory
chosen once would otherwise have to be chosen again at every install, and the
default would leave the second link standing. The record is the folder's, like
everything else AT writes (§3).

**This is the word that runs before a folder exists.** Every other invocation
confirms a Working Folder first, because everything else is ABOUT the folder;
this one is about the FILE and where it sits. So it reads the folder from where
the artifact is (§3: the binary's folder), links to it, and says plainly when
that folder is not AT's yet — and then it records nothing, because there is
nowhere of AT's to record it in, and the person is told what that costs.

**The command is `at-cli`, and the install still says what it finds.** `at` is a
command a UNIX machine may already answer to — the `at`/`atd` job scheduler, one
package away and in this distribution's own repositories — and the artifact is
named `at-cli` so that the product does not take a name that is not only its own.
That settles the NAME and not the DIRECTORY: a link can still land where another
command of its own name already answers, and there the install does not refuse
and does not choose — it writes the link and SAYS which directory wins in the
order of `PATH`, because installing is an explicit request on the person's own
machine and whoever decides is whoever will live with it (§3, Permissão de
acesso).

**The completion is generated from the word tree**, which is the one declaration
the help reads too (§5), so a word that is offered is a word that completes and
neither can drift from the other. It offers WORDS and never flags: a flag list
written here would be a second declaration of what the tree declares.
"""


from __future__ import annotations

import os
import sys
from pathlib import Path

from at.core import files, paths, settings
from at.core.install_base import (  # noqa: F401  (the facade re-exports the lot)
    ALREADY,
    BASH,
    CMD_COMMENT,
    CMD_EXTENSION,
    COMPLETIONS,
    DEFAULT_BIN,
    DONE,
    HELD,
    MARK_TEXT,
    MISSING,
    NOTHING,
    RECORD,
    REMOVED,
    WIN32,
    ZSH,
    Words,
    _is,
    _marked,
    _mine,
    _remember,
    _save,
    _written,
    forget,
    mark,
    parse,
    record,
    record_path,
    remembered,
    target,
    where,
)
from at.core.install_completion import (  # noqa: F401
    FPATH_ENV,
    _bash,
    _completion_dir,
    _write_completion,
    _zsh,
    completion_path,
    completion_text,
    fpath_needed,
    shell_name,
)
from at.core.install_path import (  # noqa: F401
    _announce,
    _foreign,
    _order,
    _path_entries,
)
from at.i18n import tr


def act(
    word: str,
    artifact: str,
    words: Words,
    bin_flag: str | None = None,
    shell: str | None = None,
    platform: str | None = None,
) -> str:
    """Put the artifact where commands are found, and say what it did.

    `word` is the command (`at-cli`, `at-deploy`) and `artifact` is the FILE in
    the folder it points at — two names, because they are two different names:
    the command is what a person types and the file is what the release
    publishes, and on Windows they differ by the `.exe`.

    `platform` is `sys.platform`, read once here and nowhere else in this
    module: a test injects it so the suite's own answer never depends on the
    machine running it, and every call below reads the `windows` this resolves
    to and never the module global again.
    """
    windows = (platform or sys.platform) == WIN32
    into = where(word, bin_flag)
    link = into / (word + CMD_EXTENSION if windows else word)
    artifact_at = target(artifact)

    if not artifact_at.is_file():
        # The link would be born pointing at nothing, and a link that means
        # nothing is worse than no link: it answers the shell with a failure that
        # names the link and not the reason.
        print(tr("install.no_artifact", artifact=artifact,
                 folder=paths.working_folder(), word=word))
        return MISSING

    obstacle = _obstacle(link, artifact, word)
    if obstacle is not None:
        key, values = obstacle
        print(tr(key, **values))
        return HELD

    shim = _shim_text(word, artifact_at) if windows else None
    already = _same(link, artifact_at, shim)

    files.guard(link)
    try:
        into.mkdir(parents=True, exist_ok=True)
        if windows:
            # No copy here either: the shim is a few lines that forward to the
            # artifact, written fresh every run — never the binary itself.
            assert shim is not None  # built above for exactly this branch
            files.atomic_write_text(link, shim)
        else:
            # Written BESIDE the link and renamed onto it, the way every text this
            # product rewrites is (`files.atomic_write_text`): a crash in the middle
            # leaves the link that was already there, never a link pointing nowhere
            # — which on a `PATH` is a command that stopped working.
            temporary = link.with_name(link.name + ".tmp")
            temporary.unlink(missing_ok=True)
            os.symlink(artifact_at, temporary)
            os.replace(temporary, link)
    except OSError:
        # A directory that cannot be written — a permission, a read-only mount.
        # The install does not bring the machine down over its own directory.
        print(tr("install.no_dir", bin=into))
        return HELD
    print(tr("install.already" if already else "install.done",
             word=word, link=link, target=artifact_at))

    _announce(word, into, link)

    completion = _write_completion(word, words, shell)
    wrote = [link] + ([completion] if completion else [])

    if settings.exists():
        _remember(word, into, wrote)
        print(tr("install.recorded", where=record_path()))
    else:
        # A folder that is not AT's has nowhere of AT's to keep the record, and
        # creating `App/` here would be creating a Working Folder through the
        # back door — which is the one thing `boot` asks before (§3).
        print(tr("install.no_folder", settings=paths.settings_file(), bin=into))

    return DONE


def _obstacle(link: Path, artifact: str, word: str) -> tuple[str, dict] | None:
    """What stands in the way, when it is not AT's to move.

    The test is the NAME the link points at, and it answers two cases at once:
    a link of AT's that is current is not in the way, and neither is one whose
    target was DELETED — the folder moved and the binary was left behind, and
    the link is still AT's because AT is the only thing that writes a link named
    after its own artifact. In a collision the person's edit rules (§3): a file,
    or a link aimed somewhere else, is not touched and the install says so.

    `_mine` answers for a symlink; `_marked` answers for the Windows shim, which
    is a plain file and carries the mark inside it instead. Asking both is what
    lets this one check serve either platform without knowing which it is on.
    """
    if not link.is_symlink() and not link.exists():
        return None
    if _mine(link, artifact) or _marked(link, word):
        return None
    if link.is_symlink():
        return "install.held.link", {"link": link, "other": link.readlink()}
    return "install.held.file", {"link": link}


def _same(link: Path, artifact_at: Path, shim: str | None = None) -> bool:
    """Whether the link (or the shim) already says what this run would say.

    A symlink answers by where it points; the Windows shim is a plain file, so
    it answers by whether its CONTENT is already the one this run would write
    — `shim` is `None` on every platform but that one.
    """
    if shim is not None:
        try:
            return link.read_text(encoding="utf-8") == shim
        except OSError:
            return False
    try:
        return link.resolve() == artifact_at.resolve()
    except OSError:
        return False


def _shim_text(word: str, artifact_at: Path) -> str:
    """The `.cmd`'s own content: forward every argument, and come back with
    the ARTIFACT's exit code and not the shim's own.

    Quoted, because the artifact sits inside the Working Folder and that
    folder's name is the person's to pick — spaces and all. `%*` is `cmd.exe`'s
    own way of saying "everything that was typed after me," already carrying
    whatever quoting the person typed it with.
    """
    return (
        "@echo off\n"
        f"{mark(word, CMD_COMMENT)}"
        f'"{artifact_at}" %*\n'
        "exit /b %ERRORLEVEL%\n"
    )


# --------------------------------------------------------------- the memory ---


def undo(
    word: str,
    artifact: str,
    bin_flag: str | None = None,
    shell: str | None = None,
    platform: str | None = None,
) -> str:
    """Take back what the install put there, and only that.

    The candidates are the record's — an exact list of what was written — plus
    the two paths this run would write, because an install made in a folder that
    is not AT's has no record and still has to be undoable.

    Every candidate is checked before it goes, and that check is the whole rule
    one more time: a link aimed at the artifact's own name is AT's, a completion
    carrying AT's mark is AT's, and so is the Windows shim, which carries the
    very same mark for the very same reason. Anything else is the person's, and
    it stays — with a sentence saying so, because "nothing happened" and "I
    refused to touch your file" are different answers.
    """
    windows = (platform or sys.platform) == WIN32
    files.guard(where(word, bin_flag))

    candidates = [Path(path) for path in _written(word)]
    link = where(word, bin_flag) / (word + CMD_EXTENSION if windows else word)
    if link not in candidates:
        candidates.append(link)
    name = shell_name() if shell is None else shell
    completion = completion_path(word, name) if name else None
    if completion is not None and completion not in candidates:
        candidates.append(completion)

    removed = held = 0
    for path in candidates:
        if not path.is_symlink() and not path.exists():
            continue
        if not _mine(path, artifact) and not _marked(path, word):
            print(tr("install.uninstall.kept", path=path))
            held += 1
            continue
        files.guard(path)
        path.unlink()
        print(tr("install.uninstall.removed", path=path))
        removed += 1

    if not removed and not held:
        print(tr("install.uninstall.nothing", word=word, bin=where(word, bin_flag)))
        return NOTHING
    forget(word)
    return HELD if held else REMOVED
