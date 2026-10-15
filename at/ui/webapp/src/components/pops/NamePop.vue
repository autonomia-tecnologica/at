<script setup lang="ts">
// NamePop — the SIMPLE INLINE FORM a create or a rename asks for (TASK-135):
// one field, the row's own name, submitted on Enter. Not the record editor
// (`RecordView.vue`) because that screen opens on a RECORD the server already
// answered with, and a project being BORN has none yet — the field this
// occasion needs is the one word every project starts from.

import { ref, onMounted } from "vue";
import { closePop } from "../../lib/pop";
import { word } from "../../lib/store";

const props = withDefaults(
  defineProps<{
    initial?: string;
    onSubmit: (value: string) => void;
  }>(),
  { initial: "" },
);

const value = ref(props.initial);
const inputEl = ref<HTMLInputElement | null>(null);

function submit(): void {
  const trimmed = value.value.trim();
  if (!trimmed) return;
  closePop();
  props.onSubmit(trimmed);
}

onMounted(() => inputEl.value?.focus());
</script>

<template>
  <form class="pop-form" @submit.prevent="submit" @click.stop>
    <input ref="inputEl" v-model="value" type="text" :aria-label="word('name')">
  </form>
</template>
