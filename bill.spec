# -*- mode: python ; coding: utf-8 -*-
"""The build that derives `dist/bill` — the app's artifact (§3, item 27).

Build it from the repository root, with the PyInstaller version the README pins:

    .venv/bin/pyinstaller --clean --noconfirm bill.spec

**There are two artifacts and two specs**, and this is the one that carries the
folder and the app: the tables, the prose, the interpreter, the WebApp and the
Wizard. The environment of §7 — Podman, the VPN, the containers, the switch and
the only elevation in the product — left this file and is built by
`bill-deploy.spec`, and what keeps it out is the import graph and not a list:
`bill` imports nothing of `bill_deploy`, so PyInstaller never reaches it. The
`excludes` below says so out loud, because the boundary is a decision and not an
accident.

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
    # The Caddy the folder runs when it exposes itself (§3, §6). It travels as
    # the vendor's own tarball and not as the unpacked binary: the artifact that
    # goes inside is the byte-identical release, with its LICENSE beside the
    # binary — and the platform's tarball is the only one this build carries,
    # because a binary frozen for one system runs on that one (§9). Whoever runs
    # from a checkout gets the same payload, unpacked by `services/caddy.py` on
    # demand, so both paths extract from one place.
    ("bill/vendor/caddy", "bill/vendor/caddy"),
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
    # (`pyproject.toml`); it has no business inside the binary either. And the
    # deploy is excluded for the reason above — nothing here imports it, and a
    # build that started carrying §7 again would be `bill` asking for elevation.
    excludes=["bill.tests", "bill_deploy", "bill_deploy.tests"],
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
