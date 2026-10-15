<script setup lang="ts">
// CreatePop — a new row of a table, born from the header's own menu
// (TASK-121): one field per column the table declares, filled together and
// sent as ONE `action: "create"` — the same door the `cli` and the
// interpreter already walk.
//
// `id` is the STORE's to allocate (never typed), and an `instant` field is
// the ENGINE's own stamp (`_touch`) — offering either here would be a door
// painted on a wall. Every other field is offered, and what is LEGAL to fill
// is the SERVER's to say: a refusal (`error.required`, `error.not_in_enum`,
// …) comes back worded already, and is shown here verbatim.

import { reactive, ref, computed } from "vue";
import { label, word } from "../../lib/store";
import { post } from "../../lib/api";
import { closePop } from "../../lib/pop";
import { poke } from "../../lib/views";
import type { FieldSpec } from "../../lib/record";

const props = defineProps<{
  entity: string;
  schema: FieldSpec[];
}>();

const fields = computed(() =>
  props.schema.filter(field => field.name !== "id" && field.type !== "instant"),
);

const values = reactive<Record<string, string>>(
  Object.fromEntries(fields.value.map(field => [field.name, ""])),
);

const refusal = ref("");

const hasEnum = (field: FieldSpec): boolean => Object.keys(field.enum || {}).length > 0;

function inputType(field: FieldSpec): string {
  if (field.type === "day") return "date";
  if (field.type === "hashed") return "password";
  return "text";
}

async function submit(): Promise<void> {
  refusal.value = "";
  const set: Record<string, string> = {};
  for (const field of fields.value) {
    const raw = values[field.name];
    if (raw) set[field.name] = raw;
  }
  try {
    await post("/api/table/" + encodeURIComponent(props.entity), { action: "create", set });
    closePop();
    poke();
  } catch (err) {
    refusal.value = (err as Error).message;
  }
}
</script>

<template>
  <form class="form" @submit.prevent="submit">
    <p v-if="refusal" class="refused">{{ refusal }}</p>
    <label v-for="field in fields" :key="field.name">
      <span>{{ label(field.labels) || field.name }}</span>
      <select v-if="hasEnum(field)" v-model="values[field.name]" :required="field.required">
        <option value=""></option>
        <option v-for="(opt, value) in field.enum" :key="value" :value="value">{{ label(opt) || value }}</option>
      </select>
      <textarea v-else-if="field.type === 'markdown'" v-model="values[field.name]"
                :required="field.required"></textarea>
      <input v-else :type="inputType(field)" v-model="values[field.name]" :required="field.required">
    </label>
    <div class="dialog-actions">
      <button type="submit" class="btn">{{ word("create") }}</button>
    </div>
  </form>
</template>
