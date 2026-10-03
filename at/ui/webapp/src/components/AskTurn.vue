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

import { computed, ref } from "vue";
import { store, word } from "../lib/store";
import type { Turn } from "../lib/ask";

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

// A BIG TABLE STARTS FOLDED — the answer is one message among many, not a
// screen of its own, and a listing long enough to push every other turn off
// screen on every reload would be the chat undoing itself one answer at a
// time. Short ones (the common case) never fold at all — the class only
// lands past `FOLD_OVER` rows, and a click past that point is what grows it.
const expanded = ref(false);
const FOLD_OVER = 6;
</script>

<template>
  <div class="turn" :data-kind="turn.kind">
    <p class="said">
      {{ turn.sentence }}
      <time v-if="when" class="stamp">{{ when }}</time>
    </p>
    <div class="answer-msg">
      <div v-if="turn.table" class="answer-table-wrap"
           :class="{ folded: turn.table.rows.length > FOLD_OVER && !expanded }"
           @click="turn.table.rows.length > FOLD_OVER && !expanded && (expanded = true)">
        <table class="answer-table">
          <thead>
            <tr><th v-for="(cell, i) in turn.table.header" :key="i">{{ cell }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="(row, r) in turn.table.rows" :key="r">
              <td v-for="(cell, c) in row" :key="c">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <ul v-else-if="turn.bullets" class="answer-bullets-wrap"
          :class="{ folded: turn.bullets.length > FOLD_OVER && !expanded }"
          @click="turn.bullets.length > FOLD_OVER && !expanded && (expanded = true)">
        <li v-for="(line, i) in turn.bullets" :key="i">{{ line }}</li>
      </ul>
      <time v-if="(turn.table || turn.bullets) && when" class="stamp">{{ when }}</time>
      <p v-if="!turn.table && !turn.bullets" class="answer">
        {{ turn.text }}
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
