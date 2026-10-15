<script setup lang="ts">
// FileTreeNode — ONE level of the file tree. Recursive: every folder is a
// `Foldable` (born collapsed, opens on click, remembers what was opened) and its
// box carries the indent (`.branch`), never a second layer — a second wrapper
// would indent the level twice.

import { computed } from "vue";
import Foldable from "./Foldable.vue";
import { isCurrent, open, showError, poke } from "../lib/views";
import { openContextMenu, vContextMenu, type MenuItem } from "../lib/menu";
import { openPop } from "../lib/pop";
import { ask } from "../lib/confirm";
import { post } from "../lib/api";
import { toast } from "../lib/toast";
import { word } from "../lib/store";
import NamePop from "./pops/NamePop.vue";
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

// THE FIRST OCCASION THIS TREE OFFERED (TASK-165, fatia 4/4), before
// create/rename/delete landed (TASK-120, fatia 5/7). Restricted to `.md`:
// converting is the only thing a Markdown source can become, and the menu
// names nothing a file cannot do.
async function toPdf(full: string): Promise<void> {
  await runConvert(full, "pdf");
}
async function toDocx(full: string): Promise<void> {
  await runConvert(full, "docx");
}

async function runConvert(full: string, to: "pdf" | "docx"): Promise<void> {
  try {
    const answer = await post<{ path: string }>("/api/convert", { path: full, to });
    toast(word("convert_toast").replace("{path}", answer.path));
  } catch (err) {
    showError(err as Error);
  }
}

// CREATE, RENAME, DELETE (TASK-120, fatia 5/7) — the folder's own CRUD, over
// `prose.inside` the server already enforces; this component invents no
// second rule, only the three requests and the confirmation delete owes
// (`lib/confirm`, the same one the table's row delete asks, TASK-122).
const basenameOf = (full: string): string => full.slice(full.lastIndexOf("/") + 1);
const parentOf = (full: string): string => {
  const i = full.lastIndexOf("/");
  return i === -1 ? "" : full.slice(0, i);
};
const joinPath = (parent: string, name: string): string => (parent ? parent + "/" + name : name);

function openNamePop(ev: MouseEvent, initial: string, onSubmit: (value: string) => void): void {
  openPop("file-name", NamePop, { initial, onSubmit },
          { point: { x: ev.clientX, y: ev.clientY } });
}

async function createEntry(parent: string, isDir: boolean, name: string): Promise<void> {
  try {
    await post("/api/file/create", { path: joinPath(parent, name), dir: isDir });
    poke();
  } catch (err) {
    toast((err as Error).message);
  }
}

async function renameEntry(full: string, name: string): Promise<void> {
  try {
    await post("/api/file/rename", { path: full, to: joinPath(parentOf(full), name) });
    poke();
  } catch (err) {
    toast((err as Error).message);
  }
}

async function deleteEntry(full: string): Promise<void> {
  if (!(await ask(word("delete_confirm").replace("{name}", basenameOf(full))))) return;
  try {
    await post("/api/file/delete", { path: full });
    poke();
  } catch (err) {
    toast((err as Error).message);
  }
}

// A FILE'S RIGHT CLICK. The ONE OCCASION this tree already offered (convert,
// TASK-165) stays first when it applies; create/rename/delete join it — create
// lands BESIDE the file, in the folder it already sits in, since a leaf is not
// a place to create INSIDE.
function onMenu(event: MouseEvent, full: string): void {
  const items: MenuItem[] = [];
  if (full.toLowerCase().endsWith(".md")) {
    items.push({ label: word("convert_pdf"), action: () => void toPdf(full) });
    items.push({ label: word("convert_docx"), action: () => void toDocx(full) });
  }
  const parent = parentOf(full);
  items.push({
    label: word("new_file"),
    action: () => openNamePop(event, "", value => void createEntry(parent, false, value)),
  });
  items.push({
    label: word("new_folder"),
    action: () => openNamePop(event, "", value => void createEntry(parent, true, value)),
  });
  items.push({
    label: word("rename"),
    action: () => openNamePop(event, basenameOf(full), value => void renameEntry(full, value)),
  });
  items.push({ label: word("delete"), action: () => void deleteEntry(full) });
  openContextMenu(event, items);
}

// A FOLDER'S RIGHT CLICK: create lands INSIDE it, and the folder itself may be
// renamed or deleted — whole, with what sits inside it (`prose.delete`).
function onDirMenu(event: MouseEvent, full: string): void {
  const items: MenuItem[] = [
    {
      label: word("new_file"),
      action: () => openNamePop(event, "", value => void createEntry(full, false, value)),
    },
    {
      label: word("new_folder"),
      action: () => openNamePop(event, "", value => void createEntry(full, true, value)),
    },
    {
      label: word("rename"),
      action: () => openNamePop(event, basenameOf(full), value => void renameEntry(full, value)),
    },
    { label: word("delete"), action: () => void deleteEntry(full) },
  ];
  openContextMenu(event, items);
}

// A closure PER FILE/FOLDER, made in script and not in the template: the
// directive's handler type takes only an event, and the path is what tells
// entries apart.
function menuHandler(full: string): (ev: MouseEvent) => void {
  return ev => onMenu(ev, full);
}
function dirMenuHandler(full: string): (ev: MouseEvent) => void {
  return ev => onDirMenu(ev, full);
}
</script>

<template>
  <template v-for="[name, child] in dirs" :key="name">
    <!-- A PLAIN WRAPPER, carrying only the folder's context menu: `Foldable`
         renders TWO root nodes (the head, the collapsible box), so a directive
         placed on the component tag itself would have nowhere certain to land.
         No class and no rule of `base.css` touches it, so the indent and the
         fold's own layout read exactly as they did before this wrapper. A
         right-click inside an open folder, on a file or a deeper folder, never
         reaches this handler — `vContextMenu` stops it at the entry it hit. -->
    <div v-context-menu="dirMenuHandler(join(name))">
      <!-- `head-class="node"`, AND NOT THE PANEL'S `folder`: a directory inside the
           tree carries the same fold, but it is not the same LEVEL of item — the
           panel's four top-level rows are its chapters, and a folder is a name
           inside one of them. A level that wears the cloth of the level above it
           is a tree with no hierarchy left to read (`base.css`, `nav .node`). -->
      <Foldable :id="'tree:' + join(name)" :label="name" box-class="branch"
                head-class="node">
        <FileTreeNode :node="child" :prefix="join(name)" />
      </Foldable>
    </div>
  </template>
  <!-- `entry` is what makes the row a file LINE rather than a project row, and the
       BUCKET goes on the row as data — the icon is drawn from it by the theme
       (`--icon-*`, base.css), so the page decides neither the glyph nor the rule. -->
  <button v-for="f in files" :key="f.name" type="button" class="file entry"
          :data-bucket="f.bucket" :data-view="FILE_VIEW + join(f.name)"
          :class="{ on: isCurrent(FILE_VIEW + join(f.name)) }"
          @click="openFile(join(f.name))"
          v-context-menu="menuHandler(join(f.name))">
    <span class="icon" aria-hidden="true"></span>
    <span>{{ f.name }}</span>
  </button>
</template>
