<script setup lang="ts">
// TablesTaskView — a porta da seção Tabelas para a tabela `task` (TASK-175).
//
// A árvore de projetos abre a MESMA tabela em `/task`, com o popup da
// TASK-173 — ali a seção é Tarefas, e o modo não muda. Aqui o endereço é
// outro (`/tables/task`), e é só por ele que `KindView` sabe que este é o
// modo planilha: não há outro sinal que sobreviva a um reload.

import { store } from "../lib/store";
import KindView from "./KindView.vue";
</script>

<template>
  <KindView :view="store.types.task" section="tables" />
</template>
