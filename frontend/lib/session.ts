//anonymous session token (feature 1, table 2).
//random, created in the browser, used by the server for the 5-per-hour rate
//limit only. it is not an account and is never shown to other people.

const KEY = "lightsout.session";
let memoryToken: string | null = null;

function randomToken(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function sessionToken(): string {
  try {
    const existing = window.localStorage.getItem(KEY);
    if (existing) return existing;
    const fresh = randomToken();
    window.localStorage.setItem(KEY, fresh);
    return fresh;
  } catch {
    //private mode or storage blocked: keep a token for this tab only.
    memoryToken ??= randomToken();
    return memoryToken;
  }
}
