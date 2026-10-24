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

import { refresh, booted, startBoot } from "./lib/shellBoot";
import { installListeners } from "./lib/shellListeners";
import { signedIn, session } from "./lib/session";
import { store, label, word } from "./lib/store";
import { balloon, trail, stepLink, pageTitle, fillsPage, frame, isWrite } from "./lib/shellRoute";
import { onMounted } from "vue";
import { toggleNav, navRail } from "./lib/nav";
import { offlineState } from "./lib/offline";
import { viewer } from "./lib/strongbox";
import Sidebar from "./components/Sidebar.vue";
import Popover from "./components/Popover.vue";
import Balloon from "./components/Balloon.vue";
import Toast from "./components/Toast.vue";
import Hint from "./components/Hint.vue";
import ConfirmDialog from "./components/ConfirmDialog.vue";
import StrongboxViewer from "./components/StrongboxViewer.vue";
import LoginView from "./views/LoginView.vue";
import SetupView from "./views/SetupView.vue";
import FolderView from "./views/FolderView.vue";

// THE TWO DOORS TO THE SAME DOOR. This is the SCRIM's click — the panel is closed
// by clicking outside it — and the panel's own button lives in the foot, which is
// `Sidebar.vue`. Both call `toggleNav`, and both read the one answer it keeps
// (`navRail`), so neither can leave the other's `aria-expanded` lying.
function toggle(): void {
  toggleNav();
}

startBoot();
onMounted(installListeners);

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
            <a v-else-if="stepLink(i)" class="crumb link" href="#"
               @click.prevent="stepLink(i)!()">{{ step }}</a>
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
        <!-- THE PAGE (F3): the one wrapper that owns the gutter and the maximum
             width (`base.css`, `.page`). The page header names the screen — the
             last step of the trail, the same words the band above ends in —
             and every view sits under it with no outer margin of its own. -->
        <div v-if="frame" class="page" :class="{ 'page--fill': fillsPage }">
          <div v-if="pageTitle" class="page-header">
            <h1 class="page-title">{{ pageTitle }}</h1>
          </div>
          <!-- THE SCREEN CHANGE (F6): the new page fades in on its own (`base.css`,
               `.page > :not(.page-header)`) — no `<Transition>` here: a leave that
               waits for the old page to finish held the new one back whenever the
               old page's root had no animation to end. -->
          <component :is="frame.component" v-bind="frame.props" :key="frame.key" />
        </div>
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
