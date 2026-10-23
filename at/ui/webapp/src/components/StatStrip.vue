<script setup lang="ts">
// StatStrip — the indicators of a section page: a big number and its label, and,
// when the items carry a `share`, the SAME numbers as one proportional bar. It
// OWNS its layout: cards in a grid on the desktop, and on the phone ONE strip of
// small chips ("n label") that wrap — the screens only hand over the items.
// The `tone` is the vocabulary's (a status or a bucket), drawn here and nowhere else.

export interface StatItem {
  key: string;
  value: number | string;
  label: string;
  tone?: string;
  title?: string;
  // The part this item has in the bar (flex-grow); no `share`, no part.
  share?: number;
}

const props = defineProps<{ items: StatItem[] }>();

function hasBar(): boolean {
  return props.items.some((item) => (item.share ?? 0) > 0);
}
</script>

<template>
  <div class="stat-strip">
    <div class="stats">
      <div v-for="item in items" :key="item.key" class="stat" :data-tone="item.tone"
           :title="item.title">
        <b>{{ item.value }}</b>
        <span>{{ item.label }}</span>
      </div>
    </div>
    <div v-if="hasBar()" class="bars">
      <span v-for="item in items.filter((i) => i.share !== undefined)" :key="item.key"
            class="bar-part" :data-tone="item.tone" :style="{ flexGrow: item.share }"
            :title="item.title ?? item.label + ': ' + item.value"></span>
    </div>
  </div>
</template>
