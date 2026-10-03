// theme — the look the page wears, and the TWO things chosen about it: WHICH
// theme, and WHICH SIDE of it.
//
// The SAME keys (`at.theme`, `at.dark`) and the SAME four states of the side.
// The `link` this module moves is `#theme`, and whoever moves it BEFORE the first
// paint is `js/boot.js` (classic, in the `head`), which repeats these keys on
// purpose — it cannot import from here.
//
// The theme is THIS browser's preference, never a flag of the server: the page
// asks by ID (`/theme.css?theme=<id>&dark`) and the server resolves it by LOOKUP
// against the declared vocabulary — an id that names no theme falls back, it
// never becomes a path.

import { reactive } from "vue";
import { store, type ThemeRow } from "./store";
import { loadPrefs, savePrefs } from "./prefs";

export const themeState = reactive({ dark: false, id: null as string | null });

export const THEME_KEY = "at.theme";
export const DARK_KEY = "at.dark";

// The FOUR states of the side. `theme` is not a side: it is "let the THEME
// answer", and the answer belongs to the theme because a side is part of what a
// theme IS. Every other theme declares nothing, and nothing means light.
export const DARK_STATES = ["system", "theme", "light", "dark"] as const;
export type DarkState = (typeof DARK_STATES)[number];

const SYSTEM_DARK = window.matchMedia("(prefers-color-scheme: dark)");

function link(): HTMLElement | null {
  return document.getElementById("theme");
}

function baseLink(): HTMLElement | null {
  return document.getElementById("base");
}

export function themeRow(id: string | null): ThemeRow | null {
  if (!id) return null;
  return store.themes.find(row => row.id === id) || null;
}

// The theme the person chose, when it is still a DECLARED one. A preference can
// outlive the theme it names — the vocabulary is data — and a stale id is not an
// error: it is simply not a choice any more, and the default answers.
export function savedTheme(): string | null {
  const id = loadPrefs(THEME_KEY).id;
  return themeRow(typeof id === "string" ? id : null) ? (id as string) : null;
}

export function darkState(): DarkState {
  const state = loadPrefs(DARK_KEY).state;
  return (DARK_STATES as readonly string[]).includes(state) ? (state as DarkState) : "system";
}

// THE SIDE A THEME WEARS BY ITSELF — the answer to the `theme` state. Who
// declares it is the theme (`side` in the registry), and a theme that declares
// nothing means LIGHT.
export function themeSide(): "light" | "dark" {
  const row = activeTheme();
  return row && row.side === "dark" ? "dark" : "light";
}

export function darkOn(): boolean {
  const state = darkState();
  if (state === "theme") return themeSide() === "dark";
  return state === "system" ? SYSTEM_DARK.matches : state === "dark";
}

// What is on screen: the saved choice, else the server's default, else the first
// declared — the SAME order the server resolves, so the page and the CSS that
// arrives agree about which theme is up.
export function activeTheme(): ThemeRow | null {
  return themeRow(savedTheme()) || themeRow(store.theme) || store.themes[0] || null;
}

export function applyTheme(): ThemeRow | null {
  const row = activeTheme();
  const node = link();
  themeState.dark = darkOn();
  themeState.id = row ? row.id : null;
  // THE ANSWER IS ONLY WRITTEN WHEN WHOEVER KNOWS IT HAS ARRIVED. What the boot
  // reads is below, and it can only be answered against the vocabulary the
  // server sends — so a call with `store.themes` still empty (the entrance,
  // which is drawn before `/api/state` is ever asked) answers `light` for every
  // theme, and writing that down would corrupt the preference in silence and
  // paint the wrong side on the NEXT load.
  if (!row || !node) return row;
  // WHAT THE BOOT READS. `js/boot.js` runs BEFORE the first paint, and by then
  // the page has no vocabulary to look a theme up in, so it cannot answer "which
  // side does this theme wear?". The answer is written down HERE, where it
  // exists, and read THERE, where it does not. It is only written under the
  // `theme` state — the other three are the boot's own.
  if (darkState() === "theme") {
    const side = themeState.dark ? "dark" : "light";
    if (loadPrefs(DARK_KEY).side !== side) savePrefs(DARK_KEY, { state: "theme", side });
  }
  const params: string[] = [];
  if (savedTheme()) params.push("theme=" + encodeURIComponent(row.id));
  if (darkOn()) params.push("dark");
  node.setAttribute("href", "/theme.css" + (params.length ? "?" + params.join("&") : ""));
  // THE SECOND LINK, THE SAME DOOR, AND THE SAME QUERY (2026-09-28). Every
  // theme in the registry names no `base` of its own today and reads
  // `base.css` — but the `"base"` field still exists for a theme that wants a
  // second vocabulary, and it was tempting to leave the query off: "`/base.css`
  // with no query is what it always was". It is not: with no query the server
  // resolves its OWN default theme, and that default is `at` (through
  // `AT_THEME` or the registry) — so a browser wearing a theme that one day
  // declares its own `base` would be served `at`'s instead. The query is what
  // says WHICH theme's base this is, so it goes whenever this browser has
  // chosen one — the most any link can know — and it stays off when the
  // choice is the server's, because then the server is right by definition.
  const base = baseLink();
  if (base) {
    const chosen = savedTheme();
    base.setAttribute("href", "/base.css" + (chosen ? "?theme=" + encodeURIComponent(row.id) : ""));
  }
  return row;
}

export function chooseTheme(id: string): ThemeRow | null {
  const row = themeRow(id);
  if (!row) return null;
  savePrefs(THEME_KEY, { id: row.id });
  return applyTheme();
}

export function chooseDark(state: DarkState): ThemeRow | null {
  savePrefs(DARK_KEY, { state: (DARK_STATES as readonly string[]).includes(state) ? state : "system" });
  return applyTheme();
}

// Whoever is on "follow the system" swaps side when the OS swaps, and the page
// cannot wait for a reload for that.
export function watchSystem(): void {
  SYSTEM_DARK.addEventListener("change", () => {
    if (darkState() === "system") applyTheme();
  });
}
