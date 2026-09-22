<script setup lang="ts">
// FilterPop — ONE column's filter: every value the column carries, checked while
// the filter accepts it. Click one to drop it, click it back to bring it in.
//
// The checking state is LOCAL and the panel does NOT rebuild itself on every
// change: what is redrawn is the table behind it. Rebuilding the panel on every
// click would lose the keyboard focus in the middle of the list.

import { ref } from "vue";

const props = withDefaults(
  defineProps<{
    values: string[];
    accepted?: Set<string> | null; // null = all of them
    onApply?: ((accepted: Set<string>) => void) | null;
  }>(),
  { accepted: null, onApply: null },
);

const boxes = ref(
  props.values.map(value => ({
    value,
    on: !props.accepted || props.accepted.has(value),
  })),
);

function toggle(item: { value: string; on: boolean }, ev: Event): void {
  item.on = (ev.target as HTMLInputElement).checked;
  const next = new Set(boxes.value.filter(box => box.on).map(box => box.value));
  if (props.onApply) props.onApply(next);
}
</script>

<template>
  <label v-for="b in boxes" :key="String(b.value)" class="opt" @click.stop>
    <input type="checkbox" :checked="b.on" @change="toggle(b, $event)">
    <span>{{ b.value || "—" }}</span>
  </label>
</template>
