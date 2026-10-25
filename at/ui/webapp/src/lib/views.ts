// views — which page the panel shows, and how one walks between them.
//
// The rule the rest stands on: a page is a FRAME — the VIEW it belongs to (a
// table's key, or `project:<id>`) and the record open in it. It is the pair
// `at.select` stores, so the path is DATA and outlives the reload along with
// the page it leads to.

import { reactive } from "vue";
import type { Component } from "vue";
import { store, tableOf, word } from "./store";
import { remember } from "./prefs";

const DEPTH = 20; // a path deeper than this is no longer a path

// The page of the tasks no project claims: a view of its own, so a reload lands
// there too. It names no PROJECT — it is the node that is not one.
export const ORPHANS_KEY = "orphans";

// THE SETTINGS SCREEN'S OWN KEY, shared by the panel (`Sidebar.vue`) and the
// shortcut table (`shortcuts.ts`) — one string, not two that could drift.
export const SETTINGS_KEY = "settings";

// THE BOARD: every task across every project that is not yet closed, as a row
// of columns — one per status — a card moved between them by dragging it. It
// sits right after ORPHANS in the panel (`Sidebar.vue`), the same tree it is
// one more door out of, and it is a VIEW of its own for the same reason
// ORPHANS is: a reload has to land there too.
export const BOARD_KEY = "board";

// THE SECTION'S OWN PAGE, AND THE SECTION IS THE FOLD. There is no item called
// "overview": the panel's folds ARE its sections, and a section's head is
// SELECTABLE — clicking TASKS opens and closes the tree under it and opens the
// tasks screen, which is one gesture over one row because the row is one thing.
// The key is the fold's own id, so the address of a section is the name of the
// section (`/tasks`), and the next fold to get a page gets it for free (FILES).
//
// It is a summary of what the folder holds, drawn from tables that already
// exist (`task`, `project`) — it invents no data of its own, only a different
// READ of the same rows KindView already fetches.
export const TASKS_KEY = "tasks";

// THE OTHER TWO SECTIONS WITH A SCREEN, by the same design: the key is the
// fold's id, so the address is the section's own name (`/files`, `/tables`), and
// the section has no step above it — it IS the first step of the band.
export const FILES_KEY = "files";
export const TABLES_KEY = "tables";

// A SEGUNDA PORTA DA TABELA `task` (TASK-175): a árvore de projetos abre `task`
// puro, com o popup da TASK-173; o card da seção Tabelas abre ESTA chave, outro
// endereço para o MESMO dado — e é o endereço que diz qual modo, já que não há
// outro sinal que sobreviva ao reload (`nav` guarda só `{view, id}`).
export const TABLES_TASK_KEY = "tables:task";

// A SEÇÃO DE LEMBRETES (TASK-164), pela mesma regra das outras: a chave é o
// nome da seção, e o endereço dela é `/reminders`. Ela NÃO é uma dobra — é uma
// linha só, entre Arquivos e Cofre — mas é uma seção com tela própria, e a
// chave é dela.
export const REMINDERS_KEY = "reminders";

// A SEÇÃO DE NOTAS (TASK-198), pela mesma regra das outras: a chave é o nome
// da seção, e o endereço dela é `/notes`. Ela É uma linha só, entre Lembretes e
// Cofre — e a tela que mora atrás dela é a da TABELA `note`, lida pela porta
// genérica: a seção não é uma tabela de nome próprio, é a tabela `note`
// mostrada do jeito que uma seção mostra.
export const NOTES_KEY = "notes";

// O COFRE NÃO TEM CHAVE DE VIEW (2026-10-05). Ele teve uma tela própria
// (TASK-156) — a quarta dobra, irmã de Arquivos —, e ela saiu: era a mesma
// árvore do painel numa página só, "sem necessidade de existir". O que o
// Cofre oferece de verdade, abrir um arquivo selado, não é uma view — é uma
// camada por cima da tela que estiver de pé (`StrongboxViewer`,
// `lib/strongbox`), então a quarta dobra é só uma dobra.

// The interpreter's chat, which is a view of the page like the others — and one
// the page does not OFFER when the interpreter is off (`store.interpreter`),
// because turning it off takes the chat away and an address that still opened one
// would be the page offering what the switch took.
export const CHAT_KEY = "chat";

