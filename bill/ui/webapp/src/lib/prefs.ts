// prefs — THIS browser's own preferences (localStorage).
//
// The rule: store only what is PREFERENCE, and never treat what is stored as
// data — an unknown key falls back to the default, and a localStorage that
// refuses (private mode) only means the preference is forgotten, never an error.

export const PREFS_KEY = "bill.sidebar";   // what is open (the folds)
export const FILTERS_KEY = "bill.filters"; // which values a column leaves out
export const COLUMNS_KEY = "bill.columns"; // a table's order and its hidden
export const SELECT_KEY = "bill.select";   // what is open, so a reload returns there

export type Prefs = Record<string, any>;

export function loadPrefs(key: string): Prefs {
  try {
    const raw = JSON.parse(localStorage.getItem(key) ?? "null");
    return raw && typeof raw === "object" ? raw : {};
  } catch {
    return {};
  }
}

export function savePrefs(key: string, prefs: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(prefs));
  } catch {
    // A refused localStorage is a preference forgotten, never a failure.
  }
}

// What the panel shows right now, so a reload comes back to it: the VIEW (a
// table's key) and, when a record was open, its id.
export function remember(view: string | null, id: unknown, back: unknown): void {
  savePrefs(SELECT_KEY, {
    view: view || null,
    id: id || null,
    back: Array.isArray(back) ? back : [],
  });
}

// The fold preferences are read ONCE and shared: a fold toggled later would
// otherwise save an older copy of them and drop what another fold just wrote.
let FOLDS: Prefs | null = null;
export function foldPrefs(): Prefs {
  if (FOLDS === null) FOLDS = loadPrefs(PREFS_KEY);
  return FOLDS;
}
