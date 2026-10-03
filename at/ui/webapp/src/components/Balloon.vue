<script setup lang="ts">
// Balloon — the floating door into `/chat`, from wherever the person happens
// to be.
//
// It keeps no conversation of its own and reads none: a click OPENS the chat
// view (`lib/views.ts`'s `open`, `CHAT_KEY`) the same way any other link in
// the panel does, and the box a person types into is the one `/chat` already
// draws — two boxes reading the SAME `chatState` were a second truth about
// what was said, and a bubble that was itself a small chat window was that
// second truth made of markup. The CORE's switch is what renders it at all
// (`store.interpreter`); the page's own preference is whether it flies
// (`balloon.ts`), and it hides this and nothing else (`App.vue`).

import { open, CHAT_KEY } from "../lib/views";
import { word } from "../lib/store";
</script>

<template>
  <button type="button" class="balloon-bubble" :aria-label="word('interpreter')" :title="word('interpreter')"
          @click="open(CHAT_KEY, null)">
  </button>
</template>
