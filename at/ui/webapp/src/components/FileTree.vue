<script setup lang="ts">
// FileTree — the listing of the prose folder: ONE tree.
//
// Whoever decides what it may list is the SERVER (a hidden segment is not
// offered), and it is the server that says which BUCKET each file is — the page
// keeps no extension table of its own.

import { ref, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav } from "../lib/views";
import FileTreeNode from "./FileTreeNode.vue";

export interface FileNode {
  dirs: Map<string, FileNode>;
  files: { name: string; bucket: string }[];
}

interface Listing {
  root: string;
  files: { path: string; bucket: string }[];
}

const rootPath = ref("");
const tree = ref<FileNode>({ dirs: new Map(), files: [] });
const error = ref("");

// Every file arrives as `{path, bucket}`; the tree is assembled here, and the
// `root` the server declares is the prefix of every file request — the page
// composes no path of its own.
function buildTree(files: Listing["files"]): FileNode {
  const root: FileNode = { dirs: new Map(), files: [] };
  for (const file of files) {
    const parts = file.path.split("/");
    let node = root;
    for (const part of parts.slice(0, -1)) {
      if (!node.dirs.has(part)) node.dirs.set(part, { dirs: new Map(), files: [] });
      node = node.dirs.get(part)!;
    }
    node.files.push({ name: parts[parts.length - 1], bucket: file.bucket });
  }
  return root;
}

async function load(): Promise<void> {
  try {
    const listing = await api<Listing>("/api/tree");
    rootPath.value = listing.root || "";
    tree.value = buildTree(listing.files || []);
    error.value = "";
  } catch (err) {
    error.value = `${word("error")} ${(err as Error).message}`;
  }
}

onMounted(load);
// A file that was born or went away has to show up without a reload.
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="error" class="empty">{{ error }}</div>
  <div v-else-if="!tree.dirs.size && !tree.files.length" class="empty">{{ word("no_records") }}</div>
  <FileTreeNode v-else :node="tree" :prefix="rootPath" />
</template>
