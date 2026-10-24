<script setup lang="ts">
// ChatView — the interpreter's chat: the WHOLE of it, and it stays.
//
// A view like every other, with an address of its own (`/chat`), so a reload lands
// back in the conversation and the panel lights the line. What is read here is the
// sentence, the proposal it became, the answer, and the question when the sentence
// was ambiguous — always the engine's words, because the page invents none.
//
// The conversation is `chat.ts`'s, shared with the balloon (TASK-183): a module
// and not this component, because a view is unmounted the moment another one
// opens, and a conversation that ended when the person looked at something
// else — or opened the balloon instead — would not be one.
//
// When there is nothing to say, the box says it in the catalog's own words rather
// than in a sentence of its own.

import { ref, nextTick, watch, watchEffect } from "vue";
import { chatState, send as sendTurn } from "../lib/chat";
import { store, word } from "../lib/store";
import { setTrail } from "../lib/views";
import AskTurn from "../components/AskTurn.vue";

const sentence = ref("");
const busy = ref(false);
const log = ref<HTMLElement | null>(null);

watchEffect(() => setTrail(word("chat")));

// THE "THINKING" BUBBLE (24/10/2026): three dots where the answer will be, but
// only once the wait passes `THINKING_AFTER_MS` — an instant answer never
// flashes them. The person's own sentence is shown at once (it left the box).
const THINKING_AFTER_MS = 250;
const thinking = ref(false);
let thinkingTimer: ReturnType<typeof setTimeout> | undefined;

watch(() => chatState.pending, (pending) => {
  clearTimeout(thinkingTimer);
  thinking.value = false;
  if (pending === null) return;
  void scrolled();
  thinkingTimer = setTimeout(() => {
    thinking.value = true;
    void scrolled();
  }, THINKING_AFTER_MS);
});

// THE NEWEST IS THE ONE READ: the conversation grows downward, and what was
// just asked is what the person is looking for. A scroll, never a reflow of
// the page.
async function scrolled(): Promise<void> {
  await nextTick();
  if (log.value) log.value.scrollTop = log.value.scrollHeight;
}

// A SENTENCE THE OPENING OFFERS: the same road as typed one — it goes up as a
// turn of its own, so the person reads the example AND its answer side by side.
async function say(text: string): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  try {
    await sendTurn(text);
    await scrolled();
  } finally {
    busy.value = false;
  }
}

async function send(): Promise<void> {
  const text = sentence.value.trim();
  if (!text || busy.value) return;
  sentence.value = "";
  await say(text);
}

// THE OPENING (20/10/2026): an empty conversation says what the box takes — a
// sentence, in plain words — and offers four of them to try, each a click that
// asks for real. The words are the catalog's, in the language of the page.
const examples = ["chat_ex1", "chat_ex2", "chat_ex3", "chat_ex4"];

// TASK-180, fatia 3/3: the SAME sentence, asked again with a Main Key — kept
// as a NEW turn, the same way the chat keeps every round rather than editing
// one that already happened.
async function retry(sentence: string, mainKey: string): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  try {
    await sendTurn(sentence, mainKey);
    await scrolled();
  } finally {
    busy.value = false;
  }
}

// TASK-183: "Confirmar"/"Negar" resolve the question IN PLACE — `AskTurn`'s
// own, with no sentence to send back up and no new turn to scroll to.
</script>

<template>
  <div class="chat">
    <div ref="log" class="chat-log">
      <div v-if="!chatState.turns.length" class="chat-hello">
        <p>{{ word("chat_hello") }}</p>
        <button v-for="key in examples" :key="key" type="button" class="chat-example"
                :title="word('chat_example')" @click="say(word(key))">
          {{ word(key) }}
        </button>
      </div>
      <AskTurn v-for="(turn, index) in chatState.turns" :key="index" :turn="turn"
               @retry="(key) => retry(turn.sentence, key)" />
      <div v-if="chatState.pending !== null" class="turn turn-pending">
        <p class="said">{{ chatState.pending }}</p>
        <div v-if="thinking" class="answer-msg thinking" role="status">
          <span class="sr-only">{{ word("chat_thinking") }}</span>
          <span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>
        </div>
      </div>
    </div>
    <p v-if="store.assist && !store.jev_ready" class="chat-notice">
      {{ word("jev_not_configured") }}
    </p>
    <form class="chat-form" @submit.prevent="send">
      <input v-model="sentence" type="text" class="chat-say" autocomplete="off"
             :placeholder="word('ask_hint')" :aria-label="word('chat')">
      <button type="submit" class="btn" :disabled="busy">{{ word("ask") }}</button>
    </form>
  </div>
</template>
