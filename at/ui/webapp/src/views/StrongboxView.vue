<script setup lang="ts">
// StrongboxView — THE STRONGBOX SECTION'S OWN SCREEN, and the section is the
// fold (TASK-156, fatia 3/3).
//
// It is the sibling of `FilesView.vue`, and reads the SAME shape of listing
// (`/api/strongbox`) the sidebar's `StrongboxTree` already draws from. Where
// `FilesView` counts by BUCKET, this page cannot: what selar hides is exactly a
// file's shape — there is no bucket to group by, and no extension to read one
// out of. What is left to show is the OTHER thing a listing has: the folders
// the paths name, as a TREE (2026-10-05) — the same nesting the panel's tree
// draws, dressed for the page.
//
// **There is no bucket here, and still no reader.** A row is a NAME: it does
// not open (TASK-155).

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import { word } from "../lib/store";
import { nav, setTrail, showError } from "../lib/views";
import StrongboxTreeNode, { type StrongboxNode } from "../components/StrongboxTreeNode.vue";

interface Listing {
  files: { path: string }[];
}

const loaded = ref(false);
const tree = ref<StrongboxNode>({ dirs: new Map(), files: [] });
const total = ref(0);

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
    total.value = (listing.files || []).length;
    loaded.value = true;
    setTrail(word("strongbox"));
  } catch (err) {
    loaded.value = false;
    showError(err as Error);
  }
}

onMounted(load);
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="loaded" class="section">
    <!-- THE ONE NUMBER THIS PAGE HAS: how many `.enc` the Strongbox already
         holds. -->
    <div class="stats">
      <div class="stat">
        <b>{{ total }}</b>
        <span>{{ word("strongbox") }}</span>
      </div>
    </div>

    <!-- WHERE THE SEALED FILES SIT, as the folders their paths name. The rows
         are READ and not opened: a sealed file has no reader on this page yet
         (TASK-155). -->
    <section class="cards">
      <h2>{{ word("strongbox") }}</h2>
      <div v-if="total" class="tree">
        <StrongboxTreeNode :node="tree" variant="page" />
      </div>
      <p v-else class="empty">{{ word("no_records") }}</p>
    </section>
  </div>
</template>