// THE TWO PREFIXES `note()` sorts a view by (TASK-126), and `App.vue`'s own
// section band reads the same two — one pair, not two that could drift apart.
export const FILE_PREFIX = "file:";
export const PROJECT_PREFIX = "project:";

// THE WRITE TAB'S OWN KEY (2026-10-05): a file opens to READ in the panel it
// was clicked from, and to WRITE in a page of its own, with no panel at all —
// `App.vue` renders NOTHING else once this prefix is the view on screen, which
// is what lets the field take the whole window instead of the card the panel
// gives it. It is a view like `file:`'s, not a mode of it: a bookmark, a
// link sent to a phone, or a browser's own "open in new tab" all have to land
// on the one page that IS the field, the same way `file:kb/note.md` always
// lands on the one page that reads it.
export const WRITE_PREFIX = "write:";

// THE WEBAPP'S OWN SURFACE FOR THE INTERPRETER IS BACK ON (2026-10-03). It was
// off from 2026-09-27 while the feature stood unfinished — no real path to the
// assist, nothing for a sentence Jev could still save to become but a flat
// refusal. TASK-180, fatia 3/3 closed that gap (`/api/ask`'s own `main_key`,
// the Control Panel's switch and mode), so the one line this constant always
// was is flipped. The CORE's switch (`store.interpreter`) is a different
// thing and is untouched by this — a folder can still be asked from the
// `cli` with the WebApp's own surface off, and still can with it on.
export const NLU_UI_ENABLED = true;

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

// THE BAND SAYS WHERE THE PAGE IS, and it says it as a TRAIL: the section, and
// then the way in — `Tarefas › WebApp`, `Arquivos › Notas › uma nota.md`,
// `Tabelas › Audit`. It used to say a COUNT ("17 record(s)"), which named the
// contents of a page without ever naming the page, and four different screens
// came out with the same band (the report: "esses números de topbar são
// péssimos"). A count is not a place, and the band is the one line a person
// reads to know where they are.
//
// THE PAGE WRITES ITS OWN STEPS. It is the only side that knows the name of the
// thing it is showing — a project's title, a path's segments, a table's name —
// and the shell writes the SECTION, because the section is a fact of the VIEW
// and not of the page (`App.vue`).
export const ui = reactive({
  trail: [] as string[],
  // A DOOR PER STEP of `trail`, same positions (`null` = a step that is only
  // text). Set by `setTrailLinks` AFTER `setTrail`, which clears it.
  trailLinks: [] as ((() => void) | null)[],
});

export function setTrail(...steps: (string | null | undefined)[]): void {
  ui.trail = steps.filter((step): step is string => Boolean(step && step.trim()));
  ui.trailLinks = [];
}

export function setTrailLinks(links: ((() => void) | null)[]): void {
  ui.trailLinks = links;
}

// THE FOLDER THE FILES BROWSER IS IN, as segments (`[]` = the root). Module
// state, so a page that leaves the browser (a file opened from it) can come
// back to the SAME folder: the crumbs of the header and the voltar of the file
// both go through `openFolder`, and `FilesView.vue` reads/writes `filesFolder`.
export const filesFolder = reactive({ segments: [] as string[] });

export function openFolder(segments: string[]): void {
  filesFolder.segments = [...segments];
  open(FILES_KEY, null);
}

// THE FOLDER IS IN THE ADDRESS (B-27): `/files/Notas/Diario`. Moving between
// folders inside the browser is a REAL history step (`pushState`), so the
// browser's Back returns to the folder that was seen; `push = false` is the
// correction of a place that no longer exists (`replaceState`).
export function stepFolder(segments: string[], push = true): void {
  filesFolder.segments = [...segments];
  const path = addressOf(FILES_KEY, null);
  if (location.pathname === path) return;
  if (push) history.pushState(null, "", path);
  else history.replaceState(null, "", path);
}

// Back/forward over those steps: the address says the folder, the page follows.
// Only addresses of the files section are read; any other is not ours.
export function folderOfAddress(pathname: string): string[] | null {
  let parts: string[];
  try {
    parts = decodeURIComponent(pathname).split("/").filter(Boolean);
  } catch {
    return null;
  }
  return parts[0] === FILES_KEY ? parts.slice(1) : null;
}

