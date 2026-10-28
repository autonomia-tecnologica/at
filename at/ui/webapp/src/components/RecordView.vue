<script setup lang="ts">
// RecordView — ONE record, explained by the table's own schema.
//
// What the table declares WRITABLE is drawn by whoever knows how to write it
// (the pick); every other field is the text it always was. And the field the
// table declares `markdown` is the prose it says it is — what decides is the
// DECLARED TYPE and nothing else: no field name is known here.

import { store, label, word } from "../lib/store";
import { back, markPage } from "../lib/views";
import PageActions from "./PageActions.vue";
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
  // HOSTED IN THE FLOATING PANEL (TASK-173), over the list it was clicked
  // from, instead of being the whole page: the step back CLOSES the panel
  // instead of walking the path, and the field's own pick opens OVER it
  // (`nest`, `lib/pop.ts`) instead of taking its place.
  popup?: boolean;
}>();

const emit = defineEmits<{ ref: [ref: RecordRef]; close: [] }>();

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
            attrs: { role: "listbox", "aria-label": label(spec(field.name)?.labels) || field.name },
            nest: props.popup });
}

// The step back: the page behind it, or — with no path — the list the record
// belongs to. HOSTED IN THE PANEL, there is no path to walk: the gesture
// CLOSES it, back to exactly the list it floats over.
function goBack(): void {
  if (props.popup) { emit("close"); return; }
  back(() => markPage(props.page, null));
}
</script>

<template>
  <div class="record-page">
    <PageActions :inline="popup">
      <!-- `btn-quiet`: the step back is a way OUT of the page and not its
           action, and a system that fills every button by default (base.css)
           has to be told which one is not the action. HOSTED IN THE PANEL
           (TASK-173) the gesture is the same door, worded as a close. -->
      <button type="button" class="btn btn-quiet" @click="goBack"
              :aria-label="popup ? word('close') : undefined">
        <template v-if="popup">× {{ record.shown_id }}</template>
        <template v-else>← {{ record.shown_id }} · {{ total }} {{ word("records") }}</template>
      </button>
    </PageActions>
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
