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
READ = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)\s*(,)?")
DECLARED = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:")
READ_BY_NAME = re.compile(r"""getPropertyValue\(\s*["'](--[a-zA-Z0-9_-]+)["']""")


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

    def test_every_theme_wears_at_least_one_side(self):
        # `at` is the one pair left (2026-10-04): every other theme kept the
        # side it wore by default and dropped its mirror, so one file is
        # enough — never zero.
        for row in webapp.theme_rows():
            sides = webapp.theme_sides(row["id"])
            self.assertTrue(sides, row["id"])

    def test_a_theme_that_is_not_declared_is_never_a_path(self):
        row = webapp.active_theme("../../etc/passwd")
        self.assertEqual(row["id"], webapp.DEFAULT_THEME)


class TheThemes(unittest.TestCase):
    """`at`, `console`, `tipography` and `paper`, each in both sides (B-39)."""

    IDS = {"at", "console", "tipography", "paper"}

    def test_the_registry_has_the_four_themes_each_with_both_sides(self):
        ids = {row["id"] for row in webapp.theme_rows()}
        self.assertEqual(ids, self.IDS)
        for ident in ids:
            self.assertEqual(webapp.theme_sides(ident), ["light", "dark"], ident)

    def test_the_retired_themes_and_the_frozen_folder_are_gone(self):
        self.assertFalse((THEMES / "frozen").exists())
        for ident in ("comunidade", "frutiger-aero", "gothic", "hotel"):
            self.assertEqual(webapp.active_theme(ident)["id"], webapp.DEFAULT_THEME)

    def test_each_side_answers_its_own_file(self):
        for ident in self.IDS:
            self.assertEqual(webapp.theme_css(ident, True),
                             (THEMES / f"{ident}-dark.css").read_text(encoding="utf-8"))
            self.assertEqual(webapp.theme_css(ident, False),
                             (THEMES / f"{ident}.css").read_text(encoding="utf-8"))


class TheTokenContract(unittest.TestCase):
    """What `base.css` reads, every theme has to declare.

    A token read WITHOUT a fallback and declared by nobody becomes `initial` —
    the value is silently nothing, and the rule that reads it quietly stops
    applying.
    """

    @classmethod
    def setUpClass(cls):
        # `base.css` IS `at`'s OWN BASE, and the fallback: any theme that names
        # none of its own reads it, which is `cls.read`. Since 2026-10-03 that
        # is every theme in the registry — `base-shared.css`, the vocabulary
        # the other ten used to walk, was retired alongside the three themes
        # that did not survive the cut. The `"base"` door (`_reads_for`
        # below) stays open for a future theme that names a second
        # vocabulary; nothing in the registry walks it today.
        cls._base_cache: dict[str, dict[str, bool]] = {}
        cls.base = (ASSETS / "base.css").read_text(encoding="utf-8")
        cls.read = read_of(cls.base)
        cls._base_cache["base.css"] = cls.read
        cls.by_name = read_by_the_page()
        cls.base_declared = declared_in(cls.base)
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

    def test_the_structure_lives_in_base_css(self):
        # F0 (2026-10-22): type, space, motion and the chrome's measures do
        # not vary between themes, so `base.css` declares them once.
        structure_tokens = {
            "--type-caption", "--type-body-sm", "--type-body", "--type-body-lg",
            "--type-title", "--type-page", "--type-display", "--font-mono", "--leading-normal",
            "--leading-tight", "--weight-medium",
            "--weight-semibold", "--letter-tight", "--r-full",
            "--space-0_5", "--space-1", "--space-2", "--space-3", "--space-4",
            "--space-5", "--space-6", "--space-8", "--space-10", "--space-12",
            "--space-16", "--nav-w",
            "--nav-rail-w", "--nav-toggle-size", "--header-h", "--page-gutter",
        }
        self.assertEqual(sorted(structure_tokens - self.base_declared), [])
        for theme in self.themes:
            self.assertEqual(sorted(structure_tokens & self.declared[theme.name]), [],
                             f"{theme.name} re-declares structure")

    def test_type_is_a_scale_by_role_and_no_literal_font_size_leaks(self):
        # F2 (2026-10-22): sizes come from `--type-*`; the only literals are
        # the scale's own declarations in `:root` and the caret's `font-size: 0`.
        import re
        css = (ASSETS / "base.css").read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        literals = re.findall(r"(?<![-\w])font-size:\s*([0-9.]+(?:px|rem|em)?)", css)
        self.assertEqual(sorted(literals), ["0"])
        for size in ("12px", "13px", "14px", "16px", "20px", "28px"):
            self.assertIn(f": {size};", css)
        self.assertIn("font-size: 0;", css)
        for name in ("at.css", "at-dark.css"):
            theme = (ASSETS / "themes" / name).read_text(encoding="utf-8")
            self.assertNotIn("--font-display", theme)
            sans = re.search(r"--font-sans:\s*([^;]+);", theme).group(1)
            self.assertNotIn("Quicksand", sans)

    def test_every_theme_token_is_declared_by_every_active_theme(self):
        # Only what base.css does not declare itself is a THEME token.
        for theme in self.themes:
            reads = self._reads_for(theme)
            demanded = {token for token, has_fallback in reads.items()
                        if not has_fallback and token not in self.base_declared}
            missing = sorted(demanded - self.declared[theme.name])
            self.assertEqual(missing, [], f"{theme.name} does not declare {missing}")

    def test_a_token_the_page_reads_by_name_is_declared_somewhere(self):
        # The page asks for these for its own arithmetic (a column's width is
        # measured, never guessed). A theme MAY leave one out — the page carries a
        # fallback for that — but a name no file declares is a name that quietly
        # reads as nothing. These three are read BY NAME regardless of which base
        # is active, so every base's themes are expected to supply them.
        declared_somewhere: set[str] = set(self.read) | self.base_declared
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
            # The neutral ramp (50..950) is a palette declared whole, by design; the
            # text roles read some of its steps, the rest are the scale's own.
            unused = sorted(t for t in declared - read_somewhere if not t.startswith("--neutral-"))
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


