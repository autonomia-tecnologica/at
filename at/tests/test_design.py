"""The design system's contract, and the three doors that serve it.

These are the rules that make the look what it is, and they are all measured
against the files themselves — `base.css`, the themes, the registry and the
manifest. Nothing here renders anything: what a rule says is checked by reading
what the rule reads.

They port from the PoC's `test_webapp.py`, which is the specification of the
design system: the token contract, the icon door, the theme door and the hosted
typefaces.
"""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

from at.ui.webapp import app as webapp

ASSETS = webapp.ASSETS
THEMES = webapp.THEMES
ICONS = webapp.ICONS
VENDOR = webapp.VENDOR
PAGE_SOURCES = list((webapp.HERE / "src").rglob("*.vue")) + list((webapp.HERE / "src").rglob("*.ts"))

COMMENT = re.compile(r"/\*.*?\*/", re.S)
# A theme may declare a BRACE as an icon character (`--icon-code: "{"`), and a
# brace inside a quoted value is not a block — so the strings leave before the
# structure is read.
QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"' + r"|'(?:[^'\\]|\\.)*'")
# `var(--x)` needs a value from somewhere; `var(--x, fallback)` does not.
READ = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)\s*(,)?")
DECLARED = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")
READ_BY_NAME = re.compile(r"""getPropertyValue\(\s*["'](--[a-zA-Z0-9-]+)["']""")


def without_comments(text: str) -> str:
    """The prose names tokens too, and prose is not a rule."""
    return COMMENT.sub("", text)


def structure(text: str) -> str:
    """The text with its prose and its strings gone — what is left is the shape."""
    return QUOTED.sub('""', without_comments(text))


def read_of(text: str) -> dict[str, bool]:
    """Every token the text reads, and whether it brought a fallback.

    WHAT IS READ IS read WITHOUT a fallback: `var(--x)` with nothing behind it
    becomes `initial` when no theme declares `x` — a value nobody wrote, which is
    the defect this contract exists to catch. `var(--x, something)` survives a
    missing declaration, so it is not a demand on the themes.
    """
    found: dict[str, bool] = {}
    for token, fallback in READ.findall(without_comments(text)):
        found[token] = found.get(token, False) or bool(fallback)
    return found


def declared_in(text: str) -> set[str]:
    return set(DECLARED.findall(without_comments(text)))


def read_by_the_page() -> set[str]:
    """The tokens the PAGE asks for by name — the ones no CSS rule can vouch for."""
    found: set[str] = set()
    for source in PAGE_SOURCES:
        found |= set(READ_BY_NAME.findall(source.read_text(encoding="utf-8")))
    return found


class TheRegistry(unittest.TestCase):
    def test_it_declares_at_least_one_theme(self):
        self.assertTrue(webapp.theme_rows())

    def test_every_theme_is_a_pair_of_files(self):
        for row in webapp.theme_rows():
            self.assertTrue((THEMES / f"{row['id']}.css").is_file(), row["id"])
            dark = THEMES / f"{row['id']}-dark.css"
            self.assertTrue(dark.is_file() or (row.get("side") != "dark"), row["id"])

    def test_a_theme_that_is_not_declared_is_never_a_path(self):
        row = webapp.active_theme("../../etc/passwd")
        self.assertEqual(row["id"], webapp.DEFAULT_THEME)


