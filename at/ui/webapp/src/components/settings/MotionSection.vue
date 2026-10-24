<script setup lang="ts">
import { ref } from "vue";
import { word } from "../../lib/store";
import { motionOn, setMotion } from "../../lib/motion";

const motion = ref(motionOn());

function toggleMotion(): void {
  motion.value = setMotion(!motion.value);
}
</script>

<template>
  <section class="block">
    <h2>{{ word("motion") }}</h2>
    <div class="block-body">
      <button type="button" class="switch" role="switch"
              :aria-label="word('motion')" :class="{ on: motion }"
              :aria-checked="motion" @click="toggleMotion"></button>
    </div>
  </section>
</template>
