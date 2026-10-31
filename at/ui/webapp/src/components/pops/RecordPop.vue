<script setup lang="ts">
// RecordPop — a record, floating over the list or the board it was clicked
// from (TASK-173), instead of swapping the whole page for it.
//
// `records` is a GETTER and not the rows themselves: the list underneath
// stays mounted and keeps reading for itself (a write, a poke, a reload), and
// reading through the getter on every access is what lets this panel follow
// that same table instead of showing the snapshot the row had the moment it
// was clicked. A record that stops being IN that list — closed by a filter,
// deleted — closes the panel with it, because there is nothing left in it to
// show.

import { computed, watch } from "vue";
import { closePop } from "../../lib/pop";
import { openRef } from "../../lib/views";
import RecordView from "../RecordView.vue";
import type { RecordRow } from "../../lib/record";

const props = defineProps<{
  entity: string;
  page: string;
  id: number;
  records: () => RecordRow[];
  // O QUE O ENGINE DEIXA ESTE ATOR ESCREVER: o painel repassa ao `RecordView`,
  // que sem `edit` é só leitura.
  actions?: string[];
}>();

const record = computed<RecordRow | null>(() => props.records().find(rec => rec.id === props.id) ?? null);
const total = computed(() => props.records().length);

watch(record, found => { if (!found) closePop(); });
</script>

<template>
  <RecordView v-if="record" :record="record" :total="total" :page="page" :entity="entity"
              :actions="actions || []" popup @ref="openRef" @close="closePop" />
</template>
