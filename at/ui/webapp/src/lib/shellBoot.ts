// The shell's BOOT: the gate (`booted`, `revealed`) and the one path that
// loads the state. Taken out of `App.vue` (B-17) unchanged.

import { nextTick, ref, watch } from "vue";
import { api } from "./api";
import { session, signedIn } from "./session";
import { applyState, word } from "./store";
import { ensureRenderer } from "./markdown";
import { ensureFonts } from "./fonts";
import { armPageLoad, pageReading, pageLoad, poke, setTrail } from "./views";
import { applyTheme } from "./theme";
import { writingState } from "./writing";
import { showSaved } from "./shellRoute";

// THE SERVER WARNING: the data changed. The words come in again through
// `applyState` (the language may have changed) and the SAME page is redrawn — in
// the same place, because whoever was reading is not thrown to the top.
export async function refresh(): Promise<void> {
  const state = await api<Record<string, unknown>>("/api/state").catch(() => null);
  if (state) {
    applyState(state);
    applyTheme();
  }
  // WHILE SOMEBODY IS WRITING, THE PAGE IS NOT REDRAWN. Every save changes the
  // file on the disk, so the writer wakes ITSELF through this very path — and
  // redrawing under a sentence is the page fighting the person.
  if (writingState.active) return;
  poke();
}


// THE SECOND STEP OF THE GATE. `signedIn` is the server saying WHO IS IN, and it
// arrives with the words of the entrance — but not with the TABLES, not with
// the page, not with the MARKDOWN RENDERER and not with the TEN SELF-HOSTED
// FACES, which land one or more answers later (`/api/state`, `/vendor/marked`,
// `lib/fonts.ts`). Drawing the shell in between paints it full-size and empty,
// fills it with raw notation that reformats a moment after, or — the one
// `font-display: block` alone does not reach — leaves a plain cell blank while
// a badge two columns over already reads fine, because the two wear different
// WEIGHTS of the same family and nothing says the files land together. So the
// gate waits for ALL of it.
export const booted = ref(false);

// AND THEN A BEAT, BEFORE ANY OF IT IS SHOWN. The shell mounting is not the
// same as the shell being READY to look at: the page it opened fetches its own
// rows, the browser lays the table out, the self-hosted faces and the markdown
// renderer land — each a fraction behind the mount, each one a small correction
// on screen if it is watched as it happens. A short, fixed pause before the
// reveal lets all of it settle BEHIND the gate, so what a person sees is the
// finished shell arriving, not the shell assembling itself. 300ms is what that
// pause measured out to: long enough to cover the corrections, short enough
// that the wait itself is not the thing they notice.
const SETTLE_MS = 300;

// THE FADE IS ON `body`, ONE ELEMENT, NOT ON `nav` AND `main` SEPARATELY: two
// elements each running their own opacity transition is two fades, and a panel
// and a page settling on different beats reads as the shell coming apart, not
// as one thing arriving. `body` sits outside the Vue tree `#app` mounts into,
// so the class is toggled by hand — the one spot this component reaches past
// its own root, on purpose.
//
// IT IS A LATCH: `signedIn` false is the ENTRANCE, shown under this same fade
// as soon as `session.ready`, and a person who then signs in must not watch the
// whole body fade back out and in while the shell takes the entrance's place —
// once there was something on screen, there always is.
const revealed = ref(false);
const bodyShown = ref(false);
watch(
  () => session.ready && (!signedIn.value || revealed.value),
  ready => { if (ready) bodyShown.value = true; },
  { immediate: true },
);
watch(
  bodyShown,
  value => document.body.classList.toggle("revealed", value),
  { immediate: true },
);

// THE BOOT, AND IT IS ONE PATH. Whoever has just proved a credential walks
// exactly what a reload walks: the state, the theme and the entry page — so the
// shell ends in the same place either way and there is no second boot.
async function load(): Promise<void> {
  // The shell goes back under the gate and only leaves it once the state is
  // applied: a credential just proved walks this same path, and it must not draw
  // the shell with the PREVIOUS state's tables.
  booted.value = false;
  armPageLoad();
  try {
    // The renderer and the ten faces ride ALONGSIDE the state fetch, not after
    // it: none of the three have anything to say to each other, and waiting
    // for one before asking for the next would only make the gate stay shut
    // longer than it has to.
    const [state] = await Promise.all([
      api<Record<string, unknown>>("/api/state"),
      ensureRenderer(),
      ensureFonts(),
    ]);
    applyState(state);
    applyTheme();
    showSaved();
  } catch (err) {
    setTrail(word("error") + " " + (err as Error).message);
  } finally {
    // Served or refused, the boot is DONE. A server that did not answer has no
    // words to wait for; holding the gate would leave the page blank forever
    // where it now shows the error it fell back to.
    booted.value = true;
  }
  // `booted` just let the page MOUNT (the template's own `v-if`), and a page
  // that reads for itself — a file's text, a table's rows — only starts that
  // read now, in its `onMounted`. One tick is what it takes for that setup to
  // have run and said whether it reads (`pageReading`); then the boot waits for
  // it, bounded so a read that never lands cannot hold the page shut.
  await nextTick();
  if (pageReading()) {
    await Promise.race([
      pageLoad(),
      new Promise<void>(resolve => setTimeout(resolve, 600)),
    ]);
  }
  await new Promise<void>(resolve => setTimeout(resolve, SETTLE_MS));
  revealed.value = true;
}

// WHATEVER LETS THE PAGE DRAW WAKES THE BOOT, and it is a WATCH and not an event
// from the entrance. The difference is not style: the entrance is UNMOUNTED the
// moment the session exists — the shell takes its place — so an event emitted
// after the awaited sign-in is an event from a component that is already gone,
// and Vue drops it. Here nobody has to survive anything: the answer changes, and
// the shell boots.
//
// `immediate` is what covers the folder that asks NOBODY: no session ever comes,
// and the page is allowed to draw from the first answer.
export function startBoot(): void {
watch(signedIn, allowed => {
  if (allowed) void load();
}, { immediate: true });
}
