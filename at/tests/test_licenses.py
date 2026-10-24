"""The licences: what the artifacts carry from outside, and what proves it (§3).

The rule is one bullet of §3: a third party only travels inside an artifact if
its licence permits, and whatever the licence demands travels WITH it. The
artifact is a single file, so there is no folder beside it for a notice to sit
in — the notices ride inside and come out through the `license` word. This module
is the gate over that promise, and it is the only place the declaration
(`at/vendor/licenses/manifest.json`) is held to what the tree actually has:

1. **the text proves the identifier.** A declaration that says `Apache-2.0` over
   a file that is not the Apache licence is a lie with a clean audit trail, so
   each declared pair has to agree — and a licence nobody has stated a proof for
   fails here rather than passing quietly;
2. **the artifact carries what it declares, and the specs collect it.** The
   declared texts have to fall under a directory the artifact's build actually
   gathers, or the word answers nothing on the machine of whoever downloaded it;
3. **the two artifacts declare different sets.** The `at-deploy` carries no
   typeface, no Vue bundle and no Caddy, and it may not claim them;
4. **the texts that are copies are held equal to their source** — the Caddy's and
   the gitleaks', each of which also travels inside its vendor's own tarball —,
   so no copy can drift apart from what it copies;
5. **the word answers.** The product's own MIT, every component of THIS artifact,
   and the vendors' texts only when they are asked for.

The typefaces are declared where the WebApp's own vendor manifest pins them, and
the two lists are held one-to-one here, because a font whose licence stopped
travelling with it would be a font the artifact serves without its terms.
"""

from __future__ import annotations

import io
import json
import os
import re
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from at import i18n
from at.core import boot, licenses, paths
from at.services import caddy, gitleaks
from at.ui.cli import main as cli_main
from at_deploy.cli import main as deploy_main

ROOT = Path(__file__).resolve().parents[2]

# The files whose DATAS say what each build gathers, and the two artifacts.
SPECS = {
    paths.ARTIFACT: ROOT / "at-cli.spec",
    paths.DEPLOY: ROOT / "at-deploy.spec",
}

# The WebApp's vendor manifest, where the typefaces are pinned, and the folder
# beside it that carries their licences.
VENDOR = ROOT / "at" / "ui" / "webapp" / "vendor"

# What each `SPDX` identifier has to LOOK like in the text that claims it. The
# point is not to parse a licence — no machine does that well — but to refuse the
# one mistake that would otherwise pass: an identifier written over somebody
# else's file. Every identifier the declaration may use is here, and a component
# declaring one that is not fails the suite and makes its author state the proof.
PROOFS = {
    "Apache-2.0": "Apache License",
    "GPL-2.0-or-later WITH Bootloader-exception":
        "SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)",
    "GPL-2.0-only WITH Classpath-exception-2.0": '"CLASSPATH" EXCEPTION TO THE GPL',
    "ISC": "Permission to use, copy, modify",
    "LGPL-2.1-or-later": "GNU LESSER GENERAL PUBLIC LICENSE",
    "MIT": "Permission is hereby granted",
    "MIT-0": "MIT No Attribution",
    "OFL-1.1": "SIL OPEN FONT LICENSE",
    "PSF-2.0": "Python Software Foundation",
}

# The `(source, destination)` pairs of a spec's DATAS, which is where a payload
# is said to travel. Read as text for the reason `test_caddy` reads it that way:
# a spec is not importable — it runs against `SPECPATH` — and what is being
# checked is the declaration of what the build gathers, which is a literal.
DATAS = re.compile(r'\("([^"]+)", "([^"]+)"\)')


