// prefs — THIS browser's own preferences (localStorage).
//
// The rule: store only what is PREFERENCE, and never treat what is stored as
// data — an unknown key falls back to the default, and a localStorage that
// refuses (private mode) only means the preference is forgotten, never an error.

export const PREFS_KEY = "at.sidebar";   // what is open (the folds)
export const FILTERS_KEY = "at.filters"; // which values a column leaves out
export const COLUMNS_KEY = "at.columns"; // a table's order and its hidden
export const SELECT_KEY = "at.select";   // what is open, so a reload returns there
export const REMINDER_DAYS_KEY = "at.reminderDays"; // the reminders screen's horizon (7/30/90 days)
export const FILES_OFFLINE_KEY = "at.filesOffline"; // the offline files of THIS browser: mode and limit (MB)

// What the browser keeps of the files it opened (item 21). "never" keeps nothing
// new; "kept" (the default) keeps what was opened, LRU, up to the limit.
export const FILES_OFFLINE_MODES = ["never", "kept"] as const;
export type FilesOfflineMode = (typeof FILES_OFFLINE_MODES)[number];
export const FILES_OFFLINE_DEFAULT_MB = 500;

export interface FilesOffline {
  mode: FilesOfflineMode;
  limitMb: number;
}

// An empty or invalid limit (anything but a whole number of MB, at least 1)
// goes back to the default: a bad number is a preference forgotten, never an error.
export function filesOfflineLimit(raw: unknown): number {
  const value = typeof raw === "string" ? raw.trim() : raw;
  const n = typeof value === "number" || (typeof value === "string" && value !== "") ? Number(value) : NaN;
  return Number.isInteger(n) && n >= 1 ? n : FILES_OFFLINE_DEFAULT_MB;
}

export function filesOfflinePrefs(): FilesOffline {
  const raw = loadPrefs(FILES_OFFLINE_KEY);
  const mode = (FILES_OFFLINE_MODES as readonly string[]).indexOf(raw.mode) !== -1 ? raw.mode : "kept";
  return { mode, limitMb: filesOfflineLimit(raw.limitMb) };
}

export function saveFilesOffline(config: FilesOffline): FilesOffline {
  const wanted: FilesOffline = {
    mode: (FILES_OFFLINE_MODES as readonly string[]).indexOf(config.mode) !== -1 ? config.mode : "kept",
    limitMb: filesOfflineLimit(config.limitMb),
  };
  savePrefs(FILES_OFFLINE_KEY, wanted);
  return wanted;
}

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
