<script setup lang="ts">
// StrongboxTree — the panel's own listing of the Strongbox (TASK-156), read
// from `/api/strongbox` — the same door the section's page reads.
//
// IT NESTS BY FOLDER, like `FileTree` does for Arquivos (2026-10-05): the
// listing arrives as one path per sealed file, and the folders those paths
// name are the parent rows. The tree is assembled here, the same way the file
// tree assembles its own, and the recursive node is `StrongboxTreeNode`.
import { ref, onMounted, watch } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav } from "../lib/views";
import StrongboxTreeNode, { type StrongboxNode } from "./StrongboxTreeNode.vue";

interface Listing {
  files: { path: string }[];
}

const tree = ref<StrongboxNode>({ dirs: new Map(), files: [] });
const error = ref("");

// Every file arrives as `{path}` alone; the folders are the path's own, never a
// second listing to trust.
function buildTree(files: Listing["files"]): StrongboxNode {
  const root: StrongboxNode = { dirs: new Map(), files: [] };
  for (const file of files) {
    const parts = file.path.split("/");
    let node = root;
    for (const part of parts.slice(0, -1)) {
      if (!node.dirs.has(part)) node.dirs.set(part, { dirs: new Map(), files: [] });
      node = node.dirs.get(part)!;
    }
    node.files.push(parts[parts.length - 1]);
  }
  return root;
}

async function load(): Promise<void> {
  try {
    const listing = await api<Listing>("/api/strongbox");
    tree.value = buildTree(listing.files || []);
    error.value = "";
  } catch (err) {
    error.value = `${word("error")} ${(err as Error).message}`;
  }
}

onMounted(load);
// A file that was sealed or went away has to show up without a reload.
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="error" class="empty">{{ error }}</div>
  <div v-else-if="!tree.dirs.size && !tree.files.length" class="empty">{{ word("no_records") }}</div>
  <StrongboxTreeNode v-else :node="tree" />
</template>
