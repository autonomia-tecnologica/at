<script setup lang="ts">
// FolderView — A PASTA QUE AINDA NÃO EXISTE (§3; TASK-169, fatia 2/3).
//
// É a tela que o TERMINAL desenharia (`boot.ensure_working_folder`), um passo
// antes da entrada e da primeira subida: o modo local não tem um terminal
// onde perguntar, então a pergunta é esta tela — e é a MESMA pergunta, a
// mesma frase (`boot.first_run.notice`, do servidor, com o caminho já
// embutido), nunca uma segunda escrita aqui.
//
// CONFIRMANDO, o servidor cria a pasta e `confirmFolder` já chama `enter()`
// de novo: a navegação segue para onde já seguia (sem admin → a primeira
// subida; com um → a casca). RECUSANDO, nada foi escrito — o servidor marca
// a recusa, que é o que fecha a janela do outro lado (`local.run`,
// `_end_on_cancel`) — e esta tela troca para a frase de despedida
// (`boot.first_run.cancelled`), a mesma do terminal, sem chamar `enter()` de
// novo: não há pasta para a próxima pergunta ler.

import { ref } from "vue";
import { word } from "../lib/store";
import { confirmFolder } from "../lib/session";

const busy = ref(false);
const cancelled = ref(false);
const refusal = ref("");

async function confirm(): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  refusal.value = "";
  try {
    await confirmFolder(true);
  } catch (err) {
    refusal.value = (err as Error).message;
  } finally {
    busy.value = false;
  }
}

async function cancel(): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  try {
    await confirmFolder(false);
  } catch {
    // A janela já está a caminho de se fechar do outro lado; não há mais
    // nada que esta tela precise dizer sobre a falha de uma chamada que o
    // próprio pedido tornou irrelevante.
  }
  cancelled.value = true;
}
</script>

<template>
  <div class="veil"></div>
  <div class="dialog" v-if="!cancelled">
    <h2>{{ word("brand") }}</h2>
    <p class="folder-notice">{{ word("boot.first_run.notice") }}</p>
    <p class="refused" v-if="refusal">{{ refusal }}</p>
    <div class="dialog-actions">
      <button class="btn" type="button" :disabled="busy" @click="cancel">
        {{ word("confirm_cancel") }}
      </button>
      <button class="btn" type="button" :disabled="busy" @click="confirm">
        {{ word("confirm_ok") }}
      </button>
    </div>
  </div>
  <div class="dialog" v-else>
    <h2>{{ word("brand") }}</h2>
    <p>{{ word("boot.first_run.cancelled") }}</p>
  </div>
</template>

<style scoped>
.folder-notice {
  white-space: pre-line;
}
</style>
