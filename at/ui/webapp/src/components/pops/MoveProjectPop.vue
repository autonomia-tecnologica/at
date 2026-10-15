<script setup lang="ts">
// MoveProjectPop — "mover" IS editing the field that links a project to its
// parent (TASK-135): a flat list to pick the new one from, the same `.opt`
// shape `FilterPop` already draws a list in. The caller is the one who left
// the project itself, and everything under it, out of `candidates` — picking
// one's own subtree as its new parent is a cycle, and this pop does not know
// the tree well enough to find that out on its own.

import { word } from "../../lib/store";
import { closePop } from "../../lib/pop";

export interface MoveCandidate {
  id: number;
  title: string;
}

const props = defineProps<{
  candidates: MoveCandidate[];
  current: number | null;
  onPick: (id: number | null) => void;
}>();

function pick(id: number | null): void {
  closePop(); // before the write: the panel is gone either way (`PickPop`'s own rule)
  props.onPick(id);
}
</script>

<template>
  <button type="button" class="opt" :class="{ on: current === null }"
          @click.stop="pick(null)">{{ word("no_parent") }}</button>
  <button v-for="c in candidates" :key="c.id" type="button" class="opt"
          :class="{ on: current === c.id }" @click.stop="pick(c.id)">{{ c.title }}</button>
</template>
