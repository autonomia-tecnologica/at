<script setup lang="ts">
// StrongboxTreeNode — ONE level of the Strongbox's tree, the sibling of
// `FileTreeNode.vue` (2026-10-05).
//
// IT NESTS BY FOLDER, LIKE THE FILE TREE DOES. This listing used to be FLAT, on
// the argument that a sealed file was a drop and not a place — but a drop still
// lands somewhere, and the path a file was sealed under is the only thing the
// row can say about it. The folder that path names is the same hierarchy
// `Arquivos` reads; this draws it the same way.
//
// A SEALED FILE IS A LEAF AND NOT A DOOR: it carries a NAME and nothing else —
// no bucket (what selar hides is exactly a file's shape), no icon and no click,
// because there is still no reader on this page (TASK-155). The row keeps the
// tree's own box so the column reads as one, and opens nothing.
//
// THE CLOTH IS THE ONLY THING THAT VARIES (`variant`): the panel's tree and the
// section's page are the same nesting and different dressing — `base.css` names
// the two (`nav .entry.leaf`, `.tree-leaf`, `.tree-dir`).
import { computed } from "vue";
import Foldable from "./Foldable.vue";

export interface StrongboxNode {
  dirs: Map<string, StrongboxNode>;
  files: string[];
}

const props = withDefaults(
  defineProps<{
    node: StrongboxNode;
    prefix?: string;
    variant?: "nav" | "page";
  }>(),
  { prefix: "", variant: "nav" },
);

const byPath = (a: string, b: string): number =>
  String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });

const dirs = computed(() => [...props.node.dirs.entries()].sort((a, b) => byPath(a[0], b[0])));
const files = computed(() => [...props.node.files].sort(byPath));

const join = (name: string): string => (props.prefix ? props.prefix + "/" + name : name);
</script>

<template>
  <template v-for="[name, child] in dirs" :key="name">
    <!-- A FOLDER INSIDE THE TREE IS A `Foldable`, born collapsed and remembering
         what was opened — the same disclosure the file tree uses, one level
         down (`head-class="node"` in the panel, `tree-dir` on the page). -->
    <Foldable :id="`strongbox:${variant}:${join(name)}`" :label="name"
              :box-class="variant === 'nav' ? 'branch' : 'tree-branch'"
              :head-class="variant === 'nav' ? 'node' : 'tree-dir'">
      <StrongboxTreeNode :node="child" :prefix="join(name)" :variant="variant" />
    </Foldable>
  </template>
  <!-- THE NAMES THAT ENDED HERE, each the tail of its own path. -->
  <div v-for="name in files" :key="name"
       :class="variant === 'nav' ? 'file entry leaf' : 'tree-leaf'">
    <span>{{ name }}</span>
  </div>
</template>
