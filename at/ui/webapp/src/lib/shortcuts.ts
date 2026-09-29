// shortcuts — THE ESC-ARMED KEYBOARD SHORTCUTS (TASK-126).
//
// One PAIR of keystrokes opens a section: ESCAPE arms it (and the hint with
// the letters shows, `Hint.vue`), and the LETTER that follows acts and
// disarms. Anything else — a second Escape, a click, a key that names no
// shortcut, a target that is an input — disarms with no action: a hint left
// open after the person moved on would be a hint lying about what a key does
// now.
//
// THE TABLE IS THE WHOLE SURFACE. A new shortcut is a new entry here, never a
// new branch in the keydown handler that plugs it in (`App.vue`).

import { reactive } from "vue";
import { store } from "./store";
import { FILES_KEY, SETTINGS_KEY, lastFile, lastTasks, open } from "./views";

export const shortcutsState = reactive({
  armed: false,
});

export interface Shortcut {
  key: string;      // the letter, uppercase
  labelKey: string; // the catalog word the hint shows
  run: () => void;
}

export const SHORTCUTS: Shortcut[] = [
  { key: "C", labelKey: "settings", run: () => open(SETTINGS_KEY, null) },
  // The last `file:*` visited, or the section's own root with none yet.
  { key: "A", labelKey: "files", run: () => open(lastFile() ?? FILES_KEY, null) },
  // The last project/orphans/"every task" visited, or "every task" with none yet.
  { key: "T", labelKey: "tasks", run: () => open(lastTasks() ?? store.types.task, null) },
];

export function arm(): void {
  shortcutsState.armed = true;
}

export function disarm(): void {
  shortcutsState.armed = false;
}

// A key that names a shortcut runs it and disarms; a key that names none is
// the caller's to disarm.
export function act(key: string): boolean {
  const found = SHORTCUTS.find(s => s.key === key.toUpperCase());
  if (!found) return false;
  found.run();
  disarm();
  return true;
}

// Inside any input, the pair neither arms nor acts — a person typing "cat" is
// typing, not asking for Tarefas.
export function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
}