class TheDeclaration(unittest.TestCase):
    """Every entry, held to the file it points at."""

    def components(self) -> tuple[licenses.Component, ...]:
        return licenses._entries()

    def test_the_declaration_travels_and_says_something(self):
        found = self.components()
        self.assertTrue(
            found,
            "no declaration under at/vendor/licenses — the build collects that "
            "folder, and an empty one is collected as nothing, which would leave "
            "the artifacts carrying third parties with no terms at all",
        )

    def test_every_component_names_what_it_is(self):
        for component in self.components():
            with self.subTest(component=component.key):
                self.assertTrue(component.name)
                self.assertTrue(component.license)
                self.assertTrue(component.text)
                self.assertTrue(component.artifacts)

    def test_the_artifacts_it_names_are_the_artifacts_there_are(self):
        # A renamed artifact would otherwise orphan a declaration that nobody
        # reads any more — the word would answer for a name no build has.
        known = {paths.ARTIFACT, paths.DEPLOY}
        for component in self.components():
            with self.subTest(component=component.key):
                self.assertLessEqual(set(component.artifacts), known)

    def test_the_text_exists_where_the_declaration_says(self):
        for component in self.components():
            with self.subTest(component=component.key):
                self.assertTrue(
                    (ROOT / component.text).is_file(),
                    f"{component.text} is declared and is not there",
                )

    def test_the_text_proves_the_identifier_it_claims(self):
        for component in self.components():
            with self.subTest(component=component.key):
                proof = PROOFS.get(component.license)
                self.assertIsNotNone(
                    proof,
                    f"{component.license} has no stated proof — add it to PROOFS "
                    f"with the words the vendor's own text carries",
                )
                body = (ROOT / component.text).read_text(encoding="utf-8")
                self.assertIn(proof, body)


class TheArtifacts(unittest.TestCase):
    """What each build gathers, and that it gathers what is declared."""

    def components(self) -> tuple[licenses.Component, ...]:
        return licenses._entries()

    def gathered(self, artifact: str) -> tuple[str, ...]:
        """The source paths the artifact's DATAS collects."""
        return tuple(
            source
            for source, _ in DATAS.findall(SPECS[artifact].read_text(encoding="utf-8"))
        )

    def test_each_artifact_collects_every_text_it_declares(self):
        for artifact in SPECS:
            gathered = self.gathered(artifact)
            with self.subTest(artifact=artifact):
                self.assertIn("at/vendor/licenses", gathered)
                self.assertIn("LICENSE.md", gathered)
                for component in licenses.declared(artifact):
                    self.assertTrue(
                        any(
                            component.text == source
                            or component.text.startswith(source + "/")
                            for source in gathered
                        ),
                        f"{artifact} declares {component.key} and its build does "
                        f"not gather {component.text}",
                    )

    def test_the_deploy_declares_what_the_app_does_not(self):
        # The two lists are not the same list, and the difference is the app's:
        # the typefaces, the Vue bundle and the two programs the app embeds — the
        # Caddy and the `gitleaks` — travel in `at-cli` only.
        app = {component.key for component in licenses.declared(paths.ARTIFACT)}
        deploy = {component.key for component in licenses.declared(paths.DEPLOY)}
        self.assertTrue(deploy < app, "the deploy's list is the shorter one")
        self.assertIn("caddy", app - deploy)
        self.assertIn("gitleaks", app - deploy)
        self.assertIn("vue", app - deploy)
        self.assertTrue({key for key in app - deploy if key.startswith("font-")})

    def test_the_declared_typefaces_are_the_pinned_ones(self):
        # The vendor manifest pins what the WebApp HOSTS; the declaration says
        # what its licence is. One-to-one, or a font is served without its terms.
        manifest = json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))
        pinned = {
            said["package"].removeprefix("@fontsource/")
            for key, said in manifest["files"].items()
            if key.startswith("font-")
        }
        declared = {
            component.text.removesuffix("-LICENSE").rsplit("/", 1)[-1]
            for component in licenses.declared(paths.ARTIFACT)
            if component.key.startswith("font-")
        }
        self.assertEqual(pinned, declared)

    def test_a_hosted_dependency_and_its_licence_agree_on_the_version(self):
        # The renderer is pinned in the WebApp's own vendor manifest — the sha256
        # travels THERE — and declared here, where the terms travel. The two ends
        # are one version: a bump on one side alone would serve a file whose
        # licence names another.
        manifest = json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))
        declared = {
            component.key: component
            for component in licenses.declared(paths.ARTIFACT)
        }
        self.assertIn("marked", declared)
        self.assertEqual(
            declared["marked"].version, manifest["files"]["marked"]["version"],
        )

    def test_the_copies_are_the_vendors_own_member(self):
        # The texts that are COPIES: each tarball carries its own LICENSE, and
        # `at-cli license` answers from the copy so it does not unpack megabytes
        # to say a licence. Held equal, so a copy cannot rot.
        for key, service in (("caddy", caddy), ("gitleaks", gitleaks)):
            with self.subTest(component=key):
                payload = service.payload()
                assert payload is not None
                with tarfile.open(payload, "r:gz") as archive:
                    inside = archive.extractfile("LICENSE")
                    assert inside is not None
                    self.assertEqual(
                        inside.read(),
                        (ROOT / "at" / "vendor" / "licenses" / key / "LICENSE").read_bytes(),
                    )


