<script setup lang="ts">
// ProseField — a text as PROSE.
//
// THE RENDERER IS NOT HERE YET (`lib/markdown`): `proseHtml` answers null, and
// what the person reads is the text as it is stored. The branch for the rendered
// prose is already drawn, so the day the renderer lands nothing here changes but
// the answer.
//
// NO WRAPPER: the base's edge rules (`.prose > :first-child` / `:last-child`)
// have to reach the first and last BLOCK.

import { ref, onMounted, watch } from "vue";
import { proseHtml } from "../lib/markdown";

const props = withDefaults(
  defineProps<{
    text?: string;
    // `field-prose` takes away the page's breathing room, which is the PAGE's:
    // inside the `<dd>` it would be a second inset.
    field?: boolean;
  }>(),
  { text: "", field: false },
);

const html = ref<string | null>(null);

async function render(): Promise<void> {
  html.value = null;
  const out = await proseHtml(props.text);
  if (out !== null) html.value = out;
}

onMounted(render);
watch(() => props.text, render);
</script>

<template>
  <div v-if="html !== null" class="prose" :class="{ 'field-prose': field }" v-html="html"></div>
  <div v-else class="prose" :class="{ 'field-prose': field }">{{ text }}</div>
</template>
