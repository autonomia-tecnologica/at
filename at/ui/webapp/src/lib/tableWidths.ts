// Each column's width: MEASURED on the content and on the theme's font, never
// guessed — and measured over EVERY record, so filtering does not change the
// table's shape. Used by TableView.

import { ref, watch, onMounted, nextTick, type ComputedRef, type Ref, type WatchSource } from "vue";
import { store, label } from "./store";
import { narrow } from "./breakpoint";
import { rendererReady, ensureRenderer } from "./markdown";
import type { FieldSpec, RecordRow } from "./record";

export function useWidths(
  props: { records: RecordRow[] },
  fields: ComputedRef<FieldSpec[]>,
  byName: ComputedRef<Record<string, FieldSpec>>,
  shown: ComputedRef<string[]>,
  sort: Ref<{ name: string; dir: number } | null>,
  shownText: (name: string, rec: RecordRow) => string,
  // What else, besides the ones read here, makes the table measure again.
  triggers: WatchSource[],
) {
  const probeEl = ref<HTMLSpanElement | null>(null);
  const widths = ref<number[]>([]);

  function widthOf(text: string): number {
    const node = probeEl.value;
    if (!node) return 0;
    node.textContent = text;
    return node.getBoundingClientRect().width;
  }

  // A hidden span measures the text IN THE ACTIVE FONT: the theme styles it
  // (`.probe`), so the measurement follows the theme like everything else.
  function measure(): void {
    const css = getComputedStyle(document.documentElement);
    const chPx = widthOf("0".repeat(50)) / 50 || 0;
    const measurePx = (parseFloat(css.getPropertyValue("--measure")) || 66) * chPx;
    const padPx = 2 * (parseFloat(css.getPropertyValue("--density-cell-pad")) || 0);

    // `flexible` marks the column the reading measure CAPPED — the one holding a
    // long text. It is the one that gives up room on a narrow screen.
    function column(name: string): { px: number; flexible: boolean } {
      const spec = byName.value[name];
      let need = widthOf(label(spec?.labels) || name);
      if (spec?.refs?.length) need += chPx;
      if (spec?.filterable) need += 2 * chPx;
      if (sort.value && sort.value.name === name) need += chPx;
      let longest = "";
      for (const rec of props.records) {
        const text = shownText(name, rec);
        if (text.length > longest.length) longest = text;
      }
      need = Math.max(need, widthOf(longest));
      return { px: Math.min(need, measurePx) + padPx + 1, flexible: need > measurePx };
    }

    const entries = shown.value.map(column);
    const out = entries.map(entry => entry.px);

    // THE TABLE FITS THE ROOM IT IS HANDED: the columns the MEASURE capped give up
    // the excess between them, down to a floor where the text wraps instead of
    // vanishing. The short columns keep what their content needs.
    {
      // The room is the PAGE's: `#body > .page` caps the width and keeps the
      // gutter on both sides, at every window width (F3).
      const body = document.getElementById("body");
      const page = body?.querySelector<HTMLElement>(".page") ?? null;
      const pagePad = 2 * (parseFloat(css.getPropertyValue("--page-gutter")) || 20);
      const panelW = Math.min(page?.clientWidth || body?.clientWidth || window.innerWidth,
                              parseFloat(css.getPropertyValue("--page-max")) || Infinity) - pagePad;
      const floor = 5 * chPx + padPx + 1; // where the text wraps instead of vanishing
      let total = out.reduce((a, b) => a + b, 0);
      // 1) The READING columns give up first: they have room to spare.
      for (const i of entries.map((entry, i) => (entry.flexible ? i : -1)).filter(i => i >= 0)) {
        if (total <= panelW) break;
        const give = Math.min(out[i] - floor, total - panelW);
        if (give > 0) {
          out[i] -= give;
          total -= give;
        }
      }
      // 2) And if even that is not enough, the columns with the MOST ROOM give up
      // first — by slack, and never by position. Walking the columns left to right
      // is what the first version did, and it took everything from whoever came
      // first: the id and the title were squeezed to nothing while the widest
      // column kept every pixel it had asked for. "The ones with room to spare" is
      // not a position; it is how much is left over the floor.
      const bySlack = entries.map((_, i) => i).sort((a, b) => (out[b] - out[a]));
      for (const i of bySlack) {
        if (total <= panelW) break;
        const give = Math.min(out[i] - floor, total - panelW);
        if (give > 0) {
          out[i] -= give;
          total -= give;
        }
      }
    }

    widths.value = out;
  }

  watch(
    [...triggers, sort, () => props.records, () => store.themes, narrow, rendererReady],
    () => nextTick(measure),
  );

  onMounted(async () => {
    nextTick(measure);
    // A markdown column is drawn as the text its notation CARRIES, and taking the
    // notation out is the parser's job — so the renderer is asked for here, ONCE.
    if (fields.value.some(field => field.type === "markdown")) await ensureRenderer();
  });

  return { probeEl, widths };
}
