<script setup lang="ts">
// Toast — the sentence itself, drawn from `lib/toast.ts`'s one slot. No close
// button (TASK-165, §"Decidido" — "sem botão de fechar manual decidido aqui"),
// and the one ACTION the caller names (B-54): the write's "Undo", a door that
// goes away with the toast.

import { toastState, DURATION, type ToastAction } from "../lib/toast";

function run(action: ToastAction | null): void {
  action?.run();
}
</script>

<template>
  <Transition leave-active-class="toast-leave-active">
    <div v-if="toastState.current" :key="toastState.current.key" class="toast"
         role="status" aria-live="polite">
      <span class="toast-row">
        <span class="toast-text">{{ toastState.current.message }}</span>
        <button v-if="toastState.current.action" type="button" class="toast-action"
                @click="run(toastState.current.action)">{{ toastState.current.action.label }}</button>
      </span>
      <span class="toast-bar" :style="{ '--toast-life': DURATION + 'ms' }"></span>
    </div>
  </Transition>
</template>
