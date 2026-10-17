<script setup lang="ts">
// Popover — THE slot of the panel that floats. Almost always one entry, at the
// logical `document.body` (the shell mounts it last); a SECOND can sit on top
// when one nests over it (`pop.ts`'s `nest`, TASK-173) — each gets its own node
// so a floating record panel and the pick it opens stay two boxes, not one
// replacing the other.
//
// The positioning is the imperative part Vue does not take away: each panel is
// measured AFTER it exists and clamped to the window — a menu near the edge
// would walk off it. Hence the `watch` with `flush: "post"`.

import { watch, nextTick } from "vue";
import type { ComponentPublicInstance } from "vue";
import { popStack, placeAt } from "../lib/pop";

const els = new Map<string, HTMLElement>();

function setEl(key: string, el: Element | ComponentPublicInstance | null): void {
  if (el) els.set(key, el as HTMLElement);
  else els.delete(key);
}

async function place(): Promise<void> {
  await nextTick();
  for (const entry of popStack) placeAt(els.get(entry.key) ?? null, { anchor: entry.anchor, point: entry.point });
}

watch(popStack, place, { flush: "post" });
</script>

<template>
  <div v-for="entry in popStack" :key="entry.key" :ref="el => setEl(entry.key, el)" class="pop"
       v-bind="entry.attrs || {}" @click.stop>
    <component :is="entry.component" v-bind="entry.props || {}" />
  </div>
</template>
