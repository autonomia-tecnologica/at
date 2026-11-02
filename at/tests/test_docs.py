"""The gate over the repository's documents.

The documents exist in two languages, and the rule says the two change together
(§3, Internacionalização). Nothing else notices when they do not, so this test
does. It checks four things, in the order a mistake happens:

1. the NAME — every markdown lives under the folder of its language, and the name
   does not repeat it; only the root door sits outside a language folder, and the
   note a Working Folder's runtime writes at its root, which is not a document of
   the product but the folder presenting itself;
2. the PAIR — a document has its sibling, the same name in the other language's
   folder;
3. the STRUCTURE — the pair carries the same headings, in the same order, because
   the mistake that actually happens is a forgotten SECTION, not a sentence;
4. the SPELLING — both languages go through the checker, and what it ignores lives
   in a versioned list, one per language, so the list is visible in a diff.

Grammar is not checked here: that is what the human reading is for. The checker is
a development tool and comes pinned in `requirements-dev.txt` — this module fails
instead of skipping when it is missing, because a gate that steps aside is not one.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

try:
    from spellchecker import SpellChecker
except ImportError:  # pragma: no cover — the failure is the point, and it is loud
    SpellChecker = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[2]

# The ignore lists are the suite's own data, and they live beside this module:
# the package and the binary already keep `at.tests` out (pyproject and
# `at-cli.spec`), so the lists travel with the gate that reads them and with
# nothing else.
HERE = Path(__file__).resolve().parent

# Nothing here is a document: the runtime folders of a Working Folder, the
# importable package, the build output and the vendored dependencies.
# The Working Folder a checkout creates for itself, and the product's other
# payloads. Both spellings of every folder are here: the checkout's own instance
# is migrated by running AT in it, and the gate must hold either way.
SKIP = {
    "node_modules", ".venv", ".git", "build", "dist", "hooks", ".claude",
    "App", "app", "Tables", "Tabelas", "Biblioteca", "Library",
    "Files", "Arquivos", "Projects", "Projetos", "Shared", "Compartilhada",
    "Harness",
    "data", "prose",
}

# The door at the root is the only markdown outside a language folder.
DOOR = ROOT / "README.md"

# And the markdown that is not ours to place. `INSTANCE.md` is not the
# product's: it is the PERSON's file — the real Working Folder, what a session
# owes it and what is still missing there —, it sits at the root of the checkout
# and the git ignore rules keep it out. The root `README.md` says it MAY exist
# and never what is inside it (§0), so the gate has to let it sit beside the
# door: a file the repository does not carry cannot be checked for a pair, and
# the suite may not depend on it. `LICENSE.md` is the other, and it is not
# state: it is a legal instrument whose text is not the product's prose. It is
# spelled by the MIT's own words, it has no language and no pair — a licence is
# not translated, and translating it would be forging it —, and it sits at the
# root because that is where a licence is looked for (§3, item 27).
RUNTIME = {ROOT / "INSTANCE.md", ROOT / "LICENSE.md"}

# Documents of the WORK, not for the reader: they have a language and no pair.
WORKING = {"backlog"}

# The language of a document is the FOLDER it lives in (§3, Internacionalização),
# and the folder brings both the checker code and the name of its ignore list.
LANGUAGES = {
    "pt_BR": ("pt", "spelling.pt_BR.txt"),
    "en_US": ("en", "spelling.en_US.txt"),
}

# A name ending in one of these inside a language folder would say the language twice.
SUFFIXES = tuple(f".{folder}.md" for folder in LANGUAGES)

# Markdown that is not prose: fenced blocks (the trees, the shell), inline code,
# links and URLs. What is left is what a person reads, and that is what is checked.
_FENCED = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
_INLINE = re.compile(r"`[^`]*`")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def documents() -> list[Path]:
    found: list[Path] = []
    for path in ROOT.rglob("*.md"):
        if SKIP.intersection(path.parts) or path in RUNTIME:
            continue
        found.append(path)
    return sorted(found)


def language_of(path: Path) -> str | None:
    """The language folder of that document, wherever in the path it is."""
    for part in path.parts:
        if part in LANGUAGES:
            return part
    return None


def sibling(path: Path) -> Path:
    """The same document in the other language: the same name, the other folder."""
    language = language_of(path)
    other = next(folder for folder in LANGUAGES if folder != language)
    parts = list(path.parts)
    parts[parts.index(language)] = other
    return Path(*parts)


def prose(path: Path) -> str:
    """The text a person reads, with the code and the markup taken out."""
    text = path.read_text(encoding="utf-8")
    text = _FENCED.sub(" ", text)
    text = _IMAGE.sub(" ", text)
    text = _INLINE.sub(" ", text)
    text = _LINK.sub(r"\1", text)
    return text


def headings(path: Path) -> list[int]:
    """The LEVEL of every heading, in order — the structure, not the words."""
    levels: list[int] = []
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced or not line.startswith("#"):
            continue
        levels.append(len(line) - len(line.lstrip("#")))
    return levels


def word_list(path: Path) -> Path:
    """The ignore list of that document's language: `spelling.<language>.txt`."""
    language = language_of(path)
    assert language is not None, f"{path} lives outside a language folder"
    return HERE / LANGUAGES[language][1]


