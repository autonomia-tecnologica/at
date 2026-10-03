<script setup lang="ts">
// ChatView — the interpreter's chat: the WHOLE of it, and it stays.
//
// A view like every other, with an address of its own (`/chat`), so a reload lands
// back in the conversation and the panel lights the line. What is read here is the
// sentence, the proposal it became, the answer, and the question when the sentence
// was ambiguous — always the engine's words, because the page invents none.
//
// The conversation is `chat.ts`, which is what the chat has and the balloon does
// not: a module and not this component, because a view is unmounted the moment
// another one opens, and a conversation that ended when the person looked at
// something else would not be one.
//
// When there is nothing to say, the box says it in the catalog's own words rather
// than in a sentence of its own.

import { ref, nextTick, watchEffect } from "vue";
import { ask } from "../lib/ask";
import { chatState, remember } from "../lib/chat";
import { word } from "../lib/store";
import { setTrail } from "../lib/views";
import AskTurn from "../components/AskTurn.vue";

const sentence = ref("");
const busy = ref(false);
const log = ref<HTMLElement | null>(null);

watchEffect(() => setTrail(word("chat")));

async function send(): Promise<void> {
  const text = sentence.value.trim();
  if (!text || busy.value) return;
  busy.value = true;
  try {
    remember(await ask(text));
    sentence.value = "";
    // THE NEWEST IS THE ONE READ: the conversation grows downward, and what was
    // just asked is what the person is looking for. A scroll, never a reflow of
    // the page.
    await nextTick();
    if (log.value) log.value.scrollTop = log.value.scrollHeight;
  } catch (err) {
    remember({
      sentence: text, kind: "refused", proposal: null,
      text: (err as Error).message, assist: false,
    });
  } finally {
    busy.value = false;
  }
}

// TASK-180, fatia 3/3: the SAME sentence, asked again with a Main Key — kept
// as a NEW turn, the same way the chat keeps every round rather than editing
// one that already happened.
async function retry(sentence: string, mainKey: string): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  try {
    remember(await ask(sentence, mainKey));
    await nextTick();
    if (log.value) log.value.scrollTop = log.value.scrollHeight;
  } catch (err) {
    remember({
      sentence, kind: "refused", proposal: null,
      text: (err as Error).message, assist: false,
    });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="chat">
    <div ref="log" class="chat-log">
      <p v-if="!chatState.turns.length" class="empty">{{ word("no_records") }}</p>
      <AskTurn v-for="(turn, index) in chatState.turns" :key="index" :turn="turn"
               @retry="(key) => retry(turn.sentence, key)" />
    </div>
    <form class="chat-form" @submit.prevent="send">
      <input v-model="sentence" type="text" class="chat-say" autocomplete="off"
             :placeholder="word('ask_hint')" :aria-label="word('chat')">
      <button type="submit" class="btn" :disabled="busy">{{ word("ask") }}</button>
    </form>
  </div>
</template>
