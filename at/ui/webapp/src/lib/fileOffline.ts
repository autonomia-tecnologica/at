// fileOffline — the page's door to the Service Worker's MARKED files (item 22).
// The page asks and draws; the SW keeps. Each question goes on a `MessageChannel`
// port sent with the message, so the answer comes back to the caller alone. No
// worker, or no answer in time, is `null`: the menu then offers nothing it cannot
// do, and the page never claims a file is kept when it is not.

export interface PinAnswer {
  ok: boolean;
  pinned?: boolean;
  // The marked files, alone, are over the limit: the page should say so.
  overflow?: boolean;
}

// A question (is it marked?) answers at once, or the menu waits for nothing: it
// gives up after this. A mark has no such limit: it downloads the file first.
const QUESTION_MS = 1500;

function ask(message: Record<string, unknown>, limitMs: number | null): Promise<PinAnswer | null> {
  return new Promise(resolve => {
    if (!("serviceWorker" in navigator)) {
      resolve(null);
      return;
    }
    const timer = limitMs === null ? null : window.setTimeout(() => done(null), limitMs);
    function done(answer: PinAnswer | null): void {
      if (timer !== null) window.clearTimeout(timer);
      resolve(answer);
    }
    navigator.serviceWorker.ready
      .then(registration => {
        const worker = registration.active;
        if (!worker) {
          done(null);
          return;
        }
        const channel = new MessageChannel();
        channel.port1.onmessage = event => done(event.data as PinAnswer);
        worker.postMessage({ ...message }, [channel.port2]);
      })
      .catch(() => done(null));
  });
}

// Whether the file is marked in THIS browser; `null` when there is no worker to ask.
export async function filePinned(path: string): Promise<boolean | null> {
  const answer = await ask({ type: "at:files-state", path }, QUESTION_MS);
  return answer && answer.ok ? Boolean(answer.pinned) : null;
}

// Marks (or unmarks) the file. A mark downloads it now, so it can fail offline.
export function setFilePin(path: string, pinned: boolean): Promise<PinAnswer | null> {
  return ask({ type: "at:files-pin", path, pinned }, null);
}
