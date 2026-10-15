<script setup lang="ts">
// ProjectsTree — the PROJECTS branch of the panel. One level at a time: the line
// of a project that has others under it gets a box of its own, and it is the BOX
// that carries the indent (`.branch`) — nothing here counts levels.
//
// The last node is the "no project" one, whenever the server says there is a task
// no project claims. It is drawn HERE, and not as another module's branch,
// because it belongs to THIS tree: it sits among the projects and opens a page of
// tasks, the same thing a project opens.

import { ref, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { store, word } from "../lib/store";
import { nav } from "../lib/views";
import ProjectTreeNode from "./ProjectTreeNode.vue";

export interface ProjectLine {
  id: number | null;
  title: string;
  status: string;
  parent: number | null;
  tasks: number;
  orphans?: boolean;
}

const kids = ref<Map<string, ProjectLine[]>>(new Map());
const error = ref("");
// What the ENGINE says this actor may do to a PROJECT (TASK-135) — the
// tree's own context menu, never this component's invention. Role-level, one
// list for the whole tree, the same shape `TableView`'s `actions` prop is.
const actions = ref<string[]>([]);

async function load(): Promise<void> {
  try {
    const answer = await api<{ tree: ProjectLine[]; actions: string[] }>("/api/projects");
    const map = new Map<string, ProjectLine[]>();
    for (const row of answer.tree) {
      const key = row.parent ? String(row.parent) : "";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(row);
    }
    kids.value = map;
    actions.value = answer.actions;
  } catch (err) {
    error.value = `${word("error")} ${(err as Error).message}`;
  }
}

onMounted(load);
// The tree is redrawn when the page is poked: a project created or closed
// anywhere — the CLI, another tab — has to show up here without a reload.
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="error" class="empty">{{ error }}</div>
  <ProjectTreeNode v-else :kids="kids" :actions="actions" parent="" />
</template>
