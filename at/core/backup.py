"""The copy that survives the machine — and it is never versioning (item 51).

`core.versioning` already says the ONE thing this module exists to be the other
half of: "it is versioning, never backup" (`versioning.py:7`). Git keeps the
folder's history on the SAME disk; this module is what leaves it. The Working
Folder whole, ciphered with a key derived the way `core.secrets` already derives
one — the Main Key, scoped `backup` (§4) — and sent to a destination the
person declares. AT never invents one: a path, an `rclone` remote, or an `ssh`
host are the three shapes a destination takes, told apart by their own syntax
and nothing this module adds.

**The scan is the gate, and it runs before anything else.** `core.scanner`
already walks the folder and its history for what should not be there (item
51); a copy that leaves the machine is exactly the moment that matters, so a
clean state is the one thing `make` asks before it ciphers a single byte. What
the scanner cannot finish — the tool missing, the report unreadable — is read
the same as a finding: a gate that cannot answer does not wave the copy
through.

**The key is derived, never stored.** `secrets.key_of("backup", phrase)` is the
very door `core.secrets` already opens for a row of the `secret` table, asked
under its own scope — the Vault keeps no catalogue of scopes, and a name here
is a name like any other's (§4). Nothing this module writes carries the phrase
or the key: the archive is ciphered in a temporary folder OUTSIDE the Working
Folder, exactly where `core.scanner`'s own report lands, and only the sealed
bytes are what travels.

**Restoring is refused into a folder that already has something to lose.**
`_fresh` reads the tables a person's own work fills — never `actor` or `role`,
because an administrator created to get a new machine going is the very setup
restoring expects to walk into — and the two folders no session fills on its
own (`Projetos/`, `Compartilhada/`). A folder that answers anything else keeps
what it has: extracting on top of REAL work, `.git` included, is exactly the
loss backing up exists to prevent, so the one place this module will not take
that risk is the one act shaped like a wipe. A folder that answers `_fresh`
loses nothing a repeated `at-cli admin` could not repeat, and the archive lands
whole — its own `.git` included, because a repository IS the history this item
is about restoring. The folder's OWN fresh `.git` is cleared first and not
merged into: git writes its objects read-only, so the two would collide on the
first path they share, and `_fresh` is what makes clearing it lose nothing.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from at.core import files, paths, scanner, secrets, settings, strongbox, tables, versioning
from at.encryption import vault
from at.i18n import tr

# The two acts, and the `cli` reads them from here (`tree.py` offers them
# under these same names): the declaration is one, and an act not offered
# cannot dispatch (§5).
MAKE = "make"
RESTORE = "restore"

# The scope a derived key is asked under (§4): a name like any other service's
# or purpose's, and the Cofre keeps no catalogue to check it against.
SCOPE = "backup"

# This module's OBJECT in the Actions catalogue (§5, `permissions`): the key
# `permissions.CATALOGUE` and the `cli` tree already call "backup", and the one
# `jobs.what` spells to name the act a scheduled job holds (`backup:make`). It
# is a name of its own and not a second `SCOPE`, even where the two agree: the
# scope is what the Vault derives a key under, and the object is what the
# catalogue prices a demand by.
OBJECT = "backup"

# What a sealed archive is named, and the whole of what says one is: a tar,
# gzipped, then sealed whole — never a base64 envelope, because this is a FILE
# and not a value that has to sit inline inside one (`vault.seal_bytes`).
SUFFIX = ".tar.gz.enc"

# The tables a person's own work fills, and the ones `_fresh` reads. `actor` and
# `role` are left out on purpose (the module docstring says why).
FRESH_TABLES = ("task", "project", "reminder", "note", "secret", "audit", "job")

# `make`'s outcomes.
MADE = "made"
BLOCKED = "blocked"
NO_TOOL = "no_tool"
FAILED = "failed"

# `restore`'s outcomes.
RESTORED = "restored"
NOT_FOUND = "not_found"
NOT_FRESH = "not_fresh"
WRONG_KEY = "wrong_key"

# The three shapes a destination takes, and nothing this module invents beyond
# them: a path is the default, and the other two are told apart by the syntax
# their OWN tools already use — `remote:path` for `rclone`, `user@host:path`
# for `scp` — so a destination that names neither is read as a path.
LOCAL = "local"
RCLONE = "rclone"
SSH = "ssh"

_SSH_SHAPE = re.compile(r"^[^\s/@:]+@[^\s/:]+:.+$")
_RCLONE_SHAPE = re.compile(r"^[^\s/:]+:.+$")

# The external tool each remote shape reaches, named and never installed: like
# `podman` and `certutil`, AT uses what the machine already has and says so
# when it does not (§7a, `at_deploy/trust.py`).
_TOOL = {RCLONE: "rclone", SSH: "scp"}


@dataclass(frozen=True)
class Report:
    """What one act of this module answers: the state, and the tool it named
    when the state is about one — `NO_TOOL` and `FAILED` are the only two."""

    state: str
    tool: str = ""


def make(phrase: Callable[[], str], destination: str) -> Report:
    """Cipher the Working Folder whole, and send it to `destination`.

    The scan runs FIRST, because it is the gate and not a detail — nothing is
    ciphered while the folder carries a secret in clear, or while the scanner
    cannot say whether it does. The destination's tool is checked next, before
    the Main Key is ever asked for: a missing `rclone` or `scp` is cheap to
    find out, and asking a person to type a phrase for a copy that cannot leave
    anyway would be asking for nothing. `phrase` is called only once both hold,
    which is what lets the CLI defer reading it until there is something to
    read it FOR.
    """
    scanned = scanner.scan()
    if scanned.state != scanner.CLEAN:
        return Report(BLOCKED)
    kind = _kind(destination)
    tool = _TOOL.get(kind, "")
    resolved = shutil.which(tool) if tool else None
    if tool and resolved is None:
        return Report(NO_TOOL, tool=tool)
    key = secrets.key_of(SCOPE, phrase())
    with tempfile.TemporaryDirectory(prefix="at-backup-") as hold:
        archive = Path(hold) / "folder.tar.gz"
        with tarfile.open(archive, "w:gz") as opened:
            opened.add(paths.working_folder(), arcname=".", filter=_strongbox_filter)
        sealed = Path(hold) / _named()
        sealed.write_bytes(vault.seal_bytes(archive.read_bytes(), key))
        ok = _send(sealed, destination, kind, resolved)
    return Report(MADE if ok else FAILED, tool=tool)


def restore(phrase: Callable[[], str], source: str) -> Report:
    """Open the sealed archive `source` and lay it over the CURRENT folder.

    **Read-only, missing and not-fresh are refused before the phrase is ever
    asked for**, the same order `make` keeps: nothing is asked for a restore
    that cannot happen anyway. What follows is the one write this module makes
    — the archive extracted whole, `.git` included, right over the folder AT is
    already running in — and it is counted (`files.mark_write`) so the version
    item 30 promises is not skipped for having arrived through `tarfile`
    instead of `atomic_write_text`. The local file is removed once the folder
    holds what it carried; the destination `make` sent it to is never touched.
    """
    path = Path(source)
    if not path.is_file():
        return Report(NOT_FOUND)
    files.guard(paths.working_folder())
    if not _fresh():
        return Report(NOT_FRESH)
    key = secrets.key_of(SCOPE, phrase())
    opened = vault.unseal_bytes(path.read_bytes(), key)
    if opened is None:
        return Report(WRONG_KEY)
    target = paths.working_folder()
    # Git's own loose objects are written read-only, so extracting ON TOP of
    # the fresh repository `boot` already gave this folder would collide on
    # the first one that shares a path. `_fresh` is what makes clearing it
    # safe: a folder that answers it has no history worth keeping yet.
    current_git = target / ".git"
    if current_git.is_dir():
        shutil.rmtree(current_git)
    with tempfile.TemporaryDirectory(prefix="at-restore-") as hold:
        archive = Path(hold) / "folder.tar.gz"
        archive.write_bytes(opened)
        with tarfile.open(archive, "r:gz") as opened_tar:
            opened_tar.extractall(target, filter="data")
    files.mark_write()
    # Item 30's own promise: an action that changes the folder ends in a
    # version, and the restored `.git` is the very repository that promise
    # already owns — `commit` reads its OWNER mark and finds it there.
    versioning.commit(tr("backup.restore.commit"))
    path.unlink()
    return Report(RESTORED)


# --------------------------------------- the round that nobody types (§4, 24) ---
#
# **The copy that depends on remembering does not happen**, so the AT fires it
# itself: `backup:make` is the `what` of a `scheduled` job (§4, item 24), and
# the clock brings it round every minute. What would be wrong is the copy going
# out on EVERY round — the folder is written to disk on every edit, and sixty
# ciphered archives an hour is not a backup — so the BACKUP's own cadence is a
# reading of its own, in the pattern of the versioning's (`versioning.interval`):
# it looks at how long ago the last attempt was and only lets the copy leave
# once the interval has passed.
#
# **The destination and the interval are settings** (§4): what `backup make
# <destino>` used to say at the terminal the round nobody types cannot say, so
# the folder keeps them. The cadence is read in MINUTES and compared in seconds,
# like the versioning's, and the comparison lives in one place.

# The two adjustments, named from `core.settings`, which owns the file's keys —
# the two homes are one — and `DEFAULT_INTERVAL` is what a folder that never
# chose is copied at: once a DAY, because the copy carries the whole folder and
# is worth a day, and a finer interval would spend the destination's bandwidth
# and history for nothing. `0` is a cadence like any other — the folder that
# wants the copy on every round, and the round is the clock's minute.
DESTINATION_KEY = settings.BACKUP_DESTINATION
INTERVAL_KEY = settings.BACKUP_INTERVAL
DEFAULT_INTERVAL = 1440.0

# When the automatic copy was last ATTEMPTED, in `App/` the way the migration's
# own stamp is (`migrations.stamp_file`): it is AT's state and never a person's
# adjustment, and it is what makes the cadence read the LAST copy instead of
# firing every round.
STAMP = "backup"

# The seconds in a minute, for the one comparison this cadence makes: the
# interval is READ in minutes and COMPARED in seconds, and the conversion lives
# here and nowhere else.
_MINUTE = 60.0


def stamp_file() -> Path:
    """`App/backup` — when the automatic copy was last attempted."""
    return paths.instance_dir() / STAMP


def destination() -> str:
    """The destination the folder DECLARED (§4, item 24) — the same one `backup
    make <destino>` types, kept so the round nobody types has one.

    Empty when the folder never chose: with nowhere to copy to, the round does
    not pretend it copied. It reads and never invents, the way every AT setting
    does.
    """
    value = settings.get(DESTINATION_KEY, "")
    return value.strip() if isinstance(value, str) else ""


def interval() -> float:
    """The backup's cadence, in MINUTES — the reading of its own (§4, item 24).

    A value that is not a number is a choice that was never made, and the folder
    answers the `DEFAULT` — never a copy that fires every minute, never one that
    quietly stops — the way `versioning.interval` answers its own. Zero is not
    that strange value: it is the cadence of a folder that wants the copy on
    every round.
    """
    value = settings.get(INTERVAL_KEY, DEFAULT_INTERVAL)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return DEFAULT_INTERVAL
    if not math.isfinite(value) or value < 0:
        return DEFAULT_INTERVAL
    return float(value)


def last() -> float | None:
    """When the automatic copy was last attempted, in seconds — the stamp's own
    reading, or `None` for a folder that never tried.

    A stamp nobody can read answers `None`, the rule failing the safe way, the
    same one `versioning.last_version` keeps: a folder whose last copy cannot be
    placed copies now.
    """
    try:
        raw = stamp_file().read_text(encoding="utf-8").strip()
        return float(raw) if raw else None
    except (OSError, ValueError):
        return None


def attempted(at: datetime) -> None:
    """Mark that the automatic copy was ATTEMPTED now — the stamp the cadence
    reads on the next round.

    It is written even when the copy did NOT go out, and that is the whole point:
    it is what makes a notice of "não aconteceu" reach the phone once per
    interval instead of every minute — the same "not in a loop, but not given up
    on either" a failed reminder already keeps.
    """
    files.atomic_write_text(stamp_file(), f"{at.timestamp()}\n")


def due(at: datetime) -> bool:
    """Whether the backup's own cadence has passed since the last attempt.

    The JOB's cadence is the clock's minute; this one is the backup's, and it is
    what keeps `backup:make` from copying on every round. A folder that never
    tried owes the first copy by definition: the first is not something a
    cadence postpones.
    """
    moment = last()
    return moment is None or at.timestamp() - moment >= interval() * _MINUTE


def _strongbox_prefix() -> str:
    """`./Cofre/` como `tarfile` nomeia um membro dela — a partir de `.`, que
    é o `arcname` que `make` já usa para a pasta inteira."""
    return f"./{strongbox.folder().relative_to(paths.working_folder()).as_posix()}/"


def _strongbox_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    """TASK-154: **o backup só leva o que carrega o fingerprint do `.enc`.**

    Fora de `Cofre/` — e a própria pasta, como entrada — nada muda: é o que a
    ausência do prefixo e `not info.isfile()` cobrem. DENTRO dela, um arquivo
    que não é `.enc`, ou que é e não carrega o fingerprint (um selo que uma
    escrita deixou pela metade, um arquivo de outra origem), não sobe — é a
    mesma pergunta que `strongbox.fingerprinted` responde, e ela não abre o
    envelope, então nenhuma Chave entra aqui para fazer essa pergunta.
    """
    if not info.isfile() or not info.name.startswith(_strongbox_prefix()):
        return info
    full = paths.working_folder() / info.name.removeprefix("./")
    if full.suffix != strongbox.SUFFIX or not strongbox.fingerprinted(full):
        return None
    return info


def _named() -> str:
    """The archive's own name — a stamp, so two backups never collide by
    name alone when the destination is a bare directory."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"at-backup-{stamp}{SUFFIX}"


