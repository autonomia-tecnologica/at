"""The display names of a permission, its object and its action.

Corte de `at.core.permissions` (a fachada); ver o docstring de lá.
"""

from __future__ import annotations

from at.core import tables
from at.data import schema
from at.i18n import tr


def label(permission: str) -> str:
    """The display name: a key of its own when one exists, and the object and the
    action composed when it does not.

    `tr` answers the key itself when the catalog lacks it, so an absent label is
    the signal to compose — the same way the engine falls back to the field's
    name.
    """
    key = f"permission.{permission.replace(':', '.')}"
    written = tr(key)
    if written != key:
        return written
    obj, _, action = permission.partition(":")
    return tr("permission.line", object=object_label(obj), action=action_label(action))


def object_label(name: str) -> str:
    """The word for the OBJECT of a permission — `Tarefas`, `Configurações`.

    A table is named the way every surface names it; anything else answers with
    its own key, and with the raw word when there is not even that. It is public
    because the screen that moves a role GROUPS the closed list by object, and a
    second reading of the same key would be the second home this module refuses.
    """
    if schema.of(name) is not None:
        return tables.table_name(name, many=True)
    key = f"permission.object.{name}"
    written = tr(key)
    return written if written != key else name


def action_key(name: str) -> str:
    """The i18n key of an action's display name — the engine's own block for the
    engine's six, and the catalogue's for the acts an object declares of itself
    (`run`, `approve`, `refuse`).

    It is public because the TREE needs the key and not the text (`Node.about` is
    an i18n key, never the sentence), and a surface that composed the key its own
    way would be the second home for the convention.
    """
    return f"table.action.{name}" if name in tables.ACTIONS else f"permission.action.{name}"


def action_label(name: str) -> str:
    """The word for the ACTION of a permission — `Ler`, `Criar`."""
    key = action_key(name)
    written = tr(key)
    return written if written != key else name
