<script setup lang="ts">
// EmptyState — an empty room that tells what it is and what to do next: an icon,
// a short title, one line of text and, in the default slot, the ACTION (a button
// that is already on screen, never a hint to go look for one).

defineProps<{ title: string; text?: string; icon?: "inbox" | "folder" | "bell" | "note" }>();

const PATHS: Record<string, string> = {
  inbox: "M3 13h5l1.5 3h5L16 13h5M3 13l2.5-8h13L21 13v6H3z",
  folder: "M3 6h6l2 2h10v11H3z",
  bell: "M6 17V11a6 6 0 0 1 12 0v6l2 2H4zM10 21h4",
  note: "M5 3h14v18H5zM9 8h6M9 12h6M9 16h4",
};
</script>

<template>
  <div class="empty-state" role="status">
    <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path :d="PATHS[icon || 'inbox']" />
    </svg>
    <h3>{{ title }}</h3>
    <p v-if="text">{{ text }}</p>
    <div v-if="$slots.default" class="empty-action"><slot /></div>
  </div>
</template>
