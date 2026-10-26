<script setup lang="ts">
// SpellPop — the suggestions under a word the checker underlined. Choosing one
// swaps THAT word, and only that: nothing changes without this click.
import { word } from "../../lib/store";
import { closePop } from "../../lib/pop";

const props = defineProps<{
  suggestions: string[];
  apply: (value: string) => void;
}>();

function choose(value: string): void {
  closePop();
  props.apply(value);
}
</script>

<template>
  <button v-for="value in suggestions" :key="value" type="button" class="opt" role="option"
          @click="choose(value)">{{ value }}</button>
  <p v-if="!suggestions.length" class="pop-note">{{ word("spell_none") }}</p>
</template>
