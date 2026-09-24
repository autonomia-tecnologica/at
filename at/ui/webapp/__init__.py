"""The WebApp — the page, the look it is served with, and the server behind it.

This package is a directory of DATA as much as of code: `assets/` (base.css, the
theme registry, the drawings, `boot.js`), `dist/` (the built Vue page) and
`vendor/` (the pinned typefaces) all travel with it, and `app.py` finds them by
walking up from its own `__file__`. So whatever packs this product has to carry
those three directories at exactly these paths — inside the single binary most of
all, where a missing `dist/` is a 500 on the front page rather than an error at
build time (§3).

`src/`, `node_modules/` and the Vite config are the derivation, not the product:
they stay out of the artifact.
"""
