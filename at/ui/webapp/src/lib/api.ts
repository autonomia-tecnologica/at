// api — the page's two network doors, and nothing else.

// A REQUEST THAT NEVER GOT AN ANSWER IS NOT A REFUSAL, and the browser's own
// message does not say which one it was: `fetch` rejects with a sentence about
// ITSELF, in ITS language ("Failed to fetch"). Nothing was written and nothing
// was read. So the failure is MARKED here and WORDED by the page, which is the
// only side that knows the language on the screen.
export interface NetTrouble extends Error {
  network?: boolean;
}

// `navigator.onLine` SÓ SABE DO ADAPTADOR, e não do SERVIDOR: um Wi-Fi ligado
// com a Tailscale desligada ainda é "online" para o navegador, e um pedido que
// nunca chega é a única prova de que ESTE servidor, e não a rede em geral,
// está fora de alcance. Por isso o aviso de offline (`lib/offline.ts`) escuta
// também esta chamada, e não só o evento do navegador.
let heardNetwork: ((ok: boolean) => void) | null = null;

export function whenNetwork(handler: (ok: boolean) => void): void {
  heardNetwork = handler;
}

export function offTheAir(err: unknown): NetTrouble {
  const message = err instanceof Error ? err.message : "network";
  const trouble: NetTrouble = new Error(message);
  trouble.network = true;
  heardNetwork?.(false);
  return trouble;
}

// WHAT A 401 MEANS. A refused request is not an error the page has to invent a
// word for — it says the session is gone, and the one way it goes is the server
// restarting under a page that is still open. Whoever listens puts the entrance
// back. It is a REGISTRATION and not an import: `api` is the floor, and the
// session is a floor above it.
let refusal: (() => void) | null = null;

export function whenRefused(handler: () => void): void {
  refusal = handler;
}

// The one place a refused answer is noticed, so that both doors hear it.
function refused(status: number): void {
  if (status === 401 && refusal) refusal();
}

export async function api<T = unknown>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { headers: { Accept: "application/json" } });
  } catch (err) {
    throw offTheAir(err);
  }
  heardNetwork?.(true);
  if (!response.ok) {
    refused(response.status);
    // The SERVER's message when it sent one, the same way the write door reads
    // it: a route refused by the ceiling says WHICH permission is missing (item
    // 11), and the page invents no word of its own (§3).
    const data = await response.json().catch(() => null);
    throw new Error((data && data.error) || response.status + " " + response.statusText);
  }
  return (await response.json()) as T;
}

// A WRITE. The body travels as JSON, and that is not a detail: a page from
// another origin can only send text/plain, urlencoded or multipart, so this
// content type is what the server uses to tell a write of ours from a foreign
// page's. The SERVER's message is what the person reads when it refuses — the
// page invents no word of its own.
export async function post<T = unknown>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw offTheAir(err);
  }
  heardNetwork?.(true);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    refused(response.status);
    throw new Error((data && data.error) || response.status + " " + response.statusText);
  }
  return data as T;
}
