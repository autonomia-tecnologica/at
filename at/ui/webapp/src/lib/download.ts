// download — save a file of the folder to the person's machine, byte a byte.
//
// CTRL+S MEANS "SAVE WHAT IS OPEN ON MY MACHINE", and the whole promise is
// fidelity: what lands in the person's folder is the file on the disk, not a
// re-encoding of it. So the bytes come from the SAME raw read door the page
// already trusts (`/api/file/bytes`, `prose.inside`) and leave through an
// `<a download>` — the browser fetches them and writes them whole. Nothing
// here decodes, re-encodes or touches a newline: the file that leaves is the
// file, byte for byte.
export function downloadFile(path: string): void {
  const name = path.split("/").pop() || "arquivo";
  const anchor = document.createElement("a");
  anchor.href = "/api/file/bytes?path=" + encodeURIComponent(path);
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

// Whether a keydown is the save gesture. `Ctrl+S` on every platform, and
// `Cmd+S` where the modifier is Meta — the two spellings of one intent.
export function isSaveGesture(event: KeyboardEvent): boolean {
  return (event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === "s";
}
