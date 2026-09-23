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

import { computed } from "vue";
import { store, word } from "../lib/store";
import { CHAT_KEY, isCurrent, open, countOf } from "../lib/views";
import { byName } from "../lib/order";
import { navRail, toggleNav } from "../lib/nav";
import Foldable from "./Foldable.vue";
import ProjectsTree from "./ProjectsTree.vue";
import FileTree from "./FileTree.vue";

const SETTINGS_KEY = "settings";

const hasProjects = computed(() => Boolean(store.types.project && store.types.task));

// The list is ALPHABETICAL, by the name the panel prints. The store declares an
// `order` of its own; what a person does with a list of tables is look one up,
// and the name is the index (order.ts).
const kinds = computed(() => [...store.tables].sort((a, b) => byName(a.label, b.label)));

function openKind(key: string): void {
  open(key, null);
}

function openSettings(): void {
  open(SETTINGS_KEY, null);
}

function openChat(): void {
  open(CHAT_KEY, null);
}
</script>

<template>
  <!-- THE LIST — what scrolls. `#kinds` is the scroller's own box (`base.css`),
       and the foot below is NOT part of it: a thing that must always be on screen
       cannot live inside the thing that leaves it. -->
  <div id="kinds">
    <Foldable v-if="hasProjects" id="tasks" :label="word('tasks')" box-class="branch">
      <ProjectsTree />
    </Foldable>
    <Foldable id="files" :label="word('files')" box-class="branch">
      <FileTree />
    </Foldable>
    <Foldable id="tables" :label="word('tables')" box-class="kinds">
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
  <div class="side-foot">
    <hr class="sep">
    <!-- THE CHAT IS THE INTERPRETER'S, and it is here whether the balloon flies or
         not: the switch of the balloon hides the balloon. What takes the chat away
         is the CORE's switch (`store.interpreter`) — with the interpreter off
         there is no box, no balloon and no chat, because the function is gone. -->
    <button v-if="store.interpreter" type="button" class="file" :data-view="CHAT_KEY"
            :class="{ on: isCurrent(CHAT_KEY) }" @click="openChat">
      <span>{{ word("chat") }}</span>
    </button>
    <button type="button" class="file" :data-view="SETTINGS_KEY"
            :class="{ on: isCurrent(SETTINGS_KEY) }" @click="openSettings">
      <span>{{ word("settings") }}</span>
    </button>
    <!-- THE LAST ROW OF THE FOOT, AND THE ONE THE RAIL CANNOT LOSE (2026-09-22).
         The collapse button used to sit in the title strip, next to the name; it
         lives HERE now, for the reason a foot exists at all: this box is always on
         screen, so a person never has to SCROLL the tree to reach the control that
         hides the tree. It is also the only target left once the panel IS the rail
         — which is why the rail hides the foot's rows and not the foot (base.css).
         The state it reads is `navRail`, the one answer both doors share.
         IT CARRIES ITS OWN NAME (2026-09-22). It was a bare glyph with an
         `aria-label` far away from it, which meant a sighted person had to guess
         what `«` did — and no arrow can answer that: an arrow says WHICH WAY the
         panel goes, never WHAT HAPPENS to it. The words say what happens. The GLYPH
         stays as the `::before` of the rule, so the theme still sizes it
         (`--nav-toggle-size`) and the two sides still swap by selector.
         ON THE RAIL THE WORDS GO AND THE ARROW TURNS — 44px has no room for a
         sentence, and the `aria-label` flips to the other verb so a screen reader
         hears the ACTION and not the position. That flip is also what keeps the
         accessible name matching the visible one where the visible one exists
         (WCAG 2.5.3, and the reason the label is not a fixed "Painel"). -->
    <!-- THE LINE ABOVE THE CONTROL. `hr.sep` is the separator this file already
         uses to close the foot off from the tree, so the control is set apart by
         the same mark and not by a second idiom invented here. -->
    <hr class="sep">
    <button id="nav-toggle" class="nav-toggle" type="button"
            :aria-label="word(navRail.railed ? 'expand_menu' : 'collapse_menu')"
            :aria-expanded="!navRail.railed"
            @click="toggleNav">
      <span class="t">{{ word("collapse_menu") }}</span>
    </button>
  </div>
</template>
