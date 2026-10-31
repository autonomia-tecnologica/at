<script setup lang="ts">
// RefPop — o seletor de uma REFERÊNCIA, ancorado no valor que a célula mostra
// (B-54). O `PickPop` de enum não serve: as escolhas não são uma lista fechada,
// são as linhas da tabela ALVO — e o que viaja de volta é o NÚMERO da linha,
// nunca o título que se leu.
//
// A tabela alvo é a declarada (`spec.refs[0].key`); a busca é pelo título que o
// servidor já resolveu para cada linha. Nada de campo por nome, nada de regra
// de escrita no cliente: quem grava é `lib/fieldWrite`.

import { ref, computed, onMounted } from "vue";
import { api } from "../../lib/api";
import { word } from "../../lib/store";
import { closeAllPops, closePop } from "../../lib/pop";
import { openRef } from "../../lib/views";
import { saveField } from "../../lib/fieldWrite";
import type { FieldSpec, RecordField, RecordRow } from "../../lib/record";

const props = defineProps<{
  field: RecordField;
  spec: FieldSpec;
  entity: string;
  record: RecordRow;
}>();

interface RefRow { id: number; title: string }

const target = computed(() => (props.spec.refs || [])[0]?.key || "");
const rows = ref<RefRow[]>([]);
const query = ref("");
const refusal = ref("");
const loading = ref(true);
const inputEl = ref<HTMLInputElement | null>(null);

async function load(): Promise<void> {
  try {
    const payload = await api<{ records: RefRow[] }>(
      "/api/table/" + encodeURIComponent(target.value) + "?all",
    );
    rows.value = payload.records;
  } catch (err) {
    refusal.value = (err as Error).message;
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await load();
  inputEl.value?.focus();
});

// A busca é pelo TÍTULO da linha — o que a pessoa lê na célula.
const found = computed(() => {
  const needle = query.value.trim().toLowerCase();
  if (!needle) return rows.value;
  return rows.value.filter(row => row.title.toLowerCase().includes(needle));
});

// `null` limpa a referência (uma linha que não aponta para nada é um valor, e
// não lixo) — mas só quando a declaração não a exige; obrigatória, o seletor só
// troca o alvo. Qualquer outra escolha grava o id numérico.
async function choose(id: number | null): Promise<void> {
  closePop();
  await saveField(props.entity, props.record, props.spec, id);
}

// O "↗" da linha ATUAL não escolhe: fecha o seletor e abre o registro que a
// referência nomeia, pela mesma porta de leitura que a tabela já usa.
function open(id: number): void {
  // A PILHA INTEIRA: o seletor E o painel do registro que o hospedou saem
  // antes de a página do registro apontado entrar.
  closeAllPops();
  openRef({ key: target.value, id });
}
</script>

<template>
  <div class="pop-form ref-pop">
    <input ref="inputEl" v-model="query" type="search"
           :placeholder="word('search')" :aria-label="word('search')">
    <p v-if="refusal" class="refused">{{ refusal }}</p>
    <button v-if="!spec.required" type="button" class="opt" @click="choose(null)">— {{ word("clear") }}</button>
    <div v-for="row in found" :key="row.id" class="ref-row">
      <button type="button" class="opt" :class="{ on: row.id === field.raw }"
              role="option" :aria-selected="row.id === field.raw"
              @click="choose(row.id)">{{ row.title }}</button>
      <!-- SÓ A LINHA ATUAL: abrir o registro não é escolher, e os dois são
           botões IRMÃOS — um botão dentro do outro roubaria o gesto. -->
      <button v-if="row.id === field.raw" type="button" class="ref-open"
              :title="word('open_record')" :aria-label="word('open_record')"
              @click.stop="open(row.id)">↗</button>
    </div>
    <p v-if="!loading && !found.length" class="pop-note">{{ word("search_none_title") }}</p>
  </div>
</template>
