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

import { computed, nextTick, onMounted, ref, watch } from "vue";
import { api, whenRefused } from "./lib/api";
import { enter, lost, session, signedIn } from "./lib/session";
import { store, applyState, label, word, tableOf } from "./lib/store";
import { ensureRenderer } from "./lib/markdown";
import { ensureFonts } from "./lib/fonts";
import { nav, ui, isKind, viewFor, open, markPage, poke, resumePath, setTrail, armPageLoad, pageReading, pageLoad, CHAT_KEY, NLU_UI_ENABLED, ORPHANS_KEY, BOARD_KEY, FILE_PREFIX, PROJECT_PREFIX, WRITE_PREFIX } from "./lib/views";
import { applyTheme, watchSystem } from "./lib/theme";
import { applyMotion } from "./lib/motion";
import { writingState } from "./lib/writing";
import { offlineState } from "./lib/offline";
import { applyNav, navRail, toggleNav } from "./lib/nav";
import { watchNarrow } from "./lib/breakpoint";
import { loadPrefs, SELECT_KEY } from "./lib/prefs";
import { popState, closePop } from "./lib/pop";
import { viewer } from "./lib/strongbox";
import { balloonOn } from "./lib/balloon";
import { shortcutsState, arm, disarm, act, isTyping } from "./lib/shortcuts";
import Sidebar from "./components/Sidebar.vue";
import Popover from "./components/Popover.vue";
import Balloon from "./components/Balloon.vue";
import Toast from "./components/Toast.vue";
import Hint from "./components/Hint.vue";
import ConfirmDialog from "./components/ConfirmDialog.vue";
import StrongboxViewer from "./components/StrongboxViewer.vue";
import KindView from "./views/KindView.vue";
import LoginView from "./views/LoginView.vue";
import SetupView from "./views/SetupView.vue";
import FolderView from "./views/FolderView.vue";

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
// arrives with the words of the entrance — but not with the TABLES, not with
// the page, not with the MARKDOWN RENDERER and not with the TEN SELF-HOSTED
// FACES, which land one or more answers later (`/api/state`, `/vendor/marked`,
// `lib/fonts.ts`). Drawing the shell in between paints it full-size and empty,
// fills it with raw notation that reformats a moment after, or — the one
// `font-display: block` alone does not reach — leaves a plain cell blank while
// a badge two columns over already reads fine, because the two wear different
// WEIGHTS of the same family and nothing says the files land together. So the
// gate waits for ALL of it.
const booted = ref(false);

// AND THEN A BEAT, BEFORE ANY OF IT IS SHOWN. The shell mounting is not the
// same as the shell being READY to look at: the page it opened fetches its own
// rows, the browser lays the table out, the self-hosted faces and the markdown
// renderer land — each a fraction behind the mount, each one a small correction
// on screen if it is watched as it happens. A short, fixed pause before the
// reveal lets all of it settle BEHIND the gate, so what a person sees is the
// finished shell arriving, not the shell assembling itself. 300ms is what that
// pause measured out to: long enough to cover the corrections, short enough
// that the wait itself is not the thing they notice.
const SETTLE_MS = 300;

// THE FADE IS ON `body`, ONE ELEMENT, NOT ON `nav` AND `main` SEPARATELY: two
// elements each running their own opacity transition is two fades, and a panel
// and a page settling on different beats reads as the shell coming apart, not
// as one thing arriving. `body` sits outside the Vue tree `#app` mounts into,
// so the class is toggled by hand — the one spot this component reaches past
// its own root, on purpose.
//
// IT IS A LATCH: `signedIn` false is the ENTRANCE, shown under this same fade
// as soon as `session.ready`, and a person who then signs in must not watch the
// whole body fade back out and in while the shell takes the entrance's place —
// once there was something on screen, there always is.
const revealed = ref(false);
const bodyShown = ref(false);
watch(
  () => session.ready && (!signedIn.value || revealed.value),
  ready => { if (ready) bodyShown.value = true; },
  { immediate: true },
);
watch(
  bodyShown,
  value => document.body.classList.toggle("revealed", value),
  { immediate: true },
);

