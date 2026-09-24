<script setup lang="ts">
// RecordView — ONE record, explained by the table's own schema.
//
// What the table declares WRITABLE is drawn by whoever knows how to write it
// (the pick); every other field is the text it always was. And the field the
// table declares `markdown` is the prose it says it is — what decides is the
// DECLARED TYPE and nothing else: no field name is known here.

import { store, label, word } from "../lib/store";
import { back, markPage } from "../lib/views";
import { openPop, closePop, isPopOpen } from "../lib/pop";
import FieldValue from "./FieldValue.vue";
import ProseField from "./ProseField.vue";
import PickPop from "./pops/PickPop.vue";
import type { FieldSpec, RecordField, RecordRef, RecordRow } from "../lib/record";

const props = defineProps<{
  record: RecordRow;
  total?: number;
  page: string;    // what a reload returns to (`at.select`)
  entity: string;  // the table the record IS
}>();

const emit = defineEmits<{ ref: [ref: RecordRef] }>();

const spec = (name: string): FieldSpec | null =>
  store.fields.find(field => field.name === name) || null;

const isProse = (field: RecordField): boolean =>
  field.type === "markdown" && !!field.value;

const pickKey = (name: string): string => "pick:" + name;

function openPick(ev: Event, field: RecordField): void {
  if (isPopOpen(pickKey(field.name))) {
    closePop();
    return;
  }
  openPop(pickKey(field.name), PickPop,
          { field, spec: spec(field.name), entity: props.entity, record: props.record },
          { anchor: ev.currentTarget as HTMLElement,
            attrs: { role: "listbox", "aria-label": label(spec(field.name)?.labels) || field.name } });
}

// The step back: the page behind it, or — with no path — the list the record
// belongs to.
function goBack(): void {
  back(() => markPage(props.page, null));
}
</script>

<template>
  <div class="record-page">
    <div class="page-actions">
      <button type="button" class="btn" @click="goBack"
              >← {{ record.shown_id }} · {{ total }} {{ word("records") }}</button>
    </div>
    <dl class="record-body">
      <template v-for="field in record.fields" :key="field.name">
        <dt>{{ label(spec(field.name)?.labels) || field.name }}</dt>
        <dd>
          <button v-if="spec(field.name)?.editable" type="button" class="pick"
                  :class="{ on: isPopOpen(pickKey(field.name)) }"
                  :title="label(spec(field.name)?.labels) || field.name"
                  :aria-label="label(spec(field.name)?.labels) || field.name"
                  aria-haspopup="listbox"
                  :aria-expanded="isPopOpen(pickKey(field.name))"
                  @click.stop="openPick($event, field)">{{ field.value || "" }}</button>
          <ProseField v-else-if="isProse(field)" :text="field.value" field />
          <FieldValue v-else :field="field" @ref="emit('ref', $event)" />
        </dd>
      </template>
    </dl>
  </div>
</template>
