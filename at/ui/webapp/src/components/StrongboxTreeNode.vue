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
// A SEALED FILE IS NOW A DOOR (TASK-155): the row carries a NAME — no bucket,
// because what selar hides is exactly a file's shape — and OPENING it, after a
// confirmation, draws the clear in the viewer over the page (`StrongboxViewer`,
// `lib/strongbox`). The row keeps the tree's own box so the column reads as one.
//
// THERE IS ONE CLOTH NOW (2026-10-05): the section's own page is gone, so the
// only tree is the panel's — `base.css` names it (`nav .entry.leaf`). The
// reader opens over ANY screen, which is why the section needed no screen of
// its own.
import { computed } from "vue";
import Foldable from "./Foldable.vue";
import { word } from "../lib/store";
import { toast } from "../lib/toast";
import { ask } from "../lib/confirm";
import { openSealed } from "../lib/strongbox";

export interface StrongboxNode {
  dirs: Map<string, StrongboxNode>;
  files: string[];
}

const props = withDefaults(
  defineProps<{
    node: StrongboxNode;
    prefix?: string;
  }>(),
  { prefix: "" },
);

const byPath = (a: string, b: string): number =>
  String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });

const dirs = computed(() => [...props.node.dirs.entries()].sort((a, b) => byPath(a[0], b[0])));
const files = computed(() => [...props.node.files].sort(byPath));

const join = (name: string): string => (props.prefix ? props.prefix + "/" + name : name);

// ONE CLICK OPENS THE FILE, after a CONFIRMATION: the clear leaves the Vault
// for the screen, and that is a thing the person says yes to. The path is the
// full one the listing hands back (`strongbox.listed`), what the server's door
// checks membership against — not a name this tree made up.
async function openLeaf(full: string): Promise<void> {
  const name = full.split("/").pop()!.replace(/\.enc$/, "");
  if (!(await ask(word("open_confirm").replace("{name}", name)))) return;
  try {
    await openSealed(full);
  } catch (err) {
    toast((err as Error).message);
  }
}
</script>

<template>
  <template v-for="[name, child] in dirs" :key="name">
    <!-- A FOLDER INSIDE THE TREE IS A `Foldable`, born collapsed and remembering
         what was opened — the same disclosure the file tree uses, one level
         down (`head-class="node"`). -->
    <Foldable :id="`strongbox:${join(name)}`" :label="name"
              box-class="branch" head-class="node">
      <StrongboxTreeNode :node="child" :prefix="join(name)" />
    </Foldable>
  </template>
  <!-- THE NAMES THAT ENDED HERE, each the tail of its own path — and each one a
       DOOR (TASK-155): the row opens the file in the viewer, over the page. -->
  <button v-for="name in files" :key="name" type="button"
          class="file entry leaf" @click="openLeaf(join(name))">
    <span>{{ name }}</span>
  </button>
</template>
