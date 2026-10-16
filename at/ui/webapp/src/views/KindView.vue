<script setup lang="ts">
// KindView — a table's own table, and the record opened over it.
//
// EVERY record is fetched (`?all`): the CLI's list goes on obeying the table's
// declared default slice, but the page hands the whole store to the column
// filters and lets the person choose — the slice is the CLI's default, not the
// page's.

import { ref, computed, watch, onMounted, nextTick } from "vue";
import { api } from "../lib/api";
import { setFields, kindLabel } from "../lib/store";
import { nav, openRef, setTrail, showError, pageReadsOnItsOwn, pageLoaded } from "../lib/views";
import TableView from "../components/TableView.vue";
import RecordView from "../components/RecordView.vue";
import type { TablePayload } from "../lib/record";

const props = defineProps<{ view: string }>();

// THIS PAGE READS FOR ITSELF, and the boot has to know: the rows come from
// `/api/table/<view>` on mount, so without this the shell would reveal over an
// empty table and fill it a beat later. It runs in SETUP (synchronously), so
// the shell — which checks one tick later — learns it before the read starts.
pageReadsOnItsOwn();

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
    // THE STEP IS THE TABLE'S OWN NAME, and the section above it is the
    // shell's (`Tabelas › Audit`) — the page names the thing it draws.
    setTrail(kindLabel(props.view));
  } catch (err) {
    payload.value = null;
    showError(err as Error);
  } finally {
    // THE SIDEBAR'S LIVE COUNT AND THE COLUMN WIDTHS LAND ONE FRAME LATE.
    // `TableView`'s `watchEffect` (the live number) only runs once `payload`
    // has mounted it — not in the same tick as the assignment above — and its
    // `measure()` (the `<col>` widths) is a DOM reading scheduled from ITS OWN
    // `onMounted` through ITS OWN `nextTick`. Awaiting the bare `nextTick`
    // left the table room to paint with NO `<col>` (the browser's auto layout)
    // and snap to the measured widths as the gate opened. Two animation frames
    // is what actually waits on the BROWSER: a `nextTick` waits only on Vue's
    // queue, and the first frame proves the one `measure` runs in has started,
    // not that its layout has been painted — the second is after that paint.
    await nextTick();
    await new Promise<void>(resolve => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    });
    // Win or lose, the boot's wait for THIS page is over.
    pageLoaded();
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
             :actions="payload.actions" :declarable="payload.declarable"
             @ref="openRef" />
</template>
