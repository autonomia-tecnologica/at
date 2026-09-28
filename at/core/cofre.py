"""O Cofre: o que entra em `Cofre/` sela sozinho (TASK-154, fatia 1/3).

**A pessoa põe o arquivo em `Cofre/` e não pensa mais nisso.** `Watcher` é o
consumidor do vigia (`at/core/vigia.py`, TASK-152): registrado na pasta, ele
recebe o evento de toda escrita, espera ela PARAR — uma rodada inteira sem
mudar de novo, porque uma escrita ainda em curso não é uma escrita pronta para
selar — e só então troca o arquivo em claro pelo `.enc`.

**A cifra não mora aqui.** Quem cifra é `at/encryption/vault`, como um HSM:
este módulo pede `seal_bytes`/`unseal_bytes` e nunca implementa a primitiva.

**A chave é entregue na subida e mantida em memória — nunca a Frase no
processo.** O mesmo desenho do WebApp e do notificador (§4, item 50,
`at/ui/webapp/keys.py`): o caminho container deriva a chave do escopo
`cofre` a partir da Vault Key de quem sobe o ambiente
(`at_deploy/environment.py:_webapp_env`) e a entrega por variável de
ambiente; o processo a lê uma vez e a guarda — e um `tick` sem chave ainda
varre (o retrato do vigia segue vivo), só não sela nada, porque um arquivo
selado sem chave seria um envelope que este mesmo processo não saberia
reabrir.

**O `.enc` carrega um FINGERPRINT, e é isso que o backup lê.** `seal_bytes`
por si não tem cabeçalho — é só o nonce e o texto cifrado —, então nada
distingue um `.enc` genuíno de um arquivo qualquer com esse nome. O selo
deste módulo prefixa um cabeçalho fixo antes do envelope, e `fingerprinted`
o lê sem abrir nada: é o que deixa o backup (`core/backup.py`) reconhecer o
que é seu sem precisar da chave.
"""

from __future__ import annotations

from pathlib import Path

from at.core import paths, vigia
from at.encryption import vault

# O escopo da chave derivada (§4) — um nome como o de qualquer serviço, e o
# Cofre não guarda catálogo nenhum dele.
SCOPE = "cofre"

# A extensão do que o selo escreve, e o que o distingue do que ainda espera.
SUFFIX = ".enc"

# O cabeçalho que só um `.enc` que ESTE módulo escreveu carrega — não é
# segredo, é assinatura: o backup lê isto para saber se o arquivo é seu sem
# abrir o envelope (`fingerprinted`), e a versão no nome é o que deixa um
# formato futuro conviver com este sem confundir um pelo outro.
FINGERPRINT = b"AT-COFRE-1\n"


def folder() -> Path:
    """`Cofre/` — onde o Watcher vigia, por padrão."""
    return paths.cofre_dir()


def sealed_name(path: Path) -> Path:
    """O nome que `path` ganha depois de selado — ao lado, com `.enc` no fim."""
    return path.with_name(path.name + SUFFIX)


def listed() -> list[str]:
    """Todo `.enc` de `Cofre/`, como caminhos POSIX relativos a ela, em ordem
    de nome (TASK-156) — a mesma forma de `at.prose.listing.listed`.

    **Só o `.enc`.** Um claro ainda esperando o selo não é o que a seção
    mostra: o que ela lista é o que já é do Cofre, e um arquivo em trânsito
    não é.
    """
    base = folder()
    if not base.is_dir():
        return []
    out: list[str] = []
    for entry in sorted(base.rglob("*")):
        if entry.is_file() and entry.suffix == SUFFIX:
            out.append(entry.relative_to(base).as_posix())
    return out


def seal_file(path: Path, key: bytes) -> Path:
    """Sela `path`: escreve o `.enc` com o fingerprint, apaga o claro, devolve
    o caminho do selado.

    A ordem é a que protege o dado: o `.enc` é escrito primeiro e só então o
    claro some — um selo que falhasse no meio do caminho não pode deixar nem
    o arquivo nem o segredo dele perdidos.
    """
    data = path.read_bytes()
    target = sealed_name(path)
    target.write_bytes(FINGERPRINT + vault.seal_bytes(data, key))
    path.unlink()
    return target


