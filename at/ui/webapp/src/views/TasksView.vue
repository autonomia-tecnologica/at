<script setup lang="ts">
// TasksView — THE TASKS SECTION'S OWN SCREEN, and the section is the fold.
//
// There is no screen called "overview" and no row that opens one: the panel's
// folds ARE its sections, and a section's head is selectable — the TASKS row
// opens the projects tree and opens this page, in one gesture over one row
// (`views.ts`, `Foldable.vue`). The address is the section's own name,
// `/tasks`, and the day FILES has a screen it will be `/files` for free.
//
// IT INVENTS NO DATA, and that is the whole discipline of this page. Every
// number is a count of rows the server already returns for two tables that
// exist (`task`, `project`), read through the very routes their own pages read
// them with — the same payload, a different cut. A row the page was not handed
// is a row the page does not count, and a summary that guessed would be a
// dashboard that lies about the folder it describes.
//
// IT ALSO INVENTS NO WORDS. The names of the statuses are the TABLE's own
// vocabulary (`fields[].enum`, handed over with the rows), the name of the
// project table is the table's own name (the panel already draws it), and what
// is left over is the page's own — the section's word, from the catalog like
// every other word on screen.
//
// WHAT IT IS NOT is a place to act: nothing here is clickable but the doors
// OUT of it (a project), because a summary that also edits is a second way to
// do what the page already does.

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import StatStrip from "../components/StatStrip.vue";
import EmptyState from "../components/EmptyState.vue";
import { store, setFields, word, label, kindLabel } from "../lib/store";
import { nav, open, setTrail, showError, TASKS_KEY } from "../lib/views";
import type { TablePayload, RecordRow, RecordField } from "../lib/record";

const tasks = ref<TablePayload | null>(null);
const projects = ref<TablePayload | null>(null);

// The rows as they arrive, in the shape this page reads them: a field looked up
// by NAME. The payload is a list of fields per record, and every question here
// is about one field.
function fieldOf(rec: RecordRow, name: string): RecordField | null {
  return rec.fields.find(f => f.name === name) || null;
}

function rawOf(rec: RecordRow, name: string): unknown {
  const field = fieldOf(rec, name);
  return field ? field.raw : null;
}

// THE STATUSES, in the order the TABLE declares them — never a list written
// here. A vocabulary that grows a status is a column this page gains without
// being touched (`task.json`, `fields.status.enum`).
const statuses = computed(() => {
  const spec = tasks.value?.fields.find(f => f.name === "status");
  return Object.entries(spec?.enum || {}).map(([key, labels]) => ({ key, labels }));
});

// One status, one number: what the panel says the table holds, cut the other
// way. The count is the ROWS, and the rows are what the server sent.
function countOfStatus(key: string): number {
  const rows = tasks.value?.records || [];
  return rows.filter(rec => rawOf(rec, "status") === key).length;
}

// A task that points at no project at all — the panel has a page for it
// (`orphans`), and the summary is where its number belongs.
const orphans = computed(
  () => (tasks.value?.records || []).filter(rec => rawOf(rec, "project") === null).length,
);

// The strip's items: a number and a bar part per status, and the orphans as a
// number alone (they are not a status, so they take no part in the proportion).
const stripItems = computed(() => [
  ...statuses.value.map(status => ({
    key: status.key, tone: status.key, value: countOfStatus(status.key),
    share: countOfStatus(status.key), label: label(status.labels),
    title: label(status.labels) + ": " + countOfStatus(status.key),
  })),
  ...(orphans.value ? [{ key: "orphans", value: orphans.value, label: word("no_project") }] : []),
]);

// WHAT EACH PROJECT HOLDS. A task names its project by NUMBER (`raw`, the way
// the engine stores a reference to one table), so the two are joined on the id
// and not on the title — a title is a translation, and two projects may share
// one in another language.
function tasksOf(projectId: number): RecordRow[] {
  return (tasks.value?.records || []).filter(rec => rawOf(rec, "project") === projectId);
}

function doneOf(projectId: number): number {
  return tasksOf(projectId).filter(rec => rawOf(rec, "status") === "done").length;
}

const projectRows = computed(() => projects.value?.records || []);

const projectsLabel = computed(() => kindLabel("project") || word("tasks"));

async function load(): Promise<void> {
  try {
    const [taskPage, projectPage] = await Promise.all([
      api<TablePayload>("/api/table/task?all"),
      api<TablePayload>("/api/table/project?all"),
    ]);
    tasks.value = taskPage;
    projects.value = projectPage;
    // The schema the OPEN RECORD of a task would draw with, so the table this
    // page cuts is the table the page hands over — one vocabulary, not two.
    setFields(taskPage.fields);
    setTrail(word("tasks"));
  } catch (err) {
    tasks.value = null;
    projects.value = null;
    showError(err as Error);
  }
}

function openProject(id: number): void {
  if (store.types.project) open(store.types.project + ":" + id, null);
}

onMounted(load);
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="tasks" class="section">
    <!-- THE NUMBERS, drawn from the table's own vocabulary, and the same numbers
         as one bar, because a proportion is read faster than four counts: the
         parts are the statuses, in the table's order, and the width is the share
         of the whole. The tones are `StatStrip`'s (the semantics the theme
         declares) — the page names neither a colour nor a width. -->
    <StatStrip :items="stripItems" />

    <!-- WHAT THE PROJECTS HOLD. Each row is a door: the project's own page is
         where its tasks are, and a summary is not a second way to read them. -->
    <section class="cards">
      <h2>{{ projectsLabel }}</h2>
      <EmptyState v-if="!projectRows.length" icon="folder" :title="word('no_records')" />
      <button v-for="project in projectRows" :key="project.id" type="button" class="card"
              @click="openProject(project.id)">
        <span class="card-top">
          <b>{{ project.title }}</b>
          <span class="n">{{ doneOf(project.id) }}/{{ tasksOf(project.id).length }}</span>
        </span>
        <span class="progress" aria-hidden="true">
          <span class="progress-part"
                :style="{ transform: 'scaleX(' + (tasksOf(project.id).length
                  ? doneOf(project.id) / tasksOf(project.id).length : 0) + ')' }"></span>
        </span>
      </button>
    </section>
  </div>
</template>
