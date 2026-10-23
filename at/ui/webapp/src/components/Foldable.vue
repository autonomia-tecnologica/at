<script lang="ts">
// THE ACCORDION: folds that share a `group` are ONE choice — at most one open.
// The state MUST live in this plain (non-setup) block: `<script setup>` compiles
// every top-level declaration INTO setup(), i.e. one copy per Foldable instance,
// and then no fold ever sees another one (every fold ended up with its own group).
// A plain block runs once per module, which is what "shared" means.
import { reactive } from "vue";
const GROUPS: Record<string, { open: string | null; ids: Set<string> }> = {};
function groupOf(name: string) {
  return (GROUPS[name] ??= reactive({ open: null, ids: new Set<string>() }) as any);
}
</script>

<script setup lang="ts">
// Foldable — the page's SINGLE disclosure: the panel's folders, dressed by
// context. It is the same gesture, so it is the same control.
//
// What it preserves, because it is behaviour and not style:
//
// · a fold is BORN COLLAPSED — what opens one is the person, and only that
//   choice (a saved preference) opens it on the next load;
// · the box takes `.foldable` and the content lives in ONE layer (`.fold`),
//   because the collapse is the height of one grid track (`1fr` ↔ `0fr`,
//   base.css) and a track that animates is a track that changes;
// · the head takes `.fold-head`, which is where `base.css`'s caret hangs.

import { ref, computed, watch, onMounted } from "vue";
import { foldPrefs, savePrefs, PREFS_KEY } from "../lib/prefs";
import { isCurrent, open } from "../lib/views";

// THE ACCORDION's shared state lives in the plain <script> block above (see there).

const props = withDefaults(
  defineProps<{
    id: string;
    label?: string;
    // The class the BOX carries besides `.foldable`. It is through it that
    // `base.css` gives the indent (`nav .kinds`, `nav .branch`).
    boxClass?: string | null;
    // The HEAD's cloth: the panel's folder (`folder`) or a page's group.
    headClass?: string;
    // THE PAGE THIS HEAD ALSO OPENS. A fold is a DISCLOSURE, and a section of
    // the panel is also a PLACE: the TASKS fold is where the tasks live, and the
    // same row opens the tree and opens the screen — one gesture, because the
    // row is one thing. `null` is a fold that is only a fold, which is what
    // every fold was before there was a screen to lead to.
    view?: string | null;
    // The accordion this fold belongs to, or `null` for a fold on its own.
    group?: string | null;
  }>(),
  { label: "", boxClass: null, headClass: "folder", view: null, group: null },
);

const prefs = foldPrefs();
const shared = props.group ? groupOf(props.group) : null;
const own = ref(prefs[props.id] === true);
if (shared) {
  shared.ids.add(props.id);
  // Old prefs may hold several open: the FIRST to mount (the panel's order) wins.
  if (own.value && shared.open === null) shared.open = props.id;
  else if (own.value) prefs[props.id] = false;
}
const isOpen = computed(() => (shared ? shared.open === props.id : own.value));
const loadedOnce = ref(isOpen.value);
watch(isOpen, now => { if (now) loadedOnce.value = true; });

function toggle(): void {
  const now = !isOpen.value;
  if (shared) {
    shared.open = now ? props.id : null;
    for (const other of shared.ids) prefs[other] = other === props.id ? now : false;
  } else {
    own.value = now;
    prefs[props.id] = now;
  }
  savePrefs(PREFS_KEY, prefs);
  if (now) loadedOnce.value = true;
}

// The head's ONE click: the fold opens or closes, and — when the fold is a
// section with a page — the section opens. The tree is the section's content and
// the page is its front, so the two travel together; giving them a click each
// would be two controls for one thing.
function head(): void {
  if (props.view) open(props.view, null);
  toggle();
}

onMounted(() => {
  if (isOpen.value) loadedOnce.value = true;
});
</script>

<template>
  <!-- `data-branch` is the ID, ON THE HEAD. The id is a prop and never reaches
       the DOM by itself, and the head is where a theme hangs the mark of what a
       fold holds (`nav .folder[data-branch="tasks"]`, base.css) — which is a
       drawing and not behaviour, so it belongs to whoever dresses the control
       and not to whoever knows what it opens. -->
  <button :data-branch="id" :class="[headClass, 'fold-head', { closed: !isOpen, on: view && isCurrent(view) }]"
          type="button" @click="head">
    <span class="caret">▾</span>
    <!-- `.t` is the WORD, and it is named because a theme may have to place it:
         what follows it — the caret — belongs to the RIGHT EDGE (`base.css`). -->
    <span class="t">{{ label }}</span>
  </button>
  <div class="foldable" :class="[boxClass, { closed: !isOpen, grouped: group }]">
    <div class="fold">
      <slot v-if="loadedOnce" />
    </div>
  </div>
</template>
