"""`python3 -m bill` — the module door into the same CLI the binary opens."""

from __future__ import annotations

import sys

from bill.ui.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
