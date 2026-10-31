// toast — a sentence that appears, holds for five seconds while a bar empties,
// and leaves on its own (TASK-165, fatia 3/4). Generic on purpose: this file
// names no conversion, no file, no anything — a caller hands it the WORDS, in
// the language already on screen, and this is the whole of what it owns.
//
// ONE AT A TIME. A second call while the first is still showing REPLACES it —
// the bar restarts at full, the clock restarts at five seconds — because two
// toasts stacked is a second thing to read while the first is still being
// read, and nothing so far needs more than one.
//
// ONE ACTION, when the caller names one (B-54): the "Saved" of a write carries
// its "Undo", and who owns the undo is the caller — this file only draws the
// door and runs it.

import { reactive } from "vue";

export const DURATION = 5000;

export interface ToastAction {
  // The word on the button, already in the language on screen.
  label: string;
  run: () => void;
}

interface Toast {
  message: string;
  action: ToastAction | null;
  // Bumped every call, including a repeat of the SAME message: it is the
  // template's `:key`, so Vue tears the bar down and builds it again — the
  // one thing that makes the CSS animation restart instead of sitting at
  // zero width from the toast it already ran for.
  key: number;
}

export const toastState = reactive<{ current: Toast | null }>({ current: null });

let timer: number | undefined;
let seq = 0;

export function toast(message: string, action: ToastAction | null = null): void {
  seq += 1;
  toastState.current = { message, action, key: seq };
  window.clearTimeout(timer);
  timer = window.setTimeout(() => {
    toastState.current = null;
  }, DURATION);
}
