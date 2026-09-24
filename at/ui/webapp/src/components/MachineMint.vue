<script setup lang="ts">
// MachineMint — the surface that MINTS a machine's credential (item 11).
//
// It is the one write of the page that does not fill a row in: a token is not
// something a person invents, so AT draws it (`POST /api/agent`), the row
// keeps the derivation and what comes back is the token itself — shown ONCE,
// because nothing reads it back afterwards.
//
// It is a COMPONENT and not a piece of a screen because two screens offer it:
// the actors' own page and the panel's People entry, which holds the actors and
// the roles together. The rule of one home applies to a form like it applies to
// a sentence.

import { ref } from "vue";
import { post } from "../lib/api";
import { label as worded, word } from "../lib/store";
import { leave, markPage, poke, showError } from "../lib/views";
import type { FieldSpec, RecordRow } from "../lib/record";

const props = defineProps<{
  roles: RecordRow[];
  fields: FieldSpec[];
}>();

const name = ref("");
const role = ref<number | null>(null);
const token = ref("");

const fieldWord = (field: string) =>
  worded(props.fields.find(item => item.name === field)?.labels);

async function mint(): Promise<void> {
  if (!name.value.trim() || role.value === null) return;
  try {
    const answer = await post<{ record: RecordRow; token: string }>("/api/agent", {
      action: "mint",
      name: name.value.trim(),
      role: role.value,
    });
    token.value = answer.token;
    name.value = "";
    poke();
    // The machine that was just born opens, so the person lands where the token
    // is, and the step back returns to the list they were reading.
    if (answer.record) {
      leave();
      markPage("actor", answer.record.id);
    }
  } catch (err) {
    showError(err as Error);
  }
}
</script>

<template>
  <div class="form-block">
    <h2>{{ word("new_machine") }}</h2>
    <div class="form">
      <label>
        <span>{{ fieldWord("name") }}</span>
        <input v-model="name" type="text" />
      </label>
      <label>
        <span>{{ fieldWord("role") }}</span>
        <select v-model="role">
          <option :value="null" disabled>—</option>
          <option v-for="one in roles" :key="one.id" :value="one.id">{{ one.title }}</option>
        </select>
      </label>
      <div>
        <button type="button" class="btn" :disabled="!name.trim() || role === null"
                @click="mint">
          {{ word("mint") }}
        </button>
      </div>
    </div>
    <div v-if="token" class="form-block">
      <h3>{{ word("token_once") }}</h3>
      <pre class="text">{{ token }}</pre>
    </div>
  </div>
</template>
