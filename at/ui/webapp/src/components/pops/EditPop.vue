<script setup lang="ts">
// EditPop — a row of a table, edited where it lies.
//
// The TWIN of `CreatePop.vue`: the same fields, the same door, one act
// different. A create POSTS `action: "create"`; an edit POSTS
// `action: "edit"` with the row's own id, and the form STARTS FROM what the
// row already holds — the value GUARDADO (`raw`), and not the value drawn.
//
// WHY IT EXISTS: the generic record view writes the fields the declaration
// marks `editable`, and `editable` is the SHORT form of a choice — the closed
// list of an enumeration. A field that is not a choice (a prose, a list of
// tags) had NO door to be written from the page: the create form made it,
// the spreadsheet's cell edits the choice-shaped ones only, and the record
// view only reads it. This form is that door — and it is GENERIC: no field
// name is known here, and the engine reads each value as the type its
// declaration says (a list is split by the comma it writes).

import { reactive, ref, computed } from "vue";
import { label, word } from "../../lib/store";
import { post } from "../../lib/api";
import { closePop } from "../../lib/pop";
import { poke } from "../../lib/views";
import type { FieldSpec, RecordRow } from "../../lib/record";

const props = defineProps<{
  entity: string;
  id: number;
  schema: FieldSpec[];
  record: RecordRow;
}>();

// The same rule `CreatePop` follows: the id is the STORE's to allocate and an
// `instant` is the ENGINE's own stamp — neither is typed here.
const fields = computed(() =>
  props.schema.filter(field => field.name !== "id" && field.type !== "instant"),
);

// O QUE A LINHA JÁ TEM: o valor guardado (`raw`), e não o desenhado. Uma
// lista guardada é uma lista, e o formulário a escreve como o motor a lê —
// separada pela vírgula.
function stored(name: string): string {
  const field = props.record.fields.find(f => f.name === name);
  const raw = field ? field.raw : null;
  if (Array.isArray(raw)) return raw.map(item => String(item)).join(", ");
  if (raw === null || raw === undefined) return "";
  return String(raw);
}

// O QUE TINHA QUANDO O FORMULÁRIO ABRIU — a comparação da escrita é com isto,
// e não com a linha de agora: um `poke` que chega enquanto o formulário está
// aberto não pode virar uma escrita que a pessoa não pediu.
const initial = Object.fromEntries(fields.value.map(field => [field.name, stored(field.name)]));

const values = reactive<Record<string, string>>({ ...initial });

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
    // Só o que MUDOU viaja: um campo que a pessoa não tocou não é reescrito,
    // e um campo VAZIO que ela limpou é — limpá-lo é um pedido, e o motor é
    // quem diz se pode.
    if (raw !== initial[field.name]) set[field.name] = raw;
  }
  try {
    await post("/api/table/" + encodeURIComponent(props.entity), {
      action: "edit",
      id: props.id,
      set,
    });
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
      <button type="submit" class="btn">{{ word("save") }}</button>
    </div>
  </form>
</template>
