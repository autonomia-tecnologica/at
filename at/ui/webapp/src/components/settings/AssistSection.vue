<script setup lang="ts">
// O ASSIST (TASK-180, fatia 3/3): o switch é o único ajuste da pasta que
// `/api/assist` escreve. `busy` evita um segundo clique enquanto o primeiro
// ainda não voltou, e o que a tela mostra depois é o que o SERVIDOR respondeu
// (`store.assist`), nunca o que foi clicado.
import { ref } from "vue";
import { store, word } from "../../lib/store";
import { post } from "../../lib/api";

const assistBusy = ref(false);

async function toggleAssist(): Promise<void> {
  if (assistBusy.value) return;
  assistBusy.value = true;
  try {
    const data = await post<{ enabled: boolean }>(
      "/api/assist", { enabled: !store.assist },
    );
    store.assist = data.enabled;
  } finally {
    assistBusy.value = false;
  }
}
</script>

<template>
  <section class="block">
    <h2>{{ word("assist") }}</h2>
    <div class="block-body">
      <p class="pop-note">{{ word("assist_hint") }}</p>
      <button type="button" class="switch" role="switch"
              :aria-label="word('assist')" :class="{ on: store.assist }"
              :aria-checked="store.assist" :disabled="assistBusy"
              @click="toggleAssist"></button>
    </div>
  </section>
</template>
