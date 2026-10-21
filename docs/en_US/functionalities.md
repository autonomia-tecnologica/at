# Functionalities

A functionality is what the [glossary](glossary.md) defines: a capability the person recognizes, with levels and dependencies. The rule that governs it is the one in §3 (The security posture). This document repeats neither — it carries what belongs to each functionality: the levels, what each level costs, and what it drags.

## What exists today

The floor is `S`. Every functionality is born there, and what brings it down is always a choice. Every graded function the founding document names sits at `S` today, and writing that down is what keeps the first letter from looking arbitrary. **Exposure is the function whose grade is the one of what the person configured** — the reach and the gate —, and so it is the first one able to leave `S` with nothing in the product having changed — [Exposure](#exposure).

## Push notifications

The first functionality with more than one way of being used. The service is `notifier`, and today whoever fulfils it is the PWA's own Web Push (§7f): the PWA's service worker subscribes to the browser's push service, and the operating system draws the alert — there is no separate app and no notifier account.

**The levels, and what each one costs:**

| level | what it is | grade |
|---|---|---|
| off | the browser did not subscribe, and there is no notification at all | `S` |
| subscribed | the PWA subscribed to the push service, and AT keeps the subscription | `S` |

**What it drags.** Notification drags the browser's permission, which the person grants on the page itself; and it drags the browser's push service being up, which is a third party's and AT does not control — which is why delivery is best-effort (§7f). **The notifier token this section used to grade died with ntfy**: there is no credential to narrow and no second factor to demand of it.

## Exposure

The function that measures who arrives. It does not look at the path, but at two things: the **reach** — who reaches AT — and the **gate** — what waits for whoever arrives. The hosted path and the container path have no grade of their own: each one receives the grade of what is configured in it, and that is why the same AT on the local loop is `S` in both, and the same AT behind the Caddy without a gate is `A` in both — [The security posture](rules.md#the-security-posture).

**The levels, and what each one costs:**

| level | what it is | grade |
|---|---|---|
| local loop | `127.0.0.1`, and nothing leaves it | `S` |
| private network with a gate (container) | the environment's network, Authelia in front, containers isolated (§7b) | `S` |
| private network with a gate (bundle, no container) | the Caddy's TLS, the vendorized Authelia in the same binary, no container isolation | `A` |
| private network without a gate | off the loop, the Caddy's TLS and Forms, no second factor | `A` |
| public network | reachable from outside the private network | `F` |

**What it drags.** Exposure drags the person's **declaration**: AT measures what is configured and what was declared, and does not measure NAT, VPN or firewall — whoever affirms the network is private is the person, and AT records that. It also drags the **distinction between the path and the configuration**: what holds the bundle at `A` and not at `S` is the lack of container isolation, not the lack of a gate ([Hosted path](paths.md#hosted-path)). And **installing does not move the grade**: an OS package, a loose binary with `at-cli install` or a Windows shim change how the binary arrives, not who reaches it.
