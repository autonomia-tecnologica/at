"""The Working Folder, and the paths that live inside it.

The rule comes from §3 (Código e delivery): the folder the binary was opened in
is the binary's folder, and that folder is the Working Folder.

**The name on disk is the face; the machine reads the internal name.** `app`,
`data`, `prose`, `projects`, `shared` and `harness` are the product's words — the
engine branches on them and on nothing a person says. What a person reads is the
localized name, and it is a DECLARATION of the table below, never an `if` in the
code that acts: the same rule that makes a table's id `task` while the name on
screen comes from `i18n`.

A folder that refused a rename keeps the name it had, so the resolution accepts
every name the product has ever given it — the active language's first, then the
other language's, then the retired faces, and the internal name itself last.
Without that, declining a rename would break AT instead of leaving the cost with
whoever declined.

`AT_ROOT` overrides the resolution so a test — or a developer running
`python3 -m at` from the checkout — can aim the engine somewhere else without
moving anything. It is the only environment variable that decides where AT
writes; nothing here creates a directory. Creation belongs to `boot`, which asks
first.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_ENV = "AT_ROOT"

# Every internal name, and the folder it is spelled with in each language. One
# home: a name that is added here gains its resolution, its birth and its
# migration at once, and no surface has to learn it.
NAMES: dict[str, dict[str, str]] = {
    "app": {"pt_BR": "App", "en_US": "App"},
    "data": {"pt_BR": "Tabelas", "en_US": "Tables"},
    "prose": {"pt_BR": "Biblioteca", "en_US": "Library"},
    "projects": {"pt_BR": "Projetos", "en_US": "Projects"},
    "shared": {"pt_BR": "Compartilhado", "en_US": "Shared"},
    # A pasta que sela sozinha (TASK-154) — irmã de `prose`, e não dentro dela:
    # o que entra aqui não é material solto, é o que a pessoa quer cifrado.
    # O nome interno é `strongbox` e não `cofre`: a palavra em português só
    # sobrevive onde ela JÁ é dado, não identificador — o escopo da chave
    # derivada (`at.core.strongbox.SCOPE`) e o fingerprint do `.enc`, os dois
    # congelados porque já há arquivo selado com eles no disco de verdade.
    "strongbox": {"pt_BR": "Cofre", "en_US": "Vault"},
    # Onde o `at/convert/` pousa o que gerou (TASK-165) — irmã de `prose` pela
    # mesma razão do Cofre: o que está aqui não é o material de origem, é o
    # produto de uma conversão, e não se mistura com `Biblioteca/`.
    "convert": {"pt_BR": "Convertidos", "en_US": "Converted"},
    # The one whose name is the same word in both languages, like `App/`: a
    # person looking for what an agent loads looks for `harness` in either, and
    # pt_BR took the word whole. It is declared here rather than spelled in the
    # code, which is what keeps the engine branching on the internal name.
    "harness": {"pt_BR": "Harness", "en_US": "Harness"},
}

# The faces a folder has carried BEFORE the one it carries today, by language,
# and in the order they were declared. One home, like `NAMES`: each rename that
# takes a folder from here to there has its own migration (31 for `prose`, 36
# for `shared`), and the resolution reads this table so a folder that still
# carries a retired spelling is still found.
#
# The resolution accepting it is the promise the module's docstring makes: a
# person who declined a rename — or a folder that has not migrated yet — cannot
# see their material disappear because the name on disk is no longer the one the
# product writes today. Declining a rename costs a name that disagrees with the
# screen, never the files.
FORMER: dict[str, dict[str, str]] = {
    "prose": {"pt_BR": "Arquivos", "en_US": "Files"},
    "shared": {"pt_BR": "Compartilhada"},
}

# The instance folder, and it is NOT localized — deliberately. The language
# itself is recorded inside it (`i18n/active`), so a name that moved with the
# language would be a folder the resolution could not find before it knew the
# language. `App/` is the same word in both, which is what makes that possible.
INSTANCE = "App"

# What the instance folder was called before, newest first. `boot` and the first
# migration read this list: a folder that carries one of these and no `App/` is
# a folder that has not migrated, never a folder that is new.
LEGACY_INSTANCE = (".bill", "app")

# The note whoever starts inside the folder reads (§0, item 25). NOT localized,
# and that is the point: it presents the folder to whoever works in it, and both
# a person and a model look for it by that name — exactly the way `README.md`
# keeps its spelling in every language. The TEXT is translated; the name is not.
ROOT_NOTE = "README.md"

# The name the note carried before `README.md` (B-56). A published migration is
# never edited, so migration 4 still writes the note under this retired name and
# migration 33 removes it; the live code only knows `ROOT_NOTE`.
AGENT_NOTE = "AGENT.md"

# The two artifacts, and the file each one is on each platform (§3, items 28
# and 29). `.app` was refused on purpose: on the Mac it is a BUNDLE, a folder,
# and the product promises ONE file. The rule is one and it covers both
# artifacts — the app and the deploy —, and it is a rule of the FILE: `.exe` on
# Windows, and NO extension on Linux and macOS, where the file's name is the
# command a person types.
#
# **The app's is `at-cli` and not `at`** (item 28). `at` is a command a UNIX
# machine may already answer to — the `at`/`atd` job scheduler, one package away
# and present in this distribution's own repositories — and the product does not
# take a name that is not only its own. The brand is AT; the word the machine
# answers to is one the machine did not already have. The deploy's name was free
# from the start, which is why only the app's carries the suffix.
#
# It is declared here because the name is what the product EXECUTES and not only
# what it publishes: §7c's WebApp container runs this very file, by this very
# name, through the folder the container mounts (`at_deploy/environment.py`).
# The two specs write the same pair — a spec runs before the package is
# importable, so it spells the names itself — and `at/tests/test_lifecycle.py`
# holds the three to each other, because a build that named another file would
# be a container that never starts.
ARTIFACT = "at-cli"
DEPLOY = "at-deploy"
WINDOWS = ".exe"
UNIX = ""


def artifact_file() -> str:
    """The app's file on this platform — `at-cli`, or `at-cli.exe` on Windows."""
    return ARTIFACT + _extension()


