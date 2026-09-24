"""The one service the BINARY carries: the Caddy (§3, §6).

This package used to hold the whole environment of §7 — Podman, the VPN, the
DNS, the identity provider, the notifier, the orchestration and the switch. That
half left `at` and became `at-deploy` (item 27), because it is the half that
needs the machine and the only one that asks for elevation: an `at` whose whole
privilege story can be read by looking at what it is.

What is left here is the Caddy, and it is not the environment's: it is the
process that `at webapp --include-caddy` unpacks into the folder and puts in
front of the WebApp, which is the HOSTED path's TLS (§6). The container path's
Caddy is a container from a pinned image, and it belongs to the deploy — while
the Caddyfile both of them run is written once, in `caddy.py`, because it is the
same Caddy answering the same questions.
"""
