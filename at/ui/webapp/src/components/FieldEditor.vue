<script setup lang="ts">
// FieldEditor — UM campo editado onde está (B-54).
//
// O VALOR É O CONTROLE: clicar no valor lido entra na edição daquele campo, e o
// corpo da linha/card continua sendo de quem abre o registro. O que cada tipo
// ganha é o que a declaração diz (`lib/fieldWrite`), nunca o nome do campo:
// texto curto → input; markdown → textarea que cresce; dia → `date` nativo;
// enum → `PickPop` ancorado no valor; lista → chips; referência → `RefPop`.
//
// A escrita é imediata (Enter/blur gravam; Esc cancela) e o desfazer de um
// passo vem no toast, de `lib/fieldWrite`.
//
// `panel` é o painel do registro: a prosa é desenhada como prosa, a lista
// adiciona inline e o campo ocupa a largura; na grade, a lista adiciona num
// popover ancorado na célula e a prosa começa com uma linha.

import { computed, nextTick, ref } from "vue";
import { label, word } from "../lib/store";
import { openPop } from "../lib/pop";
import { editableField, fieldKind, saveField, type FieldKind } from "../lib/fieldWrite";
import FieldValue from "./FieldValue.vue";
import ProseField from "./ProseField.vue";
import PickPop from "./pops/PickPop.vue";
import RefPop from "./pops/RefPop.vue";
import ListAddPop from "./pops/ListAddPop.vue";
import type { FieldSpec, RecordField, RecordRef, RecordRow } from "../lib/record";

const props = withDefaults(
  defineProps<{
    field: RecordField;
    spec: FieldSpec;
    entity: string;
    record: RecordRow;
    canEdit?: boolean;
    panel?: boolean;
    limit?: number;
    // O seletor do campo abre SOBRE o painel que o hospeda (`RecordView`
    // flutuante), e não no lugar dele: `pop.ts`'s `nest`.
    nested?: boolean;
  }>(),
  { canEdit: false, panel: false, limit: 0, nested: false },
);

const emit = defineEmits<{ ref: [ref: RecordRef] }>();

const editable = computed(() => props.canEdit && editableField(props.spec));
const kind = computed<FieldKind | "read">(() => (editable.value ? fieldKind(props.spec) : "read"));
// Uma lista EDITÁVEL e uma lista apenas LIDA são chips as duas: a vírgula com
// que o motor guarda uma lista nunca chega à tela. O log do motor (`managed`)
// continua sendo o texto que sempre foi.
const isPlainList = computed(() => props.spec.type === "list" && !props.spec.managed);
const items = computed<unknown[]>(() => (Array.isArray(props.field.raw) ? props.field.raw : []));

const editing = ref(false);
const draft = ref("");
const addDraft = ref("");
const inputEl = ref<HTMLInputElement | HTMLTextAreaElement | null>(null);

function setInput(el: unknown): void {
  if (el) inputEl.value = el as HTMLInputElement | HTMLTextAreaElement;
}

// O valor que o editor abre: o ISO do dia (o mostrado é localizado), o membro
// da lista fechada, ou o texto que a célula lê.
const current = computed<string>(() => {
  const raw = props.field.raw;
  if (kind.value === "day" || kind.value === "enum") {
    return raw === null || raw === undefined ? "" : String(raw);
  }
  return props.field.value || "";
});

const fieldLabel = computed(() => label(props.spec.labels) || props.spec.name);

function pickKey(suffix: string): string {
  return "field-" + suffix + ":" + props.entity + ":" + props.record.id + ":" + props.spec.name;
}

function openPick(ev: Event): void {
  openPop(pickKey("pick"), PickPop,
          { field: props.field, spec: props.spec, entity: props.entity, record: props.record },
          { anchor: ev.currentTarget as HTMLElement, nest: props.nested,
            attrs: { role: "listbox", "aria-label": fieldLabel.value } });
}

function openRef(ev: Event): void {
  openPop(pickKey("ref"), RefPop,
          { field: props.field, spec: props.spec, entity: props.entity, record: props.record },
          { anchor: ev.currentTarget as HTMLElement, nest: props.nested });
}

async function focusEditor(): Promise<void> {
  await nextTick();
  const el = inputEl.value;
  if (!el) return;
  el.focus();
  if (kind.value === "text" && el instanceof HTMLInputElement) el.select();
  if (kind.value === "markdown" && el instanceof HTMLTextAreaElement) {
    el.setSelectionRange(el.value.length, el.value.length);
    grow();
  }
}

async function startEdit(ev: Event): Promise<void> {
  if (!editable.value) return;
  if (kind.value === "enum") { openPick(ev); return; }
  if (kind.value === "ref") { openRef(ev); return; }
  if (kind.value === "list") return;
  draft.value = current.value;
  editing.value = true;
  await focusEditor();
}

