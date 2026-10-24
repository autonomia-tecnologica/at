# -*- mode: python ; coding: utf-8 -*-
"""The build that derives `dist/at-cli` — the app's artifact (§3, item 27).

Build it from the repository root, with the PyInstaller version the README pins:

    .venv/bin/pyinstaller --clean --noconfirm at-cli.spec

**There are two artifacts and two specs**, and this is the one that carries the
folder and the app: the tables, the prose, the interpreter and the WebApp — the
Control Panel is the WebApp now, with no Wizard beside it (TASK-169, fatia
3/3). The environment of §7 — Podman, the VPN, the containers, the switch and
the only elevation in the product — left this file and is built by
`at-deploy.spec`, and what keeps it out is the import graph and not a list:
`at` imports nothing of `at_deploy`, so PyInstaller never reaches it. The
`excludes` below says so out loud, because the boundary is a decision and not an
accident.

The product carries payloads that no import graph can see, so the list below is
written by hand rather than collected: this file is the one place that says what
travels inside the binary. Written by hand also because `at/ui/webapp/` holds
`node_modules/` and `src/`, which are the DERIVATION and must not travel —
`collect_data_files` would drag 636 directories in.

A source that is missing at build time stops the build; a source that is present
but EMPTY is collected as nothing, in silence — which is how a `dist/` that was
never `npm run build` yields a binary that answers 500 on the front page.

`--onefile` is a distribution choice, not a correctness one: `sys.executable` is
the launched binary under `--onedir` too, so `paths.working_folder()` resolves the
Working Folder to the binary's own folder either way (§3). One file is what
§3 promises, and its price is that the whole payload is re-extracted on every
launch — Tcl/Tk is not part of it (TASK-169, fatia 3/3): the Tkinter window
`at-cli` opened with no word is gone, replaced by the browser panel
(`at.ui.webapp.local`), so this binary carries no `tkinter` import for
PyInstaller to collect.
"""

import sys

ENTRY = "at/__main__.py"

# The file this build derives, and it is a rule of the PLATFORM: `.exe` on
# Windows, `.bin` on Linux and macOS (§3, item 29). `.app` was refused — on the
# Mac it is a BUNDLE, and the product promises one file.
#
# Written by hand because a spec runs before the package is importable: the
# runtime's half of the same pair is declared in `at/core/paths.py`, and
# `at/tests/test_lifecycle.py` holds the two to each other — §7c's WebApp
# container runs this very file by this very name, so a build that named another
# one would be a container that never starts.
NAME = "at-cli.exe" if sys.platform == "win32" else "at-cli"

# (source, destination). The destination is where the code looks at runtime, and
# repeating the source's last segment is required, not redundant: a directory
# source lands its CONTENTS in the dest folder, so `("…/vendor", "…/webapp")`
# would scatter the fonts into `webapp/` and lose the `vendor/` the route looks
# up. `at/ui/webapp/app.py` finds its payload by walking up from its own
# `__file__`, which the frozen loader sets to `<sys._MEIPASS>/at/ui/webapp/…`
# — the very place these datas land. The two `iterdir()` reads in `at/i18n`
# and `at/data/schema` anchor on their package directories, which is the same
# arithmetic one directory up.
DATAS = [
    ("at/i18n/blocks", "at/i18n/blocks"),
    ("at/i18n/vocabulary", "at/i18n/vocabulary"),
    ("at/data/defaults", "at/data/defaults"),
    # The Caddy the folder runs when it exposes itself (§3, §6). It travels as
    # the vendor's own tarball and not as the unpacked binary: the artifact that
    # goes inside is the byte-identical release, with its LICENSE beside the
    # binary — and the platform's tarball is the only one this build carries,
    # because a binary frozen for one system runs on that one (§9). Whoever runs
    # from a checkout gets the same payload, unpacked by `services/caddy.py` on
    # demand, so both paths extract from one place.
    ("at/vendor/caddy", "at/vendor/caddy"),
    # TASK-177 (02/10/2026): o portão do bundle hospedado, vendorizado byte a
    # byte do mesmo jeito que o Caddy acima — subido como subprocesso de
    # `at-cli`, sem container, pelo mesmo gatilho (`--include-caddy`).
    # `services/authelia.py` desempacota na hora. (O notificador do bundle era
    # o ntfy, ao lado; ele saiu — a notificação é o Web Push do PWA, e o
    # `cryptography` que ele traz é uma dependência, não um vendor.)
    ("at/vendor/authelia", "at/vendor/authelia"),
    # O `gitleaks` que a pasta varre quando alguém pede `secret scan` (item 32).
    # Ele viaja pelo mesmo motivo e pela mesma forma que o Caddy acima — o
    # tarball do fornecedor, byte a byte, e não o binário desempacotado —, e
    # só neste artefato: o `at-deploy` não tem palavra de varredura, e embarcar
    # ali pagaria os megabytes por uma porta que ninguém bate.
    ("at/vendor/gitleaks", "at/vendor/gitleaks"),
    # O serviço `spelling-checker` (LanguageTool): um tarball ÚNICO com o JRE
    # mínimo (jlink) e o servidor, montado por `python3 -m release.spelling_checker`
    # e pinado por sha256 no `manifest.json` da pasta. Viaja só neste artefato
    # (o `at-deploy` não tem corretor) e é desempacotado em
    # `App/services/spelling-checker/` por `services/spelling_checker.py`.
    ("at/vendor/spelling-checker", "at/vendor/spelling-checker"),
    # The notices of everything above, and of everything the import graph brings
    # on its own (item 27). The artifact is ONE file, so a third party's licence
    # has nowhere to sit beside it: the texts travel INSIDE, and `at-cli license`
    # is the door out — §3 requires what a licence demands to travel with the
    # thing it licenses, and `at/tests/test_licenses.py` holds the declaration to
    # what actually travels. `LICENSE.md` lands at the bundle's root, which is
    # the same `parents[2]` a checkout gives (`at/core/licenses.py`).
    ("LICENSE.md", "."),
    ("at/vendor/licenses", "at/vendor/licenses"),
    ("at/ui/webapp/assets", "at/ui/webapp/assets"),
    ("at/ui/webapp/dist", "at/ui/webapp/dist"),
    ("at/ui/webapp/vendor", "at/ui/webapp/vendor"),
]

a = Analysis(
    [ENTRY],
    # SPECPATH, not ".": the datas sources resolve against the spec's own
    # directory, so an absolute `pyinstaller /path/to/at-cli.spec` from elsewhere
    # must find them the same way `pyinstaller at-cli.spec` from the root does.
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
    #
    # A GRAMMAR DE CADA IDIOMA, pelo mesmo motivo: `at.nlu.grammar.of` carrega o
    # idioma por `importlib.import_module` DINÂMICO, e o grafo do PyInstaller não
    # segue import dinâmico — sem esta linha o binário sobe, a tabela abre, e uma
    # frase com data ou número (`hoje`, `3`) estoura com `No module named
    # 'at.nlu.grammar.pt_BR'` no meio da rota: o 502 que não diz de onde veio.
    # Um por idioma que `at/i18n.SUPPORTED` nomeia.
    hiddenimports=[
        "_cffi_backend",
        "at.nlu.grammar.pt_BR",
        "at.nlu.grammar.en_US",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # The suite reads the TypeScript sources and is excluded from the wheel
    # (`pyproject.toml`); it has no business inside the binary either. And the
    # deploy is excluded for the reason above — nothing here imports it, and a
    # build that started carrying §7 again would be `at` asking for elevation.
    excludes=["at.tests", "at_deploy", "at_deploy.tests"],
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
