<script setup lang="ts">
// ProseField — a text as PROSE.
//
// THE RENDERER IS HOSTED (`lib/markdown`): `ensureRenderer` pulls `/vendor/marked`
// once, and this field is one of the places that asks for it. Until it lands,
// `proseHtml` answers null and the field draws the source it has — the honest
// answer with no renderer —, and the field REDRAWS when it lands, which is what
// `rendererReady` carries.
//
// NO WRAPPER: the base's edge rules (`.prose > :first-child` / `:last-child`)
// have to reach the first and last BLOCK.

import { ref, onMounted, watch } from "vue";
import { proseHtml, ensureRenderer, rendererReady } from "../lib/markdown";

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

onMounted(() => {
  void ensureRenderer();
  void render();
});
watch(() => props.text, render);
// The renderer arrives AFTER the mount — it is a hosted script —, and the first
// render answered null. This is what redraws the field as prose.
watch(rendererReady, render);
</script>

<template>
  <div v-if="html !== null" class="prose" :class="{ 'field-prose': field }" v-html="html"></div>
  <div v-else class="prose" :class="{ 'field-prose': field }">{{ text }}</div>
</template>