class TheRadiusScale(unittest.TestCase):
    """The two house themes round their corners the same."""

    @staticmethod
    def scale(theme: str) -> dict[str, str]:
        text = without_comments((THEMES / theme).read_text(encoding="utf-8"))
        return dict(re.findall(r"(--r-(?:sm|md|lg))\s*:\s*([^;]+);", text))

    def test_light_and_dark_declare_the_same_radius(self) -> None:
        light, dark = self.scale("at.css"), self.scale("at-dark.css")
        self.assertEqual({"--r-sm": "8px", "--r-md": "14px", "--r-lg": "20px"}, dark)
        self.assertEqual(dark, light)


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


class TheTableBlocks(unittest.TestCase):
    """The product's table block is the GRID's, and the chat's is markdown.

    2026-10-05: the product block used `:not(.prose table)`, which reached the
    CHAT's answer table too — a markdown table is a table, and the chat's is not
    a product page. The block is scoped to `.grid` now (the class `TableView.vue`
    puts on the one table it draws), and the chat's answer is markdown rendered
    by the same parser a file is, wearing `.md-table`.
    """

    @classmethod
    def setUpClass(cls):
        cls.base = without_comments((ASSETS / "base.css").read_text(encoding="utf-8"))
        cls.ask_turn = (
            webapp.HERE / "src" / "components" / "AskTurn.vue"
        ).read_text(encoding="utf-8")

    def test_the_product_block_is_scoped_to_the_grid(self):
        self.assertIn("#body table.grid", self.base)
        # O seletor que vazava para o chat não existe mais.
        self.assertNotIn("table:not(.prose table)", self.base)

    def test_the_chat_wears_its_own_markdown_table(self):
        self.assertIn(".md-table", self.base)

    def test_the_chat_no_longer_draws_a_table_element_of_its_own(self):
        # O componente de tabela/fold do chat saiu: a resposta é UM corpo
        # markdown, e nada mais carrega `.answer-table` nem `.folded`.
        self.assertNotIn("answer-table", self.ask_turn)
        self.assertNotIn("folded", self.ask_turn)


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
        # EVERY BASE THAT DECLARES FACES, and not only the default one — the
        # door stays open for a theme that names a second `base`, even though
        # every theme in the registry walks `base.css` today. The @font-face
        # is an at-rule — a theme may never hold one — so the faces live in
        # the base beside it. The door is the same one `TheTokenContract`
        # walks; the pin is over the files.
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

    def test_every_face_blocks_and_carries_its_format(self):
        # `block`, and not `swap` (2026-10-05): these files are HOSTED, same
        # origin, a few KB each — `swap` paints the fallback immediately and
        # reflows into the real face a moment later, which is the flash the
        # boot gate (`App.vue`, `booted`) exists to kill one layer up. `block`
        # holds the glyph invisible through its short window instead.
        faces: list[str] = []
        for body in self.bases.values():
            faces += re.findall(r"@font-face\s*\{[^}]*\}", body)
        self.assertTrue(faces)
        for face in faces:
            self.assertIn("font-display: block", face)
            self.assertIn('format("woff2")', face)

    def test_the_faces_and_the_pinned_fonts_are_the_same_set(self):
        # Neither side may carry a face the other does not: a face with no file
        # is a 404 the theme hides behind a fallback, and a file with no face is
        # a file that was copied to sit there.
        faces = self.faces()
        pinned = {key for key in self.files if key.startswith("font-")}
        self.assertEqual(sorted(faces - pinned), [])
        self.assertEqual(sorted(pinned - faces), [])


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ratio(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _resolved(text: str) -> dict[str, str]:
    """Every `--x: #hex` of a theme, following `var(--y)` aliases."""
    raw = dict(re.findall(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;]+);", without_comments(text)))
    def value(name: str, depth: int = 0) -> str:
        v = raw[name].strip()
        m = re.fullmatch(r"var\(\s*(--[a-zA-Z0-9_-]+)\s*\)", v)
        return value(m.group(1), depth + 1) if m and depth < 8 else v
    return {name: value(name) for name in raw}


class TheTextRoles(unittest.TestCase):
    """F1: text is one of three roles, and each holds its ratio on every surface.

    The ratio is computed from the hex the theme declares, so a new theme (or a
    retouched one) cannot reintroduce a grey nobody can read.
    """

    FLOORS = {"--text-primary": 7.0, "--text-secondary": 4.5, "--text-tertiary": 4.5}
    SURFACES = ("--surface-canvas", "--surface-card", "--surface-raised", "--surface-sunken")

    @classmethod
    def setUpClass(cls):
        cls.base = (ASSETS / "base.css").read_text(encoding="utf-8")
        cls.themes = {t.name: _resolved(t.read_text(encoding="utf-8"))
                      for t in sorted(THEMES.glob("*.css"))}

    def test_base_reads_the_text_roles_and_not_the_old_ink(self):
        reads = set(read_of(self.base))
        self.assertEqual(sorted(r for r in reads if re.fullmatch(r"--ink-[123]", r)), [])
        self.assertTrue({"--text-primary", "--text-secondary", "--text-tertiary"} <= reads)

    def test_every_active_theme_declares_the_roles_and_the_state_texts(self):
        need = set(self.FLOORS) | {f"--{k}-text" for k in ("success", "warning", "danger", "info")}
        for name, tokens in self.themes.items():
            self.assertEqual(sorted(need - set(tokens)), [], name)

    def test_each_role_holds_its_ratio_on_every_surface(self):
        for name, tokens in self.themes.items():
            for role, floor in self.FLOORS.items():
                for surface in self.SURFACES:
                    got = _ratio(tokens[role], tokens[surface])
                    self.assertGreaterEqual(got, floor, f"{name} {role} on {surface}: {got:.2f}")

    def test_the_text_of_a_state_reads_on_its_own_ground(self):
        for name, tokens in self.themes.items():
            for kind in ("success", "warning", "danger", "info"):
                got = _ratio(tokens[f"--{kind}-text"], tokens[f"--{kind}-soft"])
                self.assertGreaterEqual(got, 4.5, f"{name} {kind}: {got:.2f}")

    def test_the_border_of_a_control_holds_three_to_one_on_every_surface(self):
        for name, tokens in self.themes.items():
            self.assertIn("--border-control", tokens, name)
            for surface in self.SURFACES:
                got = _ratio(tokens["--border-control"], tokens[surface])
                self.assertGreaterEqual(got, 3.0, f"{name} --border-control on {surface}: {got:.2f}")

    def test_the_neutral_ramp_and_the_hairline_roles_are_declared_and_ordered(self):
        for name, tokens in self.themes.items():
            for step in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950):
                self.assertIn(f"--neutral-{step}", tokens, name)
            self.assertIn("--border-subtle", tokens, name)
            self.assertIn("--border-default", tokens, name)
            for surface in self.SURFACES:
                sub = _ratio(tokens["--border-subtle"], tokens[surface])
                dflt = _ratio(tokens["--border-default"], tokens[surface])
                self.assertGreater(sub, 1.0, f"{name} --border-subtle on {surface}")
                self.assertGreaterEqual(dflt, sub, f"{name} --border-default on {surface}")
                self.assertGreaterEqual(_ratio(tokens["--border-control"], tokens[surface]), dflt)

    def test_the_placeholder_reads_a_role_that_holds_its_ratio(self):
        body = without_comments(self.base)
        self.assertRegex(body, r"::placeholder\s*\{\s*color: var\(--text-tertiary\);")
        for name, tokens in self.themes.items():
            for surface in self.SURFACES:
                got = _ratio(tokens["--text-tertiary"], tokens[surface])
                self.assertGreaterEqual(got, 4.5, f"{name} placeholder on {surface}: {got:.2f}")

    def test_the_accent_ink_reads_on_the_accent_and_on_its_wash(self):
        pairs = (("--accent-ink", "--accent"), ("--accent", "--accent-soft"))
        for name, tokens in self.themes.items():
            for fg, bg in pairs:
                got = _ratio(tokens[fg], tokens[bg])
                self.assertGreaterEqual(got, 4.5, f"{name} {fg} on {bg}: {got:.2f}")

    def test_the_main_has_no_radial_gradient(self):
        self.assertNotIn("radial-gradient(1100px", self.base)
        self.assertNotIn("--page-pad-x", self.base)

    def test_the_separator_is_text_not_a_border(self):
        body = without_comments(self.base)
        self.assertIn("#head-title .sep { color: var(--text-tertiary); }", body)


