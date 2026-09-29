<script setup lang="ts">
// Toast — the sentence itself, drawn from `lib/toast.ts`'s one slot. No close
// button, no click handler: the bar emptying IS the affordance (TASK-165,
// §"Decidido" — "sem botão de fechar manual decidido aqui").

import { toastState, DURATION } from "../lib/toast";
</script>

<template>
  <div v-if="toastState.current" :key="toastState.current.key" class="toast"
       role="status" aria-live="polite">
    <span class="toast-text">{{ toastState.current.message }}</span>
    <span class="toast-bar" :style="{ animationDuration: DURATION + 'ms' }"></span>
  </div>
</template>
