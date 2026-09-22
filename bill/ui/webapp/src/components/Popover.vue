<script setup lang="ts">
// Popover — THE slot of the panel that floats. One only, at the logical
// `document.body` (the shell mounts it last), and the content comes from whoever
// took the slot (`pop`).
//
// The positioning is the imperative part Vue does not take away: the panel is
// measured AFTER it exists and clamped to the window — a menu near the edge
// would walk off it. Hence the `watch` with `flush: "post"`.

import { ref, watch, nextTick } from "vue";
import { popState, placeAt } from "../lib/pop";

const el = ref<HTMLElement | null>(null);

async function place(): Promise<void> {
  await nextTick();
  placeAt(el.value, { anchor: popState.anchor, point: popState.point });
}

watch(() => popState.key, place, { flush: "post" });
watch(() => popState.props, place, { flush: "post" });
</script>

<template>
  <div v-if="popState.component" :key="popState.key ?? 'pop'" ref="el" class="pop"
       v-bind="popState.attrs || {}" @click.stop>
    <component :is="popState.component" v-bind="popState.props || {}" />
  </div>
</template>