window.addEventListener("popstate", () => {
  const folder = folderOfAddress(location.pathname);
  if (!folder) return;
  filesFolder.segments = folder;
  if (nav.current?.view !== FILES_KEY) {
    nav.current = { view: FILES_KEY, id: null };
    nav.path.length = 0;
  }
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

// A PAGE'S OWN FIRST READ. The boot (`App.vue`) waits for the STATE, but a page
// that also reads for itself — a file's text (`WriteView`), a table's rows
// (`KindView`) — is still filling when the shell would reveal, and revealing
// there shows the page EMPTY for a beat before its content lands. A page that
// reads on its own says so the moment it is set up (`pageReadsOnItsOwn`, called
// synchronously, before the boot decides whether it has anything to wait for)
// and calls `pageLoaded` when that read settles — win or lose.
//
// The boot RACES the wait against a short timeout, so a read that never lands
// (a slow disk, a hung request) cannot hold the page shut forever: the shell
// shows the error it fell back to instead of nothing at all.
let selfReading = false;
let settlePageLoad: (() => void) | null = null;
let loadingPage: Promise<void> = Promise.resolve();

export function armPageLoad(): void {
  selfReading = false;
  loadingPage = new Promise<void>(resolve => { settlePageLoad = resolve; });
}

export function pageReadsOnItsOwn(): void {
  selfReading = true;
}

export function pageReading(): boolean {
  return selfReading;
}

export function pageLoaded(): void {
  settlePageLoad?.();
  settlePageLoad = null;
}

export function pageLoad(): Promise<void> {
  return loadingPage;
}

// A page that could not be drawn says so where the page's own words go — the
// panel keeps whatever it was showing.
export function showError(err: Error): void {
  setTrail(`${word("error")} ${err.message}`);
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
//
// `startsWith` ONLY APPLIES WHEN THE ENTRY HAS A `prop` (TASK-175): that is the
// mark of a REAL prefix, one with a REST after it (`project:3`, `file:kb/x.md`).
// A single-key registration (`tables`, `settings`, `actor`...) has no rest, and
// treating it as a prefix too is what let `tables:task` (TASK-175's own second
// door into `task`) match the bare `tables` entry by accident — "tables:task"
// DOES start with "tables", and nothing about that string said it should count.
export function viewFor(view: string): [string, Component, string | null] | null {
  for (const [prefix, entry] of views) {
    if (view === prefix || (entry.prop && view.startsWith(prefix))) return [prefix, entry.component, entry.prop];
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

// THE LAST VIEW OF EACH CATEGORY, for the ESC-armed shortcuts (`shortcuts.ts`)
// to reopen. Kept here and not in a listener of its own: `note()` is already
// the ONE place every navigation passes through — `markPage`, `back` and
// `resumePath` all call it — so a second hook elsewhere would have to
// rediscover which calls count as a visit.
let lastFileView: string | null = null;
let lastTaskView: string | null = null;

export function lastFile(): string | null {
  return lastFileView;
}

export function lastTasks(): string | null {
  return lastTaskView;
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
  if (view.startsWith(FILE_PREFIX)) lastFileView = view;
  else if (view.startsWith(PROJECT_PREFIX) || view === ORPHANS_KEY || view === store.types.task) lastTaskView = view;
  // THE WRITE PAGE IS NOT A PLACE THE SHELL RETURNS TO (2026-10-05). It draws
  // with NO shell at all — no panel, no topo, no voltar (`WriteView.vue`,
  // `App.vue`'s `isWrite`) — and it is meant to be opened in a tab of its own.
  // But `localStorage` is shared across tabs: a visit to the write tab would
  // remember `write:<path>` as "the last place", and the next reload of the
  // MAIN tab would open the shell-less write page with no way out. The address
  // still follows the page (`/write/<path>`, a reload or a bookmark lands
  // there); only the REMEMBER is skipped.
  if (!view.startsWith(WRITE_PREFIX)) remember(view, id, nav.path);
  const path = addressOf(view, id);
  if (location.pathname !== path) history.replaceState(null, "", path);
}

// EXPORTED (2026-10-05): the write tab builds ITS OWN address from a view key
// the same way a reload does, and a second copy of this arithmetic is the copy
// that drifts the day a key's shape changes.
export function addressOf(view: string, id: number | null): string {
  const pieces = view.split(":").join("/").split("/").map(encodeURIComponent);
  if (id !== null) pieces.push(String(id));
  if (view === FILES_KEY) pieces.push(...filesFolder.segments.map(encodeURIComponent));
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
