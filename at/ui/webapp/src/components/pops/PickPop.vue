<script setup lang="ts">
// PickPop — the list that hangs under the control of a field the table offers to
// WRITE. It is the SHORT form of a choice: the record shows the value it holds,
// and the list of everything the field accepts sits under it.
//
// It is a WRITE OF THE FIELD and of nothing else: what travels is the field and
// the value, and the SERVER runs it through the same engine the CLI uses — the
// page owns no rule of the write.
//
// What is written is the MACHINE WORD the server handed over (`raw`), never the
// label on the screen.

import { ref, onMounted } from "vue";
import { label } from "../../lib/store";
import { post } from "../../lib/api";
import { closePop } from "../../lib/pop";
import { showError, poke } from "../../lib/views";
import { OFFLINE_TABLE, writeTask } from "../../lib/offline";
import type { FieldSpec, RecordField, RecordRow } from "../../lib/record";

const props = defineProps<{
  field: RecordField;
  spec: FieldSpec;
  entity: string;
  record: RecordRow;
}>();

const marked = ref<HTMLButtonElement | null>(null);
const setMarked = (el: unknown): void => {
  if (el) marked.value = el as HTMLButtonElement;
};

// The write. On success the page re-reads its page — the record comes back
// carrying the value it now holds — and on failure the page says it where it
// says every error.
//
// TASKS TAKE THE FILA'S DOOR (TASK-162): a request that never got an ANSWER
// falls to the offline queue instead of failing, and the row is patched IN
// PLACE — `field` is the very object `props.record.fields` holds, so the
// mutation is what a redraw would have shown anyway, without one. Every other
// table keeps walking straight through `post`, exactly as before.
async function choose(value: string): Promise<void> {
  closePop(); // before the await: the panel is gone either way
  try {
    if (props.entity === OFFLINE_TABLE) {
      const { queued } = await writeTask("edit", { [props.field.name]: value }, props.record.id);
      if (queued) {
        props.field.raw = value;
        props.field.value = label(props.spec.enum[value]) || value;
        return;
      }
      poke();
      return;
    }
    await post("/api/table/" + encodeURIComponent(props.entity), {
      action: "edit",
      id: props.record.id,
      set: { [props.field.name]: value },
    });
    poke();
  } catch (err) {
    showError(err as Error);
  }
}

onMounted(() => {
  if (marked.value) marked.value.focus();
});
</script>

<template>
  <button v-for="value in Object.keys(spec.enum || {})" :key="value" type="button"
          class="opt" role="option" :aria-selected="value === field.raw"
          :class="{ on: value === field.raw }"
          :ref="value === field.raw ? setMarked : undefined"
          @click="choose(value)">{{ label(spec.enum[value]) || value }}</button>
</template>
