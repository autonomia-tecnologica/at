# Functionalities

A functionality is what the [glossary](glossary.md) defines: a capability the person recognizes, with levels and dependencies. The rule that governs it is the one in §3 (The security posture). This document repeats neither — it carries what belongs to each functionality: the levels, what each level costs, and what it drags.

## What exists today

The floor is `S`. Every functionality is born there, and what brings it down is always a choice. Every graded function the founding document names sits at `S` today, and writing that down is what keeps the first letter from looking arbitrary.

## Push notifications

The first functionality with more than one way of being used. The service is `notifier`, and today whoever fulfils it is the PWA's own Web Push (§7f): the PWA's service worker subscribes to the browser's push service, and the operating system draws the alert — there is no separate app and no notifier account.

**The levels, and what each one costs:**

| level | what it is | grade |
|---|---|---|
| off | the browser did not subscribe, and there is no notification at all | `S` |
| subscribed | the PWA subscribed to the push service, and AT keeps the subscription | `S` |

**What it drags.** Notification drags the browser's permission, which the person grants on the page itself; and it drags the browser's push service being up, which is a third party's and AT does not control — which is why delivery is best-effort (§7f). **The notifier token this section used to grade died with ntfy**: there is no credential to narrow and no second factor to demand of it.