class TheTokenContract(unittest.TestCase):
    """What `base.css` reads, every theme has to declare.

    A token read WITHOUT a fallback and declared by nobody becomes `initial` —
    the value is silently nothing, and the rule that reads it quietly stops
    applying.
    """

    @classmethod
    def setUpClass(cls):
        cls.base = (ASSETS / "base.css").read_text(encoding="utf-8")
        cls.read = read_of(cls.base)
        cls.by_name = read_by_the_page()
        cls.themes = sorted(THEMES.glob("*.css"))
        cls.declared = {theme.name: declared_in(theme.read_text(encoding="utf-8"))
                        for theme in cls.themes}

    def test_the_page_reads_at_least_one_token_by_name(self):
        # The gate below is only worth having if it has something to check.
        self.assertTrue(self.by_name)

    def test_every_token_read_without_a_fallback_is_declared_by_every_theme(self):
        demanded = {token for token, has_fallback in self.read.items() if not has_fallback}
        for name, declared in self.declared.items():
            missing = sorted(demanded - declared)
            self.assertEqual(missing, [], f"{name} does not declare {missing}")

    def test_a_token_the_page_reads_by_name_is_declared_somewhere(self):
        # The page asks for these for its own arithmetic (a column's width is
        # measured, never guessed). A theme MAY leave one out — the page carries a
        # fallback for that — but a name no file declares is a name that quietly
        # reads as nothing.
        declared_somewhere: set[str] = set(self.read)
        for declared in self.declared.values():
            declared_somewhere |= declared
        self.assertEqual(sorted(self.by_name - declared_somewhere), [])

    def test_no_theme_declares_a_token_nobody_reads(self):
        # A token nobody reads is a value a theme carries for nothing — and, more
        # to the point, it hides which decorations are actually in use.
        read_somewhere = set(self.read) | self.by_name
        for declared in self.declared.values():
            read_somewhere |= declared
        for name, declared in self.declared.items():
            unused = sorted(declared - read_somewhere)
            self.assertEqual(unused, [], f"{name} declares unread {unused}")

    def test_the_two_sides_declare_the_same_names(self):
        for light in self.themes:
            if not light.stem.endswith("-dark"):
                continue
            dark = self.declared[light.name]
            pair = self.declared.get(light.stem[: -len("-dark")] + ".css")
            if pair is None:
                continue
            self.assertEqual(sorted(pair - dark), [], f"{light.name} is missing names")
            self.assertEqual(sorted(dark - pair), [], f"{light.name} adds names")

    def test_a_theme_declares_only_root(self):
        # The hard rule: a theme changes VARIABLES. Whoever declares a selector is
        # `base.css` — a theme with a selector is a theme that grew a second
        # design system inside it.
        for theme in self.themes:
            body = structure(theme.read_text(encoding="utf-8"))
            blocks = re.findall(r"([^{}]+)\{", body)
            self.assertEqual([block.strip() for block in blocks if block.strip()], [":root"],
                             f"{theme.name} declares more than :root")

    def test_no_theme_embeds_a_drawing(self):
        # The page runs under `default-src 'self'`, so an embedded SVG simply
        # never paints — and the failure is invisible.
        for theme in self.themes:
            body = without_comments(theme.read_text(encoding="utf-8"))
            self.assertNotRegex(body, r"url\(\s*[\"']?data:", theme.name)


class TheDoors(unittest.TestCase):
    def test_every_drawing_a_theme_names_is_served(self):
        for theme in sorted(THEMES.glob("*.css")):
            body = without_comments(theme.read_text(encoding="utf-8"))
            for name in re.findall(r"""url\(\s*["']?icons/([^"')]+)["']?\s*\)""", body):
                self.assertIsNotNone(webapp.served(ICONS, name), f"{theme.name} -> {name}")

    def test_a_name_that_is_a_path_is_refused(self):
        for name in ("../app.py", "a/../code.svg", "..", ".hidden.svg", "", "code.svg/"):
            self.assertIsNone(webapp.served(ICONS, name), name)
            self.assertIsNone(webapp.hosted(name), name)


class TheTypefaces(unittest.TestCase):
    """The hosted families, pinned by version and by hash.

    `base.css` declares the `@font-face` (an at-rule is not a selector, so a
    theme could never hold it) and names `/vendor/<key>`. The manifest is the
    pin: it says which package, which version and which sha256 — so what leaves
    the server can be checked against what was installed (§3).
    """

    @classmethod
    def setUpClass(cls):
        cls.base = without_comments((ASSETS / "base.css").read_text(encoding="utf-8"))
        cls.manifest = json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))
        cls.files = cls.manifest["files"]

    def test_every_face_base_css_declares_is_pinned(self):
        keys = set(re.findall(r"""url\(\s*["']?/vendor/([^"')]+)["']?\s*\)""", self.base))
        self.assertTrue(keys)
        self.assertEqual(sorted(keys - set(self.files)), [])

    def test_every_pinned_file_matches_its_hash(self):
        for key, entry in self.files.items():
            where = VENDOR / f"{key}.woff2"
            self.assertTrue(where.is_file(), key)
            digest = hashlib.sha256(where.read_bytes()).hexdigest()
            self.assertEqual(digest, entry["sha256"], key)
            self.assertEqual(where.stat().st_size, entry["bytes"], key)

    def test_every_face_swaps_and_carries_its_format(self):
        faces = re.findall(r"@font-face\s*\{[^}]*\}", self.base)
        self.assertTrue(faces)
        for face in faces:
            self.assertIn("font-display: swap", face)
            self.assertIn('format("woff2")', face)

    def test_the_faces_and_the_pinned_fonts_are_the_same_set(self):
        # Neither side may carry a face the other does not: a face with no file
        # is a 404 the theme hides behind a fallback, and a file with no face is
        # a file that was copied to sit there.
        faces = re.findall(r"""url\(\s*["']?/vendor/([^"')]+)["']?\s*\)""", self.base)
        pinned = {key for key in self.files if key.startswith("font-")}
        self.assertEqual(sorted(set(faces) - pinned), [])
        self.assertEqual(sorted(pinned - set(faces)), [])


if __name__ == "__main__":
    unittest.main()
