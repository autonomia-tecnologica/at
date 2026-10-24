<script setup lang="ts">
// OS TEMAS: the whole list, which is what a person comparing two looks came
// here for.
import { computed } from "vue";
import { store, word } from "../../lib/store";
import { chooseTheme, themeState } from "../../lib/theme";
import { byName } from "../../lib/order";
import type { ThemeRow } from "../../lib/store";

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
</script>

<template>
  <section class="block">
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
</template>
