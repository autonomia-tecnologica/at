<script setup lang="ts">
// ProjectTreeNode — ONE level of the projects tree. There is NO fold here: a
// subproject shows up indented under its parent, always visible — what opens and
// closes is the whole tree, on the panel's folder.
//
// The "no project" line is the SAME line and its own attribute: it is NOT a
// project, and marking it with a project's id would be lying about what it is.
// The title arrives from the server, like every other word.

import { computed } from "vue";
import { isCurrent, open, countOf, ORPHANS_KEY, showError, poke } from "../lib/views";
import { store, word } from "../lib/store";
import { byName } from "../lib/order";
import { openPop } from "../lib/pop";
import { openContextMenu, vContextMenu, type MenuItem } from "../lib/menu";
import { post } from "../lib/api";
import NamePop from "./pops/NamePop.vue";
import MoveProjectPop, { type MoveCandidate } from "./pops/MoveProjectPop.vue";
import type { ProjectLine } from "./ProjectsTree.vue";

const props = withDefaults(
  defineProps<{
    kids: Map<string, ProjectLine[]>;
    // What the ENGINE says this actor may do to a PROJECT (TASK-135) — one
    // list for the whole tree (§ `_project_actions`), carried down through the
    // recursion unchanged.
    actions: string[];
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

// A WRITE OF THE `project` TABLE, through the SAME door every other table's
// write walks (`post("/api/table/<t>")`): create a project or a subproject,
// rename one, or move one — the engine does not tell the three apart, they
// are `create` and `edit` over the field that means "parent" (TASK-135).
async function writeProject(
  action: "create" | "edit",
  set: Record<string, string>,
  id?: number,
): Promise<void> {
  try {
    await post("/api/table/project", { action, set, ...(id !== undefined ? { id } : {}) });
    poke();
  } catch (err) {
    showError(err as Error);
  }
}

function openNamePop(ev: MouseEvent, initial: string, onSubmit: (value: string) => void): void {
  openPop("project-name", NamePop, { initial, onSubmit },
          { point: { x: ev.clientX, y: ev.clientY } });
}

// Every project but the one under the pointer and whatever sits under IT —
// moving a subtree into itself is a cycle this pop does not have to refuse,
// because the picker it opens never offers the choice in the first place.
function descendantsOf(id: number): Set<number> {
  const out = new Set<number>();
  const queue = [id];
  while (queue.length) {
    const current = queue.pop() as number;
    for (const child of props.kids.get(String(current)) || []) {
      if (child.id !== null && !out.has(child.id)) {
        out.add(child.id);
        queue.push(child.id);
      }
    }
  }
  return out;
}

function openMovePop(ev: MouseEvent, row: ProjectLine): void {
  const id = row.id as number;
  const excluded = descendantsOf(id);
  excluded.add(id);
  const candidates: MoveCandidate[] = [...props.kids.values()]
    .flat()
    .filter(p => !p.orphans && p.id !== null && !excluded.has(p.id))
    .map(p => ({ id: p.id as number, title: p.title }))
    .sort((a, b) => byName(a.title, b.title));
  openPop("project-move", MoveProjectPop,
          {
            candidates,
            current: row.parent,
            onPick: (target: number | null) =>
              void writeProject("edit", { parent: target === null ? "" : String(target) }, id),
          },
          { point: { x: ev.clientX, y: ev.clientY } });
}

// A ROW'S RIGHT CLICK (the context-menu key, Shift+F10, and a touch
// long-press — `v-context-menu` either way): what it offers is exactly what
// the engine said was legal (`props.actions`), never this component's
// invention. The "no project" line is not a project — it gets no menu at all.
function onMenu(ev: MouseEvent, row: ProjectLine): void {
  if (row.orphans) {
    openContextMenu(ev, []);
    return;
  }
  const id = row.id as number;
  const items: MenuItem[] = [];
  if (props.actions.includes("create")) {
    items.push({
      label: word("new_project"),
      action: () => openNamePop(ev, "", value => void writeProject("create", { name: value })),
    });
    items.push({
      label: word("new_subproject"),
      action: () => openNamePop(ev, "", value =>
        void writeProject("create", { name: value, parent: String(id) })),
    });
  }
  if (props.actions.includes("edit")) {
    items.push({
      label: word("rename"),
      action: () => openNamePop(ev, row.title, value => void writeProject("edit", { name: value }, id)),
    });
    items.push({ label: word("move_to_project"), action: () => openMovePop(ev, row) });
  }
  openContextMenu(ev, items);
}

function menuHandler(row: ProjectLine): (ev: MouseEvent) => void {
  return ev => onMenu(ev, row);
}
</script>

<template>
  <template v-for="row in rows" :key="viewOf(row)">
    <button type="button" class="file" :data-view="viewOf(row)"
            :class="{ on: isCurrent(viewOf(row)) }" @click="go(row)"
            v-context-menu="menuHandler(row)">
      <span>{{ row.title }}</span>
      <!-- The line of the page on screen carries what its filter leaves; the
           others, the store's count. -->
      <span class="n">{{ countOf(viewOf(row), row.tasks) }}</span>
    </button>
    <div v-if="hasKids(row)" class="branch">
      <ProjectTreeNode :kids="kids" :actions="actions" :parent="String(row.id)" />
    </div>
  </template>
  <!-- THE LAST ROW OF THE WHOLE TREE, and only the root level draws it: a
       recursive call for EVERY project would repeat it once per level. -->
  <button v-if="!parent" type="button" class="file" :data-view="store.types.task"
          :class="{ on: isCurrent(store.types.task) }" @click="openAllTasks">
    <span>{{ word("all_tasks") }}</span>
  </button>
</template>