class TheWord(unittest.TestCase):
    """`license` — the notices' only door out of a single-file artifact."""

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"AT_ROOT": str(Path(self.scratch.name)), "AT_LANG": "pt_BR"},
        )
        self.env.start()
        i18n.reset()
        with redirect_stdout(io.StringIO()):
            boot.create_working_folder()

    def tearDown(self):
        self.env.stop()
        i18n.reset()
        self.scratch.cleanup()

    def run_words(self, word: str, *rest: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli_main([word, *rest])
        return code, output.getvalue()

    def test_it_answers_with_the_products_own_licence(self):
        code, text = self.run_words("license")
        self.assertEqual(code, 0)
        self.assertIn("MIT License", text)
        self.assertIn("Permission is hereby granted", text)

    def test_it_names_every_component_the_artifact_carries(self):
        _, text = self.run_words("license")
        for component in licenses.declared(paths.ARTIFACT):
            with self.subTest(component=component.key):
                self.assertIn(component.name, text)
                self.assertIn(component.license, text)

    def test_it_answers_for_this_artifact_and_not_the_other_one(self):
        # The same word, the same module, two different lists: what the app
        # carries and the deploy does not is exactly the app's payload.
        _, text = self.run_words("license")
        self.assertIn("Caddy", text)
        self.assertIn("Vue", text)

    def test_the_vendors_legalese_comes_only_when_it_is_asked_for(self):
        _, summary = self.run_words("license")
        self.assertNotIn("SIL OPEN FONT LICENSE", summary)
        _, full = self.run_words("license", "--include-texts")
        self.assertIn("SIL OPEN FONT LICENSE", full)
        self.assertIn("Apache License", full)

    def test_a_flag_it_does_not_offer_is_a_usage_error(self):
        code, _ = self.run_words("license", "--nope")
        self.assertEqual(code, 2)

    def test_the_deploy_answers_its_own_shorter_list(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = deploy_main(["license"])
        text = output.getvalue()
        self.assertEqual(code, 0)
        # The ROWS, and not the whole answer: AT's own licence names the family
        # of what the pair carries, and the deploy prints that too. What the
        # deploy must not do is claim a component of the app's payload.
        self.assertIn("  Python ", text)
        self.assertNotIn("  Caddy ", text)
        self.assertNotIn("  Vue ", text)


class TheRoot(unittest.TestCase):
    """The product's own licence, at the root where a licence is looked for."""

    def test_it_is_mit_and_names_the_holder(self):
        body = licenses.product()
        assert body is not None, "LICENSE.md is not at the root"
        self.assertIn("MIT License", body)
        self.assertIn("Copyright (c) 2026 Rafael Correia", body)
        self.assertIn("Permission is hereby granted", body)

    def test_it_points_at_the_one_declaration_and_at_no_other(self):
        body = licenses.product()
        assert body is not None
        self.assertIn("at/vendor/licenses/manifest.json", body)


if __name__ == "__main__":
    unittest.main()
