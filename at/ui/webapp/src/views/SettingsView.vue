<script setup lang="ts">
// SettingsView — the Settings page: what CONFIGURES the folder, and what
// configures the page.
//
// It writes no store at all for the PAGE half — the look and the box are kept in
// localStorage, never the data. The rest is reading: the language the whole
// interface is drawn in and where it came from, and the RULER of the demand
// filter, which draws what the product declares about risk. THE ONE THING HERE
// THAT DOES WRITE THE FOLDER is People (§5, item 11): who may act, with which
// ceiling, is an adjustment of the folder, and this door is where every other
// adjustment already lives.
//
// The page is made of GROUPS THAT FOLD — the SAME fold as the panel's folder, and
// what changes is the cloth: here the PAGE's (`--group-*`), there the PANEL's.
//
// THE THEME PICKER IS BACK (2026-09-28), and the day it came back is the day a
// SECOND look existed. It left on 2026-09-27 because a list of one is a caption
// and not a choice — and that was true: with Paper the only row, the control let
// a person leave the one look the product had. What changed is not the rule but
// the count: `at2` is a design system of its own, walked through its own base
// (`base_css_path`), and whoever is comparing two looks needs the row that moves
// between them. The whole mechanism stayed ready under the removal — the
// registry, `chooseTheme`, the `.theme` rows — which is what this restores, and
// nothing more.
//
// IT SITS FIRST, because the side is the THEME's: a control that asks which of a
// theme's two faces to wear, placed above the list that picks the theme, asks
// the question backwards.

import { computed, ref, watchEffect } from "vue";
import { store, word } from "../lib/store";
import { DARK_STATES, chooseDark, chooseTheme, darkState, themeState } from "../lib/theme";
import { motionOn, setMotion } from "../lib/motion";
import { byName } from "../lib/order";
import { setTrail } from "../lib/views";
import Foldable from "../components/Foldable.vue";
import PeopleView from "../components/PeopleView.vue";
import RiskRuler from "../components/RiskRuler.vue";
import type { DarkState } from "../lib/theme";
import type { ThemeRow } from "../lib/store";

// AS ABAS, na ordem em que a tela se apresenta: o que a pasta é (o idioma), o
// que se vê, quem age nela e o que ela mede de risco.
const TABS = ["general", "appearance", "people", "risk"] as const;

const tab = ref<(typeof TABS)[number]>("general");
const motion = ref(motionOn());
const side = ref(darkState());

// The theme's description is PER SIDE: the same theme describes itself
// differently in light and dark, and what is read is the side being worn —
// `themeState.dark` is the signal that follows the swap, so changing sides
// needs no redraw.
const descOf = (row: ThemeRow): string =>
  row.desc ? (themeState.dark ? row.desc.dark : row.desc.light) || "" : "";

// THE THEMES IN ALPHABETICAL ORDER, by the name the page PRINTS. The registry
// declares them in the order they were born, which is a history and not an
// index — and what somebody does with a list of themes is look one up. It is the
// same rule the panel already follows for the tables (`order.ts`).
const themeList = computed(() => [...store.themes].sort((a, b) => byName(a.label, b.label)));

function pick(row: ThemeRow): void {
  chooseTheme(row.id);
}

const WORDS: Record<DarkState, string> = {
  system: "dark_system", theme: "dark_theme", light: "dark_light", dark: "dark_dark",
};

function toggleMotion(): void {
  motion.value = setMotion(!motion.value);
}

function pickSide(state: DarkState): void {
  side.value = state;
  chooseDark(state);
}

watchEffect(() => setTrail(word("settings")));
</script>

<template>
  <!-- AS ABAS SÃO OS GRUPOS, e cada parte é uma seção. A tela configura a pasta
       inteira — o idioma, o que se vê, quem age e o que é risco —, e agrupar
       isso em dobras fazia a pessoa ABRIR para descobrir o que havia dentro; o
       que uma aba guarda não é surpresa, é a outra metade da mesma tela. -->
  <div class="page">
    <div class="tabs" role="tablist">
      <button v-for="name in TABS" :key="name" type="button" role="tab"
              class="tab" :class="{ on: tab === name }"
              :aria-selected="tab === name" @click="tab = name">{{ word(name) }}</button>
    </div>

    <div class="panel">
      <section v-if="tab === 'general'" class="block">
        <h2>{{ word("language") }}</h2>
        <div class="block-body">
          {{ store.lang }}<template v-if="store.origin"> ({{ store.origin }})</template>
        </div>
      </section>

      <!-- OS TEMAS: the whole list, which is what a person comparing two looks
           came here for. -->
      <section v-if="tab === 'appearance'" class="block">
        <h2>{{ word("themes") }}</h2>
        <div class="block-body">
          <div class="settings">
            <button v-for="row in themeList" :key="row.id" type="button" class="theme"
                    :class="{ on: themeState.id === row.id }"
                    :aria-pressed="themeState.id === row.id"
                    @click="pick(row)">
              <b>{{ row.label }}</b>
              <span class="key">{{ row.id }}</span>
              <span v-if="descOf(row)" class="desc">{{ descOf(row) }}</span>
            </button>
          </div>
        </div>
      </section>

      <section v-if="tab === 'appearance'" class="block">
        <h2>{{ word("dark_mode") }}</h2>
        <div class="block-body">
          <div class="radios" role="radiogroup" :aria-label="word('dark_mode')">
            <label v-for="state in DARK_STATES" :key="state" class="radio-row"
                   :class="{ on: side === state }">
              <input type="radio" class="radio" name="dark-side" :value="state"
                     :checked="side === state" @change="pickSide(state)">
              <span>{{ word(WORDS[state]) }}</span>
            </label>
          </div>
        </div>
      </section>

      <section v-if="tab === 'appearance'" class="block">
        <h2>{{ word("motion") }}</h2>
        <div class="block-body">
          <button type="button" class="switch" role="switch"
                  :aria-label="word('motion')" :class="{ on: motion }"
                  :aria-checked="motion" @click="toggleMotion"></button>
        </div>
      </section>

      <!-- PESSOAS (§5, item 11): quem pode agir, com qual teto. É ajuste da
           pasta, e o componente traz as DUAS seções dele (atores e papéis). -->
      <PeopleView v-if="tab === 'people'" />

      <!-- O RISCO — a escala do filtro de demanda, desenhada a partir do que o
           produto declara. É leitura e não escolha. -->
      <section v-if="tab === 'risk'" class="block">
        <h2>{{ word("risk") }}</h2>
        <div class="block-body">
          <RiskRuler />
        </div>
      </section>
    </div>
  </div>
</template>
