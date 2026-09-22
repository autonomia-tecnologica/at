<script setup lang="ts">
// App — the SHELL and the BOOT.
//
// It emits exactly the DOM `base.css` already styles — the panel's `nav`, the
// content's `main` and the veil —, and the rest is the boot: fetch the state
// from the server, apply the theme, install the page listeners and decide the
// entry page.
//
// The theme and the motion have already entered BEFORE the first paint: whoever
// applies them is `js/boot.js`, a classic script in the `head` — the bill's own,
// on the same origin. Here they are REASSERTED by their owner, and that is what
// guarantees the class and the preference do not drift after a click.

import { ref, computed, onMounted } from "vue";
import { api } from "./lib/api";
import { store, applyState, word } from "./lib/store";
import { nav, ui, isKind, viewFor, open, markPage, poke, resumePath, CHAT_KEY } from "./lib/views";
import { applyTheme, watchSystem } from "./lib/theme";
import { applyMotion } from "./lib/motion";
import { writingState } from "./lib/writing";
import { applyNav, railedNow, toggleNav, watchNav } from "./lib/nav";
import { watchNarrow } from "./lib/breakpoint";
import { loadPrefs, SELECT_KEY } from "./lib/prefs";
import { closePop } from "./lib/pop";
import { balloonOn } from "./lib/balloon";
import Sidebar from "./components/Sidebar.vue";
import Popover from "./components/Popover.vue";
import Balloon from "./components/Balloon.vue";
import KindView from "./views/KindView.vue";

const railed = ref(railedNow());

// WHEN THE BALLOON FLIES. The first two are not the page's to decide: the CORE's
// switch is on (`store.interpreter` — off, there is no function at all), and this
// browser never turned the balloon off (`balloon.ts`).
//
// The third is the page's own composition, and it is not a rule about the
// interpreter: the balloon exists for the sentence about what is ON THE SCREEN,
// and the chat already carries the box — over the chat it would be the same box
// twice, and a second box is a box nobody reads.
const balloon = computed(
  () => store.interpreter && balloonOn.value && nav.current?.view !== CHAT_KEY,
);

// The page the panel shows: whoever draws it is the module that registered itself
// for it, and a table's own table is what is left over when nobody claims the
// view. The shell knows no page by heart.
const frame = computed(() => {
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
function offered(view: string): boolean {
  if (view === CHAT_KEY && !store.interpreter) return false;
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

function showSaved(): void {
  const asked = askedFromUrl();
  if (asked) {
    open(asked.view, asked.id);
    return;
  }
  const saved = loadPrefs(SELECT_KEY);
  const view = String(saved.view || "");
  if (view && offered(view)) {
    markPage(view, saved.id);
    resumePath(saved.back); // the saved path comes back: the step back lands where it did
    return;
  }
  if (store.tables.length) open(store.tables[0].key, null);
}

// THE SERVER WARNING: the data changed. The words come in again through
// `applyState` (the language may have changed) and the SAME page is redrawn — in
// the same place, because whoever was reading is not thrown to the top.
async function refresh(): Promise<void> {
  const state = await api<Record<string, unknown>>("/api/state").catch(() => null);
  if (state) {
    applyState(state);
    applyTheme();
  }
  // WHILE SOMEBODY IS WRITING, THE PAGE IS NOT REDRAWN. Every save changes the
  // file on the disk, so the writer wakes ITSELF through this very path — and
  // redrawing under a sentence is the page fighting the person.
  if (writingState.active) return;
  poke();
}

function toggle(): void {
  toggleNav();
  railed.value = railedNow();
}

onMounted(async () => {
  // The browser's menu stays OFF on the whole page: a row that is not a target
  // opens nothing — not the native menu either.
  document.addEventListener("contextmenu", ev => ev.preventDefault());
  // One door only to close the panel: the click outside and Escape.
  document.addEventListener("click", () => closePop());
  document.addEventListener("keydown", ev => {
    if (ev.key === "Escape") closePop();
  });

  // The SIDE of the theme is the only choice the SYSTEM changes underneath.
  watchSystem();
  // Motion already entered before the paint; here it is the SAME choice, re-read
  // from the preference — keeping the two in agreement is what stops the page
  // from disagreeing with the CSS after a reload.
  applyMotion();
  applyNav();
  watchNav(() => {
    railed.value = railedNow();
  });
  watchNarrow();

  try {
    applyState(await api<Record<string, unknown>>("/api/state"));
    applyTheme();
    showSaved();
  } catch (err) {
    ui.title = word("error") + " " + (err as Error).message;
  }
});

// Re-exported for the template: `refresh` is what a write wakes.
defineExpose({ refresh });
</script>

<template>
  <nav>
    <h1 id="brand">
      <span class="brand">{{ word("brand") }}</span>
      <button id="nav-toggle" class="nav-toggle" type="button"
              :aria-label="word('panel')" :aria-expanded="!railed"
              @click="toggle"></button>
    </h1>
    <Sidebar />
  </nav>
  <main>
    <header id="head">
      <span id="head-title">
        <template v-if="ui.count"><b>{{ ui.count.shown }} {{ word("records") }}</b><span
          v-if="ui.count.hidden"> · {{ ui.count.hidden }} {{ word("hidden") }}</span></template>
        <template v-else-if="ui.bold"><b>{{ ui.bold }}</b><span>{{ ui.rest }}</span></template>
        <template v-else>{{ ui.title }}</template>
      </span>
      <span id="head-right">
        <span class="loc">
          <span class="raw">{{ store.lang }}</span>
          <span class="name">{{ word("language_name") }}</span>
          <span class="flag">{{ word("language_flag") }}</span>
        </span>
      </span>
    </header>
    <div id="body">
      <component :is="frame.component" v-if="frame" v-bind="frame.props" :key="frame.key" />
    </div>
  </main>
  <div id="scrim" class="scrim" @click="toggle"></div>
  <Popover />
  <!-- The balloon is a LAYER OF ITS OWN, and not the pop's: the pop keeps ONE
       open panel, and a balloon that lived in that slot would close every time a
       column's filter opened (`pop.ts`). -->
  <Balloon v-if="balloon" />
</template>