def deploy_file() -> str:
    """The deploy's file on this platform — `at-deploy`, or `at-deploy.exe`."""
    return DEPLOY + _extension()


def _extension() -> str:
    """The platform's answer, which on Linux and macOS is an empty one.

    A name and not a convenience: the two constants above ARE the rule, and this
    is the one place that reads the platform to choose between them. An
    extensionless file is executable because of its mode, and it is what keeps
    the file's name and the command's name the same word on those two platforms.
    """
    return WINDOWS if sys.platform == "win32" else UNIX


def source() -> bool:
    """Whether this run is the CHECKOUT and not the bundle.

    The one place that asks, and the three that read it ask for reasons of their
    own: `working_folder` asks whose folder this is, and the WebApp asks whether
    to expose the Forms (`ui/webapp/app.py`) — a run from the source tree serves
    whoever is testing it, and it serves them without an entrance.

    **It is the ARTIFACT that answers, and nothing else does.** No flag and no
    environment variable turns the entrance off, because both of them travel:
    one typed on the row of a shortcut, one exported in front of a process, and
    the release would carry the switch that closes its own door. What the bundle
    IS cannot be typed by accident.
    """
    return not getattr(sys, "frozen", False)


def working_folder() -> Path:
    """Where AT is running. Resolved fresh on every call, never cached."""
    override = os.environ.get(ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()
    if not source():
        # Packaged as the single binary: the binary IS the folder's owner, so
        # the folder is wherever the binary sits — not where it was called from.
        return Path(sys.executable).resolve().parent
    # Running from source: the checkout is the Working Folder.
    return Path.cwd().resolve()


def candidates(internal: str) -> tuple[str, ...]:
    """Every name the folder may carry, in the order the resolution tries.

    The active language's face first, then the other language's, then the faces
    this folder has carried before (`FORMER`), and the internal name last. A
    folder that declined the rename of a former face — or that has not migrated
    yet — is still the folder it names, and that is why every face is tried.
    """
    names = NAMES[internal]
    active = active_language()
    ordered = [names[active]] if active in names else []
    ordered += [name for code, name in sorted(names.items()) if code != active]
    for name in FORMER.get(internal, {}).values():
        if name not in ordered:
            ordered.append(name)
    if internal not in ordered:
        # The internal name itself, last: a folder hand-created under it, or one
        # born before this table existed, is still the folder it names.
        ordered.append(internal)
    return tuple(ordered)


def current_candidates(internal: str) -> tuple[str, ...]:
    """The names the folder is CURRENTLY spelled with — no retired face.

    The active language's name first, then the other language's, then the
    internal name. It is what `_moves` reads: a retired face is its own
    migration's subject, and offering its rename here as well would ask the
    same question twice — that migration does it without asking, so the second
    question would sometimes be answered "no" against a move that happens
    anyway.

    The internal name stays because a folder born under it is still a folder the
    language rename has to bring forward, and it is not a retired face.
    """
    names = NAMES[internal]
    active = active_language()
    ordered = [names[active]] if active in names else []
    ordered += [name for code, name in sorted(names.items()) if code != active]
    if internal not in ordered:
        ordered.append(internal)
    return tuple(ordered)


# The internal names the map of functions (`at.core.functions`) answers for, and
# the function each one is. The others — `app`, `data`, `projects`, `shared` and
# `convert` — are the fixed base structure and never ask the map.
MAPPED: dict[str, str] = {
    "prose": "library",
    "strongbox": "strongbox",
    "harness": "harness",
}


def mapped(internal: str, existing: bool = True) -> list[Path]:
    """The folders the map binds the internal name to, or `[]` for "no answer".

    A row only counts for the folders that EXIST: a row pointing at a folder
    that is not there answers nothing, and the resolution falls back to
    `NAMES`/`FORMER`. `existing=False` is for whoever creates the folders (`boot`).
    No row, no folders, or an internal name outside the map answer nothing too.
    A disabled row still answers: switching a function off preserves its data.
    """
    function = MAPPED.get(internal)
    if function is None:
        return []
    from at.core import functions

    found = functions.resolved(function)
    return [path for path in found if path.is_dir()] if existing else found


def folders(internal: str) -> list[Path]:
    """Every folder of the internal name: the map's, else the single `folder`."""
    return mapped(internal) or [folder(internal)]


def folder(internal: str) -> Path:
    """The folder the internal name points at, as this folder spells it.

    The map of functions wins when it has a row with folders for the name (the
    first one, for a function with several). Otherwise the first name that
    EXISTS wins, so a folder that declined a rename answers under the name it
    kept. When none exists the active language's name is returned — that is
    where a folder about to be born is written.
    """
    bound = mapped(internal)
    if bound:
        return bound[0]
    root = working_folder()
    for name in candidates(internal):
        if (root / name).is_dir():
            return root / name
    return root / NAMES[internal][active_language()]


def instance_dir() -> Path:
    """The folder the instance's own state lives in — `App/`.

    Resolved by what is ON DISK and never by the active language, because the
    language lives inside it. A folder carrying a legacy name is the SAME
    instance, and finding it is what lets the first migration run at all: a
    folder with `.bill/` on disk must read as a folder that has not migrated,
    never as a folder that is new.
    """
    root = working_folder()
    if (root / INSTANCE).is_dir():
        return root / INSTANCE
    for name in LEGACY_INSTANCE:
        if (root / name).is_dir():
            return root / name
    return root / INSTANCE


def app_dir() -> Path:
    """The instance folder — `App/` (§4). The internal name is `app`."""
    return instance_dir()


def settings_file() -> Path:
    """`App/settings.json` — the presence of this file is what makes a folder
    a Working Folder, so `boot` asks whenever it is missing."""
    return app_dir() / "settings.json"


def root_note() -> Path:
    """`README.md`, at the folder's root — where such a reader looks first.

    It is the folder presenting itself: written once, by AT, and never brought
    back after the person deletes it. Not inside `Biblioteca/`: that folder is
    the person's material. The name does not follow the language.
    """
    return working_folder() / ROOT_NOTE


def agent_note() -> Path:
    """`AGENT.md`, at the folder's root — the note's RETIRED name.

    Only the published migration 4 still writes it; migration 33 removes it.
    Migration 4 is never edited, so this accessor stays for it alone.
    """
    return working_folder() / AGENT_NOTE


def i18n_dir() -> Path:
    return app_dir() / "i18n"


def services_dir() -> Path:
    """`App/services/` — where EVERY service's state lives (§7), both paths.

    Inside `App/` and not a folder of its own at the root: it is what AT
    wrote to run, like the Caddy it unpacks and the language it chose, and §7
    puts every service's persistent state under it — `App/services/<serviço>`,
    so a service that does not fit its state here is a service that does not
    enter. The name does not move with the language for the same reason `App/`
    does not: what a person opens is `App/`, and the services inside it are the
    machine's words.

    **This was the CONTAINER path's alone, and it is the HOSTED path's now too.**
    The hosted path used to scatter its services across the root of `App/` —
    `App/caddy/`, `App/authelia/`, `App/push/`, `App/gitleaks/` and
    `App/jev-cache.json` — and the two paths answered to two houses for the same
    services. The Caddy made the collision plain: `caddy.directory()` (hosted) and
    `environment.state("caddy")` (container) were two folders for one service, and
    the gate file they SHARE already forced them to meet. A service lives here
    now — `<serviço>` is the same word in either path —, and the root of `App/`
    keeps only what is not a service (the settings, the counters, the install
    record, the migration stamp, the language).
    """
    return app_dir() / "services"


def service_dir(name: str) -> Path:
    """`App/services/<serviço>/` — one service's own state, whichever path runs it.

    The one place that spells the join, so a module that carries a service never
    resolves a path of its own (§4: no surface resolves a path beyond `core`).
    `name` is the machine's internal name for the service and not a word on
    screen, exactly like every other internal name here.
    """
    return services_dir() / name


def active_language_file() -> Path:
    """`App/i18n/active` — the only translation artifact the folder keeps
    (§4): the catalogs themselves are packed into the binary."""
    return i18n_dir() / "active"


def data_dir() -> Path:
    """`Tabelas/` — the tables, as `.jsonl`, and their schemas under `schema/`."""
    return folder("data")


def prose_dir() -> Path:
    """`Biblioteca/` — every file that is not structured data (§4)."""
    return folder("prose")


def prose_dirs() -> list[Path]:
    """Every root of the library, in the map's order (one when there is no map)."""
    return folders("prose")


def projects_dir() -> Path:
    """`Projetos/` — what belongs to a project, under that project's name."""
    return folder("projects")


def shared_dir() -> Path:
    """`Compartilhado/` — the files shared with other people. Named here, and
    treated later: the transport, and what this does to the backup promise, are
    the session that comes after (§3)."""
    return folder("shared")


def strongbox_dir() -> Path:
    """`Cofre/` — the folder that seals on its own (TASK-152, TASK-154).

    A sibling of `Biblioteca/` and not a folder inside it: what a person drops
    here is not loose material, it is asking to be ciphered — the vigia watches
    it and the Cofre's own consumer is the one that answers.
    """
    return folder("strongbox")


def convert_dir() -> Path:
    """`Convertidos/` — what `at/convert/` produced (TASK-165).

    A sibling of `Biblioteca/`, for the same reason `Cofre/` is one: a converted
    DOCX or PDF is not source material, it is the OUTPUT of a conversion, and
    mixing it into `Biblioteca/` would make the tree it walks list its own
    output back at it.
    """
    return folder("convert")


def harness_dir() -> Path:
    """`Harness/` — where what the agent loads lives (§2, item 25).

    Nobody's material and not AT's own state: it is what governs whoever works
    in the folder — the skill that writes into a project's vault, the rule that
    belongs to a project — beside the note that presents the folder, which sits
    at the root because that is where such a reader looks first. AT guarantees
    the place and writes nothing in it: it is born named and empty, like
    `Projetos/` and `Compartilhado/`.
    """
    return folder("harness")


def active_language() -> str:
    """The active code — resolved by `i18n`, imported here to keep `paths` the
    only layer that knows a folder has a name at all."""
    from at import i18n

    return i18n.active_code()
