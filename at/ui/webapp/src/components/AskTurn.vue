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
//
// **THE ANSWER IS MARKDOWN NOW (2026-10-05).** A `list` used to be drawn by a
// component of its own — a table element, a bullet list — dressed by the
// product's table block. That block is the PRODUCT'S, and it belongs to the
// Tables screen alone (`base.css`, `.grid`); the chat is not it. So the answer
// goes through the SAME renderer a `.md` file goes through (`lib/markdown`):
// a `list` that filled a `table` becomes a markdown table (`tableMarkdown`), a
// `list` that filled `bullets` already arrives as markdown (the engine writes
// `- line`), and every other answer is the sentence the engine wrote. The
// declared type is still read — to know HOW to build the markdown —, and the
// drawing is the chat's own block (`.md-table`).

import { computed, onMounted, ref, watch } from "vue";
import { store, word } from "../lib/store";
import type { Turn } from "../lib/ask";
import { ensureRenderer, proseHtml, rendererReady, tableMarkdown } from "../lib/markdown";

const props = defineProps<{ turn: Turn }>();

// The clock a person reads is THEIRS — the browser's own locale and zone — the
// same rule §4 gives every `instant` field: the engine keeps no second wording
// of it, and a turn with no stamp yet (mid-flight) shows nothing rather than a
// guess.
const when = computed(() => {
  if (!props.turn.at) return "";
  const date = new Date(props.turn.at);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString(store.lang.replace("_", "-"));
});
// TASK-180, fatia 3/3: the one retry a refusal can still offer — typing the
// Main Key the first attempt did not carry. It is the PARENT that re-asks
// (`Balloon`/`ChatView` both already hold the road to `ask`); this component
// only reads the typing and hands the key up.
//
// A CAUTIOUS question (`turn.confirm`) is answered the same way any other
// message is — typed in the box, "sim" or "não", read by `lib/chat.ts`'s own
// `send` before it ever reaches the engine. This is a chat, not a form: there
// is no button here for it, and none to click.
const emit = defineEmits<{ retry: [mainKey: string] }>();
const mainKey = ref("");

function retry(): void {
  const key = mainKey.value;
  if (!key) return;
  mainKey.value = "";
  emit("retry", key);
}

// THE MARKDOWN SOURCE of the answer: a table's own rows in the notation, or the
// text the engine already wrote (a plain answer, or a `list`'s `- line`
// bullets). The chat never draws the source — it renders it, below.
const body = computed(() => props.turn.table
  ? tableMarkdown(props.turn.table.header, props.turn.table.rows)
  : props.turn.text);

// The rendered HTML, or NULL while the hosted renderer has not landed — the
// turn then draws the source it has, the honest answer with no renderer
// (`ProseField.vue`'s own rule), and REDRAWS when `rendererReady` flips.
const html = ref<string | null>(null);

async function render(): Promise<void> {
  html.value = null;
  const out = await proseHtml(body.value, "md-table");
  if (out !== null) html.value = out;
}

onMounted(() => {
  void ensureRenderer();
  void render();
});
watch(body, render);
watch(rendererReady, render);
</script>

<template>
  <div class="turn" :data-kind="turn.kind">
    <p class="said">
      {{ turn.sentence }}
      <time v-if="when" class="stamp">{{ when }}</time>
    </p>
    <div class="answer-msg">
      <template v-if="html !== null">
        <div class="md-body" v-html="html"></div>
        <time v-if="when" class="stamp">{{ when }}</time>
      </template>
      <p v-else class="answer">
        {{ body }}
        <time v-if="when" class="stamp">{{ when }}</time>
      </p>
    </div>
    <form v-if="turn.assist" class="assist-retry" @submit.prevent="retry">
      <input v-model="mainKey" type="password" autocomplete="off"
             :placeholder="word('assist_key')" :aria-label="word('assist_key')">
      <button type="submit" class="btn">{{ word("assist_retry") }}</button>
    </form>
  </div>
</template>
