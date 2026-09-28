<script setup lang="ts">
// KindView — a table's own table, and the record opened over it.
//
// EVERY record is fetched (`?all`): the CLI's list goes on obeying the table's
// declared default slice, but the page hands the whole store to the column
// filters and lets the person choose — the slice is the CLI's default, not the
// page's.

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { setFields } from "../lib/store";
import { nav, openRef, setCount, showError } from "../lib/views";
import TableView from "../components/TableView.vue";
import RecordView from "../components/RecordView.vue";
import type { TablePayload } from "../lib/record";

const props = defineProps<{ view: string }>();

const payload = ref<TablePayload | null>(null);
const total = ref(0);

// The frame says which record is open — and it only counts if the view is THIS
// one.
const record = computed(() => {
  const current = nav.current;
  if (!current || current.view !== props.view || !current.id || !payload.value) return null;
  return payload.value.records.find(rec => rec.id === current.id) || null;
});

async function load(): Promise<void> {
  try {
    const data = await api<TablePayload>("/api/table/" + encodeURIComponent(props.view) + "?all");
    payload.value = data;
    setFields(data.fields);
    total.value = data.records.length;
  } catch (err) {
    payload.value = null;
    showError(err as Error);
  }
}

onMounted(load);
// A write (the pick) redraws the SAME page, in the same position.
watch(() => nav.tick, load);
watch(() => props.view, () => {
  payload.value = null;
  load();
});
</script>

<template>
  <RecordView v-if="record" :record="record" :total="total" :page="view" :entity="view"
              @ref="openRef" />
  <TableView v-else-if="payload" :entity="view" :records="payload.records"
             :schema="payload.fields" :defaults="payload.columns" :page="view"
             :actions="payload.actions" @count="setCount" @ref="openRef" />
</template>
