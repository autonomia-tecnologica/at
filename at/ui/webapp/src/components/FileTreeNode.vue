<script setup lang="ts">
// FileTreeNode — ONE level of the file tree. Recursive: every folder is a
// `Foldable` (born collapsed, opens on click, remembers what was opened) and its
// box carries the indent (`.branch`), never a second layer — a second wrapper
// would indent the level twice.

import { computed } from "vue";
import Foldable from "./Foldable.vue";
import { isCurrent, open } from "../lib/views";
import type { FileNode } from "./FileTree.vue";

const FILE_VIEW = "file:";

const props = withDefaults(
  defineProps<{
    node: FileNode;
    prefix?: string;
  }>(),
  { prefix: "" },
);

const byPath = (a: string, b: string): number =>
  String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });

const dirs = computed(() => [...props.node.dirs.entries()].sort((a, b) => byPath(a[0], b[0])));
const files = computed(() => [...props.node.files].sort((a, b) => byPath(a.name, b.name)));

const join = (name: string): string => (props.prefix ? props.prefix + "/" + name : name);

function openFile(full: string): void {
  open(FILE_VIEW + full, null);
}
</script>

<template>
  <template v-for="[name, child] in dirs" :key="name">
    <!-- `head-class="node"`, AND NOT THE PANEL'S `folder`: a directory inside the
         tree carries the same fold, but it is not the same LEVEL of item — the
         panel's four top-level rows are its chapters, and a folder is a name
         inside one of them. A level that wears the cloth of the level above it
         is a tree with no hierarchy left to read (`base.css`, `nav .node`). -->
    <Foldable :id="'tree:' + join(name)" :label="name" box-class="branch"
              head-class="node">
      <FileTreeNode :node="child" :prefix="join(name)" />
    </Foldable>
  </template>
  <!-- `entry` is what makes the row a file LINE rather than a project row, and the
       BUCKET goes on the row as data — the icon is drawn from it by the theme
       (`--icon-*`, base.css), so the page decides neither the glyph nor the rule. -->
  <button v-for="f in files" :key="f.name" type="button" class="file entry"
          :data-bucket="f.bucket" :data-view="FILE_VIEW + join(f.name)"
          :class="{ on: isCurrent(FILE_VIEW + join(f.name)) }"
          @click="openFile(join(f.name))">
    <span class="icon" aria-hidden="true"></span>
    <span>{{ f.name }}</span>
  </button>
</template>
