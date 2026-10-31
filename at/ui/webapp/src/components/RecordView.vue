<script setup lang="ts">
// RecordView — ONE record, explained by the table's own schema.
//
// Every field the person may write is drawn by `FieldEditor` — the same editors
// the grid uses, with the record's hidden fields included: this panel is the
// door of the fields a column does not show. What decides is the DECLARED TYPE
// and the engine's `edit` action, and nothing else: no field name is known
// here.
//
// `actions` is the caller's (`RecordPop`/`KindView`): without `edit` in it,
// every field is read, exactly as it was.
//
// A reference clicked inside a value is still the caller's to open (`@ref`).

import { computed } from "vue";
import { store, label, word } from "../lib/store";
import { back, markPage } from "../lib/views";
import PageActions from "./PageActions.vue";
import FieldEditor from "./FieldEditor.vue";
import FieldValue from "./FieldValue.vue";
import type { FieldSpec, RecordRef, RecordRow } from "../lib/record";

const props = withDefaults(
  defineProps<{
    record: RecordRow;
    total?: number;
    page: string;    // what a reload returns to (`at.select`)
    entity: string;  // the table the record IS
    // HOSTED IN THE FLOATING PANEL (TASK-173), over the list it was clicked
    // from, instead of being the whole page: the step back CLOSES the panel
    // instead of walking the path.
    popup?: boolean;
    // O QUE O ENGINE DIZ QUE ESTE ATOR ALCANÇA (TASK-120): sem `edit`, tudo é
    // leitura. Quem hospeda o painel é quem sabe (`RecordPop`/`KindView`).
    actions?: string[];
  }>(),
  { total: 0, popup: false, actions: () => [] },
);

const emit = defineEmits<{ ref: [ref: RecordRef]; close: [] }>();

const spec = (name: string): FieldSpec | null =>
  store.fields.find(field => field.name === name) || null;

const canEdit = computed(() => props.actions.includes("edit"));

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
          <FieldEditor v-if="spec(field.name)" :field="field" :spec="spec(field.name)!"
                       :entity="entity" :record="record" :can-edit="canEdit" panel
                       :nested="popup" @ref="emit('ref', $event)" />
          <FieldValue v-else :field="field" @ref="emit('ref', $event)" />
        </dd>
      </template>
    </dl>
  </div>
</template>
