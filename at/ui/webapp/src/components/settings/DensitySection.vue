<script setup lang="ts">
import { ref } from "vue";
import { word } from "../../lib/store";
import { DENSITIES, density, setDensity } from "../../lib/density";
import type { Density } from "../../lib/density";

const dense = ref(density());

function pickDensity(state: Density): void {
  dense.value = setDensity(state);
}
</script>

<template>
  <section class="block">
    <h2>{{ word("density") }}</h2>
    <div class="block-body">
      <div class="radios" role="radiogroup" :aria-label="word('density')">
        <label v-for="state in DENSITIES" :key="state" class="radio-row"
               :class="{ on: dense === state }">
          <input type="radio" class="radio" name="density" :value="state"
                 :checked="dense === state" @change="pickDensity(state)">
          <span>{{ word(`density_${state}`) }}</span>
        </label>
      </div>
    </div>
  </section>
</template>
