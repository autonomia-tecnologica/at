// api — the page's two network doors, and nothing else.

// A REQUEST THAT NEVER GOT AN ANSWER IS NOT A REFUSAL, and the browser's own
// message does not say which one it was: `fetch` rejects with a sentence about
// ITSELF, in ITS language ("Failed to fetch"). Nothing was written and nothing
// was read. So the failure is MARKED here and WORDED by the page, which is the
// only side that knows the language on the screen.
export interface NetTrouble extends Error {
  network?: boolean;
}

export function offTheAir(err: unknown): NetTrouble {
  const message = err instanceof Error ? err.message : "network";
  const trouble: NetTrouble = new Error(message);
  trouble.network = true;
  return trouble;
}

export async function api<T = unknown>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { headers: { Accept: "application/json" } });
  } catch (err) {
    throw offTheAir(err);
  }
  if (!response.ok) throw new Error(response.status + " " + response.statusText);
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
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error((data && data.error) || response.status + " " + response.statusText);
  }
  return data as T;
}
