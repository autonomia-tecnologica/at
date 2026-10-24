<script setup lang="ts">
// O ASSIST (TASK-180, fatia 3/3): o switch e o modo, os dois ajustes da pasta
// que `/api/assist` escreve. `busy` evita um segundo clique enquanto o
// primeiro ainda não voltou, e o que a tela mostra depois é o que o SERVIDOR
// respondeu (`store.assist`/`store.assist_mode`), nunca o que foi clicado.
import { ref } from "vue";
import { store, word } from "../../lib/store";
import { post } from "../../lib/api";

const ASSIST_MODES = ["cautious", "automatic"] as const;
const assistBusy = ref(false);

async function toggleAssist(): Promise<void> {
  if (assistBusy.value) return;
  assistBusy.value = true;
  try {
    const data = await post<{ enabled: boolean; mode: string }>(
      "/api/assist", { enabled: !store.assist },
    );
    store.assist = data.enabled;
    store.assist_mode = data.mode;
  } finally {
    assistBusy.value = false;
  }
}

async function pickAssistMode(mode: (typeof ASSIST_MODES)[number]): Promise<void> {
  if (assistBusy.value || mode === store.assist_mode) return;
  assistBusy.value = true;
  try {
    const data = await post<{ enabled: boolean; mode: string }>(
      "/api/assist", { mode },
    );
    store.assist = data.enabled;
    store.assist_mode = data.mode;
  } finally {
    assistBusy.value = false;
  }
}
</script>

<template>
  <!-- O modo só aparece com o assist ligado — um modo escolhido com o assist
       desligado não teria o que fazer. -->
  <section class="block">
    <h2>{{ word("assist") }}</h2>
    <div class="block-body">
      <p class="pop-note">{{ word("assist_hint") }}</p>
      <button type="button" class="switch" role="switch"
              :aria-label="word('assist')" :class="{ on: store.assist }"
              :aria-checked="store.assist" :disabled="assistBusy"
              @click="toggleAssist"></button>
      <div v-if="store.assist" class="radios" role="radiogroup" :aria-label="word('assist_mode')">
        <label v-for="mode in ASSIST_MODES" :key="mode" class="radio-row"
               :class="{ on: store.assist_mode === mode }">
          <input type="radio" class="radio" name="assist-mode" :value="mode"
                 :checked="store.assist_mode === mode" :disabled="assistBusy"
                 @change="pickAssistMode(mode)">
          <span>{{ word(`assist_${mode}`) }}</span>
        </label>
      </div>
    </div>
  </section>
</template>
