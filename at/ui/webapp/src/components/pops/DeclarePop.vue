<script setup lang="ts">
// DeclarePop — um job novo, `scheduled` desde que nasce (relógio, fatia 3/3):
// a pessoa escolhe a TABELA, o ATO que o relógio vai rodar sozinho, e o
// QUANDO — e, para um `create`/`edit`, os campos que esse ato leva, do mesmo
// jeito que `CreatePop` já desenha os de uma criação comum.
//
// `declarable` é o que o servidor já filtrou (`_declarable_payload`): só as
// tabelas e os atos que este actor já alcança DIRETO hoje — o teto de
// verdade é o do DONO, relido a cada rodada do relógio (`ask._ceiling`), e
// este painel só evita oferecer o que recusaria na hora.

import { reactive, ref, computed, watch } from "vue";
import { label, word } from "../../lib/store";
import { post } from "../../lib/api";
import { closePop } from "../../lib/pop";
import { poke } from "../../lib/views";
import type { DeclarableTable, FieldSpec } from "../../lib/record";

const props = defineProps<{
  declarable: DeclarableTable[];
}>();

const tableKey = ref("");
const actKey = ref("");
const whenLocal = ref("");
const rowId = ref("");
const refusal = ref("");

const selectedTable = computed(
  () => props.declarable.find(entry => entry.key === tableKey.value) || null,
);
const selectedAction = computed(
  () => selectedTable.value?.actions.find(entry => entry.action === actKey.value) || null,
);

// O ID NUNCA É UM CAMPO DO ATO, e o `when` é O DO JOB e não do ato agendado —
// os dois já são tratados aparte (`rowId`, `whenLocal`), do mesmo jeito que
// `CreatePop` deixa de fora o que o motor já cobre sozinho.
const fields = computed((): FieldSpec[] =>
  (selectedAction.value?.fields || []).filter(
    field => field.name !== "id" && field.type !== "instant",
  ),
);

const values = reactive<Record<string, string>>({});

watch(tableKey, () => { actKey.value = ""; });

watch(selectedAction, action => {
  for (const key of Object.keys(values)) delete values[key];
  for (const field of action?.fields ?? []) {
    if (field.name === "id" || field.type === "instant") continue;
    values[field.name] = "";
  }
});

const hasEnum = (field: FieldSpec): boolean => Object.keys(field.enum || {}).length > 0;

function inputType(field: FieldSpec): string {
  if (field.type === "day") return "date";
  if (field.type === "hashed") return "password";
  return "text";
}

async function submit(): Promise<void> {
  refusal.value = "";
  const table = selectedTable.value;
  const action = selectedAction.value;
  if (!table || !action || !whenLocal.value) return;
  const set: Record<string, string> = {};
  for (const field of fields.value) {
    const raw = values[field.name];
    if (raw) set[field.name] = raw;
  }
  const body: Record<string, unknown> = {
    action: "declare",
    table: table.key,
    act: action.action,
    when: new Date(whenLocal.value).toISOString(),
    set,
  };
  if (action.requires_id) body.id = rowId.value;
  try {
    await post("/api/job", body);
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
    <label>
      <span>{{ word("declare_table") }}</span>
      <select v-model="tableKey" required>
        <option value=""></option>
        <option v-for="entry in declarable" :key="entry.key" :value="entry.key">{{ entry.name }}</option>
      </select>
    </label>
    <label v-if="selectedTable">
      <span>{{ word("declare_act") }}</span>
      <select v-model="actKey" required>
        <option value=""></option>
        <option v-for="entry in selectedTable.actions" :key="entry.action" :value="entry.action">
          {{ entry.label }}
        </option>
      </select>
    </label>
    <label v-if="selectedAction && selectedAction.requires_id">
      <span>{{ word("declare_id") }}</span>
      <input v-model="rowId" type="text" required>
    </label>
    <label v-if="selectedAction">
      <span>{{ word("declare_when") }}</span>
      <input v-model="whenLocal" type="datetime-local" required>
    </label>
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
      <button type="submit" class="btn">{{ word("declare") }}</button>
    </div>
  </form>
</template>