class TheSpecimen(unittest.TestCase):
    """F8: the system is visible, and the CSS stays terse."""

    def test_base_css_is_at_most_ten_percent_comments(self):
        text = (ASSETS / "base.css").read_text(encoding="utf-8")
        inside, count = False, 0
        for line in text.split("\n"):
            if inside or "/*" in line:
                count += 1
            if "/*" in line:
                inside = "*/" not in line.split("/*", 1)[1]
            elif inside and "*/" in line:
                inside = False
        self.assertLessEqual(count / len(text.split("\n")), 0.10)

    def test_the_old_ink_lives_nowhere(self):
        for css in ASSETS.rglob("*.css"):
            if "frozen" in css.parts:
                continue
            self.assertIsNone(re.search(r"--ink-\d", css.read_text(encoding="utf-8")), css.name)

    def test_the_specimen_is_a_view_with_no_row_in_the_panel(self):
        src = webapp.HERE / "src"
        self.assertTrue((src / "views" / "DesignView.vue").is_file())
        self.assertIn('registerView("design"', (src / "main.ts").read_text(encoding="utf-8"))
        self.assertNotIn("design", (src / "components" / "Sidebar.vue").read_text(encoding="utf-8").lower())


class TheTitlesAreInNormalCase(unittest.TestCase):
    """B-36: only the table header (`th`) is upper case; titles are `--type-title`."""

    def test_no_rule_outside_th_sets_text_transform_uppercase(self):
        src = Path(webapp.__file__).parent / "src"
        sheets = [ASSETS / "base.css", *src.rglob("*.vue"), *src.rglob("*.css")]
        for sheet in sheets:
            text = without_comments(sheet.read_text(encoding="utf-8"))
            for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
                if re.search(r"text-transform:\s*uppercase", body):
                    names = [n.strip() for n in selector.split(",")]
                    self.assertTrue(all(re.search(r"(^|[\s>+~])th$", n) for n in names),
                                    f"{sheet.name}: {selector.strip()}")

    def test_the_sidebar_and_the_card_titles_read_the_title_size(self):
        text = without_comments((ASSETS / "base.css").read_text(encoding="utf-8"))
        for head in (r"nav \.folder,\s*nav \.file\[data-view=\"reminders\"\]", r"\.cards h2"):
            body = re.search(head + r"[^{]*\{([^}]*)\}", text).group(1)
            self.assertIn("var(--type-title)", body)
            self.assertNotIn("letter-spacing", body)


