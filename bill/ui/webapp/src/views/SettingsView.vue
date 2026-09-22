<script setup lang="ts">
// SettingsView — the Settings page: what CONFIGURES the page, and the two things
// changed here — the THEME and the MOTION EFFECTS.
//
// It writes no store at all: what is configured is the page (the look, in
// localStorage), never the data. The rest is reading: the language the whole
// interface is drawn in, and where it came from.
//
// The page is made of GROUPS THAT FOLD — the SAME fold as the panel's folder, and
// what changes is the cloth: here the PAGE's (`--group-*`), there the PANEL's.

import { ref, computed, watchEffect } from "vue";
import { store, word } from "../lib/store";
import { DARK_STATES, chooseDark, chooseTheme, darkState, themeState } from "../lib/theme";
import { motionOn, setMotion } from "../lib/motion";
import { setTitle } from "../lib/views";
import { byName } from "../lib/order";
import Foldable from "../components/Foldable.vue";
import type { DarkState } from "../lib/theme";
import type { ThemeRow } from "../lib/store";

const motion = ref(motionOn());
const side = ref(darkState());

// The theme's description is PER SIDE: the same theme describes itself differently
// in light and dark, and what is read is the side being worn — `themeState.dark`
// is the signal that follows the swap, so changing sides needs no redraw.
const descOf = (row: ThemeRow): string =>
  row.desc ? (themeState.dark ? row.desc.dark : row.desc.light) || "" : "";

// THE THEMES IN ALPHABETICAL ORDER, by the name the page PRINTS. The registry
// declares them in the order they were born, which is a history and not an index —
// and what somebody does with a list of themes is look one up. It is the same
// rule the panel already follows for the tables (`order.ts`).
const themeList = computed(() => [...store.themes].sort((a, b) => byName(a.label, b.label)));

const WORDS: Record<DarkState, string> = {
  system: "dark_system", theme: "dark_theme", light: "dark_light", dark: "dark_dark",
};

function pick(row: ThemeRow): void {
  chooseTheme(row.id);
}

function toggleMotion(): void {
  motion.value = setMotion(!motion.value);
}

function pickSide(state: DarkState): void {
  side.value = state;
  chooseDark(state);
}

watchEffect(() => setTitle(word("settings")));
</script>

<template>
  <div class="groups">
    <div class="group">
      <Foldable id="settings:general" :label="word('general')"
                head-class="group-head" box-class="group-body">
        <dl>
          <dt>{{ word("language") }}</dt>
          <dd>{{ store.lang }}<template v-if="store.origin"> ({{ store.origin }})</template></dd>
        </dl>
      </Foldable>
    </div>

    <div class="group">
      <Foldable id="settings:appearance" :label="word('appearance')"
                head-class="group-head" box-class="group-body">
        <dl>
          <dt>{{ word("dark_mode") }}</dt>
          <dd>
            <div class="radios" role="radiogroup" :aria-label="word('dark_mode')">
              <label v-for="state in DARK_STATES" :key="state" class="radio-row"
                     :class="{ on: side === state }">
                <input type="radio" class="radio" name="dark-side" :value="state"
                       :checked="side === state" @change="pickSide(state)">
                <span>{{ word(WORDS[state]) }}</span>
              </label>
            </div>
          </dd>

          <dt>{{ word("motion") }}</dt>
          <dd>
            <button type="button" class="switch" role="switch"
                    :aria-label="word('motion')" :class="{ on: motion }"
                    :aria-checked="motion" @click="toggleMotion"></button>
          </dd>

          <!-- THE THEMES ARE APPEARANCE, and not a section of their own: a theme
               IS the page's look, and the list lives beside whoever governs it.
               What it has of its own is the CEILING — there are eleven themes and
               there may be more (the vocabulary is data), so the list scrolls
               inside itself instead of pushing the page down without end
               (`base.css`, `.settings`). -->
          <dt>{{ word("themes") }}</dt>
          <dd>
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
          </dd>
        </dl>
      </Foldable>
    </div>
  </div>
</template>
