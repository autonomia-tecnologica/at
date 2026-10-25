<script setup lang="ts">
// RangePop — ONE date column's filter, as an INTERVAL: from a day, until a day,
// either end optional. An empty end is an open end; both empty is no filter.
//
// The panel keeps no copy of the table: each change is handed to whoever opened
// it, the way `FilterPop` does, and the table behind it is what is redrawn.

import { ref } from "vue";
import { word } from "../../lib/store";

const props = withDefaults(
  defineProps<{
    from?: string;
    until?: string;
    onApply?: ((range: { from: string; until: string }) => void) | null;
  }>(),
  { from: "", until: "", onApply: null },
);

const from = ref(props.from);
const until = ref(props.until);

function change(): void {
  if (props.onApply) props.onApply({ from: from.value, until: until.value });
}
</script>

<template>
  <label class="opt range" @click.stop>
    <span>{{ word("date_from") }}</span>
    <input v-model="from" type="date" @change="change">
  </label>
  <label class="opt range" @click.stop>
    <span>{{ word("date_until") }}</span>
    <input v-model="until" type="date" @change="change">
  </label>
</template>
