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
}

const props = defineProps<{ id: string }>();

const payload = ref<ProjectPayload | null>(null);

const page = computed(() => "project:" + props.id);

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
    setHeading(String(data.id),
               " · " + data.title + " · " + data.status + " · "
               + data.records.length + " " + word("tasks"));
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
  if (!payload.value) return;
  const { id, title, status } = payload.value;
  setHeading(String(id),
             " · " + title + " · " + status + " · " + shown + " " + word("tasks")
             + (hidden ? " · " + hidden + " " + word("hidden") : ""));
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
               @count="onCount" @ref="openRef" />
  </div>
</template>
