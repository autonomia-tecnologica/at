<script setup lang="ts">
// ConfirmDialog — `lib/confirm.ts`'s one layer: a question, and two answers.
//
// It wears the Design System's own "stop and ask" (`.veil` + `.dialog`, the
// same pair the entrance and the first run wear), so a confirmation belongs to
// the app and not to the browser's chrome. Escape says no, Enter says yes, and
// the yes button takes the focus the moment the box opens — the keyboard is
// how a confirmation is answered.
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from "vue";
import { word } from "../lib/store";
import { confirmState, answer } from "../lib/confirm";

const yes = ref<HTMLButtonElement | null>(null);

function onKeydown(event: KeyboardEvent): void {
  if (!confirmState.open) return;
  if (event.key === "Escape") {
    event.preventDefault();
    answer(false);
  } else if (event.key === "Enter") {
    event.preventDefault();
    answer(true);
  }
}

watch(() => confirmState.open, async open => {
  if (!open) return;
  await nextTick();
  yes.value?.focus();
});

onMounted(() => document.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => document.removeEventListener("keydown", onKeydown));
</script>

<template>
  <Transition leave-active-class="veil-leave-active">
    <div v-if="confirmState.open" class="veil" @click="answer(false)"></div>
  </Transition>
  <Transition leave-active-class="dialog-leave-active">
  <div v-if="confirmState.open" class="dialog confirm" role="dialog" aria-modal="true">
    <p>{{ confirmState.message }}</p>
    <div class="dialog-actions">
      <button type="button" class="btn btn-quiet" @click="answer(false)">
        {{ word("confirm_cancel") }}
      </button>
      <button ref="yes" type="button" class="btn" @click="answer(true)">
        {{ word("confirm_ok") }}
      </button>
    </div>
  </div>
  </Transition>
</template>
