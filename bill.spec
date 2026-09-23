# -*- mode: python ; coding: utf-8 -*-
"""The build that derives `dist/bill` — the single binary (§3).

Build it from the repository root, with the PyInstaller version the README pins:

    .venv/bin/pyinstaller --clean --noconfirm bill.spec

The product carries payloads that no import graph can see, so the list below is
written by hand rather than collected: this file is the one place that says what
travels inside the binary. Written by hand also because `bill/ui/webapp/` holds
`node_modules/` and `src/`, which are the DERIVATION and must not travel —
`collect_data_files` would drag 636 directories in.

A source that is missing at build time stops the build; a source that is present
but EMPTY is collected as nothing, in silence — which is how a `dist/` that was
never `npm run build` yields a binary that answers 500 on the front page.

`--onefile` is a distribution choice, not a correctness one: `sys.executable` is
the launched binary under `--onedir` too, so `paths.working_folder()` resolves the
Working Folder to the binary's own folder either way (§3). One file is what
§3 promises, and its price is that the whole payload — Tcl/Tk included —
is re-extracted on every launch.
"""

ENTRY = "bill/__main__.py"

# (source, destination). The destination is where the code looks at runtime, and
# repeating the source's last segment is required, not redundant: a directory
# source lands its CONTENTS in the dest folder, so `("…/vendor", "…/webapp")`
# would scatter the fonts into `webapp/` and lose the `vendor/` the route looks
# up. `bill/ui/webapp/app.py` finds its payload by walking up from its own
# `__file__`, which the frozen loader sets to `<sys._MEIPASS>/bill/ui/webapp/…`
# — the very place these datas land. The two `iterdir()` reads in `bill/i18n`
# and `bill/data/schema` anchor on their package directories, which is the same
# arithmetic one directory up.
DATAS = [
    ("bill/i18n/blocks", "bill/i18n/blocks"),
    ("bill/i18n/vocabulary", "bill/i18n/vocabulary"),
    ("bill/data/defaults", "bill/data/defaults"),
    ("bill/ui/webapp/assets", "bill/ui/webapp/assets"),
    ("bill/ui/webapp/dist", "bill/ui/webapp/dist"),
    ("bill/ui/webapp/vendor", "bill/ui/webapp/vendor"),
]

a = Analysis(
    [ENTRY],
    # SPECPATH, not ".": the datas sources resolve against the spec's own
    # directory, so an absolute `pyinstaller /path/to/bill.spec` from elsewhere
    # must find them the same way `pyinstaller bill.spec` from the root does.
    pathex=[SPECPATH],
    binaries=[],
    datas=DATAS,
    # `_cffi_backend` is the cffi runtime's own C extension, and no import graph
    # reaches it: `nacl.bindings` loads it through cffi, at RUNTIME. The
    # `hook-nacl.py` of `pyinstaller-hooks-contrib` collects `nacl`'s `_lib/`
    # extensions and leaves this one behind, so a binary built without it dies on
    # `import nacl.bindings` — `No module named '_cffi_backend'` — which is the
    # product's one runtime dependency failing to travel. Named here by hand, like
    # every other payload no import graph can see.
    hiddenimports=["_cffi_backend"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # The suite reads the TypeScript sources and is excluded from the wheel
    # (`pyproject.toml`); it has no business inside the binary either.
    excludes=["bill.tests"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="bill",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # No UPX: it is not installed, and a compressed bootloader is one more
    # moving part between this build and a binary that runs (§3).
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
