# -*- mode: python ; coding: utf-8 -*-
"""The build that derives `dist/at-deploy` — the environment's artifact (§7).

Build it from the repository root, with the PyInstaller version the README pins:

    .venv/bin/pyinstaller --clean --noconfirm at-deploy.spec

**Why a second file and not a second target of `at-cli.spec`.** A spec IS one
artifact: it names the entry point, the payloads and the exclusions, and the two
artifacts differ in all three. Written apart, the difference is readable — what
travels inside each one is a list somebody can read — and the deploy's list is
deliberately SHORT, because the deploy carries no WebApp, no interpreter and
neither of the two programs the app embeds — no Caddy, no `gitleaks` (item 32):
it is a command line and the environment it orchestrates.

**The shared core travels in both, and it is one source.** `paths`, `i18n`,
`files` and the table engine live in `at/`, the deploy imports them, and
PyInstaller collects them from there — the same files the other build collects,
never a copy. The direction is one-way: `at_deploy` imports `at`, and `at`
imports nothing of the deploy, which is what makes §3's promise readable off the
artifact — `at` cannot ask for elevation, because the code that does is not in
it.

**What does NOT travel here.** The WebApp's payloads (`assets`, `dist`,
`vendor`) and the two third-party programs the app carries — the Caddy's tarball
and the `gitleaks`' (item 32) — are `at`'s, and no import of this package reaches
them. The `vocabulary` — the interpreter's word list — is `at`'s too: the deploy
neither reads a sentence nor proposes one. A payload left out of a build fails
silently, so each one left out is named here rather than omitted in silence.

**Tcl/Tk does NOT travel here, and it is the Wizard's absence.** The deploy's
Wizard (`at_deploy/wizard.py`) is the front §6 declares for this artifact, and
the `Tk` stepped aside for now — the same decision `at-cli` took in item 9, and
for the same reason: the door is the `cli`, which §5's one-way rule leaves whole
on its own, and the screen is only how somebody who does not type reaches it.

A Tkinter window needs the interpreter's toolchain — `_tkinter` and the Tcl/Tk
libraries beside it, some tens of megabytes extracted on every launch of a
`--onefile` binary — and that is the payload of a caller this release does not
have. It is also a payload that COSTS: the Tk/X11 chain needs a newer glibc for
the artifact (`libexpat`), and what the release promises it must hold.

The payload is out, and it is said here for the reason above: a payload decided
by silence is a payload nobody can read. When the `Tk` comes back it comes back
HERE, and `release/builder.json` gains the builder package and the promised
payload with it.
"""

import sys

ENTRY = "at_deploy/__main__.py"

# The file this build derives, and it is the SAME rule the app's build follows —
# `.exe` on Windows, `.bin` on Linux and macOS (§3, item 29) —, because the pair
# is a rule of the FILE and not of one artifact. The word does not move: the
# second artifact is `at-deploy`, and what §7 does to the machine is what gave
# it the name.
NAME = "at-deploy.exe" if sys.platform == "win32" else "at-deploy"

# (source, destination), and the destination repeats the last segment for the
# same reason `at-cli.spec` does: a directory source lands its CONTENTS in the
# dest folder, so the destination has to be the folder the code looks at
# runtime. Both of these anchor on their package directories (`at/i18n` and
# `at/data/schema`), which is the same arithmetic one directory up.
DATAS = [
    # Every sentence of the product, both languages. The deploy says the
    # environment's, and it shares the blocks with `at` because there is one
    # `i18n` and not two.
    ("at/i18n/blocks", "at/i18n/blocks"),
    # The declarations the first run seeds into a folder that has none. The
    # deploy confirms the Working Folder exactly as `at` does, so it has to be
    # able to make one.
    ("at/data/defaults", "at/data/defaults"),
    # The notices of the third parties THIS artifact carries (item 27), and the
    # product's own licence with them: the frozen binary holds the interpreter,
    # PyInstaller's bootloader and the crypto binding, so it owes their terms —
    # and `at-deploy license` is the door out, exactly as `at-cli license` is on
    # the other side. The list is shorter here for the same reason the payload
    # list above is: no typeface, no Vue bundle, no Caddy travels in this one,
    # and a licence declared for something the artifact does not hold would be a
    # lie the declaration itself refuses (`at/core/licenses.py`).
    ("LICENSE.md", "."),
    ("at/vendor/licenses", "at/vendor/licenses"),
]

a = Analysis(
    [ENTRY],
    # SPECPATH, not ".": the datas sources resolve against the spec's own
    # directory, so an absolute `pyinstaller /path/to/at-deploy.spec` from
    # elsewhere must find them the same way `pyinstaller at-deploy.spec` from
    # the root does.
    pathex=[SPECPATH],
    binaries=[],
    datas=DATAS,
    # `_cffi_backend` is the cffi runtime's own C extension, and no import graph
    # reaches it: `nacl.bindings` loads it through cffi, at RUNTIME. The deploy
    # reaches `nacl` the same way `at` does — the first run seeds the `actor`
    # table, and the hashed field's derivation is `libsodium`'s — so the same
    # hand-named payload travels here.
    #
    # `tkinter` was named here, and it is NOT any more: the `Tk` stepped aside
    # (the docstring says why), and what the release does not carry it does not
    # promise. Naming a payload the artifact has no caller for would be paying
    # the megabytes and the glibc for a window nobody opens.
    hiddenimports=["_cffi_backend"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # The suite has no business inside the binary, here either.
    excludes=["at.tests", "at_deploy.tests"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name=NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # No UPX, for the same reason the other build has none (§3).
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
