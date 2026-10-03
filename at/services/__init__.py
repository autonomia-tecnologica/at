"""The two programs the BINARY carries: the Caddy (§3, §6) and `gitleaks` (item 51).

This package used to hold the whole environment of §7 — Podman, the VPN, the
DNS, the identity provider, the notifier, the orchestration and the switch. That
half left `at-cli` and became `at-deploy` (item 27), because it is the half that
needs the machine and the only one that asks for elevation: an `at-cli` whose whole
privilege story can be read by looking at what it is.

What is left are four third parties that are not the environment's, and all four
are there for the same reason: §3 pins a package by carrying it, and the artifact
that carries it is where the pin lives.

The first is the Caddy: the process that `at-cli webapp` unpacks into the
folder and puts in front of the WebApp by default, which is the HOSTED path's
TLS (§6). `--no-caddy` is the one way out of it. The container path's Caddy is a container from a pinned image, and it
belongs to the deploy — while the Caddyfile both of them run is written once, in
`caddy.py`, because it is the same Caddy answering the same questions.

**TASK-177 (2026-10-02) added the third: Authelia, the bundle's own gate.**
It comes up with the SAME trigger as the Caddy — no new flag, no container, no
second artifact — and fronts the WebApp exactly the way its container-path
counterpart does (`at_deploy/environment.py`), minus the isolamento por raio de
explosão a container buys (§6: nota `A`, not `S`). `authelia.py` is the
Caddy's own arithmetic once more: a vendored tarball, unpacked on demand, run
as a subprocess of this process tree. (The bundle's notifier was the ntfy, at
its side; it is gone — the notification is the PWA's own Web Push now, and
`core/push.py` is where it lives.)

The fourth is `gitleaks`, the scanner `at-cli secret scan` walks the folder with
(item 51). It travels in `at-cli` only: the deploy has no scanning word, and
embedding it there would pay the megabytes for a door nobody knocks on. The walk
and the answer are `at/core/scanner.py`'s; what lives here is the payload and the
unpacking, which is the Caddy's own arithmetic.
"""
