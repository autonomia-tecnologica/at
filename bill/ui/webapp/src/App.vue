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

import { computed, onMounted, watch } from "vue";
import { api, whenRefused } from "./lib/api";
import { enter, lost, session, signedIn } from "./lib/session";
import { store, applyState, word } from "./lib/store";
import { nav, ui, isKind, viewFor, open, markPage, poke, resumePath, CHAT_KEY } from "./lib/views";
import { applyTheme, watchSystem } from "./lib/theme";
import { applyMotion } from "./lib/motion";
import { writingState } from "./lib/writing";
import { applyNav, syncNav, toggleNav, watchNav } from "./lib/nav";
import { watchNarrow } from "./lib/breakpoint";
import { loadPrefs, SELECT_KEY } from "./lib/prefs";
import { closePop } from "./lib/pop";
import { balloonOn } from "./lib/balloon";
import Sidebar from "./components/Sidebar.vue";
import Popover from "./components/Popover.vue";
import Balloon from "./components/Balloon.vue";
import KindView from "./views/KindView.vue";
import LoginView from "./views/LoginView.vue";

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

// THE TWO DOORS TO THE SAME DOOR. This is the SCRIM's click — the panel is closed
// by clicking outside it — and the panel's own button lives in the foot, which is
// `Sidebar.vue`. Both call `toggleNav`, and both read the one answer it keeps
// (`navRail`), so neither can leave the other's `aria-expanded` lying.
function toggle(): void {
  toggleNav();
}

// THE BOOT, AND IT IS ONE PATH. Whoever has just proved a credential walks
// exactly what a reload walks: the state, the theme and the entry page — so the
// shell ends in the same place either way and there is no second boot.
async function load(): Promise<void> {
  try {
    applyState(await api<Record<string, unknown>>("/api/state"));
    applyTheme();
    showSaved();
  } catch (err) {
    ui.title = word("error") + " " + (err as Error).message;
  }
}

// WHATEVER LETS THE PAGE DRAW WAKES THE BOOT, and it is a WATCH and not an event
// from the entrance. The difference is not style: the entrance is UNMOUNTED the
// moment the session exists — the shell takes its place — so an event emitted
// after the awaited sign-in is an event from a component that is already gone,
// and Vue drops it. Here nobody has to survive anything: the answer changes, and
// the shell boots.
//
// `immediate` is what covers the folder that asks NOBODY: no session ever comes,
// and the page is allowed to draw from the first answer.
watch(signedIn, allowed => {
  if (allowed) void load();
}, { immediate: true });

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
    syncNav();
  });
  watchNarrow();

  // A 401 under a running page is the session gone — the server was restarted
  // under it — and what it costs is the ENTRANCE coming back, never a page
  // full of "401 Unauthorized". Wired here, and not as a side effect of a
  // module, so the two floors meet in one place.
  whenRefused(lost);

  // WHO IS IN, before anything else: `/api/state` is refused to whoever is not,
  // and the words the entrance draws with arrive in this same answer.
  try {
    await enter();
  } catch (err) {
    // A server that did not answer has no entrance to draw and no words to draw
    // it with: the page falls back to the shell it drew before there was an
    // entrance, and the head carries what happened. (The boot below runs from
    // this too — `ready` is what lets the page draw — and it will fail the same
    // way, which is the state that was already true.)
    session.auth = false;
    session.ready = true;
    ui.title = word("error") + " " + (err as Error).message;
  }
});

// Re-exported for the template: `refresh` is what a write wakes.
defineExpose({ refresh });
</script>

<template>
  <!-- NOTHING until the server has said who is in. `session.ready` false is a
       state of its own — the answer is on its way and the page does not know it
       yet — and drawing the shell there would flash the entrance on every
       reload, one screen before the one `js/boot.js` already guards.
       THE WHOLE SHELL IS UNDER THE GATE, the balloon included: with no session
       the interpreter's switch is still its default, and a balloon flying over
       the entrance would be a box talking to nobody. -->
  <template v-if="signedIn">
    <nav>
      <h1 id="brand">
        <span class="brand">{{ word("brand") }}</span>
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
         open panel, and a balloon that lived in that slot would close every time
         a column's filter opened (`pop.ts`). -->
    <Balloon v-if="balloon" />
  </template>
  <LoginView v-else-if="session.ready" />
</template>
