// strongbox — the Vault's own state on the page: the one file open in the
// viewer, and how it opens and closes.
//
// THE CLEAR NEVER LANDS HERE. What this holds is the ADDRESS the server minted
// (`/api/strongbox/open`) and the KIND it answered, so the viewer knows how to
// draw the file. Walking that address — a `<img>`, an `<iframe>`, the fetch
// that reads the text — spends the one-time token (`strongbox_links`), which is
// why Ctrl+S mints a FRESH address instead of reusing the one on screen: the
// link the file was opened with is already gone by the time anybody saves.
import { reactive } from "vue";
import { post } from "./api";

export type SealedKind = "text" | "image" | "pdf" | "other";

export interface Sealed {
  path: string; // the `.enc` relative path
  name: string; // the original name, with the `.enc` off
  kind: SealedKind;
  url: string;  // the one-time clear address
}

export const viewer = reactive({ file: null as Sealed | null });

// The name the person gave the file: the `.enc` off the tail. The folder it sat
// in is the Cofre's own tree, not part of what was named.
export function clearName(path: string): string {
  const tail = path.split("/").pop() || path;
  return tail.endsWith(".enc") ? tail.slice(0, -4) : tail;
}

// Whether the viewer pushed a history entry that has to be popped when it
// closes — the entry exists only while the overlay is up.
let armed = false;

// Mint the one-time link and open the viewer on it. A file the key does not
// open, or one this boot has no key for, is refused by the SERVER and nothing
// opens — the refusal is the caller's to show.
export async function openSealed(path: string): Promise<void> {
  const answer = await post<{ url: string; kind: SealedKind }>("/api/strongbox/open", { path });
  viewer.file = { path, name: clearName(path), kind: answer.kind, url: answer.url };
  armed = true;
  // ONE ENTRY, so the SYSTEM BACK closes the viewer instead of leaving the app
  // (`popstate`, below). The page's own navigation is `replaceState`
  // (`views.ts`), so this is the only pushed entry and the back that pops it
  // lands exactly on the page that was under the overlay.
  history.pushState({ at: "strongbox" }, "");
}

// A FRESH link for the same file — what Ctrl+S saves. The address on screen was
// spent when the file opened; minting another is how the clear is walked a
// second time without this module ever holding it.
export async function sealedLink(path: string): Promise<string> {
  const answer = await post<{ url: string }>("/api/strongbox/open", { path });
  return answer.url;
}

export function closeSealed(): void {
  viewer.file = null;
  if (armed) {
    armed = false;
    history.back();
  }
}

// THE BACK GESTURE CLOSES THE VIEWER. Opening pushed one entry; the system back
// pops it, and this is what turns that pop into a close. `armed` is what tells
// the two backs apart: the one that already closed the viewer must not be
// answered again.
window.addEventListener("popstate", () => {
  if (!viewer.file) return;
  armed = false;
  viewer.file = null;
});
