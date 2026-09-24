<script setup lang="ts">
// RiskRuler — the demand filter's scale, drawn over the numbers that GOVERN.
//
// From `0` to `1`, the line of the threshold, and a mark for every catalogue
// entry. The engine's rule (§4) is what the drawing says: a demand BELOW the line
// runs, and one AT or above it waits — the boundary is the waiting side.
//
// The ruler invents no number. It draws the marks the server hands it, and the
// server hands it what each entry is measured at: the catalogue's own risk,
// adjusted by what the folder wrote in `settings.json` (§5's per-action
// adjustment). It reads the SAME number the demand filter compares against, so
// the mark and the engine cannot disagree about what runs and what waits.
//
// THE MARK IS DRAWN TO THE RIGHT OF ITS OWN VALUE, never centred on it: a mark
// exactly ON the line then falls on the waiting side, which is the side the engine
// will put it on. Centring it would draw the one demand that matters on the wrong
// side of the line it is read against.

import { computed } from "vue";
import { store, word } from "../lib/store";

// Where a value sits on the drawing. The scale is the engine's; a value off it is
// brought INTO it, because a mark outside the ruler is a mark nobody can read.
const at = (value: number): string =>
  `${Math.min(Math.max(Number(value) || 0, 0), 1) * 100}%`;

const threshold = computed(() => store.risk.threshold);
</script>

<template>
  <div class="ruler" :data-threshold="at(threshold)">
    <div class="ruler-track">
      <!-- The two regions are the RULE: below the line runs, at or above it
           waits. They are drawn from the threshold, so the boundary between
           them IS the line. -->
      <span class="ruler-part runs" :style="{ width: at(threshold) }"></span>
      <span class="ruler-part waits"></span>
      <span class="ruler-line" :style="{ left: at(threshold) }"></span>
      <span v-for="mark in store.risk.marks" :key="mark.key" class="ruler-mark"
            :style="{ left: at(mark.risk) }" :title="`${mark.key} ${mark.risk}`"></span>
    </div>
    <!-- EACH WORD SITS IN THE REGION IT NAMES, and it is the SAME measurement the
         drawing uses — so the label moves with the line, and neither can say
         something the other does not. -->
    <div class="ruler-legend">
      <span class="runs" :style="{ width: at(threshold) }">{{ word("risk_runs") }}</span>
      <span class="waits">{{ word("risk_waits") }}</span>
    </div>
    <p class="ruler-note">{{ word("risk_threshold") }}: {{ threshold }}</p>
    <p v-if="!store.risk.marks.length" class="ruler-none">{{ word("risk_none") }}</p>
  </div>
</template>
