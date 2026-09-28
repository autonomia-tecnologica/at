<script setup lang="ts">
// ContextMenu — the ONE panel every declared right-click occasion opens
// (TASK-120, fatia 1). What it shows is never its own invention: whoever
// opens it (`lib/menu.ts`) hands over the items already filtered by what the
// engine says is legal — this component draws a list and nothing else.

import { closePop } from "../../lib/pop";

export interface MenuItem {
  label: string;
  action: () => void;
}

const props = defineProps<{
  items: MenuItem[];
}>();

function run(item: MenuItem): void {
  // `closePop` first: an item whose action does not itself open another pop
  // (`openColumns` does; a plain write does not) still has to close this one.
  closePop();
  item.action();
}
</script>

<template>
  <button v-for="(item, i) in props.items" :key="i" type="button" class="opt"
          @click.stop="run(item)">{{ item.label }}</button>
</template>