class TheDensity(unittest.TestCase):
    def test_compact_is_an_attribute_that_only_overrides_tokens(self):
        base = Path(webapp.__file__).parent / "assets" / "base.css"
        text = without_comments(base.read_text(encoding="utf-8"))
        self.assertIn('html[data-density="compact"]', text)
        self.assertIn("--density-cell-pad-y: 8px;", text)
        self.assertIn("--density-cell-pad-y: 12px;", text)
        boot = (Path(webapp.__file__).parent / "assets" / "js" / "boot.js").read_text(encoding="utf-8")
        self.assertIn("at.density", boot)


class ThePageWide(unittest.TestCase):
    """B-24: `.page--wide` lets the table and the board read up to 1600px."""

    SRC = Path(webapp.__file__).parent / "src"

    def test_the_class_reads_a_token_declared_at_1600(self):
        text = without_comments((ASSETS / "base.css").read_text(encoding="utf-8"))
        self.assertIn("--page-wide-max: 1600px;", text)
        self.assertIn(".page--wide { max-width: var(--page-wide-max); }", text)

    def test_the_shell_puts_it_on_the_table_and_the_board(self):
        app = (self.SRC / "App.vue").read_text(encoding="utf-8")
        self.assertIn("'page--wide': widensPage", app)
        route = (self.SRC / "lib" / "shellRoute.ts").read_text(encoding="utf-8")
        body = route.split("export const widensPage", 1)[1].split("});", 1)[0]
        for needle in ("isKind(view)", "BOARD_KEY", "ORPHANS_KEY", "PROJECT_PREFIX"):
            self.assertIn(needle, body)


