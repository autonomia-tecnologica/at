"""The frontier between the two artifacts, as a property of the import graph.

Item 27 splits the product in two, and the promise the split is FOR is readable
off the artifact: `at-cli` is architected to run without administration
permissions, and §3's closed list of elevations names `at-deploy` as the one
that asks. That promise is worth nothing if it is a convention — so it is
affirmed here, from the SOURCE, by the two questions that make it true:

1. **`at` names nothing of the deploy.** Not one import statement under
   `at/` reaches `at_deploy`, which is what makes an `at-cli` built by
   PyInstaller carry no line of §7: the collector follows the imports, and there
   is nothing to follow.
2. **No elevation survives in `at`.** The word `sudo`, the function that
   spends it and the file that decides the low-port rule are gone from the
   package — not moved behind a flag, not left as a dead branch.

And the other direction, which is the point of the shared core: the deploy reads
`at`'s (`paths`, `i18n`, `files`, the table engine), so there is one source and
not two. Nothing here is a substitute for the build — the specs are what assemble
the files — but a build cannot notice that a boundary was crossed in a comment or
a lazy import, and this can.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

# Both packages, from the repository root. This file lives two levels down.
ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "at"
DEPLOY = ROOT / "at_deploy"

# What `at` keeps of what used to be §7's package, and neither is the
# environment's. The Caddy the BINARY carries is the HOSTED path's TLS — the
# environment's Caddy is a container of the deploy's manifest — and the
# `gitleaks` is the scanner `secret scan` walks the folder with (item 32).
# **`authelia` joined them on 02/10/2026 (TASK-177)**: the bundle's own gate,
# vendorized and run as a subprocess of `at-cli` itself, exactly the Caddy's own
# arithmetic — and still no container, no orchestration, no elevation, which is
# the whole of what keeps it on this side of the boundary and not the deploy's.
# Every one of the four is a third party the artifact embeds, which is §3's way
# of pinning a package.
KEPT = {"authelia", "caddy", "caddy_base", "caddy_file", "caddy_gate", "gitleaks", "spelling_checker"}


def sources(package: Path) -> list[Path]:
    """Every module of that package. Not `__pycache__`, and not its tests."""
    return sorted(
        path for path in package.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
    )


def imported(text: str) -> set[str]:
    """Every module an import statement in that source names.

    Parsed and not searched for: the point of this gate is that an import is a
    FACT of the code, and a comment that mentions `at_deploy` is not one.
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


class TheAppCannotAsk(unittest.TestCase):
    """§3 (Privilege), item 27: the elevation MOVED, and it does not come back."""

    def test_at_names_nothing_of_the_deploy(self):
        for path in sources(APP):
            with self.subTest(module=path.relative_to(ROOT)):
                for name in imported(path.read_text(encoding="utf-8")):
                    self.assertFalse(
                        name == "at_deploy" or name.startswith("at_deploy."),
                        f"{path.relative_to(ROOT)} imports `{name}`; the two "
                        f"artifacts share the FOLDER's state and not an API, and "
                        f"`at-cli` must not be able to reach §7 — the import graph "
                        f"is what keeps the elevation out of the artifact",
                    )

    def test_no_elevation_survives_in_at(self):
        # The words and not the shape: the closed list, the sysctl that moves the
        # floor, the spend. A dead branch left behind would still be a code path
        # that asks, and the artifact's promise is that there is none.
        for path in sources(APP):
            text = path.read_text(encoding="utf-8")
            with self.subTest(module=path.relative_to(ROOT)):
                for word in ("sudo", "spend_elevation", "ip_unprivileged_port_start"):
                    self.assertNotIn(
                        word, text,
                        f"{path.relative_to(ROOT)} still names `{word}`; §3's "
                        f"elevation is `at-deploy`'s and only its own",
                    )

    def test_the_environment_left_the_binary_whole(self):
        # `at/services/` is what survives of the package §7 used to be, and it
        # is two files — the hosted Caddy and the scanner —, neither of them the
        # environment's. Every other module of §7 — the runtime, the VPN, the
        # orchestration, the switch — is the deploy's.
        left = {path.stem for path in sources(APP / "services") if path.stem != "__init__"}
        self.assertEqual(left, KEPT)


class TheCoreIsOneSource(unittest.TestCase):
    """The deploy reads the app's core, and never a copy of it."""

    def test_the_deploy_imports_the_shared_core(self):
        # The direction, said positively: `at.core`, `at.i18n` and
        # `at.data` are what the deploy builds on, and it names no module of
        # its own for them.
        text = "\n".join(path.read_text(encoding="utf-8") for path in sources(DEPLOY))
        for module in ("at.core", "at.i18n"):
            with self.subTest(module=module):
                self.assertIn(f"from {module} import", text)

    def test_the_deploy_carries_the_ten_modules_of_two_subjects(self):
        # A list, so that a module added here is a decision somebody makes on
        # purpose: the deploy is §7, and everything it owns is named. `wizard`
        # is the front §6 declares for this artifact — the sequence of §7 walked
        # over the words the `cli` already has (item 27's third slice). `trust`
        # left this list in TASK-187: it was the CA in the browser's NSS, the
        # other half of a name (`cert.at.local`) the environment no longer
        # answers for. And `notifier` left it with the ntfy: a notificação é o
        # Web Push do PWA (`at/core/push.py`), que roda dentro do WebApp e não
        # precisa de um container de entrega. `host` and `systemd` arrived
        # with TASK-190: the hosted path's own environment, and the seam its
        # one runtime (`systemctl --user`) goes through — the same pair of
        # roles `environment` and `podman` already play for the container one.
        self.assertEqual(
            {path.stem for path in sources(DEPLOY) if path.stem != "__init__"},
            {"cli", "tree", "__main__", "environment", "podman", "vpn",
             "switch", "wizard", "host", "systemd",
             "environment_base", "environment_paths", "environment_models",
             "environment_pins", "environment_secrets", "environment_edge",
             "environment_identity", "environment_webapp", "environment_run",
             "environment_probe"},
        )


class TheTwoTreesDoNotMix(unittest.TestCase):
    """§5's one-way rule holds inside each artifact, and the words do not leak."""

    def test_the_environment_words_are_the_deploys_alone(self):
        from at.ui.cli import tree as app_tree
        from at_deploy import tree as deploy_tree

        for word in deploy_tree.environment_words():
            with self.subTest(word=word):
                self.assertIsNone(
                    next((node for node in app_tree.WORDS if node.name == word), None),
                    f"`at-cli` offers `{word}`; the environment is `at-deploy`'s",
                )
                self.assertIsNotNone(deploy_tree.find(word))

    def test_the_deploys_help_is_drawn_in_both_languages(self):
        # The commands are machine words and stay machine words (§3); what is
        # translated is every sentence around them.
        from at import i18n
        from at_deploy import tree as deploy_tree

        for code in i18n.SUPPORTED:
            for node in deploy_tree.roots():
                with self.subTest(key=node.about, language=code):
                    self.assertNotEqual(i18n.text(node.about, code), node.about)


if __name__ == "__main__":
    unittest.main()
