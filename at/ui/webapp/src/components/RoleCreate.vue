<script setup lang="ts">
// RoleCreate — a role being BORN, which is the one other way a role moves.
//
// It creates through the table route every surface already walks
// (`POST /api/table/role`, `action: create`): the row is born carrying the
// declared default — no permission at all — and what the person picks is picked
// on the role's own screen, where the closed list is drawn.
//
// It is a COMPONENT for the same reason `MachineMint` is: the roles' page and
// the panel's People entry both offer it, and a form has one home.

import { ref } from "vue";
import { post } from "../lib/api";
import { label as worded, word } from "../lib/store";
import { leave, markPage, poke, showError } from "../lib/views";
import type { FieldSpec, RecordRow } from "../lib/record";

const props = defineProps<{ fields: FieldSpec[] }>();

const fresh = ref("");

const fieldWord = (field: string) =>
  worded(props.fields.find(item => item.name === field)?.labels);

async function create(): Promise<void> {
  if (!fresh.value.trim()) return;
  try {
    const answer = await post<{ record: RecordRow }>("/api/table/role", {
      action: "create",
      set: { name: fresh.value.trim() },
    });
    fresh.value = "";
    poke();
    if (answer.record) {
      leave();
      markPage("role", answer.record.id);
    }
  } catch (err) {
    showError(err as Error);
  }
}
</script>

<template>
  <div class="form-block">
    <h2>{{ word("new_role") }}</h2>
    <div class="form">
      <label>
        <span>{{ fieldWord("name") }}</span>
        <input v-model="fresh" type="text" @keyup.enter="create" />
      </label>
      <div>
        <button type="button" class="btn" :disabled="!fresh.trim()" @click="create">
          {{ word("create") }}
        </button>
      </div>
    </div>
  </div>
</template>
