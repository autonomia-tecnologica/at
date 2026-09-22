<script setup lang="ts">
// ColumnsPop — the panel a RIGHT CLICK on a header opens, and the same one the
// pill at the end of the row opens when a column is hidden.
//
// Every column shows up in the order it is displayed, one check per column:
// unchecked is hidden, and checking it back brings it in where the order puts it.
// The `id` is listed too — checked and disabled: what names a row is not a thing
// to lose.

import { label } from "../../lib/store";
import type { FieldSpec } from "../../lib/record";

const props = withDefaults(
  defineProps<{
    order: string[];
    hidden: Set<string>;
    fields: FieldSpec[];
    onToggle?: ((name: string, hide: boolean) => void) | null;
  }>(),
  { onToggle: null },
);

const byName = (name: string): FieldSpec | null =>
  props.fields.find(field => field.name === name) || null;

function change(name: string, ev: Event): void {
  const checked = (ev.target as HTMLInputElement).checked;
  if (props.onToggle) props.onToggle(name, !checked);
}
</script>

<template>
  <label v-for="name in order" :key="name" class="opt" @click.stop>
    <input type="checkbox" :checked="!hidden.has(name)" :disabled="name === 'id'"
           @change="change(name, $event)">
    <span>{{ label(byName(name)?.labels) || name }}</span>
  </label>
</template>
