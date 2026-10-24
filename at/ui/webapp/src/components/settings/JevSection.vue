<script setup lang="ts">
// A CREDENCIAL DO JEV: só a chave da API (TypeSafe). A Chave Principal NÃO é
// digitada aqui — ela é a da SUBIDA, guardada em memória pelo host, e é ela que
// sela a chave do Jev. A linha que nasce (`secret` de escopo `jev`) é o que faz
// o chat parar de dizer "Jev não configurado".
import { ref } from "vue";
import { store, word } from "../../lib/store";
import { post } from "../../lib/api";

const jevKey = ref("");
const jevBusy = ref(false);
const jevError = ref("");

async function saveJev(): Promise<void> {
  if (jevBusy.value || !jevKey.value) return;
  jevBusy.value = true;
  jevError.value = "";
  try {
    await post("/api/jev", { key: jevKey.value });
    store.jev_ready = true;
    jevKey.value = "";
  } catch (err) {
    jevError.value = (err as Error).message;
  } finally {
    jevBusy.value = false;
  }
}
</script>

<template>
  <section class="block">
    <h2>{{ word("jev") }}</h2>
    <div class="block-body">
      <p class="pop-note">{{ word("jev_hint") }}</p>
      <div class="jev-form">
        <input v-model="jevKey" type="password" autocomplete="off"
               class="jev-input" :placeholder="word('jev_key')"
               :aria-label="word('jev_key')">
        <button type="button" class="btn"
                :disabled="jevBusy || !jevKey" @click="saveJev">
          {{ word("jev_save") }}
        </button>
      </div>
      <p v-if="jevError" class="pop-note">{{ jevError }}</p>
      <p v-else-if="store.jev_ready" class="pop-note">{{ word("jev_saved") }}</p>
    </div>
  </section>
</template>
