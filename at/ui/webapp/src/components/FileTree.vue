<script setup lang="ts">
// FileTree — the listing of the prose folder: ONE tree.
//
// Whoever decides what it may list is the SERVER (a hidden segment is not
// offered), and it is the server that says which BUCKET each file is — the page
// keeps no extension table of its own.

import { ref, watch, onMounted } from "vue";
import { api, post } from "../lib/api";
import { word } from "../lib/store";
import { nav, poke } from "../lib/views";
import { openContextMenu, vContextMenu, type MenuItem } from "../lib/menu";
import { openPop } from "../lib/pop";
import { toast } from "../lib/toast";
import NamePop from "./pops/NamePop.vue";
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

// THE TREE'S OWN RIGHT CLICK, when there is nothing in it (TASK-137, fatia
// 6/7): the same pair `FileTreeNode`'s folder menu already offers
// (`new_file`/`new_folder`), landing at the ROOT — there is no node here to
// hold the pattern, so it is repeated at this one, narrower door.
function openNamePop(ev: MouseEvent, onSubmit: (value: string) => void): void {
  openPop("file-name", NamePop, { initial: "", onSubmit },
          { point: { x: ev.clientX, y: ev.clientY } });
}

async function createEntry(isDir: boolean, name: string): Promise<void> {
  try {
    await post("/api/file/create", { path: rootPath.value ? rootPath.value + "/" + name : name, dir: isDir });
    poke();
  } catch (err) {
    toast((err as Error).message);
  }
}

function openEmptyMenu(ev: MouseEvent): void {
  const items: MenuItem[] = [
    { label: word("new_file"), action: () => openNamePop(ev, value => void createEntry(false, value)) },
    { label: word("new_folder"), action: () => openNamePop(ev, value => void createEntry(true, value)) },
  ];
  openContextMenu(ev, items);
}
</script>

<template>
  <div v-if="error" class="empty">{{ error }}</div>
  <div v-else-if="!tree.dirs.size && !tree.files.length" class="empty"
       v-context-menu="openEmptyMenu">{{ word("no_records") }}</div>
  <FileTreeNode v-else :node="tree" :prefix="rootPath" />
</template>
