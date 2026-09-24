// balloon — whether the interpreter's balloon flies, THIS browser's preference.
//
// The balloon is the interpreter's other shape: the box that stays over whatever
// view is open and takes one sentence about it. Turning it off is a PREFERENCE
// and not a datum, so it lives here, beside `at.motion` (`prefs.ts`), under the
// rule those already carry: ON is the default for whoever never chose, a strange
// value counts for nothing, and a localStorage that refuses is a preference
// forgotten and never an error.
//
// What it hides is the BALLOON and nothing else: the chat stays, the interpreter
// stays. The CORE's switch is another one (`interpreter`, in `app/settings.json`),
// and it is the one that takes the whole function away.

import { ref } from "vue";
import { loadPrefs, savePrefs } from "./prefs";

export const BALLOON_KEY = "at.balloon";

// The state is SHARED by the two who need it — the switch in Settings and the
// balloon itself —, because a module read twice is a module that drifts.
export const balloonOn = ref(loadPrefs(BALLOON_KEY).on !== false);

export function setBalloon(on: boolean): boolean {
  savePrefs(BALLOON_KEY, { on: !!on });
  balloonOn.value = !!on;
  return balloonOn.value;
}
