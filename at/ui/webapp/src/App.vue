<script setup lang="ts">
// App — the SHELL and the BOOT.
//
// It emits exactly the DOM `base.css` already styles — the panel's `nav`, the
// content's `main` and the veil —, and the rest is the boot: fetch the state
// from the server, apply the theme, install the page listeners and decide the
// entry page.
//
// The theme and the motion have already entered BEFORE the first paint: whoever
// applies them is `js/boot.js`, a classic script in the `head` — AT's own,
// on the same origin. Here they are REASSERTED by their owner, and that is what
// guarantees the class and the preference do not drift after a click.

import { computed, onMounted, ref, watch } from "vue";
import { api, whenRefused } from "./lib/api";
import { enter, lost, session, signedIn } from "./lib/session";
import { store, applyState, label, word, tableOf } from "./lib/store";
import { nav, ui, isKind, viewFor, open, markPage, poke, resumePath, setTrail, CHAT_KEY, NLU_UI_ENABLED, ORPHANS_KEY, BOARD_KEY, FILE_PREFIX, PROJECT_PREFIX, WRITE_PREFIX } from "./lib/views";
import { applyTheme, watchSystem } from "./lib/theme";
import { applyMotion } from "./lib/motion";
import { writingState } from "./lib/writing";
import { offlineState } from "./lib/offline";
import { applyNav, navRail, toggleNav } from "./lib/nav";
import { watchNarrow } from "./lib/breakpoint";
import { loadPrefs, SELECT_KEY } from "./lib/prefs";
import { popState, closePop } from "./lib/pop";
import { balloonOn } from "./lib/balloon";
import { shortcutsState, arm, disarm, act, isTyping } from "./lib/shortcuts";
import Sidebar from "./components/Sidebar.vue";
import Popover from "./components/Popover.vue";
import Balloon from "./components/Balloon.vue";
import Toast from "./components/Toast.vue";
import Hint from "./components/Hint.vue";
import KindView from "./views/KindView.vue";
import LoginView from "./views/LoginView.vue";
import SetupView from "./views/SetupView.vue";

