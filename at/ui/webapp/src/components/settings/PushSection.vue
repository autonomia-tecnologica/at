<script setup lang="ts">
// NOTIFICAÇÕES (Web Push): o botão PEDE a permissão do navegador e inscreve o
// PWA — sem ntfy, sem app à parte. Um navegador que não sabe fazer push não
// mostra o bloco. O estado do push é o que a tela mostra: o navegador pergunta
// uma vez, e depois disso é a permissão que responde (`push.state`).
import { ref } from "vue";
import { word } from "../../lib/store";
import { enable as enablePush, state as pushNow } from "../../lib/push";

const pushState = ref(pushNow());

async function askPush(): Promise<void> {
  const ok = await enablePush();
  pushState.value = ok ? "on" : pushNow();
}
</script>

<template>
  <section v-if="pushState !== 'unsupported'" class="block">
    <h2>{{ word("notifications") }}</h2>
    <div class="block-body">
      <p class="pop-note">{{ word("notifications_hint") }}</p>
      <button type="button" class="btn"
              :disabled="pushState === 'on' || pushState === 'denied'"
              @click="askPush">
        {{ pushState === "on" ? word("notifications_on") : word("notifications_off") }}
      </button>
    </div>
  </section>
</template>
