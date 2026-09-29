<script setup lang="ts">
// ProjectTreeNode — ONE level of the projects tree. There is NO fold here: a
// subproject shows up indented under its parent, always visible — what opens and
// closes is the whole tree, on the panel's folder.
//
// The "no project" line is the SAME line and its own attribute: it is NOT a
// project, and marking it with a project's id would be lying about what it is.
// The title arrives from the server, like every other word.

import { computed } from "vue";
import { isCurrent, open, countOf, ORPHANS_KEY } from "../lib/views";
import { store, word } from "../lib/store";
import { byName } from "../lib/order";
import type { ProjectLine } from "./ProjectsTree.vue";

const props = withDefaults(
  defineProps<{
    kids: Map<string, ProjectLine[]>;
    parent?: string;
  }>(),
  { parent: "" },
);

// ALPHABETICAL, level by level — the order is of the SIBLINGS, never a flattening
// of the tree. And the "no project" node is not a project: it goes LAST, wherever
// its title would fall in the alphabet.
const rows = computed(() => {
  const list = [...(props.kids.get(props.parent) || [])];
  const projects = list.filter(row => !row.orphans).sort((a, b) => byName(a.title, b.title));
  const rest = list.filter(row => row.orphans);
  return [...projects, ...rest];
});

const hasKids = (row: ProjectLine): boolean => props.kids.has(String(row.id));

const viewOf = (row: ProjectLine): string => (row.orphans ? ORPHANS_KEY : "project:" + row.id);

function go(row: ProjectLine): void {
  open(viewOf(row), null);
}

// "TODAS AS TAREFAS" (TASK-126): the task table itself, with no project filter
// — the same view the ESC T shortcut falls back to with nothing visited yet.
// It sits at the very END of the tree and not among `rows`, because it names
// no project and no "no project" either: it is every task at once.
function openAllTasks(): void {
  open(store.types.task, null);
}
</script>

<template>
  <template v-for="row in rows" :key="viewOf(row)">
    <button type="button" class="file" :data-view="viewOf(row)"
            :class="{ on: isCurrent(viewOf(row)) }" @click="go(row)">
      <span>{{ row.title }}</span>
      <!-- The line of the page on screen carries what its filter leaves; the
           others, the store's count. -->
      <span class="n">{{ countOf(viewOf(row), row.tasks) }}</span>
    </button>
    <div v-if="hasKids(row)" class="branch">
      <ProjectTreeNode :kids="kids" :parent="String(row.id)" />
    </div>
  </template>
  <!-- THE LAST ROW OF THE WHOLE TREE, and only the root level draws it: a
       recursive call for EVERY project would repeat it once per level. -->
  <button v-if="!parent" type="button" class="file" :data-view="store.types.task"
          :class="{ on: isCurrent(store.types.task) }" @click="openAllTasks">
    <span>{{ word("all_tasks") }}</span>
  </button>
</template>
