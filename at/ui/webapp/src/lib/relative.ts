// relative — o caminho RELATIVO que o markdown escreve, e as portas que ele vira.
//
// A REGRA, e ela é uma só: um `![](...)` ou um `[...](...)` que não tem
// esquema é RELATIVO ao arquivo que o escreve — como em qualquer markdown, e
// como quem escreve espera. A base é a PASTA do arquivo, e o caminho que sai
// daqui é o caminho DENTRO de `Arquivos/`, que é o que o servidor entende.
//
// AS DUAS PORTAS que o relativo vira: os BYTES de uma imagem
// (`/api/file/bytes?path=`) e o ENDEREÇO de um arquivo no AT (`/file/...`).
// Nenhuma das duas é inventada aqui — são as que o servidor já atende, e o
// que muda é o NOME que a pessoa escreve, não a porta por onde o byte passa.
//
// NADA É INVENTADO NEM ADIVINHADO: um caminho que sai da base (`../` demais)
// não vira caminho nenhum, e é o SERVIDOR quem decide o que existe em disco
// (`prose.inside`, que recusa o mesmo `..`). Este módulo só diz para onde o
// nome aponta — e um nome que não aponta para lugar nenhum sai sem atributo.

const SCHEME = /^([a-z][a-z0-9+.-]*):/i;

// O ENDEREÇO de um arquivo no AT — o mesmo que `views.addressOf` dá para a
// view `file:`. A fórmula mora aqui para as duas não derivarem uma da outra.
export const FILE_DOOR = "/file/";

// A PORTA DOS BYTES de um arquivo de `Arquivos/` — a mesma que a página já
// usa para uma imagem e que o download usa para levar o arquivo à máquina.
export function bytesDoor(path: string): string {
  return "/api/file/bytes?path=" + encodeURIComponent(path);
}

// O ENDEREÇO de um arquivo no AT: `/file/<caminho>`, com cada pedaço do
// caminho codificado — um nome com espaço é um nome, não uma palavra.
export function fileDoor(path: string): string {
  return FILE_DOOR + path.split("/").map(encodeURIComponent).join("/");
}

// O CAMINHO que um endereço nomeia, ou null quando o endereço não é de um
// arquivo do AT. É o caminho CRU (sem a codificação) — o que o servidor
// entende.
//
// O MESMO CAMINHO QUE O SERVIDOR ACEITA (`prose.inside`, `at/prose/listing.py`):
// o `fileOf` não pode prometer um caminho que o `inside` recusa, ou os dois
// discordariam sobre o que é um caminho — e duas regras que derivam uma da
// outra derivam uma divergência. Um caminho vazio, um absoluto e um `..`
// (mesmo escondido atrás de um `%2F`) não são caminho nenhum.
export function fileOf(address: string): string | null {
  if (!address.startsWith(FILE_DOOR)) return null;
  let path: string;
  try {
    path = decodeURIComponent(address.slice(FILE_DOOR.length));
  } catch {
    return null;
  }
  if (!path || path.startsWith("/") || path.includes("\\")) return null;
  const parts = path.split("/").filter(part => part !== "" && part !== ".");
  if (!parts.length) return null;
  if (parts.some(part => part === ".." || part.startsWith("."))) return null;
  return path;
}

// O que um `href` ou um `src` é, antes de qualquer resolução.
export type Relative =
  | { readonly kind: "relative" }  // um caminho dentro de `Arquivos/`
  | { readonly kind: "external" }  // http, mailto: — a porta é de outra
  | { readonly kind: "anchor" };   // `#seção` — dentro do próprio arquivo

// A CLASSIFICAÇÃO, e ela é o que decide o que se faz com o atributo: um
// caminho relativo se resolve contra a pasta do arquivo; um link de fora não
// é nosso; uma âncora é do próprio texto.
export function classify(ref: string): Relative {
  if (!ref) return { kind: "external" };
  if (ref.startsWith("#")) return { kind: "anchor" };
  if (ref.startsWith("/")) return { kind: "external" };
  if (SCHEME.test(ref)) return { kind: "external" };
  return { kind: "relative" };
}

// A PASTA de um caminho — a base contra a qual o relativo se resolve.
export function dirOf(path: string): string {
  const at = path.lastIndexOf("/");
  return at < 0 ? "" : path.slice(0, at);
}

// O QUE UM NOME APONTA, resolvido contra a base. `null` quando o nome não
// aponta para lugar nenhum — o que saiu da base, e o que não é caminho.
export interface Resolved {
  readonly path: string;     // o caminho dentro de `Arquivos/`
  readonly query: string;    // o que vier depois de "?"
  readonly fragment: string; // o que vier depois de "#"
}

export function resolve(baseDir: string, ref: string): Resolved | null {
  if (classify(ref).kind !== "relative") return null;
  let rest = ref;
  let fragment = "";
  let query = "";
  const hash = rest.indexOf("#");
  if (hash >= 0) {
    fragment = rest.slice(hash);
    rest = rest.slice(0, hash);
  }
  const mark = rest.indexOf("?");
  if (mark >= 0) {
    query = rest.slice(mark);
    rest = rest.slice(0, mark);
  }
  const out = baseDir.split("/").filter(Boolean);
  for (const piece of rest.split("/")) {
    if (!piece || piece === ".") continue;
    const segment = decodeSegment(piece);
    // UM NOME QUE SE ESCONDE ATRÁS DE UM "%2F" É UM NOME QUE QUER PASSAR POR
    // OUTRO: um caminho tem "/" dentro dele ou não tem — e este tem.
    if (segment === null) return null;
    if (segment === "..") {
      // O QUE SAI DA BASE NÃO VIRA CAMINHO NENHUM. É o servidor quem recusa
      // o resto, mas um nome que nem aponta para dentro da base não chega lá.
      if (!out.length) return null;
      out.pop();
      continue;
    }
    out.push(segment);
  }
  if (!out.length) return null;
  return { path: out.join("/"), query, fragment };
}

// UM NOME DECODIFICADO, ou null quando o nome não é um nome — um "%" sozinho
// é o nome que a pessoa deu, e não há o que decodificar nele.
function decodeSegment(piece: string): string | null {
  let decoded: string;
  try {
    decoded = decodeURIComponent(piece);
  } catch {
    return piece;
  }
  if (decoded.includes("/")) return null;
  return decoded;
}

// O QUE UM ATRIBUTO VIRA, depois da resolução: `keep` (não é nosso e fica
// como está), `set` (o novo valor) e `drop` (era um caminho e não aponta para
// lugar nenhum — o atributo sai, e um link sem destino não é link).
export type Rewrite =
  | { readonly kind: "keep" }
  | { readonly kind: "set"; readonly value: string }
  | { readonly kind: "drop" };

// O `src` de uma imagem: o caminho virado na PORTA DOS BYTES.
export function rewriteSrc(src: string, baseDir: string): Rewrite {
  if (classify(src).kind !== "relative") return { kind: "keep" };
  const found = resolve(baseDir, src);
  if (!found) return { kind: "drop" };
  return { kind: "set", value: bytesDoor(found.path) };
}

// O `href` de um link: o caminho virado no ENDEREÇO DO ARQUIVO.
export function rewriteHref(href: string, baseDir: string): Rewrite {
  if (classify(href).kind !== "relative") return { kind: "keep" };
  const found = resolve(baseDir, href);
  if (!found) return { kind: "drop" };
  return { kind: "set", value: fileDoor(found.path) + found.query + found.fragment };
}