// WHEN THE BALLOON FLIES. The first two are not the page's to decide: the CORE's
// switch is on (`store.interpreter` — off, there is no function at all), and this
// browser never turned the balloon off (`balloon.ts`).
//
// The third is the page's own composition, and it is not a rule about the
// interpreter: the balloon exists for the sentence about what is ON THE SCREEN,
// and the chat already carries the box — over the chat it would be the same box
// twice, and a second box is a box nobody reads.
const balloon = computed(
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
const section = computed(() => {
  const view = nav.current?.view || "";
  if (tableOf(view)) return word("tables");        // a table is met in the tables
  if (view.startsWith(FILE_PREFIX)) return word("files");
  if (view.startsWith(PROJECT_PREFIX) || view === ORPHANS_KEY || view === BOARD_KEY) return word("tasks");
  if (view.startsWith(ACTOR_PREFIX) || view.startsWith(ROLE_PREFIX)) return word("settings");
  return "";
});

// The band: the section, and then what the page wrote for itself.
const trail = computed(() => (section.value ? [section.value, ...ui.trail] : ui.trail));


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

// THE WRITE TAB IS NOT IN THE SHELL (2026-10-05): no `nav`, no `header`, no
// trail — `frame` alone, filling the window on its own terms
// (`WriteView.vue`'s own CSS). A click that opens `/write/<path>` opens it in
// a tab of its own (`FileView.vue`), so this is never the ONLY way in: it is
// a fact of the VIEW, read the same way from a reload or a bookmark too.
const isWrite = computed(() => Boolean(nav.current?.view.startsWith(WRITE_PREFIX)));

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

// THE SECOND STEP OF THE GATE. `signedIn` is the server saying WHO IS IN, and it
// arrives with the words of the entrance — but not with the TABLES and not with
// the page, which come in `/api/state` one answer later. Drawing the shell in
// between paints it full-size and empty and fills it a moment after, the same
// flash `js/boot.js` kills one screen earlier. So the gate waits for BOTH.
const booted = ref(false);

// THE BOOT, AND IT IS ONE PATH. Whoever has just proved a credential walks
// exactly what a reload walks: the state, the theme and the entry page — so the
// shell ends in the same place either way and there is no second boot.
async function load(): Promise<void> {
  // The shell goes back under the gate and only leaves it once the state is
  // applied: a credential just proved walks this same path, and it must not draw
  // the shell with the PREVIOUS state's tables.
  booted.value = false;
  try {
    applyState(await api<Record<string, unknown>>("/api/state"));
    applyTheme();
    showSaved();
  } catch (err) {
    setTrail(word("error") + " " + (err as Error).message);
  } finally {
    // Served or refused, the boot is DONE. A server that did not answer has no
    // words to wait for; holding the gate would leave the page blank forever
    // where it now shows the error it fell back to.
    booted.value = true;
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
  // One door only to close the panel: the click outside and Escape. A click
  // outside also disarms the shortcuts pair (TASK-126) — the same "outside" a
  // popover already closes on.
  document.addEventListener("click", () => {
    closePop();
    disarm();
  });
  // ESCAPE, AND WHAT IT MEANS DEPENDS ON WHAT IS ON SCREEN (TASK-126). A pop
  // open beats everything else, exactly as it did before this shortcut
  // existed — the pair only arms with NO pop open. Past that: Escape arms (the
  // hint shows), Escape again disarms, and any key that follows either runs
  // its shortcut or disarms — a key that names nothing is not a key left
  // half-pressed.
  document.addEventListener("keydown", ev => {
    if (ev.key === "Escape") {
      if (popState.key) { closePop(); return; }
      if (isTyping(ev.target)) return;
      if (shortcutsState.armed) disarm(); else arm();
      return;
    }
    if (!shortcutsState.armed) return;
    if (isTyping(ev.target)) { disarm(); return; }
    // A modifier or a named key (Tab, ArrowLeft…) has `key.length > 1`, and
    // none of them is a letter this table knows — left alone, not disarmed,
    // because reaching for the capital letter with Shift held is not giving up.
    if (ev.ctrlKey || ev.metaKey || ev.altKey || ev.key.length !== 1) return;
    if (!act(ev.key)) disarm();
  });

  // The SIDE of the theme is the only choice the SYSTEM changes underneath.
  watchSystem();
  // Motion already entered before the paint; here it is the SAME choice, re-read
  // from the preference — keeping the two in agreement is what stops the page
  // from disagreeing with the CSS after a reload.
  applyMotion();
  applyNav();
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
    setTrail(word("error") + " " + (err as Error).message);
  }
});

// Re-exported for the template: `refresh` is what a write wakes.
defineExpose({ refresh });
</script>

