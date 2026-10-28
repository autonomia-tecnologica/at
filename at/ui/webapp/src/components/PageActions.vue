<script setup lang="ts">
// PageActions — the screen's ACTIONS, drawn on the right of the page header
// (`App.vue`, `#page-header-actions`). A screen declares them where it already
// keeps them; this component moves them up. `inline` keeps them in place, for
// a screen hosted somewhere with no page header (the record panel).
defineProps<{ inline?: boolean }>();
</script>

<template>
  <Teleport to="#page-header-actions" defer :disabled="inline">
    <div class="page-actions"><slot /></div>
  </Teleport>
</template>
