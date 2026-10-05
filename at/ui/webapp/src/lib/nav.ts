// nav — the left panel: an overlay drawer, shut unless a person opens it.
//
// The SAME key and classes (`at.nav`, `nav-rail`, `nav-open`), which `base.css`
// reads and `js/boot.js` applies before the paint.
//
// WITH NO SAVED CHOICE THE PANEL IS SHUT (2026-10-05). It used to default open
// on a wide window and shut on a narrow one — the panel pushed `main` aside on
// the wide side, so there was a width worth defaulting by. It is a drawer over
// the page now, at every width, and a drawer nobody asked to see yet has
// nothing to default open FOR.

import { reactive } from "vue";
import { loadPrefs, savePrefs } from "./prefs";

export const NAV_KEY = "at.nav";
export const RAIL_CLASS = "nav-rail";
export const OPEN_CLASS = "nav-open";

export function navState(): "rail" | "open" | null {
  const prefs = loadPrefs(NAV_KEY);
  return prefs.state === "rail" || prefs.state === "open" ? prefs.state : null;
}

export function applyNav(): void {
  const html = document.documentElement;
  html.classList.toggle(RAIL_CLASS, navState() === "rail");
  html.classList.toggle(OPEN_CLASS, navState() === "open");
}

// What is on SCREEN now. Anything but an explicit "open" is shut.
export function railedNow(): boolean {
  return navState() !== "open";
}

// WHAT IS ON SCREEN, AS STATE THE PAGE CAN REACT TO (2026-09-22). There are TWO
// doors to the same answer — the corner button and the scrim — and they live in
// different components (the button is in `App.vue`'s header, the scrim is the
// App's own layer). A `ref` on either side would go stale the moment the OTHER
// one was clicked, and the button's `aria-expanded` is a claim about what is on
// screen: it cannot be a claim one of the two doors is allowed to falsify. So
// the answer is held ONCE, here, where both doors already come for the write.
export const navRail = reactive({ railed: railedNow() });

export function syncNav(): void {
  navRail.railed = railedNow();
}

export function toggleNav(): void {
  savePrefs(NAV_KEY, { state: railedNow() ? "open" : "rail" });
  applyNav();
  syncNav();
}
