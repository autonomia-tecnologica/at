// menu — the ONE door every declared right-click occasion opens through
// (TASK-120, fatia 1). It is `pop.ts`'s CONTEXT MENU role (`point`, not
// `anchor`): the panel opens AT THE POINTER, and the pointer is where a mouse
// right-click landed OR where the browser places a keyboard-invoked one (the
// context-menu key, Shift+F10) — a native `contextmenu` event carries
// `clientX`/`clientY` either way, so the two inputs need no separate code.
//
// An occasion with nothing legal to show opens nothing: a menu with zero
// items is worse than no menu, and the native one stays suppressed either way
// (the caller's own `v-context-menu`, below).

import type { Directive } from "vue";
import { openPop } from "./pop";
import ContextMenu, { type MenuItem } from "../components/pops/ContextMenu.vue";

export type { MenuItem };

const KEY = "menu";

export function openContextMenu(event: MouseEvent, items: MenuItem[]): void {
  if (!items.length) return;
  openPop(KEY, ContextMenu, { items }, { point: { x: event.clientX, y: event.clientY } });
}

// THE TOUCH DOOR (TASK-174): a right click has no finger. `v-context-menu`
// is the ONE gatilho every occasion binds to — it wires the native
// `contextmenu` event (mouse, keyboard) AND a long-press timer (touch) to the
// SAME handler, so a consumer gains the touch door by writing the directive
// once instead of a gesture timer per component.
type Handler = (event: MouseEvent) => void;

const LONG_PRESS_MS = 500; // the OS default for "this is a hold, not a tap"
const MOVE_THRESHOLD = 10; // px of drift that turns a hold into a scroll/drag

interface State {
  handler: Handler;
  timer: ReturnType<typeof setTimeout> | null;
  start: { x: number; y: number };
  touchFired: boolean; // swallows the `contextmenu` some browsers still fire after a touch long-press
  cleanup: () => void;
}

const states = new WeakMap<HTMLElement, State>();

// A MouseEvent BY SHAPE, not by birth: `openContextMenu` and the handlers
// this directive calls read only `clientX`/`clientY`/`currentTarget` off it,
// which is exactly what a touch point has to offer.
function touchAsMouseEvent(el: HTMLElement, x: number, y: number): MouseEvent {
  return {
    clientX: x,
    clientY: y,
    currentTarget: el,
    target: el,
    preventDefault() {},
    stopPropagation() {},
  } as unknown as MouseEvent;
}

function cancelPress(state: State): void {
  if (state.timer !== null) {
    clearTimeout(state.timer);
    state.timer = null;
  }
}

export const vContextMenu: Directive<HTMLElement, Handler> = {
  mounted(el, binding) {
    const state: State = {
      handler: binding.value,
      timer: null,
      start: { x: 0, y: 0 },
      touchFired: false,
      cleanup: () => {},
    };

    const onTouchStart = (ev: TouchEvent): void => {
      if (ev.touches.length !== 1) return;
      const touch = ev.touches[0];
      state.start = { x: touch.clientX, y: touch.clientY };
      cancelPress(state);
      state.timer = setTimeout(() => {
        state.timer = null;
        state.touchFired = true;
        state.handler(touchAsMouseEvent(el, state.start.x, state.start.y));
      }, LONG_PRESS_MS);
    };
    const onTouchMove = (ev: TouchEvent): void => {
      const touch = ev.touches[0];
      if (!touch) return;
      const dx = touch.clientX - state.start.x;
      const dy = touch.clientY - state.start.y;
      if (Math.hypot(dx, dy) > MOVE_THRESHOLD) cancelPress(state);
    };
    const onTouchEnd = (): void => {
      cancelPress(state);
      if (state.touchFired) setTimeout(() => { state.touchFired = false; }, 400);
    };
    const onContextMenu = (ev: MouseEvent): void => {
      ev.preventDefault();
      ev.stopPropagation();
      if (state.touchFired) return; // this gesture already opened it
      state.handler(ev);
    };

    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchmove", onTouchMove, { passive: true });
    el.addEventListener("touchend", onTouchEnd);
    el.addEventListener("touchcancel", onTouchEnd);
    el.addEventListener("contextmenu", onContextMenu);

    state.cleanup = () => {
      cancelPress(state);
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchmove", onTouchMove);
      el.removeEventListener("touchend", onTouchEnd);
      el.removeEventListener("touchcancel", onTouchEnd);
      el.removeEventListener("contextmenu", onContextMenu);
    };
    states.set(el, state);
  },

  updated(el, binding) {
    const state = states.get(el);
    if (state) state.handler = binding.value;
  },

  unmounted(el) {
    states.get(el)?.cleanup();
    states.delete(el);
  },
};
