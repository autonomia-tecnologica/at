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
import { isCurrent, open, countOf } from "../lib/views";
import { byName } from "../lib/order";
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
    <button type="button" class="file" :data-view="SETTINGS_KEY"
            :class="{ on: isCurrent(SETTINGS_KEY) }" @click="openSettings">
      <span>{{ word("settings") }}</span>
    </button>
  </div>
</template>
