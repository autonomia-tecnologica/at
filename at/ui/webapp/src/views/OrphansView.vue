<script setup lang="ts">
// OrphansView — the page of the tasks no project claims.
//
// It is a BOARD of tasks and nothing else: there is no project header, no
// subproject and no parent — the very absence of all that is what put these tasks
// here, and the same absence is why no card here ever carries a project chip
// (`show-project` false). The word and the rows are both the server's.

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { store, setFields, word } from "../lib/store";
import { nav, openRef, setTrail, showError, ORPHANS_KEY } from "../lib/views";
import TaskBoard from "../components/TaskBoard.vue";
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
    setTrail(word("no_project"));
  } catch (err) {
    payload.value = null;
    showError(err as Error);
  }
}

onMounted(load);
watch(() => nav.tick, load);
</script>

<template>
  <RecordView v-if="record" :record="record" :total="payload?.records.length ?? 0"
              :page="ORPHANS_KEY" :entity="store.types.task" @ref="openRef" />
  <!-- THE SAME BOARD A PROJECT'S PAGE DRAWS: the two are the SAME shape — every
       row carries the same project, or the same absence — and the table
       declares `hide: ["project", "orphans"]` for both. -->
  <TaskBoard v-else-if="payload" :entity="store.types.task" :records="payload.records"
             :schema="payload.fields" :page="ORPHANS_KEY" :show-project="false" @ref="openRef" />
</template>