def accepted(path: Path) -> set[str]:
    """The words the checker must ignore, from the versioned list beside this module."""
    words: set[str] = set()
    where = word_list(path)
    if not where.is_file():
        return words
    for line in where.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.add(line.lower())
    return words


class TheNames(unittest.TestCase):
    def test_every_markdown_lives_in_a_language_folder(self):
        for path in documents():
            if path == DOOR:
                continue
            with self.subTest(document=path.relative_to(ROOT)):
                self.assertIsNotNone(
                    language_of(path),
                    f"{path.relative_to(ROOT)} lives outside a language folder; every "
                    f"document sits under `pt_BR/` or `en_US/` (§3, Internacionalização), "
                    f"and only the root README.md is allowed out",
                )

    def test_a_document_does_not_repeat_its_language_in_the_name(self):
        for path in documents():
            if language_of(path) is None:
                continue
            with self.subTest(document=path.relative_to(ROOT)):
                self.assertFalse(
                    path.name.endswith(SUFFIXES),
                    f"{path.relative_to(ROOT)} carries the language in the name as well "
                    f"as in the folder; the folder already says it (§3, "
                    f"Internacionalização)",
                )

    def test_the_door_is_the_only_one_without_a_language(self):
        self.assertTrue(DOOR.is_file(), "the root README.md is the door and must exist")


class ThePairs(unittest.TestCase):
    def test_a_document_has_its_sibling(self):
        for path in documents():
            if path == DOOR or language_of(path) is None or path.stem in WORKING:
                continue
            with self.subTest(document=path.relative_to(ROOT)):
                other = sibling(path)
                self.assertTrue(
                    other.is_file(),
                    f"{path.relative_to(ROOT)} has no sibling at {other.relative_to(ROOT)}; "
                    f"a document changes in both or it does not change (§3)",
                )

    def test_the_pair_has_the_same_structure(self):
        for path in documents():
            if path == DOOR or language_of(path) is None or path.stem in WORKING:
                continue
            other = sibling(path)
            if not other.is_file():
                continue
            with self.subTest(document=path.relative_to(ROOT)):
                self.assertEqual(
                    headings(path), headings(other),
                    f"{path.name} and {other.name} do not carry the same headings, in the "
                    f"same order — a forgotten section is the mistake this gate exists for",
                )


class TheSpelling(unittest.TestCase):
    def setUp(self):
        if SpellChecker is None:
            self.fail(
                "pyspellchecker is missing. It is a development dependency and comes "
                "pinned in requirements-dev.txt:\n"
                "  .venv/bin/pip install --require-hashes -r requirements-dev.txt"
            )
        self.checkers = {
            folder: SpellChecker(language=code)
            for folder, (code, _) in LANGUAGES.items()
        }

    def test_the_documents_are_spelled(self):
        for path in documents():
            language = language_of(path)
            if language is None:
                continue
            # The working document is a notebook: it quotes decisions in the language
            # they were decided in, and checking it would turn the list into half a
            # Portuguese dictionary for no gain (§3, Internacionalização).
            if path.stem in WORKING:
                continue
            with self.subTest(document=path.relative_to(ROOT)):
                words = {word.lower() for word in _WORD.findall(prose(path))}
                unknown = sorted(
                    self.checkers[language].unknown(words) - accepted(path)
                )
                self.assertEqual(
                    unknown, [],
                    f"{path.relative_to(ROOT)}: {len(unknown)} word(s) the checker does not "
                    f"know. Either they are typos, or they are legitimate and belong in "
                    f"{word_list(path).name} — the list is the gate's off switch, so every "
                    f"addition shows up in a diff on purpose",
                )


if __name__ == "__main__":
    unittest.main()