if __name__ == "__main__":
    unittest.main()


class TheDesignPlanRules(unittest.TestCase):
    """F3-F6 of the design plan, as far as grep and parse can see them."""

    @classmethod
    def setUpClass(cls):
        cls.css = without_comments((ASSETS / "base.css").read_text(encoding="utf-8"))
        cls.raw = (ASSETS / "base.css").read_text(encoding="utf-8")

    def test_static_surfaces_carry_no_shadow(self):
        # F5: elevation is for what floats (pop, dialog, balloon, toast), never a resting card.
        static = {".block", ".card", ".stat-strip .stat", "table.grid"}
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", self.css):
            names = {name.strip() for name in selectors.split(",")}
            if not names & static:
                continue
            for value in re.findall(r"box-shadow:\s*([^;]+)", body):
                self.assertEqual(value.strip(), "none", f"{sorted(names)} floats: box-shadow {value}")

    # Elevation tokens may appear only where something floats or is a control's own lift.
    # `.btn` / `.btn:hover` / `.switch::after` rest on the page and still wear `--shadow-e1`:
    # kept here as KNOWN exceptions (B-4 pendencies), so a NEW resting shadow fails.
    ELEVATED = {".pop", ".dialog", ".balloon-bubble", ".toast", ".shortcut-hint"}
    KNOWN_RESTING = {".btn", ".btn:hover", ".switch::after"}

    def test_no_elevation_token_on_any_selector_outside_the_floating_set(self):
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", self.css):
            names = {" ".join(name.split()) for name in selectors.split(",")}
            for value in re.findall(r"box-shadow:\s*([^;]+)", body):
                if "--shadow-" not in value:
                    continue  # none, focus ring, inset edge, 1px ring: not elevation
                self.assertLessEqual(names, self.ELEVATED | self.KNOWN_RESTING,
                                     f"{sorted(names)} rests on the page with an elevation: {value}")

    def test_the_themes_declare_two_elevation_levels_and_the_hover_does_not_lift(self):
        # B-22: --shadow-e1 and --shadow-e2, and nothing else named --shadow-<level>.
        for name in ("at.css", "at-dark.css"):
            text = without_comments((THEMES / name).read_text(encoding="utf-8"))
            declared = set(re.findall(r"(--shadow-[\w-]+)\s*:", text))
            self.assertEqual(declared - {"--shadow-rgb"}, {"--shadow-e1", "--shadow-e2"}, name)
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", self.css):
            if ":hover" in selectors:
                self.assertNotIn("--shadow-e", body, f"{selectors.strip()} lifts on hover")
        self.assertNotRegex(self.css, r"--shadow-(xs|sm|card|lg)\b")

    # Hairlines (a border, ring or edge up to 3px) are not "sizes"; the rest of the literals below
    # are the KNOWN backlog of the px-to-token migration. The set may only shrink.
    HAIRLINE = re.compile(r"^(border[\w-]*|outline|box-shadow|border-width):[^;]*?\b[0-3]px\b")
    PX_ALLOWED = {
        "background-image: radial-gradient(circle, var(--accent) 4px, transparent 4px)",
        "border-radius: 4px", "border-radius: 5px", "gap: 2px", "gap: 4px", "gap: 5px",
        "grid-template-columns: repeat(auto-fill, minmax(112px, 1fr))",
        "grid-template-columns: repeat(auto-fit, minmax(148px, 1fr))",
        "grid-template-columns: repeat(auto-fit, minmax(240px, 1fr))",
        "height: 10px", "height: 12px", "height: 16px", "height: 1px", "height: 20px", "height: 24px",
        "height: 34px", "height: 3px", "height: 44px", "height: 56px", "height: 6px", "height: 8px",
        "inset: -6px -2px", "inset: 1px", "left: -10000px", "left: 2px", "left: 4px",
        "margin-bottom: -1px", "margin-left: -1px", "margin-left: 4px", "margin-left: 6px",
        "margin-top: -8px", "margin: -1px", "margin: 0 -2px", "margin: 4px 0 0",
        "max-height: 320px", "max-width: calc(100vw - 24px)", "min-height: 240px", "min-height: 44px",
        "min-width: 190px", "min-width: 20px", "min-width: 6px",
        "outline-offset: -2px", "padding: 0 2px", "padding: 1px", "padding: 2px 6px",
        "padding: 2px var(--space-3)", "padding: var(--space-2) 0 var(--foot-space, 140px)",
        "top: 1px", "transform: translateX(-2px)", "transform: translateX(14px)",
        "transform: translateY(-4px)", "transform: translateY(4px)", "transform: translateY(8px)",
        "vertical-align: -1px", "vertical-align: -2px",
        "width: 10px", "width: 16px", "width: 1px", "width: 24px", "width: 2px", "width: 34px",
        "width: 36px", "width: 4px", "width: 56px", "width: 8px",
        "width: min(640px, calc(100vw - 2 * var(--space-8)))",
    }

    def test_no_new_literal_px_outside_root(self):
        css = re.sub(r"@media[^{]*", "", self.css)
        css = re.sub(r"(?<![\w-]):root\s*\{[^{}]*\}", "", css)
        found = {" ".join(d.split()) for d in re.findall(r"([\w-]+\s*:[^;{}]*\d(?:\.\d+)?px[^;{}]*)", css)}
        found = {d for d in found if not d.startswith(("--", "font-size")) and not self.HAIRLINE.match(d)}
        self.assertEqual(sorted(found - self.PX_ALLOWED), [])
        self.assertEqual(sorted(self.PX_ALLOWED - found), [], "leaving the list? shrink it")

    def test_no_literal_px_font_size_outside_root(self):
        css = re.sub(r":root\s*\{[^{}]*\}", "", self.css)
        self.assertEqual(re.findall(r"font-size:\s*[0-9.]+px", css), [])

    def test_the_temporary_aliases_stay_gone(self):
        # F0/F8: the names the scales replaced do not come back.
        for name in ("--dur-fast", "--dur-base", "--ease-out", "--weight-bold"):
            self.assertNotIn(name, self.css)
            for theme in ("at.css", "at-dark.css"):
                self.assertNotIn(name, (ASSETS / "themes" / theme).read_text(encoding="utf-8"))
            for source in PAGE_SOURCES:
                self.assertNotIn(name, source.read_text(encoding="utf-8"), source.name)

    def test_the_open_fold_takes_its_content_height_and_never_zero(self):
        css = (ASSETS / "base.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"flex:\s*1 1 0;\s*min-height:\s*0")
        rule = re.search(r"#kinds > \.foldable\.grouped:not\(\.closed\)\s*\{([^}]*)\}", css).group(1)
        self.assertIn("flex: 0 1 auto", rule)
        self.assertRegex(rule, r"min-height:\s*var\(--fold-floor")
        self.assertRegex(css, r"grid-template-rows var\(--dur-4\)")
        self.assertRegex(css, r"@media \(prefers-reduced-motion: reduce\) \{ \.foldable \{ transition: none; \} \}")

    def test_no_transition_waits_for_the_old_one_to_leave(self):
        for source in PAGE_SOURCES:
            if source.suffix == ".vue":
                self.assertNotRegex(source.read_text(encoding="utf-8"), r"mode=.out-in", source.name)

    def test_every_leave_class_a_view_declares_animates_and_has_its_reduced_motion(self):
        css = without_comments((ASSETS / "base.css").read_text(encoding="utf-8"))
        reduced = css[css.index("@media (prefers-reduced-motion: reduce) {\n  *,"):]
        found = set()
        for source in PAGE_SOURCES:
            if source.suffix != ".vue":
                continue
            for name in re.findall(r'leave-active-class="([\w-]+)"', source.read_text(encoding="utf-8")):
                found.add(name)
                rule = re.search(r"\.%s\s*\{([^}]*)\}" % re.escape(name), css)
                self.assertIsNotNone(rule, name)
                self.assertRegex(rule.group(1), r"animation:\s*[\w-]+-out var\(--dur-[1-4]\)", name)
                self.assertIn(":not(.%s)" % name, reduced, name)
        self.assertIn("view-leave-active", found)

    def test_the_screen_that_leaves_leaves_out_of_the_flow_over_the_new_one(self):
        css = without_comments((ASSETS / "base.css").read_text(encoding="utf-8"))
        rule = re.search(r"\.page > \.view-leave-active\s*\{([^}]*)\}", css).group(1)
        self.assertIn("position: absolute", rule)
        self.assertRegex(re.search(r"\.page\s*\{([^}]*)\}", css).group(1), r"position:\s*relative")

    def test_the_empty_state_is_a_room_not_a_line(self):
        rule = re.search(r"\.empty-state\s*\{([^}]*)\}", self.css).group(1)
        self.assertIn("min-height: 240px", rule)
        self.assertRegex(self.css, r"\.empty-state \.empty-icon\s*\{\s*width: 24px; height: 24px;")

    def test_icons_read_the_icon_scale(self):
        self.assertNotRegex(self.css, r"::before\s*\{[^}]*(?<![-\w])(?:width|height):\s*1[0-9]px")
        self.assertIn("--icon-sm:", self.css)
        self.assertIn("--icon-md:", self.css)


class TheFilesFolderIsInTheUrl(unittest.TestCase):
    """B-27: the Files browser's folder rides in the address (`/files/a/b`)."""

    SRC = Path(webapp.__file__).parent / "src"

    def test_the_address_carries_the_folder_and_steps_are_history(self):
        views = (self.SRC / "lib" / "views.ts").read_text(encoding="utf-8")
        self.assertIn("pieces.push(...filesFolder.segments.map(encodeURIComponent))", views)
        self.assertIn("history.pushState(null, \"\", path)", views)
        self.assertIn("window.addEventListener(\"popstate\"", views)
        self.assertIn("parts[0] === FILES_KEY ? parts.slice(1) : null", views)

    def test_a_link_to_a_folder_opens_it_and_the_screen_steps_through_it(self):
        route = (self.SRC / "lib" / "shellRoute.ts").read_text(encoding="utf-8")
        self.assertIn("filesFolder.segments = folderOfAddress(location.pathname)", route)
        view = (self.SRC / "views" / "FilesView.vue").read_text(encoding="utf-8")
        self.assertIn("stepFolder([...here.value, name])", view)
        self.assertIn("watch(() => filesFolder.segments.join(\"/\")", view)
