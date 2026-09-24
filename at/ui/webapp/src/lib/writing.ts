// writing — the contract of a field that SAVES ITSELF.
//
// There is no save button and there does not need to be one: what somebody writes
// is what is on the disk a moment later. What this owes, in exchange, is that a
// save never loses a keystroke and never overwrites somebody else's.
//
// Three rules, and each one exists because its absence was felt:
//
// · a save that did not LAND is retried, and only when the request never
//   ARRIVED (a refusal is the server's answer and will be the same in five
//   seconds);
// · a failure does not advance the revision and does not touch the buffer — a
//   retry has to be the SAME attempt, not a new version the page made up;
// · leaving the page flushes, and the answer's revision is kept: a write that
//   landed changes the digest on the disk, and without it the next save would
//   answer 409 forever.

import { reactive, ref } from "vue";
import { post } from "./api";

export const SAVE_DELAY = 1200;
export const SAVE_RETRY = 5000;
export const SAVE_NOTICE = 2000;

// Whether somebody is writing right now. The shell reads it to hold the redraw:
// every save changes the file on the disk, and redrawing under a sentence is the
// page fighting the person.
export const writingState = reactive({
  active: false,
  status: "",
  failed: false,
});

export interface Saved {
  path: string;
  rev: string;
}

export function saveFile(path: string, text: string, base: string): Promise<Saved> {
  return post<Saved>("/api/file", { path, text, base });
}

export function useWriting(path: () => string) {
  const revision = ref("");
  let buffer = "";
  let saved = "";
  let timer: number | undefined;

  function say(message: string, bad = false): void {
    writingState.status = message;
    writingState.failed = bad;
    // "Saved" is NEWS and clears itself; a failure is a STATE and does not —
    // the line that a save did not land is text that is not on the disk, and
    // clearing it to keep the screen pretty is the failure that costs a chapter.
    if (!bad) window.setTimeout(() => {
      if (!writingState.failed) writingState.status = "";
    }, SAVE_NOTICE);
  }

  async function run(): Promise<void> {
    const attempt = buffer;
    try {
      const answer = await saveFile(path(), attempt, revision.value);
      revision.value = answer.rev;
      saved = attempt;
      if (buffer === saved) say("");
    } catch (err) {
      const trouble = err as Error & { network?: boolean };
      say(trouble.message, true);
      // Only a request that never ARRIVED is retried: a refusal is an answer.
      if (trouble.network) {
        window.setTimeout(() => {
          if (buffer !== saved) void run();
        }, SAVE_RETRY);
      }
    }
  }

  return {
    revision,

    // What was read from the disk, so the first save has something to compare
    // against and does not overwrite an edit nobody saw.
    set(text: string, rev: string): void {
      buffer = text;
      saved = text;
      revision.value = rev;
    },

    touch(text: string): void {
      buffer = text;
      writingState.active = true;
      window.clearTimeout(timer);
      if (buffer === saved) {
        writingState.status = "";
        writingState.failed = false;
        return;
      }
      timer = window.setTimeout(() => void run(), SAVE_DELAY);
    },

    // On the way out, and the answer's revision is KEPT: a write that landed
    // changes the digest on the disk, and dropping it would make the next save
    // 409 against the page's own write.
    async flush(): Promise<void> {
      window.clearTimeout(timer);
      if (buffer === saved) return;
      try {
        const answer = await saveFile(path(), buffer, revision.value);
        revision.value = answer.rev;
        saved = buffer;
      } catch {
        // Leaving either way; the failure was already said on the line.
      }
    },

    leave(): void {
      window.clearTimeout(timer);
      writingState.active = false;
    },
  };
}