def _kind(destination: str) -> str:
    """Which of the three shapes `destination` is — read by syntax, and never
    by asking: the same door `rclone` and `scp` read their own arguments by."""
    if _SSH_SHAPE.match(destination):
        return SSH
    if _RCLONE_SHAPE.match(destination):
        return RCLONE
    return LOCAL


def _send(sealed: Path, destination: str, kind: str, tool: str | None) -> bool:
    """The one call that moves the sealed archive — the seam, and the only one.

    A local destination is a plain copy: a directory takes the archive's own
    name, and a named file takes exactly that name. The two remote shapes are
    one call each to the tool `make` already resolved, so nothing here has to
    know a second time whether it is there.
    """
    if kind == LOCAL:
        target = Path(destination)
        if target.is_dir():
            target = target / sealed.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sealed, target)
        return True
    assert tool is not None  # `make` resolved the tool before the key was ever asked
    args = [tool, "copyto", str(sealed), destination] if kind == RCLONE \
        else [tool, str(sealed), destination]
    return subprocess.run(  # noqa: S603 — the tool the destination named, resolved by `make`
        args, capture_output=True, text=True
    ).returncode == 0


def _fresh() -> bool:
    """Whether this folder has nothing yet that restoring over it would lose.

    The module docstring says which tables count and why; the two folders
    checked here are the ones no session fills on its own (`boot.py`), so a
    third file in either is a person's own — the welcome note `Arquivos/` is
    born with is the one file `_fresh` still allows.
    """
    if any(tables.rows(name, show_all=True) for name in FRESH_TABLES):
        return False
    if len(list(paths.prose_dir().iterdir())) > 1:
        return False
    if any(paths.projects_dir().iterdir()):
        return False
    if any(paths.shared_dir().iterdir()):
        return False
    return True
