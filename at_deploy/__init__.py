"""`at-deploy` — the environment of §7, as a second artifact (item 27).

`at-cli` is a file that gives its word about privilege, and the word was weaker
than it could be: it *can* ask for elevation. The environment half of the product
— Podman, the VPN, the DNS, the gate's containers, the edge, and the
transactional switch between the two paths — is a DEPLOYMENT concern, and it is
the half that needs the machine. Splitting it away leaves a file whose whole
privilege story can be read by looking at what it is: **`at-cli` has no elevation
code path at all**, and §3's closed list names this artifact as the one that
asks.

**The boundary between the two is the folder's STATE and not an API.** Both
artifacts read the same Working Folder; this one is the one that WRITES the
environment's state — `App/services/`, the pins, and the gate secret — and `at-cli`
is the one that keeps reading `authenticator` and the gate secret with this
artifact absent, refusing the Forms on the container path and closing when the
gate falls. §3's division is the shape of it: the deploy tool is what a person
uses to build and to move the environment, and `at-cli` is what serves the folder.

**The shared core is one source, not two.** `paths`, `i18n`, `files` and the
table engine live in `at/`, and this package imports them: the deploy carries
the core the same way `at-cli` does, and neither of them carries a copy of it. The
direction is one-way — `at_deploy` imports `at`, and `at` imports nothing
of this package, which is the property the suite affirms.
"""

from at import __version__

# The deploy is the same product's second artifact, and it wears the same
# version: there is one release, and it publishes both files (§3, item 27).
__all__ = ["__version__"]
