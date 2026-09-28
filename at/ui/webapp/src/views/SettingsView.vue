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

    <!-- PEOPLE (§5, item 11): who may act, with which ceiling. It is an
         adjustment of the folder, not a table to browse, which is why it sits
         here and not in the Tabelas fold any more — `PeopleView` is a fragment
         (two `.group`s of its own), dropped straight into this page's `.groups`
         box instead of nesting one flex column inside another. -->
    <PeopleView />

    <div class="group">
      <Foldable id="settings:appearance" :label="word('appearance')"
                head-class="group-head" box-class="group-body">
        <dl>
          <!-- THE THEMES ARE APPEARANCE, and not a section of their own: a theme
               IS the page's look, and the list lives beside whoever governs it.
               What it has of its own is the CEILING — there are twelve themes
               and there may be more (the vocabulary is data), so the list
               scrolls inside itself instead of pushing the page down without
               end (`base.css`, `.settings`). -->
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
        </dl>
      </Foldable>
    </div>

    <!-- THE RULER — the demand filter's scale, drawn from what the product
         declares (§4). It is a read and not a choice: nothing here is configured,
         and the page invents no risk. -->
    <div class="group">
      <Foldable id="settings:risk" :label="word('risk')"
                head-class="group-head" box-class="group-body">
        <RiskRuler />
      </Foldable>
    </div>
  </div>
</template>
