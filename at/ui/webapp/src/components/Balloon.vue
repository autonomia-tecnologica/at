<script setup lang="ts">
// Balloon — the interpreter's other shape: ONE sentence about what is on the
// screen, and the effect lands where the person already is.
//
// It is NOT a `.pop`. `pop.ts` keeps ONE open panel, and a balloon that took that
// slot would close every time a column's filter opened — which is the one thing a
// box that lives over the view cannot do. It is a layer of its own, over the view,
// and it takes no slot from anybody.
//
// It carries the EFFECT and not the conversation: one round, replaced by the next.
// What the sentence wrote shows in the view underneath, which is redrawn in place
// (`ask`), and the words read here are the engine's. The conversation, with its
// history, is the chat's.
//
// The CORE's switch is what renders it at all (`store.interpreter`); the page's
// own preference is whether it flies (`balloon.ts`), and it hides this and nothing
// else.

import { ref } from "vue";
import { ask } from "../lib/ask";
import { word } from "../lib/store";
import type { Turn } from "../lib/ask";
import AskTurn from "./AskTurn.vue";

const sentence = ref("");
const turn = ref<Turn | null>(null);
const busy = ref(false);

async function send(): Promise<void> {
  const text = sentence.value.trim();
  if (!text || busy.value) return;
  busy.value = true;
  try {
    turn.value = await ask(text);
    // The sentence is spent once the interpreter has read it — a refusal and a
    // question were read too. What is NOT spent is a request that never arrived:
    // there the sentence stays, and the person tries again.
    sentence.value = "";
  } catch (err) {
    turn.value = {
      sentence: text, kind: "refused", proposal: null,
      text: (err as Error).message, assist: false,
    };
  } finally {
    busy.value = false;
  }
}

// TASK-180, fatia 3/3: the SAME sentence, asked again with a Main Key — never
// a second one the person has to retype.
async function retry(mainKey: string): Promise<void> {
  if (!turn.value || busy.value) return;
  const asked = turn.value.sentence;
  busy.value = true;
  try {
    turn.value = await ask(asked, mainKey);
  } catch (err) {
    turn.value = {
      sentence: asked, kind: "refused", proposal: null,
      text: (err as Error).message, assist: false,
    };
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <aside class="balloon" role="region" :aria-label="word('balloon')">
    <form class="balloon-form" @submit.prevent="send">
      <input v-model="sentence" type="text" class="balloon-say" autocomplete="off"
             :placeholder="word('ask_hint')" :aria-label="word('interpreter')">
      <button type="submit" class="btn" :disabled="busy">{{ word("ask") }}</button>
    </form>
    <AskTurn v-if="turn" :turn="turn" @retry="retry" />
  </aside>
</template>
