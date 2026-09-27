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
// THE THEME PICKER IS GONE (2026-09-27). AT wears one look now — Paper — and a
// list of one is not a choice, it is a caption. The eleven other themes stay
// exactly as they were (nobody touched a line of their CSS): the REGISTRY still
// declares them, and `theme.ts` still resolves whichever one the server hands
// over, which is what keeps the whole mechanism ready the day this comes back.
// What is gone is the ROW that let a person leave Paper — the side (light/dark)
// is not that choice, it is Paper's own two faces, and it stays.

import { ref, watchEffect } from "vue";
import { store, word } from "../lib/store";
import { DARK_STATES, chooseDark, darkState } from "../lib/theme";
import { motionOn, setMotion } from "../lib/motion";
import { setTitle } from "../lib/views";
import Foldable from "../components/Foldable.vue";
import PeopleView from "../components/PeopleView.vue";
import RiskRuler from "../components/RiskRuler.vue";
import type { DarkState } from "../lib/theme";

const motion = ref(motionOn());
const side = ref(darkState());

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
