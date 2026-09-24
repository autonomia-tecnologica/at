<script setup lang="ts">
// OrphansView — the page of the tasks no project claims.
//
// It is a TABLE of tasks and nothing else: there is no project header, no
// subproject and no parent — the very absence of all that is what put these tasks
// here. The word and the rows are both the server's.

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { store, setFields, word } from "../lib/store";
import { nav, openRef, setHeading, showError, ORPHANS_KEY } from "../lib/views";
import TableView from "../components/TableView.vue";
import RecordView from "../components/RecordView.vue";
import type { TablePayload } from "../lib/record";

const payload = ref<TablePayload | null>(null);

const record = computed(() => {
  const current = nav.current;
  if (!current || current.view !== ORPHANS_KEY || !current.id || !payload.value) return null;
  return payload.value.records.find(rec => rec.id === current.id) || null;
});

async function load(): Promise<void> {
  try {
    const data = await api<TablePayload>("/api/orphans");
    payload.value = data;
    setFields(data.fields);
    setHeading(word("no_project"), " · " + data.records.length + " " + word("tasks"));
  } catch (err) {
    payload.value = null;
    showError(err as Error);
  }
}

// The band carries what the FILTER leaves, like the panel's line does: the two
// numbers describe the same rows and may not disagree. It arrives from the table
// itself, which is who holds the rows.
function onCount(shown: number, hidden: number): void {
  if (!payload.value) return;
  setHeading(word("no_project"),
             " · " + shown + " " + word("tasks")
             + (hidden ? " · " + hidden + " " + word("hidden") : ""));
}

onMounted(load);
watch(() => nav.tick, load);
</script>

<template>
  <RecordView v-if="record" :record="record" :total="payload?.records.length ?? 0"
              :page="ORPHANS_KEY" :entity="store.types.task" @ref="openRef" />
  <!-- THE RULE HOLDS HERE AS ON A PROJECT'S PAGE (`rule`): the two are the SAME
       shape — every row carries the same project, or the same absence — and the
       table declares `hide: ["project", "orphans"]` for both. -->
  <TableView v-else-if="payload" :entity="store.types.task" :records="payload.records"
             :schema="payload.fields" :view-key="ORPHANS_KEY" :page="ORPHANS_KEY" rule
             @count="onCount" @ref="openRef" />
</template>
