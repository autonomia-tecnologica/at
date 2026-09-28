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
import { api } from "../lib/api";
import { store, setFields, word } from "../lib/store";
import { nav, markPage, leave, open, openRef, setHeading, showError } from "../lib/views";
import TableView from "../components/TableView.vue";
import RecordView from "../components/RecordView.vue";
import ProseField from "../components/ProseField.vue";
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
  project: { fields: FieldSpec[]; record: RecordRow };
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

// The band's sentence, built once: what the page IS — the item, its state, and
// the priority the queue is ordered by when the row carries one — and how much
// of it the filter leaves. A migrated row has no priority, and it says nothing
// rather than a placeholder: the ORDER already reads a missing value as the
// declared default, and the band does not have to spell it out.
function describe(shown: number, hidden = 0): void {
  if (!payload.value) return;
  const { id, title, status } = payload.value;
  const priority = payload.value.project.record.fields.find(field => field.name === "priority");
  const parts = [title, status];
  if (priority?.raw) parts.push(priority.value);
  parts.push(shown + " " + word("tasks"));
  if (hidden) parts.push(hidden + " " + word("hidden"));
  setHeading(String(id), " · " + parts.join(" · "));
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
    describe(data.records.length);
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

// The band carries what the FILTER leaves, like the panel's line does — the two
// numbers describe the same rows and may not disagree.
function onCount(shown: number, hidden: number): void {
  describe(shown, hidden);
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
  <div v-else-if="payload">
    <!-- The parent's line is the way up, and it is the tree the page lives in —
         not a "back" the page keeps of its own. -->
    <div v-if="payload.parent" class="back" @click="go(payload.parent.id)">
      ← {{ payload.parent.id }}  ({{ payload.parent.title }})
    </div>
    <!-- The ITEM's body, drawn as the page's prose: the fields this table
         declares `markdown` — the `desc` where an item keeps its why. -->
    <ProseField v-for="field in prose" :key="field.name" :text="field.value" />
    <div v-if="payload.children.length" class="subs">
      <button v-for="child in payload.children" :key="child.id" type="button" class="sub"
              @click="go(child.id)">
        <b>{{ child.id }}</b>
        <span>{{ child.title }}</span>
        <span class="st">{{ child.status }}</span>
        <span class="n">{{ child.tasks }} {{ word("tasks") }}</span>
      </button>
    </div>
    <!-- The table below is the TASKS' — the table the server said declares the
         TYPE `task`, never the word "task" read as a table's name. -->
    <TableView v-if="store.types.task" :entity="store.types.task" :records="payload.records"
               :schema="payload.fields" view-key="project" :page="page" rule
               :actions="payload.actions" @count="onCount" @ref="openRef" />
  </div>
</template>
