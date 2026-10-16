<script setup lang="ts">
// ProjectView — the page a project opens.
//
// A project is a SCOPE of tasks, not a table of its own: the page shows the
// projects directly inside it and then the tasks of the WHOLE subtree, each row
// saying which subproject it came from. The page holds no data and no vocabulary
// — the tree, the counts and the rows all come from the API, which resolved the
// `parent` tree and the task links.
//
// It has no "back" of its own: what it has is the tree it lives in, and the
// parent's line is the way up.

import { ref, computed, watch, onMounted } from "vue";
import { api, post } from "../lib/api";
import { store, setFields, word } from "../lib/store";
import { nav, markPage, leave, open, openRef, setTrail, showError, poke } from "../lib/views";
import { openContextMenu, vContextMenu, type MenuItem } from "../lib/menu";
import { openPop } from "../lib/pop";
import { ask } from "../lib/confirm";
import { toast } from "../lib/toast";
import TaskBoard from "../components/TaskBoard.vue";
import RecordView from "../components/RecordView.vue";
import ProseField from "../components/ProseField.vue";
import ClosePop from "../components/pops/ClosePop.vue";
import type { FieldSpec, RecordRow } from "../lib/record";

interface Child {
  id: number;
  title: string;
  status: string;
  tasks: number;
}

interface ProjectPayload {
  id: number;
  title: string;
  status: string;
  parent: { id: number; title: string } | null;
  children: Child[];
  fields: FieldSpec[];
  records: RecordRow[];
  actions: string[];
  // The project's OWN fields and record — the pair `fields`/`records` above is
  // the TASKS the page draws, and this one is the project the page IS. It is
  // where the body of an item arrives: the `desc` the table declares
  // `markdown`, which is what a backlog item keeps its why and its decided in.
  // `actions` here is the ENGINE's own word on the project record itself
  // (TASK-137, fatia 7/7) — `_table_actions("project")` on the server, the
  // same door a table's row menu already asks, and never the tree's
  // `_project_actions` (create/edit only).
  project: { fields: FieldSpec[]; record: RecordRow; actions: string[] };
}

const props = defineProps<{ id: string }>();

const payload = ref<ProjectPayload | null>(null);

const page = computed(() => "project:" + props.id);

// THE BODY OF THE ITEM: every field of the project the table declares
// `markdown`, which is where an item keeps its why, its decided and its open.
// It is drawn AS PROSE — the renderer is the debt `lib/markdown` names, and
// until it lands the text a person reads is the text as it is stored.
const prose = computed(() =>
  (payload.value?.project.record.fields || []).filter(field => field.type === "markdown" && field.value),
);

// THE BAND IS THE WAY IN: `Tarefas › WebApp`, and the section is the shell's
// to add (`App.vue`). The state, the priority and the counts it used to spell
// out here are all IN the page, where a person reads them with the rows they
// describe — a band that recites four values is a band that stops being a
// place.
function describe(): void {
  if (!payload.value) return;
  setTrail(payload.value.title);
}

const record = computed(() => {
  const current = nav.current;
  if (!current || current.view !== page.value || !current.id || !payload.value) return null;
  return payload.value.records.find(rec => rec.id === current.id) || null;
});

async function load(): Promise<void> {
  // The record that was open survives the page being reloaded.
  const wasOpen = nav.current ? nav.current.id : null;
  try {
    const data = await api<ProjectPayload>("/api/project/" + encodeURIComponent(props.id));
    payload.value = data;
    setFields(data.fields);
    markPage("project:" + data.id, wasOpen);
    describe();
  } catch (err) {
    // A project can have been CLOSED, and the preference outlives what it names:
    // the page falls to the first table, never to an error page.
    payload.value = null;
    if (store.tables.length) open(store.tables[0].key, null);
    else showError(err as Error);
  }
}

// Going down the tree is a NAVIGATION: the page left behind goes on the path,
// the same way a reference does.
function go(id: number): void {
  leave();
  markPage("project:" + id, null);
}

// THE PAGE'S OWN RIGHT CLICK (TASK-137, fatia 7/7): close and delete, the
// same two the row menu already offers a table (`TableView.vue`'s
// `openRowMenu`) — and never `edit`, because this page already IS the
// project's form. What shows is exactly what the engine allowed
// (`payload.project.actions`), nothing this page invents.
function openProjectMenu(ev: MouseEvent): void {
  if (!payload.value) return;
  const point = { x: ev.clientX, y: ev.clientY };
  const items: MenuItem[] = [];
  if (payload.value.project.actions.includes("cancel")) {
    items.push({ label: word("close"), action: () => openCloseProject(point) });
  }
  if (payload.value.project.actions.includes("delete")) {
    items.push({ label: word("delete"), action: () => deleteProject() });
  }
  openContextMenu(ev, items);
}

function openCloseProject(point: { x: number; y: number }): void {
  if (!payload.value) return;
  const rec = payload.value.project.record;
  openPop("close:project:" + rec.id, ClosePop,
          { entity: "project", id: rec.id, title: rec.title || payload.value.title },
          { point });
}

async function deleteProject(): Promise<void> {
  if (!payload.value) return;
  const name = payload.value.title;
  if (!(await ask(word("delete_confirm").replace("{name}", name)))) return;
  try {
    await post("/api/table/project", { action: "delete", id: payload.value.project.record.id });
    poke();
  } catch (err) {
    toast((err as Error).message);
  }
}

onMounted(load);
watch(() => nav.tick, load);
watch(() => props.id, () => {
  payload.value = null;
  load();
});
</script>

<template>
  <RecordView v-if="record" :record="record" :total="payload?.records.length ?? 0"
              :page="page" :entity="store.types.task" @ref="openRef" />
  <!-- THE PAGE'S OWN RIGHT CLICK (TASK-137, fatia 7/7): anchored on the whole
       body, because the page has no header of its own to carry it on — the
       title lives in the shell's trail band, not here. `TaskBoard` offers no
       row menu of its own yet, so a right click anywhere on this page — the
       prose, a task card, the board's empty room — reaches this one, about
       the PROJECT itself. -->
  <div v-else-if="payload" v-context-menu="openProjectMenu">
    <!-- The parent's line is the way up, and it is the tree the page lives in —
         not a "back" the page keeps of its own. -->
    <div v-if="payload.parent" class="back" @click="go(payload.parent.id)">
      ← {{ payload.parent.id }}  ({{ payload.parent.title }})
    </div>
    <!-- The ITEM's body, drawn as the page's prose: the fields this table
         declares `markdown` — the `desc` where an item keeps its why. -->
    <ProseField v-for="field in prose" :key="field.name" :text="field.value" />
    <!-- THE BOARD BELOW IS THE TASKS' — the table the server said declares the
         TYPE `task`, never the word "task" read as a table's name. It hides
         the project chip a card would otherwise carry (`show-project`
         false): every card here already lives inside this project's own
         page, the same reason the table declares `hide: ["project"]` for the
         column a plain table would have drawn. A macro project's subprojects
         are the TREE's to show, not the task view's — the board here is
         tasks and only tasks, so the quick-add is off too: it writes no
         `project`, and a card born on this page landing as an orphan would
         be the page lying about where it put it. -->
    <TaskBoard v-if="store.types.task" :entity="store.types.task" :records="payload.records"
               :schema="payload.fields" :page="page" :show-project="false" :allow-create="false"
               @ref="openRef" />
  </div>
</template>
