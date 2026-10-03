<script setup lang="ts">
// AskTurn — what a sentence turned into, drawn the ONE way both shapes draw it.
//
// The chat keeps a list of these and the balloon keeps the last one, but what is
// READ is the same in both, and that is the rule of the box: the two ask the same
// thing and show the same thing. The sentence, the proposal it became — in the
// engine's words —, and then what the engine answered. A question and a refusal
// are answers too, and they are shown where the answer goes: the page writes none
// of these sentences, it puts where they are read the ones it was handed.

import { ref } from "vue";
import { word } from "../lib/store";
import type { Turn } from "../lib/ask";

defineProps<{ turn: Turn }>();
// TASK-180, fatia 3/3: the one retry a refusal can still offer — typing the
// Main Key the first attempt did not carry. It is the PARENT that re-asks
// (`Balloon`/`ChatView` both already hold the road to `ask`); this component
// only reads the typing and hands the key up.
const emit = defineEmits<{ retry: [mainKey: string] }>();
const mainKey = ref("");

function retry(): void {
  const key = mainKey.value;
  if (!key) return;
  mainKey.value = "";
  emit("retry", key);
}
</script>

<template>
  <div class="turn" :data-kind="turn.kind">
    <p class="said">{{ turn.sentence }}</p>
    <p v-if="turn.proposal" class="proposal">
      <span class="tag">{{ word("proposal") }}</span>{{ turn.proposal }}
    </p>
    <p class="answer">{{ turn.text }}</p>
    <form v-if="turn.assist" class="assist-retry" @submit.prevent="retry">
      <input v-model="mainKey" type="password" autocomplete="off"
             :placeholder="word('assist_key')" :aria-label="word('assist_key')">
      <button type="submit" class="btn">{{ word("assist_retry") }}</button>
    </form>
  </div>
</template>
