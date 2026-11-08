<script setup lang="ts">
// SetupView — A PRIMEIRA SUBIDA (§3; TASK-176, fatia 3/3).
//
// It is the ENTRANCE's sibling and not a screen of the shell: a folder with no
// administrator yet has nobody to prove, so the only thing the page can ask for
// is the name and the Main Key that create the first one. It wears the same
// `.veil`/`.dialog` pieces LoginView wears — the stop-and-ask of the Design
// System — and adds nothing to the look.
//
// THE WORDS ARE THE SERVER'S, AND THEY ARE THE TERMINAL'S. `admin.name`,
// `admin.credential`, `admin.credential.again`, `admin.credential.twice` and
// `admin.error.short` come from the same catalog block `at-cli admin` reads
// (`_first_words`, in the server), so the sentence a person meets here and the
// one they would meet at a terminal are one string. The page composes no label
// of its own and fills in no number: the floor travels already written.
//
// THE TWO READS ARE ONE RULE, NOT TWO FIELDS. The Main Key is not recovered —
// there is no "forgot the password" in a folder on your own disk — so it is
// typed twice, exactly as the word reads it twice, and the server refuses the
// pair that does not match (`admin.error.mismatch`, from `/api/first`).
//
// The credential is cleared from the field once the answer comes back, like
// the entrance's: it is the one value on this screen that should not outlive
// its use.

import { ref } from "vue";
import { word } from "../lib/store";
import { firstRun } from "../lib/session";

const name = ref("");
const credential = ref("");
const again = ref("");
const refusal = ref("");
const busy = ref(false);

async function submit(): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  refusal.value = "";
  try {
    // Once this returns the administrator exists and the SHELL takes this
    // screen's place — the server opened the session in the same answer.
    await firstRun(name.value, credential.value, again.value);
    credential.value = "";
    again.value = "";
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
    <h2 class="brand"><span class="sr-only">{{ word("brand_name") }}</span></h2>
    <p>{{ word("first_hint") }}</p>
    <label>
      <span>{{ word("admin.name") }}</span>
      <input v-model="name" name="name" autocomplete="username" autofocus />
    </label>
    <label>
      <span>{{ word("admin.credential") }}</span>
      <input v-model="credential" name="credential" type="password"
             autocomplete="new-password" />
    </label>
    <label>
      <span>{{ word("admin.credential.again") }}</span>
      <input v-model="again" name="again" type="password"
             autocomplete="new-password" />
    </label>
    <!-- O preço e o porquê das duas leituras, ANTES da recusa: é a mesma
         sentença que o terminal imprime entre as duas (a fatia 2/3 a pôs lá
         pelo mesmo motivo). Aqui ela é a dica do formulário e continua sendo a
         mesma string — não há uma segunda frase que possa divergir dela. -->
    <p>
      {{ word("admin.error.short") }}<br />{{ word("admin.credential.twice") }}
    </p>
    <p class="refused" v-if="refusal">{{ refusal }}</p>
    <div class="dialog-actions">
      <button class="btn" type="submit" :disabled="busy">
        {{ word("create") }}
      </button>
    </div>
  </form>
</template>
