// pop — the panel that FLOATS, and the single slot it takes.
//
// In the AT there is ONE open panel at a time, and they all speak the same
// language: a column's filter, the columns list and a field's pick. Whoever
// draws it is `Popover.vue`.
//
// The two ANCHORS are two roles, and that is the whole difference between them:
// a POPOVER hangs on the control that asked for it, a CONTEXT MENU opens AT THE
// POINTER.
//
// THE STACK IS ALMOST ALWAYS ONE DEEP (TASK-173): a plain `openPop` still
// CLEARS whatever was open before pushing its own — that is the rule above,
// untouched. The second level exists for exactly one case: a record opened as
// a FLOATING PANEL over the list it was clicked from, and the pick one of its
// OWN fields opens (`RecordView.vue`) — that pick has to land OVER the record
// and not in its place, which is what `nest: true` is for. `closePop` always
// takes the TOP entry off, so Escape and an outside click close the pick
// first and the record panel on the next one — the record is never torn away
// under a pick still open on top of it.

import { reactive, markRaw } from "vue";
import type { Component } from "vue";

export interface PopEntry {
  key: string;
  component: Component;
  props: Record<string, unknown> | null;
  anchor: HTMLElement | null;
  point: { x: number; y: number } | null;
  onClose: (() => void) | null;
  attrs: Record<string, string> | null;
}

export const popStack = reactive<PopEntry[]>([]);

// Opening TAKES the slot: whatever was open leaves first, and its `onClose`
// runs — unless `nest` says this one opens OVER it instead.
export function openPop(
  key: string,
  component: Component,
  props: Record<string, unknown>,
  { anchor = null, point = null, onClose = null, attrs = null, nest = false }:
    {
      anchor?: HTMLElement | null;
      point?: { x: number; y: number } | null;
      onClose?: (() => void) | null;
      attrs?: Record<string, string> | null;
      nest?: boolean;
    } = {},
): void {
  if (!nest) while (popStack.length) closePop();
  popStack.push({ key, component: markRaw(component), props, anchor, point, onClose, attrs });
}

// The ONE way out (Escape, a click outside, another panel taking the slot) —
// and it takes only the TOP entry, which is the whole stack whenever nothing
// nested it. The `onClose` runs HERE and not in each of those three places —
// a control that says OPEN cannot go on saying it after the panel is gone.
export function closePop(): void {
  const done = popStack.pop()?.onClose;
  if (done) done();
}

// A PILHA INTEIRA, quando o próximo passo é uma PÁGINA e não outro painel: o
// seletor e o painel do registro que o hospedou saem juntos, e nada fica
// flutuando sobre o registro que vai abrir.
export function closeAllPops(): void {
  while (popStack.length) closePop();
}

export function isPopOpen(key: string): boolean {
  return popStack.some(entry => entry.key === key);
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
