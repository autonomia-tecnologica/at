// breakpoint — the ONE window width the page asks about, in one place.
//
// 960 is the SAME number as the base's band (base.css, section 5) and as nav's
// NARROW. It cannot come from a token: a media query does not read custom
// properties — it is the one family of value that has to be a literal, and the
// places are a set by contract.

import { ref } from "vue";
import type { Ref } from "vue";

export const NARROW = window.matchMedia("(max-width: 960px)");

// What the window IS right now, reactive. Whoever installs the listener is the
// app's boot, ONCE — this module installs nothing for having been imported.
export const narrow: Ref<boolean> = ref(NARROW.matches);

export function watchNarrow(): void {
  NARROW.addEventListener("change", () => {
    narrow.value = NARROW.matches;
  });
}
