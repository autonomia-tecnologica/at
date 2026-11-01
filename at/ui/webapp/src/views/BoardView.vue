<script setup lang="ts">
// BoardView — every task, across every project, as a BOARD.
//
// It is the same rows `TasksView.vue` already counts (`/api/table/task?all`),
// cut a different way: not a summary, but every task itself, in the column its
// own status already names. It invents no data and no word, the same discipline
// `TasksView.vue` keeps.

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { store, setFields, word } from "../lib/store";
import { nav, openRef, setTrail, showError, BOARD_KEY } from "../lib/views";
import TaskBoard from "../components/TaskBoard.vue";
import RecordView from "../components/RecordView.vue";
import type { TablePayload } from "../lib/record";

const payload = ref<TablePayload | null>(null);

const record = computed(() => {
  const current = nav.current;
  if (!current || current.view !== BOARD_KEY || !current.id || !payload.value) return null;
  return payload.value.records.find(rec => rec.id === current.id) || null;
});

async function load(): Promise<void> {
  try {
    const data = await api<TablePayload>("/api/table/task?all");
    payload.value = data;
    setFields(data.fields);
    setTrail(word("board"));
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
              :page="BOARD_KEY" :entity="store.types.task" @ref="openRef" />
  <TaskBoard v-else-if="payload" :entity="store.types.task" :records="payload.records"
             :schema="payload.fields" :page="BOARD_KEY" :actions="payload.actions"
             @ref="openRef" />
</template>
