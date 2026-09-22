// views — which page the panel shows, and how one walks between them.
//
// The rule the rest stands on: a page is a FRAME — the VIEW it belongs to (a
// table's key, or `project:<id>`) and the record open in it. It is the pair
// `bill.select` stores, so the path is DATA and outlives the reload along with
// the page it leads to.

import { reactive } from "vue";
import type { Component } from "vue";
import { store, tableOf, word } from "./store";
import { remember } from "./prefs";

const DEPTH = 20; // a path deeper than this is no longer a path

// The page of the tasks no project claims: a view of its own, so a reload lands
// there too. It names no PROJECT — it is the node that is not one.
export const ORPHANS_KEY = "orphans";

export interface Frame {
  view: string;
  id: number | null;
}

// The panel shows ONE page at a time: `current` is the one on screen, `path` are
// the ones behind it. `tick` changes when the SAME page is redrawn.
export const nav = reactive({
  current: null as Frame | null,
  path: [] as Frame[],
  tick: 0,
});

// The band's title. A table writes the COUNT; the other pages write text. No page
// invents a word — they come from the catalog.
export const ui = reactive({
  title: "",
  bold: "",
  rest: "",
  count: null as { shown: number; hidden: number } | null,
});

// THE PANEL'S NUMBER for the view ON SCREEN. The count the server sends is the
// STORE'S total, and the filter that hides rows is the person's — the server
// cannot know it, so the filtered count comes from whoever holds the rows: the
// view drawing them.
export const liveCounts = reactive<Record<string, number>>({});

export function setLiveCount(view: string, n: number): void {
  if (view) liveCounts[view] = n;
}

export function countOf(view: string, total: number): number {
  const live = liveCounts[view];
  return live === undefined ? total : live;
}

export function setTitle(text: string): void {
  ui.title = text || "";
  ui.bold = "";
  ui.rest = "";
  ui.count = null;
}

export function setHeading(bold: string, rest: string): void {
  ui.bold = bold || "";
  ui.rest = rest || "";
  ui.title = "";
  ui.count = null;
}

export function setCount(shown: number, hidden: number): void {
  ui.count = { shown, hidden };
  ui.title = "";
  ui.bold = "";
  ui.rest = "";
}

// A page that could not be drawn says so where the page's own words go — the
// panel keeps whatever it was showing.
export function showError(err: Error): void {
  ui.title = `${word("error")} ${err.message}`;
  ui.count = null;
}

// --- the page registry ---------------------------------------------------------
// A view that is MORE than a table's table draws its own page, and only its own
// module knows how: it registers itself here (`project:` → the project page).
// Without it, opening a project would open its table.
const views = new Map<string, { component: Component; prop: string | null }>();
const types = new Map<string, string>(); // declared type → view prefix

// `prop` is the name of the prop that receives the REST of the key (`project:3` →
// `id="3"`, `file:kb/note.md` → `path="kb/note.md"`); a page that is a single key
// (`settings`, `orphans`) has no rest and passes `null`.
export function registerView(prefix: string, component: Component, prop: string | null = null): void {
  views.set(prefix, { component, prop });
}

// A DECLARED type → the PREFIX of the view that knows how to draw it (`project`
// → `project:`). Whoever asks is a REFERENCE followed from a table: what it names
// is a PAGE, not a record in a table.
export function registerType(type: string, prefix: string): void {
  types.set(type, prefix);
}

// The entry that claims a view, or null when NO module claims it: a table's own
// table claims nothing — it is what is left over.
export function viewFor(view: string): [string, Component, string | null] | null {
  for (const [prefix, entry] of views) {
    if (view === prefix || view.startsWith(prefix)) return [prefix, entry.component, entry.prop];
  }
  return null;
}

// The PREFIX of the page of a table that declares a type, or null.
export function pagePrefixFor(table: string): string | null {
  const entry = tableOf(table);
  return (entry && entry.type && types.get(entry.type)) || null;
}

// A table's own table is what is left over when nobody claims the view.
export function isKind(view: string): boolean {
  return Boolean(tableOf(view));
}

// --- the path -----------------------------------------------------------------
export function markPage(view: string, id: unknown): void {
  nav.current = { view, id: typeof id === "number" ? id : null };
  note();
}

// The page about to be left goes on the path.
export function leave(): void {
  if (nav.current) nav.path.push({ ...nav.current });
  if (nav.path.length > DEPTH) nav.path.shift();
}

export function freshPath(): void {
  nav.current = null;
  nav.path.length = 0;
}

// Opens a page from the panel: a new path, and the page is the one that enters.
export function open(view: string, id: unknown): void {
  freshPath();
  markPage(view, id);
}

// One step back. With nothing behind it — a record opened straight from a reload,
// with no saved path —, the step is the list the record belongs to.
export function back(fallback?: () => void): void {
  const frame = nav.path.pop();
  if (frame) {
    nav.current = frame;
    note();
    return;
  }
  if (fallback) fallback();
}

// The path the saved page came with, put back where it was.
export function resumePath(frames: unknown): void {
  nav.path.length = 0;
  for (const frame of Array.isArray(frames) ? frames : []) {
    if (frame && typeof frame.view === "string") nav.path.push(frame as Frame);
  }
  note();
}

// THE ADDRESS FOLLOWS THE PAGE. Every view the person can reach has one, and it
// is the view's own key with `/` where the key has `:` — `/task`, and `/task/3`
// when a record is open in it, `/project/2`, `/file/kb/note.md`. A link copied
// from the browser opens what was being read. It is `replace` and not `push`,
// because the step back the page already has is its own path (`nav.path`), and
// two histories would disagree.
function note(): void {
  if (!nav.current) return;
  const { view, id } = nav.current;
  remember(view, id, nav.path);
  const path = addressOf(view, id);
  if (location.pathname !== path) history.replaceState(null, "", path);
}

function addressOf(view: string, id: number | null): string {
  const pieces = view.split(":").join("/").split("/").map(encodeURIComponent);
  if (id !== null) pieces.push(String(id));
  return "/" + pieces.join("/");
}

// The signal that the data changed: the same page stays on screen, but its data
// is old. Whoever listens is whoever knows what it showed.
export function poke(): void {
  nav.tick++;
}

// The page on screen, so the panel lights the right line.
export function isCurrent(view: string): boolean {
  return !!(nav.current && nav.current.view === view);
}

// A reference was clicked: the record it names opens in ITS table, and the page
// it was clicked on goes on the path first — that is what makes the step back
// land on the table the person was reading. A table that declares a TYPE with a
// page of its own IS that page: a reference to a project opens the project.
export function openRef(ref: { key: string; id: number }): void {
  leave();
  const prefix = pagePrefixFor(ref.key);
  if (prefix) markPage(prefix + ref.id, null);
  else markPage(ref.key, ref.id);
}
