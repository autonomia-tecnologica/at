<script setup lang="ts">
// ActionsView — a árvore de Actions (TASK-189, fatia 4/4): o catálogo inteiro,
// agrupado por OBJETO, cada objeto com os verbos que o alcançam, cada verbo com
// os modificadores (flag/argumento) que o ato aceita, e a marca de quais portas
// (terminal, web, assist) o alcançam.
//
// É SÓ LEITURA. Nenhum controle aqui executa um ato — a árvore existe para
// que uma pessoa veja o catálogo inteiro de uma vez, não para mover nada; quem
// move um papel é RoleView, e é lá que o checkbox mora.
//
// O catálogo é lido do MESMO `/api/catalogue` que RoleView já lê, e o
// agrupamento reaproveita `groupCatalogue` — os dois agrupam pelo OBJETO (o
// cabeçalho é "Tarefas", e os verbos vêm abaixo); o que muda é só o que cada
// linha mostra. Nenhum dos dois é uma segunda cópia do catálogo.
//
// A linha mostra o VERBO (`entry.action_label`) e, abaixo, a DESCRIÇÃO do que
// ele faz (`entry.description`) — a frase que veio do catálogo no lugar do
// nome técnico (`note:create`). Descrição vazia é uma permissão cujo texto
// ainda falta: a linha esconde a nota em vez de mostrar um buraco.

import { onMounted, ref } from "vue";
import { fetchCatalogue, groupCatalogue } from "../lib/catalogue";
import { word } from "../lib/store";
import { showError } from "../lib/views";
import type { CatalogueEntry } from "../lib/catalogue";

const catalogue = ref<CatalogueEntry[]>([]);
const groups = ref<ReturnType<typeof groupCatalogue>>([]);

async function load(): Promise<void> {
  try {
    catalogue.value = await fetchCatalogue();
    groups.value = groupCatalogue(
      catalogue.value,
      entry => entry.object,
      entry => entry.object_label,
    );
  } catch (err) {
    catalogue.value = [];
    groups.value = [];
    showError(err as Error);
  }
}

// A marca de cada porta carrega sua própria palavra (`reach_cli`, `reach_web`,
// `reach_llm`); uma marca que o servidor mande e esta tela não conheça ainda
// (outra interface, um dia) cai de volta no próprio nome, nunca num texto
// quebrado.
function reachWord(mark: string): string {
  const key = `reach_${mark}`;
  const found = word(key);
  return found === key ? mark : found;
}

onMounted(load);
</script>

<template>
  <div class="actions-tree">
    <p class="pop-note">{{ word("actions_hint") }}</p>
    <div v-for="group in groups" :key="group.key" class="form-block">
      <h3>{{ group.label }}</h3>
      <div class="row" v-for="entry in group.entries" :key="entry.key">
        <div>
          <b>{{ entry.action_label }}</b>
          <div v-if="entry.description" class="pop-note">{{ entry.description }}</div>
          <ul v-if="entry.modifiers.length">
            <li v-for="modifier in entry.modifiers" :key="modifier.name">
              <span class="chip" :data-value="modifier.kind">
                {{ word(`modifier_${modifier.kind}`) }}
              </span>
              <code>{{ modifier.name }}</code> — {{ modifier.label }}
            </li>
          </ul>
        </div>
        <span class="n">
          <span v-for="mark in entry.reach" :key="mark" class="chip" :data-value="mark">
            {{ reachWord(mark) }}
          </span>
          <span v-if="!entry.reach.length" class="chip"
                :data-value="entry.orphan ? 'critical' : undefined">
            {{ entry.orphan ? word("reach_orphan") : word("reach_none_known") }}
          </span>
        </span>
      </div>
    </div>
  </div>
</template>