<template>
  <!-- NOTHING until the server has said who is in, AND NOTHING AGAIN until the
       state it promised has arrived. The gate is now TWO steps: `signedIn`
       false is the answer on its way and the page does not know it yet, and
       `signedIn` true with `booted` false is the words of the entrance already
       in but the TABLES and the page still one answer away (`/api/state`) —
       drawing the shell in either gap would flash it empty, one screen before
       the one `js/boot.js` already guards.
       THE WHOLE SHELL IS UNDER THE GATE, the balloon included: with no session
       the interpreter's switch is still its default, and a balloon flying over
       the entrance would be a box talking to nobody. -->
  <template v-if="signedIn && booted">
    <!-- THE WRITE TAB OWNS THE WINDOW, ALONE (2026-10-05): no `nav`, no
         `header`, nothing this shell would otherwise always draw — the one
         page that is allowed to be the whole screen, because it is the one
         screen a person opened FOR that (`views.ts`, `WRITE_PREFIX`). -->
    <template v-if="isWrite">
      <component :is="frame.component" v-if="frame" v-bind="frame.props" :key="frame.key" />
    </template>
    <template v-else>
    <nav>
      <!-- A MARCA E O NOME DELA, lado a lado: a telha é a sigla, e o que vem
           depois dela é o nome inteiro — quem chega não tem como saber o que
           "AT" quer dizer, e a sidebar é onde o produto se apresenta. -->
      <h1 id="brand">
        <span class="brand">{{ word("brand") }}</span>
        <span class="brand-name">{{ word("brand_name") }}</span>
      </h1>
      <Sidebar />
    </nav>
    <main>
      <header id="head">
        <!-- THE PANEL'S DOOR, IN THE ONE CORNER IT NOW LIVES IN: the words flip
             with the state the same way the old row-button's did, so a screen
             reader hears the ACTION ("abrir"/"fechar") and not a position
             nobody chose (WCAG 2.5.3 — the reason this is not a fixed
             "Painel"). -->
        <button id="nav-toggle" class="menu-toggle" type="button"
                :aria-label="word(navRail.railed ? 'expand_menu' : 'collapse_menu')"
                :aria-expanded="!navRail.railed"
                @click="toggleNav">
        </button>
        <span id="head-title">
          <!-- The separator is the TEXT's and not the layout's: this band is
               drawn by two design systems, and a `gap` that only one of them
               declares would leave the other reading "Tasks17 record(s)". -->
          <!-- THE TRAIL: every step but the last is where the page was reached
               from, and the LAST one is the page itself — the only one that
               wears the strong ink, so the eye lands there after reading the
               way in. The separator is an ELEMENT and not a `content:` in the
               CSS: the two design systems dress the band differently, and one
               of them not at all, so what the band says has to be in the page
               (`base.css` draws it). -->
          <template v-for="(step, i) in trail" :key="i">
            <span v-if="i" class="sep">›</span>
            <b v-if="i === trail.length - 1">{{ step }}</b>
            <span v-else class="crumb">{{ step }}</span>
          </template>
        </span>
        <span id="head-right">
          <!-- THE FILA, WHEN THERE IS ONE (TASK-162, fatia 2/2): the same two
               facts `lib/offline.ts` keeps — is this browser online, and how
               many edits it made without being — shown where a person is
               already looking, the header every page shares. No fila, no
               badge: silence is what "nothing to sync" looks like. -->
          <span v-if="!offlineState.online || offlineState.pending" id="offline-badge">
            <span v-if="!offlineState.online">{{ word("offline") }}</span>
            <span v-if="offlineState.pending"><b>{{ offlineState.pending }}</b> {{ word("queued") }}</span>
          </span>
          <span class="loc">
            <span class="raw">{{ store.lang }}</span>
            <span class="name">{{ word("language_name") }}</span>
            <span class="flag">{{ word("language_flag") }}</span>
          </span>
        </span>
      </header>
      <!-- THE FOLDER'S VERSIONING, when there is something to say about it (§4,
           item 30). AT drives git, and a folder AT does not version is a folder
           whose history nothing keeps — a thing to say out loud, once per page,
           and not a state to leave quiet. The sentence is the SERVER's, written
           out in every language like a theme's description; the page picks the
           one on screen and invents none. No sentence, no strip. -->
      <p v-if="store.versioning" id="versioning">{{ label(store.versioning) }}</p>
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
    <!-- The toaster (TASK-165, fatia 3/4): a layer of its own too, mounted
         once here so every screen reaches it through `lib/toast.ts` and none
         has to mount its own. -->
    <Toast />
    <!-- THE ESC-ARMED SHORTCUTS' HINT (TASK-126): a layer of its own too,
         mounted once so it stays reachable from `lib/shortcuts.ts` alone. -->
    <Hint />
    </template>
  </template>
  <!-- A PRIMEIRA SUBIDA vem ANTES da entrada, e as duas são o mesmo `else`:
       uma pasta sem administrador não tem credencial nenhuma para conferir, e
       a entrada desenhada ali seria um formulário que ninguém poderia ganhar.
       O que a página pede, nesse estado, é o que CRIA o primeiro (TASK-176,
       fatia 3/3). -->
  <SetupView v-else-if="!signedIn && session.ready && session.first" />
  <LoginView v-else-if="!signedIn && session.ready" />
</template>