// A textarea cresce com o que tem dentro; Enter quebra a linha (não grava).
function grow(): void {
  const el = inputEl.value;
  if (!(el instanceof HTMLTextAreaElement)) return;
  el.style.height = "auto";
  el.style.height = el.scrollHeight + "px";
}

async function commit(): Promise<void> {
  if (!editing.value) return;
  const value = draft.value;
  editing.value = false;
  if (value === current.value) return; // nada mudou, nada para escrever
  await saveField(props.entity, props.record, props.spec, value);
}

function cancel(): void {
  editing.value = false;
}

async function addItem(value: string): Promise<void> {
  const next = [...items.value.map(item => String(item)), value];
  await saveField(props.entity, props.record, props.spec, next);
}

async function removeItem(index: number): Promise<void> {
  const next = items.value.map(item => String(item)).filter((_, i) => i !== index);
  await saveField(props.entity, props.record, props.spec, next);
}

function openAdd(ev: Event): void {
  openPop(pickKey("add"), ListAddPop,
          { onAdd: (value: string) => { void addItem(value); } },
          { anchor: ev.currentTarget as HTMLElement, nest: props.nested });
}

async function addInline(): Promise<void> {
  const value = addDraft.value.trim();
  if (!value) return;
  addDraft.value = "";
  await addItem(value);
}
</script>

<template>
  <!-- UMA LISTA É CHIPS, nunca a vírgula do armazenamento. -->
  <div v-if="isPlainList" class="field-list">
    <span v-for="(item, i) in items" :key="i" class="field-chip">
      {{ String(item) }}
      <button v-if="editable" type="button" class="field-chip-remove"
              :title="word('remove')" :aria-label="word('remove')"
              @click.stop="removeItem(i)">×</button>
    </span>
    <button v-if="editable && !panel" type="button" class="field-chip-add"
            :title="word('add')" :aria-label="word('add')"
            @click.stop="openAdd($event)">+</button>
    <form v-if="editable && panel" class="field-add" @submit.prevent="addInline">
      <input v-model="addDraft" :placeholder="word('add')" :aria-label="word('add')">
      <button type="submit" class="btn btn-sm">{{ word("add") }}</button>
    </form>
  </div>

  <!-- LEITURA: sem permissão, ou um campo técnico. -->
  <template v-else-if="kind === 'read'">
    <ProseField v-if="panel && spec.type === 'markdown' && field.value"
                :text="field.value" field />
    <FieldValue v-else :field="field" :limit="limit" by-title @ref="emit('ref', $event)" />
  </template>

  <!-- ENUM: a lista ancorada no próprio valor, sem o valor travado. -->
  <div v-else-if="kind === 'enum'" class="field-read" role="button" tabindex="0"
       :aria-label="fieldLabel" @click.stop="startEdit($event)"
       @keydown.enter.stop.prevent="startEdit($event)"
       @keydown.space.stop.prevent="startEdit($event)">
    <span class="v"><FieldValue :field="field" :limit="limit" by-title @ref="emit('ref', $event)" /></span>
  </div>

  <!-- EDITANDO: input, textarea que cresce, ou o `date` nativo. -->
  <div v-else-if="editing" class="field-edit">
    <textarea v-if="kind === 'markdown'" :ref="setInput" v-model="draft" rows="1"
              @input="grow" @blur="commit"
              @keydown.esc.stop.prevent="cancel"></textarea>
    <input v-else-if="kind === 'day'" :ref="setInput" type="date" :value="draft"
           @input="draft = ($event.target as HTMLInputElement).value"
           @change="commit" @blur="commit"
           @keydown.enter.prevent="commit" @keydown.esc.stop.prevent="cancel">
    <input v-else :ref="setInput" type="text" v-model="draft"
           @blur="commit" @keydown.enter.prevent="commit"
           @keydown.esc.stop.prevent="cancel">
  </div>

  <!-- LENDO, MAS É O CONTROLE: clicar no valor abre o editor. -->
  <div v-else class="field-read" role="button" tabindex="0"
       :aria-label="fieldLabel" @click.stop="startEdit($event)"
       @keydown.enter.stop.prevent="startEdit($event)"
       @keydown.space.stop.prevent="startEdit($event)">
    <ProseField v-if="panel && kind === 'markdown' && field.value" :text="field.value" field />
    <!-- A REFERÊNCIA EDITÁVEL É TEXTO SIMPLES: o clique no valor abre o
         seletor, e um link dentro do valor roubaria o gesto. Não editável
         continua com o link de hoje (o ramo de leitura acima). -->
    <span v-else-if="kind === 'ref'" class="v">{{ field.value || "—" }}</span>
    <span v-else class="v"><FieldValue :field="field" :limit="limit" by-title @ref="emit('ref', $event)" /></span>
  </div>
</template>
