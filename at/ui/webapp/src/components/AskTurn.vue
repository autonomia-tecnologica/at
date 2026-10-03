<script setup lang="ts">
// AskTurn — what a sentence turned into, drawn the ONE way both shapes draw it.
//
// The chat and the balloon keep the SAME list of these (TASK-183: one history,
// `lib/chat.ts`, so the two never disagree about what was said), but what is
// READ here is the same in both regardless, and that is the rule of the box: the
// two ask the same thing and show the same thing. The sentence, the proposal it
// became — in the engine's words —, and then what the engine answered. A
// question and a refusal are answers too, and they are shown where the answer
// goes: the page writes none of these sentences, it puts where they are read the
// ones it was handed.

import { ref } from "vue";
import { word } from "../lib/store";
import type { Turn } from "../lib/ask";

const props = defineProps<{ turn: Turn }>();
// TASK-180, fatia 3/3: the one retry a refusal can still offer — typing the
// Main Key the first attempt did not carry. It is the PARENT that re-asks
// (`Balloon`/`ChatView` both already hold the road to `ask`); this component
// only reads the typing and hands the key up.
//
// TASK-183: "Confirmar" hands the REWRITTEN sentence up for the parent to ask
// again — the same road a retry already walks, with no key to type because
// the rewritten sentence resolves on its own. "Negar" asks nothing: it is
// read entirely here, by `declined` below, the same way a refusal nobody
// retried stays exactly as it was asked.
const emit = defineEmits<{ retry: [mainKey: string]; confirm: [sentence: string] }>();
const mainKey = ref("");
const declined = ref(false);

function retry(): void {
  const key = mainKey.value;
  if (!key) return;
  mainKey.value = "";
  emit("retry", key);
}

function confirm(): void {
  if (!props.turn.confirm) return;
  emit("confirm", props.turn.confirm);
}

function deny(): void {
  declined.value = true;
}
</script>

<template>
  <div class="turn" :data-kind="turn.kind">
    <p class="said">{{ turn.sentence }}</p>
    <p v-if="turn.proposal" class="proposal">
      <span class="tag">{{ word("proposal") }}</span>{{ turn.proposal }}
    </p>
    <p class="answer">{{ turn.text }}</p>
    <div v-if="turn.confirm && !declined" class="assist-confirm">
      <button type="button" class="btn" @click="confirm">{{ word("assist_confirm") }}</button>
      <button type="button" class="btn btn-quiet" @click="deny">{{ word("assist_deny") }}</button>
    </div>
    <form v-if="turn.assist" class="assist-retry" @submit.prevent="retry">
      <input v-model="mainKey" type="password" autocomplete="off"
             :placeholder="word('assist_key')" :aria-label="word('assist_key')">
      <button type="submit" class="btn">{{ word("assist_retry") }}</button>
    </form>
  </div>
</template>
