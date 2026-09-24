"""`settings.json` — the instance's key-value configuration (§4).

It lives in the instance folder, whose internal name is `app` and whose face is
`App/` (`paths.instance_dir` resolves it). Deliberately not the home of the
active language: that lives in `i18n/active`, beside it, because the catalogs
are packed into the binary and only the choice is the folder's. This file
carries what is neither translation nor table.

**This module is the DOOR.** §4 makes the settings reachable through the core
API — `setting:read` and `setting:edit` are permissions — and the door is here:
`keys` says which keys the folder hands over, `get` is the one read, `put` is the
one write, and `literal` is what a value a person typed becomes. **No surface
composes this path or touches the JSON**: the read goes through `get` and the
write through `put`, and a surface that opened the file itself would be a second
reader of a shape that has one home.

**The core reads the same `get`, and that is not a hole in the door.** A setting
is what the core reads of itself — `risk` its bar, `gate` its authenticator,
`migrations` its decisions, `nlu` its switch — and those four ARE the core: the
door is not a wall it is held behind, and wrapping each of those reads in a
function of its own would be a second name for the same one. What the door is FOR
is the other side: a surface, which has neither the shape of the file nor the
right to move the keys AT writes.

**The act is the WRITE, and the line is written where the actor is known.** §3
makes a read not an act, so `keys` and a read of one key leave nothing at all;
a setting that changes is an act like any other, and its line is born at the
door the surfaces reach (`at.ui.ask`), which is where the actor and the via
exist. Nothing is written here that would be a line without them.

**The numbers a key carries are §4's per-argument declaration.** The risk of a
demand is the highest among the action and the arguments it carries, and the
settings are not a table — there is no declaration file for a key's number to
live in, so it lives here, beside the key (`RAISED`).
"""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from at.core import files, paths
from at.i18n import tr

# The shape version. It exists so a later release can migrate a folder instead
# of guessing at it — the first run after an update is when structure changes
# are applied (§3).
SCHEMA = 1

# The keys the product READS, in the order the door hands them over. A key the
# folder carries and this tuple does not name is still shown — the file is the
# person's — and it comes after these, by name.
#
# Being known is not being adjustable: `schema` and `folders` are AT's own
# record of a shape and of a decision (the first run, and the language rename),
# and the door shows them because a folder that hides what it wrote would be a
# folder with a secret.
KNOWN = (
    "interpreter",
    "basic_auth",
    "risk_threshold",
    "authenticator",
    "folders",
    "schema",
)

# The keys AT OWNS rather than the person, and the one write the door refuses
# because of it: the shape version is what a migration reads to know how far
# this folder has come, and a hand moving it would be the folder lying about its
# own shape — the next update would skip the catch-up this stamp exists for.
RESERVED = ("schema",)

# The number each key RAISES a demand to when it is EDITED (§4, item 15). The
# settings are not a table and have no schema to declare it in, so it is
# declared here, beside the keys it belongs to — and `risk_threshold` is the one
# §4 names: whichever demand moves the bar is priced for it, because whoever can
# lower the wall learns where it is.
RAISED = {"risk_threshold": 0.95}


def exists() -> bool:
    return paths.settings_file().is_file()


def load() -> dict[str, Any]:
    """The settings as they are on disk; `{}` for a folder not yet configured.

    A corrupt file is reported, never silently replaced: rewriting it would
    destroy whatever a person had put there.
    """
    try:
        text = paths.settings_file().read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        settings = json.loads(text)
    except JSONDecodeError as error:
        raise SettingsError(f"{paths.settings_file()}: {error}") from error
    if not isinstance(settings, dict):
        raise SettingsError(f"{paths.settings_file()}: not a JSON object")
    return settings


def save(settings: dict[str, Any]) -> None:
    text = json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    files.atomic_write_text(paths.settings_file(), text)


def get(key: str, default: Any = None) -> Any:
    """The value on disk, or `default` — the read the CORE does of its own file.

    It answers the STORED value and never an invented one: what a key means when
    the folder never chose is each reader's, and they already answer it (`nlu`
    its switch, `gate` its authenticator, `risk` its bar). A door that decided
    here would be a second home for the same answer.
    """
    return load().get(key, default)


# ---------------------------------------------------------------- the door ---


def keys() -> list[str]:
    """Every key the door hands over: the ones the product reads, and then the
    ones this folder carries that no reader named, by name.

    The known ones come first so the list has a stable order and a person sees
    the adjustments before the records — and a key the product does not read is
    shown all the same, because the file is the person's and a door that hid
    half of it would be the door lying.
    """
    carried = load()
    return [*KNOWN, *sorted(key for key in carried if key not in KNOWN)]


def put(key: str, value: Any) -> str:
    """Write one key — the door's write, and the whole of what it refuses.

    A key is a NAME: an empty one, or one that is not a string at all, names
    nothing and is refused before the file is touched. And a key AT owns is
    refused by name (`RESERVED`), because some of what this file carries is not
    an adjustment of the person's.

    The write is the whole file, merged: `save` is the one writer, and it keeps
    every other key exactly as it was.
    """
    name = key.strip() if isinstance(key, str) else ""
    if not name:
        raise Refused("setting.error.key")
    if name in RESERVED:
        raise Refused("setting.error.reserved", setting=name)
    save({**load(), name: value})
    return name


def literal(text: str) -> Any:
    """The VALUE a person typed: JSON when it parses, the text when it does not.

    §4's settings are key-value properties, and the values are the ones JSON
    writes — `0.95` is the float the filter compares against, `true` turns a
    permission on, and `forms` is a word. Reading all three as text would make
    the bar a string and the switch a word nothing answers.

    The three JSON literals are forgiven their case, and only they: a person
    types `True` as easily as `true`, while the words that are VALUES — `forms`,
    `gate` — are read exactly as they were written, because two words that
    differ in a letter are two words.
    """
    body = text.strip()
    if body.lower() in ("true", "false", "null"):
        body = body.lower()
    try:
        return json.loads(body)
    except JSONDecodeError:
        return text


def raised(key: str) -> Any:
    """The number this key raises a demand to, or `None` when it declares none.

    A key nobody raised is not an error: it makes the demand no dearer than the
    action already does, and the floor is the absence of a number and not a zero
    written here.
    """
    return RAISED.get(key)


class SettingsError(Exception):
    """The settings file exists but cannot be read as one."""


class Refused(Exception):
    """The door refused the write, by the key of the sentence that says why.

    The message is already in the active language, like the engine's
    (`tables.TableError`), so every surface prints it as it stands. It is not a
    `SettingsError`: that one is a file nobody can read, and this one is a file
    that is fine and a write that is not — a caller that swallows the first has
    no business swallowing the second.
    """

    def __init__(self, key: str, **kw: object) -> None:
        self.key = key
        self.kw = kw
        super().__init__(tr(key, **kw))
