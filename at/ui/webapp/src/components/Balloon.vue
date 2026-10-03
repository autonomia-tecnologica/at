<script setup lang="ts">
// Balloon — the interpreter's other shape: the SAME conversation as `/chat`
// (TASK-183), read from wherever the person happens to be instead of a view
// of its own.
//
// It is NOT a `.pop`. `pop.ts` keeps ONE open panel, and a balloon that took that
// slot would close every time a column's filter opened — which is the one thing a
// box that lives over the view cannot do. It is a layer of its own, over the view,
// and it takes no slot from anybody.
//
// **The history is `lib/chat.ts`'s, and not this component's own.** Two lists
// of the same conversation would be two truths about what was said the first
// time a person opened the balloon after asking something in `/chat`, or the
// other way round — so both shapes read `chatState` and both call `remember`,
// and `ask()` is the one door either walks to get there. What stays this
// component's own is the OPEN/CLOSED shape: a bubble in the corner until a
// click grows it into the window, and never the other way around.
//
// The CORE's switch is what renders it at all (`store.interpreter`); the page's
// own preference is whether it flies (`balloon.ts`), and it hides this and nothing
// else.

import { ref, nextTick } from "vue";
import { ask } from "../lib/ask";
import { chatState, remember } from "../lib/chat";
import { word } from "../lib/store";
import AskTurn from "./AskTurn.vue";

const sentence = ref("");
const busy = ref(false);
const log = ref<HTMLElement | null>(null);

// CLOSED, ALWAYS, ON BIRTH (padrão Claude) — a bubble in the corner that opens
// into the window on a click, and never the other way: a balloon that opened
// by itself would compete with whatever page the person just reached. The
// state is this component's own and answers no navigation: it is read nowhere
// else, so a page change neither opens nor closes it on its own.
const open = ref(false);

async function scrolled(): Promise<void> {
  await nextTick();
  if (log.value) log.value.scrollTop = log.value.scrollHeight;
}

async function send(): Promise<void> {
  const text = sentence.value.trim();
  if (!text || busy.value) return;
  busy.value = true;
  try {
    remember(await ask(text));
    // The sentence is spent once the interpreter has read it — a refusal and a
    // question were read too. What is NOT spent is a request that never arrived:
    // there the sentence stays, and the person tries again.
    sentence.value = "";
    await scrolled();
  } catch (err) {
    remember({
      sentence: text, kind: "refused", proposal: null,
      text: (err as Error).message, assist: false, confirm: null,
    });
  } finally {
    busy.value = false;
  }
}

// TASK-180, fatia 3/3: the SAME sentence, asked again with a Main Key — never
// a second one the person has to retype.
async function retry(sentence: string, mainKey: string): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  try {
    remember(await ask(sentence, mainKey));
    await scrolled();
  } catch (err) {
    remember({
      sentence, kind: "refused", proposal: null,
      text: (err as Error).message, assist: false, confirm: null,
    });
  } finally {
    busy.value = false;
  }
}

// TASK-183: "Confirmar" on a cautious assist's question — the REWRITTEN
// sentence `AskTurn` already carries, asked again with no Main Key at all: it
// resolves on its own through the ordinary matcher.
async function confirm(sentence: string): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  try {
    remember(await ask(sentence));
    await scrolled();
  } catch (err) {
    remember({
      sentence, kind: "refused", proposal: null,
      text: (err as Error).message, assist: false, confirm: null,
    });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <button v-if="!open" type="button" class="balloon-bubble" @click="open = true">
    {{ word("interpreter") }}
  </button>
  <aside v-else class="balloon" role="region" :aria-label="word('balloon')">
    <div class="balloon-head">
      <strong>{{ word("balloon") }}</strong>
      <button type="button" class="balloon-close" :aria-label="word('balloon_close')" @click="open = false">✕</button>
    </div>
    <div ref="log" class="balloon-log">
      <p v-if="!chatState.turns.length" class="empty">{{ word("no_records") }}</p>
      <AskTurn v-for="(turn, index) in chatState.turns" :key="index" :turn="turn"
               @retry="(key) => retry(turn.sentence, key)" @confirm="confirm" />
    </div>
    <form class="balloon-form" @submit.prevent="send">
      <input v-model="sentence" type="text" class="balloon-say" autocomplete="off"
             :placeholder="word('ask_hint')" :aria-label="word('interpreter')">
      <button type="submit" class="btn" :disabled="busy">{{ word("ask") }}</button>
    </form>
  </aside>
</template>
