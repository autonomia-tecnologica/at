<script setup lang="ts">
// Sidebar — the panel: the two branches, the tables, and Settings at the foot.
//
// The order is deliberate and comes from the PoC: the branches (tasks, files)
// BEFORE the tables list, because what a day is made of are the TASKS and the
// vocabulary that names them is a reference, not the front door. Settings sits
// behind a line, because where the page configures itself is no longer one more
// thing in the day's tree.
//
// "Tarefas" IS the projects tree — a project is a scope of tasks, and the tree is
// how one reaches them. There is no separate "Projetos" line: it would be the
// same door with another name.
//
// The mark on the open line is of what the VIEW IS (`isCurrent`), not of what
// each module decided to write there — that way a new page does not need to know
// a mark exists.

import { computed, onMounted, onUnmounted, ref } from "vue";
import { store, word } from "../lib/store";
import { CHAT_KEY, NLU_UI_ENABLED, TASKS_KEY, FILES_KEY, TABLES_KEY, REMINDERS_KEY, BOARD_KEY, SETTINGS_KEY, isCurrent, open, countOf } from "../lib/views";
import { byName } from "../lib/order";
import { toggleNav } from "../lib/nav";
import Foldable from "./Foldable.vue";
import ProjectsTree from "./ProjectsTree.vue";
import FileTree from "./FileTree.vue";
import StrongboxTree from "./StrongboxTree.vue";

const foot = ref<HTMLElement | null>(null);
let footWatcher: ResizeObserver | null = null;

// THE TWO SYSTEM TABLES PEOPLE OWNS (§5, item 11) DO NOT LIVE HERE TWICE. An
// actor and a role are still declared tables — the server counts them, a
// reference still resolves to them — but Tabelas is a list of things to BROWSE,
// and these two already have their own screen, inside Configurações: a table
// that also has a door of its own is not a table any more to this fold, it is a
// duplicate of that door. `at.core.audit.ACTOR`/`"role"`, the same two words.
const PEOPLE_TABLES = ["actor", "role"];

const hasProjects = computed(() => Boolean(store.types.project && store.types.task));

// THE BOARD'S OWN NUMBER is the task table's count, and that count is already
// the one that matters here: `tables.rows` (the server's) answers by the
// STATUS the schema marks `show` — todo and doing — the same reason a done or
// a cancelled row never inflates a count anywhere else in the panel. The board
// draws every status in its own column, but what the row before it promises is
// what still needs doing, not the total.
const boardCount = computed(() => store.tables.find(kind => kind.key === store.types.task)?.count ?? 0);

// The list is ALPHABETICAL, by the name the panel prints. The store declares an
// `order` of its own; what a person does with a list of tables is look one up,
// and the name is the index (order.ts).
const kinds = computed(() =>
  [...store.tables]
    .filter(kind => !PEOPLE_TABLES.includes(kind.key))
    .sort((a, b) => byName(a.label, b.label)),
);

function openKind(key: string): void {
  open(key, null);
}

function openSettings(): void {
  open(SETTINGS_KEY, null);
}

function openChat(): void {
  open(CHAT_KEY, null);
}

function openReminders(): void {
  open(REMINDERS_KEY, null);
}

// `--foot-space` USED TO BE A GUESS (2026-09-27): a constant in `base.css`,
// measured by hand against whatever rows the foot held the day someone last
// counted them — and every time a row was added or taken away (the collapse
// button, People, this very change), the guess went stale and the list's last
// row ended up hidden under the foot with no scroll left to reach it (the
// "the sidebar's scroll does not work" report). The foot's real height is not
// a thing to guess: it is a thing the BROWSER already knows, so this reads it
// off the box itself and writes it down as the token `#kinds`'s padding reads
// (`base.css`) — on mount, and on every resize the foot's own box reports
// (a language switch, a font swap, a row appearing or gone).
function syncFootSpace(): void {
  if (foot.value) {
    document.documentElement.style.setProperty("--foot-space", `${foot.value.offsetHeight}px`);
  }
}

onMounted(() => {
  syncFootSpace();
  if (foot.value) {
    footWatcher = new ResizeObserver(syncFootSpace);
    footWatcher.observe(foot.value);
  }
});

onUnmounted(() => {
  footWatcher?.disconnect();
});
</script>

