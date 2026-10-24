"""`install` — the completion generated from the word tree."""

from __future__ import annotations

import os
from pathlib import Path

from at.core import files
from at.core.install_base import COMPLETIONS, ZSH, Words, _is, mark
from at.i18n import tr


def shell_name() -> str:
    """The shell the person is in, by its own name — `$SHELL`'s last word.

    `/bin/zsh` and `zsh` are the same shell: what is read is the name of the
    program, and never the directory it happens to be installed under.
    """
    return Path(os.environ.get("SHELL", "")).name


def completion_path(word: str, shell: str) -> Path | None:
    """Where that shell reads the completion of that word.

    The FILE name is not a choice: bash-completion loads a file by the command's
    name, and zsh reads a file whose name is the command's with an underscore in
    front. `None` for a shell whose completion has no home the product knows.
    """
    directory = _completion_dir(shell)
    if directory is None:
        return None
    return directory / (f"_{word}" if shell == ZSH else word)


def _completion_dir(shell: str) -> Path | None:
    parts = COMPLETIONS.get(shell)
    return Path.home().joinpath(*parts) if parts else None


def _write_completion(word: str, words: Words, shell: str | None) -> Path | None:
    """The completion, written where the shell reads it — or nothing, and said.

    No terminal to read `$SHELL` from is not a failure: a completion is what
    makes the words reachable without a path, and it is not what makes the
    command work. So an unknown shell is a sentence and nothing else — the link
    is already written by the time this runs.
    """
    name = shell_name() if shell is None else shell
    if not name:
        print(tr("install.completion.no_shell"))
        return None
    path = completion_path(word, name)
    if path is None:
        print(tr("install.completion.unknown", shell=name))
        return None
    files.atomic_write_text(path, completion_text(word, words, name))
    print(tr("install.completion.written", shell=name, path=path))
    if name == ZSH:
        # zsh reads a file off its `fpath`, and the person's own directory is
        # not on it by default. AT prints the line and does not write it: the
        # shell's configuration file is the person's, and a product that edited
        # it would be a product that has to find and undo its own edit later.
        print(tr("install.completion.fpath", folder=path.parent))
    return path


# The variable zsh ties its `fpath` array to, and the one this module can ask
# a CHILD process about: `fpath` itself is a shell-local array, and a person's
# `.zshrc` has to export it (or `typeset -g -x FPATH`) for a process AT starts
# to see it at all. A shell that never exports it answers the same as one that
# has not been fixed yet — the safe side is asking again.
FPATH_ENV = "FPATH"


def fpath_needed(word: str) -> Path | None:
    """The zsh completion's directory, while the person has not put it on
    `fpath` yet — or `None` when there is nothing to remind about.

    Asked on every run of `version`, and not only right after `install`: the
    shell reads its own `fpath` once, at start, and a completion written a
    minute — or a week — ago is not on it until the `.zshrc` line is added AND
    the shell is restarted, which is a gap `install`'s own one-time print
    cannot close on its own.

    A folder with no zsh completion written at all has nothing to remind about
    (`None`, the same answer `completion_path` gives a shell with no home),
    and neither does one whose directory is already in the INHERITED
    `$FPATH` — the heuristic this door has: a directory a person's `.zshrc`
    already put there is a line already fixed, and asking again would be
    noise nobody needs. `$FPATH` unset or not carrying it yet reads as "not
    resolved", which is the floor this reminder cannot go below: repeating a
    line that was already fixed costs a sentence, and going quiet on one that
    was not costs the completion itself.
    """
    path = completion_path(word, ZSH)
    if path is None or not path.is_file():
        return None
    directory = path.parent
    inherited = os.environ.get(FPATH_ENV, "")
    entries = [Path(entry).expanduser() for entry in inherited.split(os.pathsep) if entry]
    if any(_is(entry, directory) for entry in entries):
        return None
    return directory


def completion_text(word: str, words: Words, shell: str) -> str:
    """The completion script for one artifact, in one shell.

    Generated from the tree and never from a list kept here: the words offered
    are the words the help offers, and the day a word arrives it arrives in
    both. Only the comment is the person's — the rest is the shell's own
    language, and it is not translated for the same reason the command words
    are not (§3).
    """
    note = f"# {tr('install.note', word=word)}\n"
    head = f"{mark(word)}{note}"
    if shell == ZSH:
        return f"#compdef {word}\n{head}{_zsh(words)}\n"
    return f"{head}{_bash(word, words)}\n"


def _bash(word: str, words: Words) -> str:
    function = "_" + word.replace("-", "_") + "_complete"
    roots = " ".join(name for name, _ in words)
    lines = [
        f"{function}() {{",
        '  local cur="${COMP_WORDS[COMP_CWORD]}"',
        "  local offer",
        '  case "${COMP_WORDS[1]}" in',
    ]
    for name, under in words:
        if under:
            lines.append(f"    {name}) offer=\"{' '.join(under)}\" ;;")
    lines += [
        f'    *) offer="{roots}" ;;',
        "  esac",
        '  COMPREPLY=($(compgen -W "$offer" -- "$cur"))',
        "}",
        f"complete -F {function} {word}",
    ]
    return "\n".join(lines)


def _zsh(words: Words) -> str:
    roots = " ".join(name for name, _ in words)
    lines = ["local -a offer", 'case "${words[2]}" in']
    for name, under in words:
        if under:
            lines.append(f"  {name}) offer=({' '.join(under)}) ;;")
    lines += [
        f"  *) offer=({roots}) ;;",
        "esac",
        "_describe 'word' offer",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- the undo ---
