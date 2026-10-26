<script setup lang="ts">
// O LADO (claro/escuro/sistema). SÓ UM TEMA COM OS DOIS LADOS TEM O QUE ESCOLHER:
// `row.sides` é o que o SERVIDOR leu do disco, nunca um palpite desta tela. Sem
// os dois lados, não há radiogroup. Hoje todos os temas têm os dois.
import { computed, ref } from "vue";
import { store, word } from "../../lib/store";
import { DARK_STATES, chooseDark, darkState, themeState } from "../../lib/theme";
import type { DarkState } from "../../lib/theme";

const side = ref(darkState());

const WORDS: Record<DarkState, string> = {
  system: "dark_system", light: "dark_light", dark: "dark_dark",
};

const sideStates = computed<readonly DarkState[]>(() => {
  const row = store.themes.find(r => r.id === themeState.id);
  return row && row.sides.length > 1 ? DARK_STATES : [];
});

function pickSide(state: DarkState): void {
  side.value = state;
  chooseDark(state);
}
</script>

<template>
  <section v-if="sideStates.length" class="block">
    <h2>{{ word("dark_mode") }}</h2>
    <div class="block-body">
      <div class="radios" role="radiogroup" :aria-label="word('dark_mode')">
        <label v-for="state in sideStates" :key="state" class="radio-row"
               :class="{ on: side === state }">
          <input type="radio" class="radio" name="dark-side" :value="state"
                 :checked="side === state" @change="pickSide(state)">
          <span>{{ word(WORDS[state]) }}</span>
        </label>
      </div>
    </div>
  </section>
</template>