def fingerprinted(path: Path) -> bool:
    """Se `path` carrega o fingerprint deste módulo — sem abrir o envelope.

    É a pergunta do backup (`core/backup.py`): um `.enc` sem este cabeçalho —
    um selo que uma escrita deixou pela metade, um arquivo de outra origem —
    não sobe, e isto responde sem precisar da chave para saber.
    """
    try:
        with path.open("rb") as handle:
            return handle.read(len(FINGERPRINT)) == FINGERPRINT
    except OSError:
        return False


def open_file(path: Path, key: bytes) -> bytes | None:
    """O claro que `path` guarda, ou `None` — fingerprint que não bate ou
    chave que não abre são a mesma resposta, como em todo lugar que este
    produto lê um selo (`vault.unseal`)."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if not raw.startswith(FINGERPRINT):
        return None
    return vault.unseal_bytes(raw[len(FINGERPRINT):], key)


class Watcher:
    """O consumidor do vigia: recebe a escrita, espera ela parar, sela.

    Uma instância por pasta — a mesma razão do `Vigia` que ela carrega
    (`vigia.py`): duas pastas vigiadas não têm por que compartilhar um
    estado, e um teste que vigia uma pasta descartável não pode ver o
    retrato de outro.
    """

    def __init__(self, target: Path | None = None) -> None:
        self.folder = target if target is not None else folder()
        self._vigia = vigia.Vigia(self.folder)
        self._vigia.watch(self._noticed)
        self._pending: dict[Path, int] = {}
        self._seed()
        # O retrato do vigia nasce AGORA, e não no primeiro `tick`: a primeira
        # varredura dele é sempre muda (§ `Vigia`), e se ela ficasse para o
        # primeiro `tick` um arquivo escrito ENTRE o nascimento deste Watcher
        # e essa chamada entraria nela sem disparar `_noticed` — a mesma
        # supressão que existe para não inundar o Watcher de arquivos que já
        # estavam aqui (e que `_seed` já cobriu, por fora do vigia).
        self._vigia.scan()

    def _seed(self) -> None:
        """O que já estava na pasta antes deste `Watcher` nascer entra na
        fila também — "largar o arquivo e não pensar mais nisso" não pode
        depender de o WebApp já estar de pé no instante exato da escrita."""
        if not self.folder.is_dir():
            return
        for item in self.folder.rglob("*"):
            if item.is_file() and item.suffix != SUFFIX:
                try:
                    self._pending[item] = item.stat().st_mtime_ns
                except OSError:
                    continue

    def _noticed(self, event: vigia.Event) -> None:
        """O vigia despachou uma escrita — um `.enc` não é dele (já é selo,
        não pede selo), e qualquer outro arquivo entra ou reinicia a espera."""
        if event.path.suffix == SUFFIX:
            return
        try:
            self._pending[event.path] = event.path.stat().st_mtime_ns
        except OSError:
            self._pending.pop(event.path, None)

    def tick(self, key: bytes | None) -> tuple[Path, ...]:
        """Uma rodada: varre, e sela o que ficou PARADO por uma rodada inteira.

        `candidates` é o que já esperava ANTES desta varredura. O que a
        varredura acabou de acrescentar ou tocar de novo (`_noticed`) espera
        mais uma rodada — uma escrita vista há um instante pode não ter
        parado —, e é por isso que a comparação é contra o retrato de ANTES
        e não contra o disco de agora.
        """
        candidates = dict(self._pending)
        self._vigia.scan()
        settled: list[Path] = []
        for path, seen in candidates.items():
            if self._pending.get(path) != seen:
                continue
            if key is None:
                # Parado, mas sem chave nesta subida: fica na fila para a
                # próxima rodada tentar de novo — nada se perde por a Frase
                # não ter sido lida ainda neste boot.
                continue
            del self._pending[path]
            if not path.is_file():
                continue
            settled.append(seal_file(path, key))
        return tuple(settled)
