// menu — the ONE door every declared right-click occasion opens through
// (TASK-120, fatia 1). It is `pop.ts`'s CONTEXT MENU role (`point`, not
// `anchor`): the panel opens AT THE POINTER, and the pointer is where a mouse
// right-click landed OR where the browser places a keyboard-invoked one (the
// context-menu key, Shift+F10) — a native `contextmenu` event carries
// `clientX`/`clientY` either way, so the two inputs need no separate code.
//
// An occasion with nothing legal to show opens nothing: a menu with zero
// items is worse than no menu, and the native one stays suppressed either way
// (the caller's own `@contextmenu.prevent.stop`).

import { openPop } from "./pop";
import ContextMenu, { type MenuItem } from "../components/pops/ContextMenu.vue";

export type { MenuItem };

const KEY = "menu";

export function openContextMenu(event: MouseEvent, items: MenuItem[]): void {
  if (!items.length) return;
  openPop(KEY, ContextMenu, { items }, { point: { x: event.clientX, y: event.clientY } });
}
