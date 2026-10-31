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
// label on the screen. AND WHAT THE SERVER MARKS `locked` IS NOT OFFERED (B-54):
// a `cancelled` is reached by the act of closing, never by choosing it here.
//
// The write — and its one-step undo — is `lib/fieldWrite`'s, the same door every
// other in-place editor walks.

import { ref, onMounted, computed } from "vue";
import { label } from "../../lib/store";
import { closePop } from "../../lib/pop";
import { saveField } from "../../lib/fieldWrite";
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

// THE VALUES THE ENGINE LOCKED ARE NOT CHOICES. The server says which they are
// (`locked`); this list omits them and invents nothing.
const choices = computed(() =>
  Object.keys(props.spec.enum || {}).filter(value => !(props.spec.locked || []).includes(value)),
);

async function choose(value: string): Promise<void> {
  closePop(); // before the await: the panel is gone either way
  await saveField(props.entity, props.record, props.spec, value);
}

onMounted(() => {
  if (marked.value) marked.value.focus();
});
</script>

<template>
  <button v-for="value in choices" :key="value" type="button"
          class="opt" role="option" :aria-selected="value === field.raw"
          :class="{ on: value === field.raw }"
          :ref="value === field.raw ? setMarked : undefined"
          @click="choose(value)">{{ label(spec.enum[value]) || value }}</button>
</template>
