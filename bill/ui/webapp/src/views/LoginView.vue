<script setup lang="ts">
// LoginView — the ENTRANCE (§3, Forms local; §5: "the theme holds for the whole
// WebApp, the login screen included").
//
// It is a `.dialog` on a `.veil`, which is the Design System's own "stop and
// ask" piece — the ground, the line, the radius, the shadow and the motion are
// the overlay's tokens, so the entrance wears whatever theme is on and this file
// adds nothing to the look. The heading is the BRAND word, from the catalog like
// every other word on screen.
//
// THE FORM IS NOT A FORM OF THE BROWSER'S. `@submit.prevent` is load-bearing: a
// native submit is a navigation, and the credential would travel in the query
// string — the address bar, the history and every log in between. The credential
// goes in a JSON body and nowhere else.
//
// The refusal is the SERVER's sentence, in the active language. It is the same
// sentence whether the name is unknown or the credential is wrong, so the answer
// says neither — and the page adds no word of its own to it.

import { ref } from "vue";
import { word } from "../lib/store";
import { signIn } from "../lib/session";

const name = ref("");
const credential = ref("");
const refusal = ref("");
const busy = ref(false);

async function submit(): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  refusal.value = "";
  try {
    // Once this returns, the session exists and the SHELL takes this screen's
    // place — there is nothing to tell anybody, and nothing here survives it.
    await signIn(name.value, credential.value);
    // The credential is not kept in the field: the page has no use for it once
    // the session exists, and it is the one value on this screen that should not
    // outlive its use.
    credential.value = "";
  } catch (err) {
    refusal.value = (err as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="veil"></div>
  <form class="dialog" @submit.prevent="submit">
    <h2>{{ word("brand") }}</h2>
    <p>{{ word("session_hint") }}</p>
    <label>
      <span>{{ word("session_name") }}</span>
      <input v-model="name" name="name" autocomplete="username" autofocus />
    </label>
    <label>
      <span>{{ word("session_credential") }}</span>
      <input v-model="credential" name="credential" type="password"
             autocomplete="current-password" />
    </label>
    <p class="refused" v-if="refusal">{{ refusal }}</p>
    <div class="dialog-actions">
      <button class="btn" type="submit" :disabled="busy">
        {{ word("session_enter") }}
      </button>
    </div>
  </form>
</template>