// THE BOOT, AND IT IS ONE PATH. Whoever has just proved a credential walks
// exactly what a reload walks: the state, the theme and the entry page — so the
// shell ends in the same place either way and there is no second boot.
async function load(): Promise<void> {
  // The shell goes back under the gate and only leaves it once the state is
  // applied: a credential just proved walks this same path, and it must not draw
  // the shell with the PREVIOUS state's tables.
  booted.value = false;
  armPageLoad();
  try {
    // The renderer and the ten faces ride ALONGSIDE the state fetch, not after
    // it: none of the three have anything to say to each other, and waiting
    // for one before asking for the next would only make the gate stay shut
    // longer than it has to.
    const [state] = await Promise.all([
      api<Record<string, unknown>>("/api/state"),
      ensureRenderer(),
      ensureFonts(),
    ]);
    applyState(state);
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
  // `booted` just let the page MOUNT (the template's own `v-if`), and a page
  // that reads for itself — a file's text, a table's rows — only starts that
  // read now, in its `onMounted`. One tick is what it takes for that setup to
  // have run and said whether it reads (`pageReading`); then the boot waits for
  // it, bounded so a read that never lands cannot hold the page shut.
  await nextTick();
  if (pageReading()) {
    await Promise.race([
      pageLoad(),
      new Promise<void>(resolve => setTimeout(resolve, 600)),
    ]);
  }
  await new Promise<void>(resolve => setTimeout(resolve, SETTLE_MS));
  revealed.value = true;
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
       state and the renderer it promised have both arrived. The gate is TWO
       steps: `signedIn` false is the answer on its way and the page does not
       know it yet, and `signedIn` true with `booted` false is the words of
       the entrance already in but the TABLES, the page and `/vendor/marked`
       still an answer away (`load()`, `Promise.all`) — drawing the shell in
       either gap would flash it empty, or flash its markdown unformatted, one
       screen before the one `js/boot.js` already guards.
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
    <!-- THE FADE (0.3s, on `body` — see `revealed` above): `nav` and `main`
         are already MOUNTED the moment `booted` is true — a table page is
         already fetching its rows behind this — but the WHOLE BODY stays
         invisible until `revealed` turns true, one step later (`load()`).
         What was a hard cut from nothing to the full shell is now ONE 0.3s
         fade into the FINISHED state, sidebar numbers included. -->
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
    <!-- A PERGUNTA DA CASA (2026-10-05): o "sim ou não" desenhado pelo produto
         em vez da caixa do navegador — `lib/confirm.ts` é a porta, e este é o
         único lugar que a monta. -->
    <ConfirmDialog />
    <!-- O LEITOR DO COFRE (TASK-155): uma camada por cima de tudo, montada
         uma vez só aqui — o arquivo selado abre por qualquer lugar (o painel,
         a seção), e quem o desenha não pertence a nenhum dos dois. -->
    <StrongboxViewer v-if="viewer.file" />
    </template>
  </template>
  <!-- A PASTA vem ANTES de tudo (TASK-169, fatia 2/3): sem ela não há admin,
       não há tabela, não há nada — e é por isso que `session.folder` é
       conferido ANTES de `session.first` abaixo, embora os dois nunca
       estejam juntos (sem pasta o servidor não conta admin nenhum). -->
  <FolderView v-else-if="!signedIn && session.ready && session.folder" />
  <!-- A PRIMEIRA SUBIDA vem ANTES da entrada, e as duas são o mesmo `else`:
       uma pasta sem administrador não tem credencial nenhuma para conferir, e
       a entrada desenhada ali seria um formulário que ninguém poderia ganhar.
       O que a página pede, nesse estado, é o que CRIA o primeiro (TASK-176,
       fatia 3/3). -->
  <SetupView v-else-if="!signedIn && session.ready && session.first" />
  <LoginView v-else-if="!signedIn && session.ready" />
</template>
