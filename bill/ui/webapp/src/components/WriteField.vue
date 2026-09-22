<script setup lang="ts">
// WriteField — the field a TEXT file is written in, and it saves itself.
//
// It is a `<textarea>`: the caret, the selection, the keyboard and the undo stack
// are the browser's, and a contenteditable that reinvented them would be a worse
// editor for no gain. What this owns is the SAVE: when it goes, what it does when
// it fails, and what it tells the page while it is happening (`writing.ts`).
//
// The spell-check layer the PoC drew BEHIND the textarea is not here: there is no
// checker yet, and an empty mirror layer would be a rule the page does not have.

import { ref, onMounted, onBeforeUnmount } from "vue";
import { useWriting } from "../lib/writing";

const props = defineProps<{
  path: string;
  text: string;
  rev: string;
}>();

const draft = ref(props.text);
const el = ref<HTMLTextAreaElement | null>(null);
const writer = useWriting(() => props.path);

// The textarea grows with what is written — a scrollbar inside a page that
// already scrolls is two scrollers for one text.
function grow(): void {
  const node = el.value;
  if (!node) return;
  node.style.height = "auto";
  node.style.height = node.scrollHeight + "px";
}

function onInput(): void {
  writer.touch(draft.value);
  grow();
}

// The one save that may have to outlive the page: leaving the tab, or leaving the
// page. The answer's revision is kept, so the next save is not refused against
// the page's own write.
function flush(): void {
  void writer.flush();
}

onMounted(() => {
  writer.set(props.text, props.rev);
  grow();
  el.value?.focus();
  document.addEventListener("visibilitychange", flush);
});

onBeforeUnmount(() => {
  document.removeEventListener("visibilitychange", flush);
  flush();
  writer.leave();
});
</script>

<template>
  <div class="write-wrap">
    <div class="write">
      <textarea ref="el" v-model="draft" class="write-field" spellcheck="false"
                @input="onInput"></textarea>
    </div>
  </div>
</template>
