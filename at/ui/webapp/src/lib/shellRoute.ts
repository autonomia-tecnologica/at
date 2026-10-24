// The shell's ROUTE: which page the address / the saved place / the trail say.
// Taken out of `App.vue` (B-17) unchanged.

import { computed } from "vue";
import { store, word, tableOf } from "./store";
import { nav, ui, isKind, viewFor, open, openFolder, markPage, resumePath, CHAT_KEY, NLU_UI_ENABLED, ORPHANS_KEY, BOARD_KEY, FILE_PREFIX, PROJECT_PREFIX, WRITE_PREFIX, TABLES_TASK_KEY } from "./views";
import { loadPrefs, SELECT_KEY } from "./prefs";
import { balloonOn } from "./balloon";
import KindView from "../views/KindView.vue";

// WHEN THE BALLOON FLIES. The first two are not the page's to decide: the CORE's
// switch is on (`store.interpreter` — off, there is no function at all), and this
// browser never turned the balloon off (`balloon.ts`).
//
// The third is the page's own composition, and it is not a rule about the
// interpreter: the balloon exists for the sentence about what is ON THE SCREEN,
// and the chat already carries the box — over the chat it would be the same box
// twice, and a second box is a box nobody reads.
export const balloon = computed(
  () => NLU_UI_ENABLED && store.interpreter && balloonOn.value && nav.current?.view !== CHAT_KEY,
);

// The view PREFIXES that name a record and not a table — the same ones
// `main.ts` registers (`registerView`), read here to know where a page sits.
// `FILE_PREFIX`/`PROJECT_PREFIX` come from `views.ts`, the same two `note()`
// sorts a visit by (TASK-126) — one pair, not two that could drift apart.
const ACTOR_PREFIX = "actor:";
const ROLE_PREFIX = "role:";

// THE FIRST STEP OF THE TRAIL: WHICH SECTION THIS PAGE BELONGS TO. It is the
// shell's to say and not the page's, because it is a fact of the VIEW — a
// project lives in the tasks, a file in the files, a table in the tables — and
// the page it belongs to would have to repeat the mapping to know it.
//
// A PAGE THAT IS ITSELF A SECTION (the tasks screen, Settings, the chat) has no
// section above it, and answers with nothing: then the page's own first step is
// the whole band (`Trail`), and it says its name like any other page.
export const section = computed(() => {
  const view = nav.current?.view || "";
  // `tables:task` É A SEGUNDA PORTA DE `task` (TASK-175): `tableOf` não a
  // reconhece — não é o nome de uma tabela —, e é a mesma seção mesmo assim.
  if (tableOf(view) || view === TABLES_TASK_KEY) return word("tables");        // a table is met in the tables
  if (view.startsWith(FILE_PREFIX)) return word("files");
  if (view.startsWith(PROJECT_PREFIX) || view === ORPHANS_KEY || view === BOARD_KEY) return word("tasks");
  if (view.startsWith(ACTOR_PREFIX) || view.startsWith(ROLE_PREFIX)) return word("settings");
  return "";
});

// The band: the section, and then what the page wrote for itself.
export const trail = computed(() => (section.value ? [section.value, ...ui.trail] : ui.trail));


// A DOOR PER STEP: the page's own links (`ui.trailLinks`, aligned with ITS steps)
// and, for a file, the section step itself — "Arquivos" opens the browser at the
// root. A step without a door stays text.
export function stepLink(i: number): (() => void) | null {
  if (section.value) {
    if (i === 0) return nav.current?.view?.startsWith(FILE_PREFIX) ? () => openFolder([]) : null;
    return ui.trailLinks[i - 1] || null;
  }
  return ui.trailLinks[i] || null;
}

// The title the page header says: the last step of the trail — the page's own
// name. The chat fills the page's height instead of growing it.
export const pageTitle = computed(() => trail.value[trail.value.length - 1] || "");
export const fillsPage = computed(() => nav.current?.view === CHAT_KEY);

// The page the panel shows: whoever draws it is the module that registered itself
// for it, and a table's own table is what is left over when nobody claims the
// view. The shell knows no page by heart.
export const frame = computed(() => {
  const current = nav.current;
  if (!current || !offered(current.view)) return null;
  const claimed = viewFor(current.view);
  if (claimed) {
    const [prefix, component, prop] = claimed;
    const props = prop ? { [prop]: current.view.slice(prefix.length) } : {};
    return { component, props, key: current.view };
  }
  if (isKind(current.view)) {
    return { component: KindView, props: { view: current.view }, key: current.view };
  }
  return null;
});

// THE WRITE TAB IS NOT IN THE SHELL (2026-10-05): no `nav`, no `header`, no
// trail — `frame` alone, filling the window on its own terms
// (`WriteView.vue`'s own CSS). A click that opens `/write/<path>` opens it in
// a tab of its own (`FileView.vue`), so this is never the ONLY way in: it is
// a fact of the VIEW, read the same way from a reload or a bookmark too.
export const isWrite = computed(() => Boolean(nav.current?.view.startsWith(WRITE_PREFIX)));

// The page has ONE address, and it is a PATH. It is the view's own key with `/`
// where the key has `:` — `/task` is the table, `/task/3` is the record open in
// it, `/project/2` and `/file/kb/note.md` are the pages that own those keys. An
// explicit link BEATS what the browser remembered, and a name the page does not
// know is ignored, like a saved one: no address opens an error page. The query
// form (`?view=`) still answers, because a link somebody saved is not a link to
// break.
// A view the page does not OFFER is ignored like a name it does not know — and
// the chat is one when the interpreter is off: the switch takes the chat away, so
// an address that still opened one would be the page offering what is gone.
export function offered(view: string): boolean {
  if (view === CHAT_KEY && (!NLU_UI_ENABLED || !store.interpreter)) return false;
  return Boolean(viewFor(view) || isKind(view));
}

function askedFromUrl(): { view: string; id: number | null } | null {
  const asked = new URLSearchParams(location.search).get("view");
  if (asked) {
    return store.tables.some(kind => kind.key === asked) ? { view: asked, id: null } : null;
  }

  const parts = pathParts();
  if (!parts.length) return null;
  const [head, ...rest] = parts;
  const key = rest.length ? `${head}:${rest.join("/")}` : head;
  if (offered(key)) return { view: key, id: null };
  // A table with no page of its own takes the second piece as the RECORD, which
  // is what clicking the row does.
  if (rest.length === 1 && isKind(head)) {
    return { view: head, id: /^\d+$/.test(rest[0]) ? Number(rest[0]) : null };
  }
  return null;
}

function pathParts(): string[] {
  try {
    return decodeURIComponent(location.pathname).split("/").filter(Boolean);
  } catch {
    // A path the browser could not have written is a path with nothing to open.
    return [];
  }
}

export function showSaved(): void {
  const asked = askedFromUrl();
  if (asked) {
    open(asked.view, asked.id);
    return;
  }
  const saved = loadPrefs(SELECT_KEY);
  const view = String(saved.view || "");
  // A `write:` DOES NOT RESUME (2026-10-05): it is shell-less, and a browser
  // that already saved one as "the last place" before this rule existed would
  // otherwise reopen the stranded write page. The address still opens it
  // (`/write/<path>`); the REMEMBERED one is ignored.
  if (view && !view.startsWith(WRITE_PREFIX) && offered(view)) {
    markPage(view, saved.id);
    resumePath(saved.back); // the saved path comes back: the step back lands where it did
    return;
  }
  if (store.tables.length) open(store.tables[0].key, null);
}

