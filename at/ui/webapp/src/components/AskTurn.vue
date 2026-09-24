<script setup lang="ts">
// AskTurn — what a sentence turned into, drawn the ONE way both shapes draw it.
//
// The chat keeps a list of these and the balloon keeps the last one, but what is
// READ is the same in both, and that is the rule of the box: the two ask the same
// thing and show the same thing. The sentence, the proposal it became — in the
// engine's words —, and then what the engine answered. A question and a refusal
// are answers too, and they are shown where the answer goes: the page writes none
// of these sentences, it puts where they are read the ones it was handed.

import { word } from "../lib/store";
import type { Turn } from "../lib/ask";

defineProps<{ turn: Turn }>();
</script>

<template>
  <div class="turn" :data-kind="turn.kind">
    <p class="said">{{ turn.sentence }}</p>
    <p v-if="turn.proposal" class="proposal">
      <span class="tag">{{ word("proposal") }}</span>{{ turn.proposal }}
    </p>
    <p class="answer">{{ turn.text }}</p>
  </div>
</template>
