# -*- mode: python ; coding: utf-8 -*-
"""The build that derives `dist/bill-deploy` — the environment's artifact (§7).

Build it from the repository root, with the PyInstaller version the README pins:

    .venv/bin/pyinstaller --clean --noconfirm bill-deploy.spec

**Why a second file and not a second target of `bill.spec`.** A spec IS one
artifact: it names the entry point, the payloads and the exclusions, and the two
artifacts differ in all three. Written apart, the difference is readable — what
travels inside each one is a list somebody can read — and the deploy's list is
deliberately SHORT, because the deploy carries no WebApp, no interpreter and no
Caddy: it is a command line and the environment it orchestrates.

**The shared core travels in both, and it is one source.** `paths`, `i18n`,
`files` and the table engine live in `bill/`, the deploy imports them, and
PyInstaller collects them from there — the same files the other build collects,
never a copy. The direction is one-way: `bill_deploy` imports `bill`, and `bill`
imports nothing of the deploy, which is what makes §3's promise readable off the
artifact — `bill` cannot ask for elevation, because the code that does is not in
it.

**What does NOT travel here.** The WebApp's payloads (`assets`, `dist`,
`vendor`) and the Caddy's tarball are `bill`'s, and no import of this package
reaches them. The `vocabulary` — the interpreter's word list — is `bill`'s too:
the deploy neither reads a sentence nor proposes one. A payload left out of a
build fails silently, so each one left out is named here rather than omitted in
silence.

**Tcl/Tk travels here, and it is the Wizard's price.** The deploy's Wizard
(`bill_deploy/wizard.py`) is the front §6 declares for this artifact, and a
Tkinter window needs the interpreter's toolchain: `_tkinter` and the Tcl/Tk
libraries beside it, some tens of megabytes extracted on every launch of a
`--onefile` binary. It is written here instead of discovered at the pyz level
because the price is part of what the artifact IS — `bill` pays it already, and
whoever reads a build has to be able to read this one too.
"""

ENTRY = "bill_deploy/__main__.py"

# (source, destination), and the destination repeats the last segment for the
# same reason `bill.spec` does: a directory source lands its CONTENTS in the
# dest folder, so the destination has to be the folder the code looks at
# runtime. Both of these anchor on their package directories (`bill/i18n` and
# `bill/data/schema`), which is the same arithmetic one directory up.
DATAS = [
    # Every sentence of the product, both languages. The deploy says the
    # environment's, and it shares the blocks with `bill` because there is one
    # `i18n` and not two.
    ("bill/i18n/blocks", "bill/i18n/blocks"),
    # The declarations the first run seeds into a folder that has none. The
    # deploy confirms the Working Folder exactly as `bill` does, so it has to be
    # able to make one.
    ("bill/data/defaults", "bill/data/defaults"),
]

a = Analysis(
    [ENTRY],
    # SPECPATH, not ".": the datas sources resolve against the spec's own
    # directory, so an absolute `pyinstaller /path/to/bill-deploy.spec` from
    # elsewhere must find them the same way `pyinstaller bill-deploy.spec` from
    # the root does.
    pathex=[SPECPATH],
    binaries=[],
    datas=DATAS,
    # `_cffi_backend` is the cffi runtime's own C extension, and no import graph
    # reaches it: `nacl.bindings` loads it through cffi, at RUNTIME. The deploy
    # reaches `nacl` the same way `bill` does — the first run seeds the `actor`
    # table, and the hashed field's derivation is `libsodium`'s — so the same
    # hand-named payload travels here.
    #
    # `tkinter` is the Wizard's, and it is named for the reason above and one
    # more: the module that reaches it does so INSIDE a function, because a
    # machine with no display has to be answered and not crashed on
    # (`bill_deploy/wizard.py`), and a payload decided by an import that only
    # happens at run time is a payload this file has to say out loud. Its hook
    # is what drags `_tkinter` and the Tcl/Tk libraries in with it (the
    # docstring is where the price is declared).
    hiddenimports=["_cffi_backend", "tkinter"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # The suite has no business inside the binary, here either.
    excludes=["bill.tests", "bill_deploy.tests"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="bill-deploy",
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