<template>
  <!-- THE LIST — what scrolls. `#kinds` is the scroller's own box (`base.css`),
       and the foot below is NOT part of it: a thing that must always be on screen
       cannot live inside the thing that leaves it. -->
  <div id="kinds">
    <!-- THE SECTION IS THE FOLD, and its head is SELECTABLE: this one row opens
         the tree under it and opens the section's screen (`views.ts`, TASKS_KEY)
         — clicking it once is arriving in the tasks. That is why there is no
         row called "Overview" above the others: the panel's folds ARE its
         sections, and a second door to the same place would be a door with
         nothing behind it. -->
    <Foldable v-if="hasProjects" id="tasks" :label="word('tasks')" box-class="branch"
              :view="TASKS_KEY">
      <ProjectsTree />
      <!-- THE BOARD SITS RIGHT AFTER "SEM PROJETO" — the tree's own last row
           (`ProjectTreeNode.vue` sorts the orphans line last), so this button
           lands right under it without knowing where that row ends. -->
      <button type="button" class="file" :data-view="BOARD_KEY"
              :class="{ on: isCurrent(BOARD_KEY) }" @click="openKind(BOARD_KEY)">
        <span>{{ word("board") }}</span>
        <span class="n">{{ countOf(BOARD_KEY, boardCount) }}</span>
      </button>
    </Foldable>
    <Foldable id="files" :label="word('files')" box-class="branch" :view="FILES_KEY">
      <FileTree />
    </Foldable>
    <!-- LEMBRETES (TASK-164), entre Arquivos e Cofre: uma LINHA, e não uma
         dobra — o que ela guarda é uma tela só (o que vem, e o que já tocou
         hoje), e a tela é o todo dela. A marca (o sino) é pendurada por
         `base.css` na `data-view`, como a de toda porta com forma. -->
    <button type="button" class="file" :data-view="REMINDERS_KEY"
            :class="{ on: isCurrent(REMINDERS_KEY) }" @click="openReminders">
      <span>{{ word("reminders") }}</span>
    </button>
    <!-- THE STRONGBOX, right after Lembretes — a fourth fold, and ONLY a fold
         now (2026-10-05): the section's own screen is gone, so the head opens
         and closes the tree and goes nowhere. What it lists is what the vigia
         already sealed, and a file opens over WHATEVER screen is up. -->
    <Foldable id="strongbox" :label="word('strongbox')" box-class="branch">
      <StrongboxTree />
    </Foldable>
    <Foldable id="tables" :label="word('tables')" box-class="kinds" :view="TABLES_KEY">
      <button v-for="kind in kinds" :key="kind.key" type="button"
              :data-view="kind.key" :class="{ on: isCurrent(kind.key) }"
              @click="openKind(kind.key)">
        <span>{{ kind.label }}</span>
        <!-- The number of the view on screen is what its FILTER leaves; the
             others carry the store's total. -->
        <span class="n">{{ countOf(kind.key, kind.count) }}</span>
      </button>
    </Foldable>
  </div>
  <!-- THE FOOT — the buttons that are ALWAYS on screen, with the list scrolling
       BEHIND them. It floats over the list (the box is out of the flow in
       `base.css`), so a long tree passes under it instead of pushing it away. -->
  <div class="side-foot" ref="foot">
    <hr class="sep">
    <!-- THE CHAT IS THE INTERPRETER'S, and it is here whether the balloon flies or
         not: the switch of the balloon hides the balloon. What takes the chat away
         is the CORE's switch (`store.interpreter`) — with the interpreter off
         there is no box, no balloon and no chat, because the function is gone.
         `NLU_UI_ENABLED` is the WEBAPP's own switch, above that one (views.ts) —
         on since TASK-180, fatia 3/3 closed the feature. -->
    <button v-if="NLU_UI_ENABLED && store.interpreter" type="button" class="file"
            :data-view="CHAT_KEY" :class="{ on: isCurrent(CHAT_KEY) }" @click="openChat">
      <span>{{ word("chat") }}</span>
    </button>
    <!-- PEOPLE LIVES IN CONFIGURAÇÕES NOW (2026-09-27): who may act, with which
         ceiling, is an adjustment of the folder, not a table to browse — the same
         reason Settings itself sits behind this line. The door is gone from here;
         the screen moved, not the words that describe it (`SettingsView.vue`). -->
    <button type="button" class="file" :data-view="SETTINGS_KEY"
            :class="{ on: isCurrent(SETTINGS_KEY) }" @click="openSettings">
      <span>{{ word("settings") }}</span>
    </button>
    <!-- THE PANEL'S OWN CLOSE, BACK IN THE FOOT (2026-10-05). The corner button
         (`App.vue`'s header) opens it from OUTSIDE; this is the door from the
         INSIDE — reached without a hand leaving the panel that is already open,
         which is the one the foot's own scroll-proof position (base.css) was
         always FOR. It only ever shows while the panel is open, so there is
         only one thing it can mean: unlike the corner button, no label/icon
         swap is needed here at all. -->
    <hr class="sep">
    <button class="file nav-toggle" type="button" @click="toggleNav">
      <span>{{ word("collapse_menu") }}</span>
    </button>
  </div>
</template>
