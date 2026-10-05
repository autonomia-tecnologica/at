// confirm — a question the page asks in the page's OWN cloth.
//
// It is the browser's `confirm` done properly: a promise the caller awaits, and
// a dialog drawn by AT's design system (`.veil` + `.dialog`, the same "stop and
// ask" the entrance wears) instead of the native box — the one piece of a
// foreign OS that used to land in the middle of the app.
//
// ONE AT A TIME, like the pop and the toast: a second `ask` replaces the first,
// and the promise it left behind resolves `false` — an unanswered question is a
// "no", never a hang.
import { reactive } from "vue";

export const confirmState = reactive({
  open: false,
  message: "",
});

let settle: ((ok: boolean) => void) | null = null;

export function ask(message: string): Promise<boolean> {
  if (settle) {
    const beat = settle;
    settle = null;
    beat(false);
  }
  confirmState.message = message;
  confirmState.open = true;
  return new Promise<boolean>(resolve => { settle = resolve; });
}

export function answer(ok: boolean): void {
  confirmState.open = false;
  const done = settle;
  settle = null;
  if (done) done(ok);
}
