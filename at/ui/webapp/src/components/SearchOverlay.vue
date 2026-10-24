<script setup lang="ts">
// SearchOverlay — the global search's one layer (B-21), opened by `/`.
//
// It wears the same `.veil` + `.dialog` pair the confirmation does. The field
// takes the focus when it opens; ArrowUp/ArrowDown walk the results, Enter opens
// the one marked, a click opens the one clicked, and Escape (heard by the shell,
// `shellListeners.ts`) closes it.
import { ref, watch, nextTick } from "vue";
import { word } from "../lib/store";
import { searchState, typed, move, pick, closeSearch } from "../lib/search";
import EmptyState from "./EmptyState.vue";

const field = ref<HTMLInputElement | null>(null);

watch(() => searchState.open, async open => {
  if (!open) return;
  await nextTick();
  field.value?.focus();
});

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "ArrowDown") { event.preventDefault(); move(1); }
  else if (event.key === "ArrowUp") { event.preventDefault(); move(-1); }
  else if (event.key === "Enter") { event.preventDefault(); pick(searchState.hits[searchState.active]); }
}

function where(hit: { kind: string; where: string; id: string | null }): string {
  return hit.kind === "file" ? hit.where : `${hit.where} ${hit.id ?? ""}`.trim();
}

function detail(hit: { kind: string; field: string; line: number | null }): string {
  if (hit.kind !== "file") return hit.field;
  return hit.field === "name" ? word("search_name") : `${word("search_line")} ${hit.line}`;
}
</script>

<template>
  <Transition leave-active-class="veil-leave-active">
    <div v-if="searchState.open" class="veil" @click="closeSearch()"></div>
  </Transition>
  <Transition leave-active-class="dialog-leave-active">
    <div v-if="searchState.open" class="dialog search" role="dialog" aria-modal="true"
         :aria-label="word('search')">
      <input ref="field" type="search" class="input" autocomplete="off" spellcheck="false"
             role="combobox" aria-expanded="true" aria-controls="search-results"
             :aria-activedescendant="searchState.hits.length ? 'search-hit-' + searchState.active : undefined"
             :placeholder="word('search_placeholder')" :aria-label="word('search')"
             :value="searchState.term"
             @input="typed(($event.target as HTMLInputElement).value)"
             @keydown="onKeydown" />
      <p v-if="searchState.error" class="refused" role="alert">{{ searchState.error }}</p>
      <ul v-if="searchState.hits.length" id="search-results" class="search-results" role="listbox">
        <li v-for="(hit, i) in searchState.hits" :id="'search-hit-' + i" :key="i"
            class="search-hit" :class="{ on: i === searchState.active }"
            role="option" :aria-selected="i === searchState.active"
            @mousemove="searchState.active = i" @click="pick(hit)">
          <span class="search-where">{{ where(hit) }}</span>
          <span class="search-detail">{{ detail(hit) }}</span>
          <span class="search-snippet">{{ hit.snippet }}</span>
        </li>
      </ul>
      <EmptyState v-else-if="searchState.asked && !searchState.error"
                  icon="folder" :title="word('search_none_title')" :text="word('search_none_text')" />
      <EmptyState v-else-if="!searchState.term.trim()"
                  icon="note" :title="word('search')" :text="word('search_start')" />
    </div>
  </Transition>
</template>
