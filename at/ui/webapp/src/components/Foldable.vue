<script setup lang="ts">
// Foldable — the page's SINGLE disclosure: the panel's folders, dressed by
// context. It is the same gesture, so it is the same control.
//
// What it preserves, because it is behaviour and not style:
//
// · a fold is BORN COLLAPSED — what opens one is the person, and only that
//   choice (a saved preference) opens it on the next load;
// · the box takes `.foldable` and the content lives in ONE layer (`.fold`),
//   because the collapse is the height of one grid track (`1fr` ↔ `0fr`,
//   base.css) and a track that animates is a track that changes;
// · the head takes `.fold-head`, which is where `base.css`'s caret hangs.

import { ref, onMounted } from "vue";
import { foldPrefs, savePrefs, PREFS_KEY } from "../lib/prefs";

const props = withDefaults(
  defineProps<{
    id: string;
    label?: string;
    // The class the BOX carries besides `.foldable`. It is through it that
    // `base.css` gives the indent (`nav .kinds`, `nav .branch`).
    boxClass?: string | null;
    // The HEAD's cloth: the panel's folder (`folder`) or a page's group.
    headClass?: string;
    // WHAT THE FOLD HOLDS, when whoever opened it already knows — the panel's
    // own count, drawn at the head's right edge (`nav .n`, base2.css). It is
    // `null` where nothing has counted: a number invented here would be the
    // page guessing at its own data.
    count?: number | null;
  }>(),
  { label: "", boxClass: null, headClass: "folder", count: null },
);

const prefs = foldPrefs();
const isOpen = ref(prefs[props.id] === true);
const loadedOnce = ref(isOpen.value);

function toggle(): void {
  isOpen.value = !isOpen.value;
  prefs[props.id] = isOpen.value;
  savePrefs(PREFS_KEY, prefs);
  if (isOpen.value) loadedOnce.value = true;
}

onMounted(() => {
  if (isOpen.value) loadedOnce.value = true;
});
</script>

<template>
  <!-- `data-branch` is the ID, ON THE HEAD. The id is a prop and never reaches
       the DOM by itself, and the head is where a theme hangs the mark of what a
       fold holds (`nav .folder[data-branch="tasks"]`, base2.css) — which is a
       drawing and not behaviour, so it belongs to whoever dresses the control
       and not to whoever knows what it opens. -->
  <button :data-branch="id" :class="[headClass, 'fold-head', { closed: !isOpen }]"
          type="button" @click="toggle">
    <span class="caret">▾</span>
    <span>{{ label }}</span>
    <span v-if="count !== null" class="n">{{ count }}</span>
  </button>
  <div class="foldable" :class="[boxClass, { closed: !isOpen }]">
    <div class="fold">
      <slot v-if="loadedOnce" />
    </div>
  </div>
</template>
