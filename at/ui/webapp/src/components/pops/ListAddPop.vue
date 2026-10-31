<script setup lang="ts">
// ListAddPop — o campo de ADICIONAR de uma lista, ancorado na célula (B-54).
// No painel do registro ele é inline (`FieldEditor`); na grade, a célula já
// está cheia de chips e o campo abre por cima dela, no mesmo lugar.

import { ref, onMounted } from "vue";
import { word } from "../../lib/store";
import { closePop } from "../../lib/pop";

const props = defineProps<{
  onAdd: (value: string) => void;
}>();

const text = ref("");
const inputEl = ref<HTMLInputElement | null>(null);

function submit(): void {
  const value = text.value.trim();
  if (!value) return;
  closePop();
  props.onAdd(value);
}

onMounted(() => inputEl.value?.focus());
</script>

<template>
  <form class="pop-form" @submit.prevent="submit">
    <input ref="inputEl" v-model="text" :placeholder="word('add')" :aria-label="word('add')"
           @keydown.esc.prevent="closePop()">
  </form>
</template>
