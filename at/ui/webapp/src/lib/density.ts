// density — how much room the page gives a row, and THIS browser's preference.
//
// The SAME shape as `motion.ts`: a key (`at.density`), a root attribute
// (`data-density`) that `base.css` reads, and `js/boot.js` applying it before the
// first paint. COMFORTABLE is the default and wears no attribute at all; only
// "compact" is written on the root.

import { loadPrefs, savePrefs } from "./prefs";

export const DENSITY_KEY = "at.density";
export const DENSITIES = ["comfortable", "compact"] as const;
export type Density = (typeof DENSITIES)[number];

export function density(): Density {
  return loadPrefs(DENSITY_KEY).state === "compact" ? "compact" : "comfortable";
}

export function applyDensity(state?: Density): Density {
  const wanted = state === undefined ? density() : state;
  const root = document.documentElement;
  if (root) {
    if (wanted === "compact") root.setAttribute("data-density", "compact");
    else root.removeAttribute("data-density");
  }
  return wanted;
}

export function setDensity(state: Density): Density {
  const wanted: Density = state === "compact" ? "compact" : "comfortable";
  savePrefs(DENSITY_KEY, { state: wanted });
  return applyDensity(wanted);
}
