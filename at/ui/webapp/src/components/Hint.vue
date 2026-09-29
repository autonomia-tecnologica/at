<script setup lang="ts">
// Hint — the ESC-armed shortcuts' own dica (TASK-126): the letters on screen
// while the pair is armed, so a person knows what to press next.
//
// A LAYER OF ITS OWN, like `Toast.vue` and `Balloon.vue`, and not the pop's
// slot: the pop is ONE open panel that a click or an action closes outright,
// and reusing that slot would mean a real popover and this hint fighting over
// the same one seat.

import { shortcutsState, SHORTCUTS } from "../lib/shortcuts";
import { word } from "../lib/store";
</script>

<template>
  <div v-if="shortcutsState.armed" class="shortcut-hint" role="status" aria-live="polite">
    <span v-for="s in SHORTCUTS" :key="s.key" class="shortcut">
      <b>{{ s.key }}</b>
      <span>{{ word(s.labelKey) }}</span>
    </span>
  </div>
</template>
