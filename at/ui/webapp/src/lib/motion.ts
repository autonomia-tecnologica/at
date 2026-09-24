// motion — AT's transitions, and THIS browser's preference that mutes them.
//
// The SAME key (`at.motion`) and the SAME class (`no-motion`), which `base.css`
// already knows how to read and which `js/boot.js` applies before the first
// paint.

import { loadPrefs, savePrefs } from "./prefs";

export const MOTION_KEY = "at.motion";
export const MOTION_CLASS = "no-motion";

// ON is the default: whoever never chose sees the whole at, with the
// transitions. A saved preference counts; a strange value in it counts for
// nothing.
export function motionOn(): boolean {
  return loadPrefs(MOTION_KEY).on !== false;
}

// The ONE door: whoever wants to know how the page looks reads the class the CSS
// reads — not an in-memory copy that can drift from it.
export function applyMotion(on?: boolean): boolean {
  const wanted = on === undefined ? motionOn() : !!on;
  const root = document.documentElement;
  if (root) root.classList.toggle(MOTION_CLASS, !wanted);
  return wanted;
}

export function setMotion(on: boolean): boolean {
  savePrefs(MOTION_KEY, { on: !!on });
  return applyMotion(on);
}
