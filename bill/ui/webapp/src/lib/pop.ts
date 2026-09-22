// pop — the panel that FLOATS, and the single slot it takes.
//
// In the bill there is ONE open panel at a time, and they all speak the same
// language: a column's filter, the columns list and a field's pick. Whoever
// draws it is `Popover.vue`.
//
// The two ANCHORS are two roles, and that is the whole difference between them:
// a POPOVER hangs on the control that asked for it, a CONTEXT MENU opens AT THE
// POINTER.

import { reactive, markRaw } from "vue";
import type { Component } from "vue";

export const popState = reactive({
  key: null as string | null,
  component: null as Component | null,
  props: null as Record<string, unknown> | null,
  anchor: null as HTMLElement | null,
  point: null as { x: number; y: number } | null,
  onClose: null as (() => void) | null,
  attrs: null as Record<string, string> | null,
});

// Opening TAKES the slot: whatever was open leaves first, and its `onClose` runs.
export function openPop(
  key: string,
  component: Component,
  props: Record<string, unknown>,
  { anchor = null, point = null, onClose = null, attrs = null }:
    {
      anchor?: HTMLElement | null;
      point?: { x: number; y: number } | null;
      onClose?: (() => void) | null;
      attrs?: Record<string, string> | null;
    } = {},
): void {
  closePop();
  popState.key = key;
  popState.component = markRaw(component);
  popState.props = props;
  popState.anchor = anchor;
  popState.point = point;
  popState.onClose = onClose;
  popState.attrs = attrs;
}

// The ONE way out (Escape, a click outside, another panel taking the slot). The
// `onClose` runs HERE and not in each of those three places — a control that
// says OPEN cannot go on saying it after the panel is gone.
export function closePop(): void {
  const done = popState.onClose;
  popState.key = null;
  popState.component = null;
  popState.props = null;
  popState.anchor = null;
  popState.point = null;
  popState.onClose = null;
  popState.attrs = null;
  if (done) done();
}

export function isPopOpen(key: string): boolean {
  return popState.key === key;
}

// Where a panel LANDS, and never off the window. It reads the panel's OWN size —
// which is why whoever calls it places it AFTER the panel exists.
export function placeAt(
  node: HTMLElement | null,
  { anchor = null, point = null }: { anchor?: HTMLElement | null; point?: { x: number; y: number } | null },
): void {
  if (!node) return;
  let left: number;
  let top: number;
  if (point) {
    left = point.x;
    top = point.y;
  } else if (anchor) {
    const rect = anchor.getBoundingClientRect();
    left = rect.left;
    top = rect.bottom + 4;
  } else {
    return;
  }
  node.style.left = Math.max(8, Math.min(left, window.innerWidth - node.offsetWidth - 8)) + "px";
  node.style.top = Math.max(8, Math.min(top, window.innerHeight - node.offsetHeight - 8)) + "px";
}
