// nav — the left panel: open, or collapsed into the rail.
//
// The SAME key and classes (`bill.nav`, `nav-rail`, `nav-open`), which `base.css`
// reads and `js/boot.js` applies before the paint.
//
// The WINDOW width is not a saved choice: whoever never chose gets the rail when
// the window is narrow, and that half belongs to the media query (base.css,
// section 5) — the same state by two doors, and whoever is in front wins.

import { reactive } from "vue";
import { loadPrefs, savePrefs } from "./prefs";

export const NAV_KEY = "bill.nav";
export const RAIL_CLASS = "nav-rail";
export const OPEN_CLASS = "nav-open";

// The SAME number as section 5 of `base.css`: here it answers "is the window
// narrow now?", which is what the button needs to know to know what the click
// does.
export const NARROW = window.matchMedia("(max-width: 960px)");

export function navState(): "rail" | "open" | null {
  const prefs = loadPrefs(NAV_KEY);
  return prefs.state === "rail" || prefs.state === "open" ? prefs.state : null;
}

// The two classes EXCLUDE each other, and with no choice neither of them stays:
// the empty hands the decision back to the width — the media query collapses,
// and only it.
export function applyNav(): void {
  const html = document.documentElement;
  html.classList.toggle(RAIL_CLASS, navState() === "rail");
  html.classList.toggle(OPEN_CLASS, navState() === "open");
}

// What is on SCREEN now, adding the two doors: the choice, when it exists, and
// the width when it does not. It is what the click inverts.
export function railedNow(): boolean {
  const state = navState();
  if (state === "rail") return true;
  if (state === "open") return false;
  return NARROW.matches;
}

// WHAT IS ON SCREEN, AS STATE THE PAGE CAN REACT TO (2026-09-22). There are TWO
// doors to the same answer — the collapse button and the scrim — and they live in
// different components (the button is a row of the panel's foot, the scrim is the
// App's). A `ref` on either side would go stale the moment the OTHER one was
// clicked, and the button's `aria-expanded` is a claim about what is on screen:
// it cannot be a claim one of the two doors is allowed to falsify. So the answer
// is held ONCE, here, where both doors already come for the write.
export const navRail = reactive({ railed: railedNow() });

export function syncNav(): void {
  navRail.railed = railedNow();
}

export function toggleNav(): void {
  savePrefs(NAV_KEY, { state: railedNow() ? "open" : "rail" });
  applyNav();
  syncNav();
}

export function watchNav(onChange: () => void): void {
  NARROW.addEventListener("change", onChange);
}
