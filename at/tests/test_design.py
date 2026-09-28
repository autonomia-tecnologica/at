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
        # `base.css` IS `at`'s OWN BASE, and the fallback: any theme that names
        # none of its own reads it, which is `cls.read`. Almost every OTHER
        # theme walks its own door instead (`"base"` in the registry row, which
        # for ten of the eleven points at `base-shared.css`), and its token
        # contract is checked against THAT file, not this one: `base-shared.css`
        # does not read `--sidebar-item-bg-on` any more than `base.css` reads
        # `--nav-bg`, and holding every theme to the same file's vocabulary
        # would fail the from-scratch system by construction.
        cls._base_cache: dict[str, dict[str, bool]] = {}
        cls.base = (ASSETS / "base.css").read_text(encoding="utf-8")
        cls.read = read_of(cls.base)
        cls._base_cache["base.css"] = cls.read
        cls.by_name = read_by_the_page()
        cls.themes = sorted(THEMES.glob("*.css"))
        cls.declared = {theme.name: declared_in(theme.read_text(encoding="utf-8"))
                        for theme in cls.themes}
        cls._registry = {row["id"]: row for row in webapp.theme_rows() if row.get("id")}

    def _reads_for(self, theme_path: Path) -> dict[str, bool]:
        stem = theme_path.stem
        ident = stem[: -len("-dark")] if stem.endswith("-dark") else stem
        name = self._registry.get(ident, {}).get("base")
        name = name if isinstance(name, str) else "base.css"
        if name not in self._base_cache:
            self._base_cache[name] = read_of((ASSETS / name).read_text(encoding="utf-8"))
        return self._base_cache[name]

    def test_the_page_reads_at_least_one_token_by_name(self):
        # The gate below is only worth having if it has something to check.
        self.assertTrue(self.by_name)

    def test_every_token_read_without_a_fallback_is_declared_by_every_theme(self):
        for theme in self.themes:
            reads = self._reads_for(theme)
            demanded = {token for token, has_fallback in reads.items() if not has_fallback}
            missing = sorted(demanded - self.declared[theme.name])
            self.assertEqual(missing, [], f"{theme.name} does not declare {missing}")

    def test_a_token_the_page_reads_by_name_is_declared_somewhere(self):
        # The page asks for these for its own arithmetic (a column's width is
        # measured, never guessed). A theme MAY leave one out — the page carries a
        # fallback for that — but a name no file declares is a name that quietly
        # reads as nothing. These three are read BY NAME regardless of which base
        # is active, so every base's themes are expected to supply them.
        declared_somewhere: set[str] = set(self.read)
        for declared in self.declared.values():
            declared_somewhere |= declared
        self.assertEqual(sorted(self.by_name - declared_somewhere), [])

    def test_no_theme_declares_a_token_nobody_reads(self):
        # A token nobody reads is a value a theme carries for nothing — and, more
        # to the point, it hides which decorations are actually in use. "Reads"
        # includes the theme's OWN composition (`--sidebar-item-pad: 6px
        # var(--sidebar-pad)` is `--sidebar-pad` in real use, even though only
        # the composed name ever reaches base.css) — a theme is one file, and a
        # token feeding another token in it is not a token nobody reads.
        for name, declared in self.declared.items():
            theme = next(t for t in self.themes if t.name == name)
            own_reads = read_of(theme.read_text(encoding="utf-8"))
            read_somewhere = set(self._reads_for(theme)) | self.by_name | set(own_reads)
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
    """The hosted files, pinned by version and by hash.

    `base.css` declares the `@font-face` (an at-rule is not a selector, so a
    theme could never hold it) and names `/vendor/<key>`. The manifest is the
    pin: it says which package, which version and which sha256 — so what leaves
    the server can be checked against what was installed (§3). What it hosts is
    no longer only typefaces: the markdown renderer travels the same door
    (`lib/markdown.ts`), and the pin below is over EVERY entry, font or code.
    """

    @classmethod
    def setUpClass(cls):
        # EVERY BASE THAT DECLARES FACES, and not only the default one: the ten
        # themes that walk `base-shared.css` bring its typefaces with them, and
        # the @font-face is an at-rule — a theme may never hold one — so the
        # faces live in the base beside it. The door is the same one
        # `TheTokenContract` walks; the pin is over the files.
        names = {"base.css"}
        for row in webapp.theme_rows():
            if isinstance(row.get("base"), str):
                names.add(row["base"])
        cls.bases = {
            name: without_comments((ASSETS / name).read_text(encoding="utf-8"))
            for name in sorted(names)
        }
        cls.manifest = json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))
        cls.files = cls.manifest["files"]

    def faces(self) -> set[str]:
        """Every `/vendor/` file NAMED by a base that declares faces."""
        found: set[str] = set()
        for body in self.bases.values():
            if "@font-face" not in body:
                continue
            found |= set(re.findall(r"""url\(\s*["']?/vendor/([^"')]+)["']?\s*\)""", body))
        return found

    def test_every_face_a_base_declares_is_pinned(self):
        keys = self.faces()
        self.assertTrue(keys)
        self.assertEqual(sorted(keys - set(self.files)), [])

    def test_every_pinned_file_matches_its_hash(self):
        # The file is the key plus the extension the vendor's `upstream` carries
        # — `.woff2` for a typeface, `.js` for the renderer —, the same
        # arithmetic `app.hosted` does when it serves it.
        for key, entry in self.files.items():
            where = VENDOR / f"{key}{Path(entry['upstream']).suffix}"
            self.assertTrue(where.is_file(), key)
            digest = hashlib.sha256(where.read_bytes()).hexdigest()
            self.assertEqual(digest, entry["sha256"], key)
            self.assertEqual(where.stat().st_size, entry["bytes"], key)

    def test_every_face_swaps_and_carries_its_format(self):
        faces: list[str] = []
        for body in self.bases.values():
            faces += re.findall(r"@font-face\s*\{[^}]*\}", body)
        self.assertTrue(faces)
        for face in faces:
            self.assertIn("font-display: swap", face)
            self.assertIn('format("woff2")', face)

    def test_the_faces_and_the_pinned_fonts_are_the_same_set(self):
        # Neither side may carry a face the other does not: a face with no file
        # is a 404 the theme hides behind a fallback, and a file with no face is
        # a file that was copied to sit there.
        faces = self.faces()
        pinned = {key for key in self.files if key.startswith("font-")}
        self.assertEqual(sorted(faces - pinned), [])
        self.assertEqual(sorted(pinned - faces), [])


if __name__ == "__main__":
    unittest.main()
