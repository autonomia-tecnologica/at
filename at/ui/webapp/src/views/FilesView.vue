<script setup lang="ts">
// FilesView — THE FILES SECTION'S OWN SCREEN, and the section is the fold.
//
// It is the sibling of `TasksView.vue` and follows the same discipline: it
// INVENTS NOTHING. Every number is a count of what the server already lists for
// the section (`/api/tree`, the same listing the panel's tree is built from),
// cut a different way — by the BUCKET each file falls in, and by the top folder
// it sits under. A file the page was not handed is a file the page does not
// count.
//
// THE BUCKETS ARE THE PANEL'S OWN, and this page does not choose them: they are
// the five the file rows wear a mark for (`prose.bucket`, in `at/prose/listing.py`
// — a fifth, `image`, TASK-167), in the order the panel draws them. The words
// come from the catalog, like every other word on screen.

import { ref, computed, watch, onMounted } from "vue";
import { api } from "../lib/api";
import StatStrip from "../components/StatStrip.vue";
import EmptyState from "../components/EmptyState.vue";
import { word } from "../lib/store";
import { nav, open, setTrail, showError, filesFolder } from "../lib/views";

interface Listing {
  root: string;
  files: { path: string; bucket: string }[];
}

const listing = ref<Listing | null>(null);

// The five the engine knows, in the panel's order — never a list written here.
const BUCKETS = ["text", "code", "data", "image", "other"] as const;

// WHERE THE PERSON IS: the folder's path as segments, `[]` being the root. It is
// state of the SCREEN and not of the server — the listing is flat (`path` +
// `bucket`), so "inside a folder" is only a prefix of those paths, cut here.
// Restored from the module state: a file opened from here, or a crumb of its
// header, brings the person back to the same folder.
const here = ref<string[]>([...filesFolder.segments]);
const prefix = computed(() => (here.value.length ? here.value.join("/") + "/" : ""));

// EVERYTHING UNDER THE FOLDER, recursively — the counters and the bar count this,
// and not the whole listing, so the top always speaks about the folder on screen.
const inside = computed(() =>
  (listing.value?.files || []).filter(file => file.path.startsWith(prefix.value)));

const total = computed(() => inside.value.length);

function countOf(bucket: string): number {
  return inside.value.filter(file => file.bucket === bucket).length;
}

const stripItems = computed(() => BUCKETS.map(bucket => ({
  key: bucket, tone: bucket, value: countOf(bucket), share: countOf(bucket),
  label: word("bucket_" + bucket),
  title: word("bucket_" + bucket) + ": " + countOf(bucket),
})));

// THE FOLDER'S ENTRIES, cut from the flat listing: the next segment of each path
// is either a file (it ends there) or a folder (it goes on — and every file
// below it counts toward the folder's number, as a person looking for it would
// expect). Folders first, then files, each by name — the order a file browser
// has always had. A folder with nothing in it is not listed by the server, so
// it cannot show here either.
const entries = computed(() => {
  const dirs = new Map<string, number>();
  const files: { name: string; path: string; bucket: string }[] = [];
  for (const file of inside.value) {
    const rest = file.path.slice(prefix.value.length);
    const slash = rest.indexOf("/");
    if (slash < 0) files.push({ name: rest, path: file.path, bucket: file.bucket });
    else {
      const name = rest.slice(0, slash);
      dirs.set(name, (dirs.get(name) || 0) + 1);
    }
  }
  const by = (a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: "base" });
  return {
    dirs: [...dirs.entries()].map(([name, count]) => ({ name, count })).sort((a, b) => by(a.name, b.name)),
    files: files.sort((a, b) => by(a.name, b.name)),
  };
});

function enter(name: string): void {
  here.value = [...here.value, name];
  trail();
}

// THE CRUMBS: `to` is how many segments of `here` stay; 0 is the root.
function goTo(to: number): void {
  here.value = here.value.slice(0, to);
  trail();
}

// A FILE OPENS THE FILE'S OWN PAGE — the same door the tree uses, so the two
// ways in land in the same room.
function openFile(path: string): void {
  open("file:" + path, null);
}

// The header says which folder this is: "Arquivos / Notas / Diário".
function trail(): void {
  filesFolder.segments = [...here.value];
  setTrail(word("files"), ...here.value);
}

async function load(): Promise<void> {
  try {
    listing.value = await api<Listing>("/api/tree");
    // A folder that vanished with the reload (its last file was moved) is a place
    // that no longer exists: back to the root rather than an empty ghost.
    if (here.value.length && !inside.value.length) here.value = [];
    trail();
  } catch (err) {
    listing.value = null;
    showError(err as Error);
  }
}

onMounted(load);
watch(() => nav.tick, load);
</script>

<template>
  <div v-if="listing" class="section">
    <!-- WHAT THE FOLDER HOLDS, by bucket — the folder in view, not the whole —
         and the same numbers as one bar. -->
    <StatStrip :items="stripItems" />

    <!-- THE BROWSER: only to SEE. Up, the crumbs, folders that open and files that
         open their page — nothing here copies, moves, renames or deletes. -->
    <section class="cards fbrowse">
      <div class="fbar">
        <button type="button" class="back" :disabled="!here.length"
                :title="word('folder_up')" @click="goTo(here.length - 1)">{{ word("back") }}</button>
        <div class="crumbs" role="navigation" aria-label="path">
          <button type="button" class="crumb" :class="{ on: !here.length }" @click="goTo(0)">{{ word("files") }}</button>
          <template v-for="(seg, k) in here" :key="k">
            <span class="sep" aria-hidden="true">/</span>
            <button type="button" class="crumb" :class="{ on: k === here.length - 1 }" @click="goTo(k + 1)">{{ seg }}</button>
          </template>
        </div>
      </div>

      <div v-if="entries.dirs.length || entries.files.length" class="fgrid">
        <button v-for="d in entries.dirs" :key="'d:' + d.name" type="button"
                class="fitem" data-kind="folder" :title="d.name" @click="enter(d.name)">
          <span class="icon" aria-hidden="true"></span>
          <span class="fname">{{ d.name }}</span>
          <span class="fmeta">{{ d.count }} {{ word("items") }}</span>
        </button>
        <button v-for="f in entries.files" :key="'f:' + f.name" type="button"
                class="fitem" :data-bucket="f.bucket" :title="f.name" @click="openFile(f.path)">
          <span class="fsheet" aria-hidden="true"><span class="icon"></span></span>
          <span class="fname">{{ f.name }}</span>
        </button>
      </div>
      <EmptyState v-else icon="folder" :title="total ? word('folder_empty') : word('no_records')" />
    </section>
  </div>
</template>
