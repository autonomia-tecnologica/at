// The page's LISTENERS and the entrance: what the shell installs once it is
// mounted. Taken out of `App.vue` (B-17) unchanged.

import { whenRefused } from "./api";
import { enter, lost, session } from "./session";
import { word } from "./store";
import { setTrail } from "./views";
import { watchSystem } from "./theme";
import { applyMotion } from "./motion";
import { applyDensity } from "./density";
import { applyNav } from "./nav";
import { watchNarrow } from "./breakpoint";
import { popStack, closePop } from "./pop";
import { searchState, openSearch, closeSearch } from "./search";
import { shortcutsState, arm, disarm, act, isTyping } from "./shortcuts";

export async function installListeners(): Promise<void> {
  // The browser's menu stays OFF on the whole page: a row that is not a target
  // opens nothing — not the native menu either.
  document.addEventListener("contextmenu", ev => ev.preventDefault());
  // One door only to close the panel: the click outside and Escape. A click
  // outside also disarms the shortcuts pair (TASK-126) — the same "outside" a
  // popover already closes on.
  document.addEventListener("click", () => {
    closePop();
    disarm();
  });
  // ESCAPE, AND WHAT IT MEANS DEPENDS ON WHAT IS ON SCREEN (TASK-126). A pop
  // open beats everything else, exactly as it did before this shortcut
  // existed — the pair only arms with NO pop open. Past that: Escape arms (the
  // hint shows), Escape again disarms, and any key that follows either runs
  // its shortcut or disarms — a key that names nothing is not a key left
  // half-pressed.
  document.addEventListener("keydown", ev => {
    // THE GLOBAL SEARCH (B-21): `/` opens it, never inside a field, and Escape
    // closes it before anything else reads the key.
    if (ev.key === "Escape" && searchState.open) { closeSearch(); return; }
    if (ev.key === "/" && !ev.ctrlKey && !ev.metaKey && !ev.altKey && !searchState.open
        && !isTyping(ev.target)) {
      ev.preventDefault();
      openSearch();
      return;
    }
    if (ev.key === "Escape") {
      if (popStack.length) { closePop(); return; }
      if (isTyping(ev.target)) return;
      if (shortcutsState.armed) disarm(); else arm();
      return;
    }
    if (!shortcutsState.armed) return;
    if (isTyping(ev.target)) { disarm(); return; }
    // A modifier or a named key (Tab, ArrowLeft…) has `key.length > 1`, and
    // none of them is a letter this table knows — left alone, not disarmed,
    // because reaching for the capital letter with Shift held is not giving up.
    if (ev.ctrlKey || ev.metaKey || ev.altKey || ev.key.length !== 1) return;
    if (!act(ev.key)) disarm();
  });

  // The SIDE of the theme is the only choice the SYSTEM changes underneath.
  watchSystem();
  // Motion already entered before the paint; here it is the SAME choice, re-read
  // from the preference — keeping the two in agreement is what stops the page
  // from disagreeing with the CSS after a reload.
  applyMotion();
  applyDensity();
  applyNav();
  watchNarrow();

  // A 401 under a running page is the session gone — the server was restarted
  // under it — and what it costs is the ENTRANCE coming back, never a page
  // full of "401 Unauthorized". Wired here, and not as a side effect of a
  // module, so the two floors meet in one place.
  whenRefused(lost);

  // WHO IS IN, before anything else: `/api/state` is refused to whoever is not,
  // and the words the entrance draws with arrive in this same answer.
  try {
    await enter();
  } catch (err) {
    // A server that did not answer has no entrance to draw and no words to draw
    // it with: the page falls back to the shell it drew before there was an
    // entrance, and the head carries what happened. (The boot below runs from
    // this too — `ready` is what lets the page draw — and it will fail the same
    // way, which is the state that was already true.)
    session.auth = false;
    session.ready = true;
    setTrail(word("error") + " " + (err as Error).message);
  }
}
