// theme — the look the page wears, and the TWO things chosen about it: WHICH
// theme, and WHICH SIDE of it.
//
// The SAME keys (`at.theme`, `at.dark`) and the SAME three states of the side.
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

// The THREE states of the side. A fourth, `theme` — "let the theme answer
// its own declared side" — existed until 2026-10-04 and is gone: it only
// ever paid for itself on `at`, and `at` wears light and dark by a person's
// own choice like every other theme now does.
export const DARK_STATES = ["system", "light", "dark"] as const;
export type DarkState = (typeof DARK_STATES)[number];

const SYSTEM_DARK = window.matchMedia("(prefers-color-scheme: dark)");

function link(): HTMLElement | null {
  return document.getElementById("theme");
}

function baseLink(): HTMLElement | null {
  return document.getElementById("base");
}

// THE SYSTEM BARS WEAR THE CANVAS of the theme and the side on screen. The
// value is READ OFF the theme's CSS (`--surface-canvas`), the same reading
// `js/boot.js` does: one palette, the CSS's. The two files repeat it ON
// PURPOSE, as they already repeat the `at.theme`/`at.dark` keys — the boot is
// classic and cannot import from here.
function paintBars(): void {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (!meta) return;
  const canvas = getComputedStyle(document.documentElement)
    .getPropertyValue("--surface-canvas").trim();
  if (canvas) meta.setAttribute("content", canvas);
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

export function darkOn(): boolean {
  const state = darkState();
  return state === "system" ? SYSTEM_DARK.matches : state === "dark";
}

// What is on screen: the saved choice, else the server's default, else the first
// declared — the SAME order the server resolves, so the page and the CSS that
// arrives agree about which theme is up.
export function activeTheme(): ThemeRow | null {
  return themeRow(savedTheme()) || themeRow(store.theme) || store.themes[0] || null;
}

// WHICH SIDE IS ON SCREEN, for THIS theme (2026-10-04). Most themes answer
// only one side — `row.sides` says which, read off the files the server
// actually found — and a theme with one side wears it no matter what the
// person's light/dark preference is: there is nothing there to choose from.
// Only a theme with both (only `at`, today) asks `darkOn()`.
function activeSide(row: ThemeRow | null): boolean {
  if (row && row.sides.length === 1) return row.sides[0] === "dark";
  return darkOn();
}

export function applyTheme(): ThemeRow | null {
  const row = activeTheme();
  const node = link();
  const dark = activeSide(row);
  themeState.dark = dark;
  themeState.id = row ? row.id : null;
  if (!row || !node) return row;
  const params: string[] = [];
  if (savedTheme()) params.push("theme=" + encodeURIComponent(row.id));
  if (dark) params.push("dark");
  const href = "/theme.css" + (params.length ? "?" + params.join("&") : "");
  if (node.getAttribute("href") !== href) {
    node.setAttribute("href", href);
    // The stylesheet on screen is still the OLD one when the `href` just
    // moved, so the colour is read when the new one lands (and on `error`,
    // for the same reason the boot waits for it there).
    node.addEventListener("load", paintBars, { once: true });
    node.addEventListener("error", paintBars, { once: true });
  } else {
    // The sheet already applied is this href's: nothing to wait for.
    paintBars();
  }
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
