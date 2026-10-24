"""The WebApp as a container (§7c): the artifact it runs and what it is told.
"""

from __future__ import annotations

import sys

from at.core import paths, strongbox
from at.services import caddy as caddy_service
from at.ui.webapp import keys as webapp_keys
from at_deploy.environment_base import GATE_ENV, GATE_MOUNT, IDENTITY, IDENTITY_PORT, WEBAPP, WEBAPP_HOST, WEBAPP_PORT
from at_deploy.environment_paths import container
from at_deploy.environment_secrets import _derived_b64


def binary() -> str:
    """The artifact the WebApp container runs — `at-cli`, the app's own (§7c).

    The binary IS the WebApp, so a container that ran another artifact would be a
    second product — and since item 27 that distinction is the whole point: what
    runs inside is `at-cli`, the artifact that keeps the folder and the app, and
    never `at-deploy`, which is the tool that put the container there.

    It is reached through the folder both of them see at the same path, and the
    artifact running is NOT the one being named: `at-deploy` is what brings the
    container up, and what goes inside it is `at-cli` (item 27). Frozen, the app
    sits beside the deploy at the folder's root, which is where §3 puts the
    binary and its Windows spelling. Run from a checkout, it is `dist/at-cli`,
    which is where `at-cli.spec` puts the artifact and which is inside the folder
    too — NOT `at/`, which is the package, and a directory is not something a
    container can execute. A folder that never built the artifact names a path
    that is not there, and that is honest: the switch is what notices, by proving
    the WebApp answers instead of believing this line.

    **The NAME comes from `paths.artifact_file()` and is not spelled here**, and
    that is the point of it being a name at all: the same pair — `.exe` on
    Windows, no extension on Linux and macOS — is what each spec writes (`at-cli.spec`,
    `at-deploy.spec`), and a container that guessed the spelling would be a
    container that never starts.
    """
    if getattr(sys, "frozen", False):
        return str(paths.working_folder() / paths.artifact_file())
    return str(paths.working_folder() / "dist" / paths.artifact_file())


def _webapp_command() -> tuple[str, ...]:
    """What §7c's container runs: the artifact, serving the WebApp on the network.

    The address is the container's own (`WEBAPP_HOST`) and it is the whole point
    of the command being written here: the app's default is the loop, and on the
    loop nobody inside the environment reaches it. The port is the WebApp's own
    default, and it is the one the Caddyfile proxies to — the two are the same
    number, and `test_environment` is what holds them together.
    """
    return (binary(), "webapp",
            "--port", str(WEBAPP_PORT), "--host", WEBAPP_HOST)


def _webapp_env(key: bytes | None) -> tuple[tuple[str, str], ...]:
    """What §7c's WebApp is TOLD: where its gate is, where its folder is, and —
    when this subida has the key — the derived keys it holds in memory.

    The gate, because a container cannot see the host's loop and the name is the
    environment's to say (`GATE_ENV`), **and the gate's FILE, because the one
    the WebApp would read by the folder is the folder's** (`GATE_MOUNT`, item
    50): the container gets the copy the `up` materialized, and the variable is
    how the `at-cli` inside it is told where that copy is — the same shape as
    the address above and for the same reason. And the FOLDER, which is the same
    lesson as the address and was measured the same way: run from a checkout, the
    artifact this container executes sits in `<folder>/dist/at-cli`, and an app
    that read its folder from where its binary is — the `install` rule, §3 —
    would take `<folder>/dist` for the person's folder, find no `App/`, and ask
    to confirm a new Working Folder that no terminal in a container can answer.
    It is a WebApp that never serves.

    **Frozen it lands right, and that is the worst kind of right**: the artifact
    sits at the folder's root, the inference agrees, and the defect waits for
    the first run from a checkout. `AT_ROOT` is the contract the image already
    declares in its own words (`Containerfile`), and naming it here costs one
    variable.

    **§4, item 50: os DOIS derived keys ride the same door, and only when
    there is a Main Key to derive them from.** `key` is `None` on a subida
    whose folder had nothing to open, draw or migrate this round (`unlock`) —
    a folder already entirely sealed does not get asked the Main Key again, so
    it does not get these variables either, and the WebApp inside it simply
    has no derived key this boot (`at.ui.webapp.keys.get`'s own contract).
    When there IS a key, it never travels itself — only `vault.derived_key`'s
    answer does, one scope at a time: the WebApp's own (`WEBAPP`), and the
    Vault's (TASK-154, `at.core.strongbox.SCOPE`), what
    `strongbox.Watcher.tick` seals a settled write in `Cofre/` with.
    """
    env = [
        (GATE_ENV, f"{container(IDENTITY)}:{IDENTITY_PORT}"),
        (paths.ROOT_ENV, str(paths.working_folder())),
        (caddy_service.GATE_PATH_ENV, GATE_MOUNT),
    ]
    if key is not None:
        env.append((webapp_keys.WEBAPP_KEY_ENV, _derived_b64(key, WEBAPP)))
        # TASK-154: a terceira porta para o que já existe — a mesma chave,
        # o escopo `cofre` (`at.core.strongbox.SCOPE` — o valor congelado
        # continua `"cofre"`), nenhum envelope resselado.
        env.append((webapp_keys.STRONGBOX_KEY_ENV, _derived_b64(key, strongbox.SCOPE)))
    return tuple(env)
