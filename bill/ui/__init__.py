"""The surfaces — different ways of reaching the same `core` (§5).

`cli` and `wizard` exist today; `webapp` arrives as a container. The rule is
one-way: everything the WebApp and the Wizard offer is reachable from the CLI.

`ask` is not a surface: it is the interpreter's DOOR, and the surfaces that reach
the interpreter read it — the `cli` prints what it answers, the WebApp's box puts
it in the conversation. It lives here because it is made of surfaces' concerns,
and not because it is one.
"""
