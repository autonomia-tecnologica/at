# Functionalities

A functionality is what the [glossary](glossary.md) defines: a capability the person recognizes, with levels and dependencies. The rule that governs it is the one in `README` §3 (The security posture). This document repeats neither — it carries what belongs to each functionality: the levels, what each level costs, and what it drags.

## What exists today

The floor is `S`. Every functionality is born there, and what brings it down is always a choice. Every graded function the founding document names sits at `S` today, and writing that down is what keeps the first letter from looking arbitrary.

## Push notifications

The first functionality with more than one way of being used. The service is `notifier`, and today whoever fulfils it is `ntfy` (`README` §7f).

**The levels, and what each one costs:**

| level | what it is | grade |
|---|---|---|
| off | nothing is installed, and there is no notification at all | `S` |
| installed | the `ntfy` container exists and runs | `S` |
| as a service | Bill has it configured | `S` |
| read-only token | the token only reads | `S` |
| read-and-write token, no second factor | the token reads and writes, and nothing beyond it confirms who is using it | `A` |
| the same, with the token service (TOTP) | the second factor closes the token | `S` |

**What it drags.** Notification drags installing `ntfy`; installing drags having it as a configured service, because installed but not configured notifies nobody; and the open token drags enabling the token service (TOTP).
