"""A CA do AT no cofre que o navegador desta máquina lê — o NSS (item 49).

O certificado da borda é de uma CA local (`tls internal`), e quem confia nele
tem de ser apresentado à CA. O §7a já a entrega pelo NOME — `cert.at.local`,
servido pela própria borda —, e isso resolve o aparelho que não lê o disco desta
máquina: o celular, o navegador de outro computador. **O navegador DESTA máquina
é outro problema**, e é este arquivo. O Firefox não lê o cofre do sistema: tem o
NSS dele, um por perfil (`cert9.db` dentro de cada um). O Chromium lê o
`~/.pki/nssdb`. Os dois bancos são arquivos da PRÓPRIA pessoa, e é por isso que
esta palavra não pede elevação nenhuma (§3, Permissão de acesso).

**Quem escreve no NSS é o `certutil`.** É o mesmo programa que o navegador usa
por baixo, vem do pacote `nss` do sistema, e é o único jeito de pôr um
certificado nesses bancos sem abrir a tela do navegador. Onde ele não existe, o
AT não instala nada: as duas saídas são as da pessoa — instalar o pacote e rodar
de novo, ou importar a CA à mão pela tela de certificados, que já está ao alcance
em `cert.at.local` —, e é a mesma forma que o Podman segue (§7a). Uma diferença,
e ela é do desenho: aqui não se PERGUNTA. A pergunta do Podman decide um caminho
(a pasta fica hospedada ou vai ao container) e por isso muda o que o AT faz; aqui
as duas saídas acabam no mesmo lugar — o AT não instala nada —, e o que a pessoa
precisa é das duas estradas ditas, não de uma escolha que não muda nada.

**O cofre DO SISTEMA fica de fora, e é uma decisão medida.** Ele seria a SEGUNDA
entrada da lista fechada de elevação do §3 — a primeira é a porta baixa do
`dnsmasq` —, e não compraria a promessa desta palavra: o Firefox não o lê de todo
modo (o NSS dele é por perfil), e o Chromium desta máquina usa o `~/.pki/nssdb`,
que é da pessoa. §3 pede o MAIS ESTREITO que funciona, e o mais estreito aqui é
não pedir nada. O que a palavra promete é o cofre que o navegador DESTA máquina
lê, e é exatamente o que ela cobre.

**Ela desinstala também, e por uma razão de auditoria**: um cofre que só cresce é
um cofre que ninguém audita. A CA entra com um apelido fixo (`NICKNAME`), e é por
ele que a saída a encontra — a mesma palavra que a pôs a tira. O que o apelido
NÃO é: o CN do certificado. O CN é do Caddy e muda quando a autoridade nasce de
novo; o apelido é o que a pessoa lê na lista de certificados e o que o
`uninstall` apaga.

**O `certutil` é chamado por um seam só** (`run`), como o Podman: o banco de cada
cofre, o apelido, a confiança e o caminho do certificado são ARGUMENTOS, e é aí
que as decisões ficam legíveis — e prováveis numa máquina sem `certutil` nenhum.

**O primeiro acesso do navegador ainda pede o clique no aviso**, e isso é
inerente a quem não tem uma CA pública: é TLS sem CA confiada. O que a palavra
entrega é o aviso sumir DEPOIS disso, e a CA chegar ao cofre sem cabo e sem
`scp` — a outra metade do que a fatia 1 abriu.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from at.i18n import tr
from at.services import caddy

from at_deploy import environment

# Os alvos, e eles são os COFRES e não as marcas: o nome diz qual banco o
# navegador lê, e é por ele que a pessoa pede. O cofre do sistema não está aqui,
# e o docstring do módulo diz por quê.
FIREFOX = "firefox"
CHROMIUM = "chromium"
TARGETS = (FIREFOX, CHROMIUM)

# Os dois atos, e a `cli` os lê da ÁRVORE (`tree.py` os oferece com estes nomes):
# a declaração é uma só, e um ato que não é oferecido não pode despachar (§5).
INSTALL = "install"
UNINSTALL = "uninstall"
ACTS = (INSTALL, UNINSTALL)

# O banco NSS moderno, e o único que esta palavra procura: o SQLite, que o
# Firefox usa desde a v58 e o Chromium sempre usou. Um diretório sem ele não é um
# cofre — é um perfil que o navegador nunca abriu —, e tratá-lo como cofre seria
# anunciar uma instalação que ninguém lê. O `cert8.db`, o banco antigo, fica de
# fora pela mesma razão: um navegador que ainda o use não é um que a pessoa
# alcança hoje, e cobri-lo seria carregar um formato morto.
DB = "cert9.db"

# Onde os cofres moram, relativos ao lar de quem navega. São dois caminhos e não
# uma busca: é onde o Firefox e o Chromium os põem, e uma varredura pelo disco
# inteiro acharia bancos de outra coisa.
FIREFOX_HOME = (".mozilla", "firefox")
CHROMIUM_HOME = (".pki", "nssdb")

# O binário que escreve no NSS, e o único que AT conhece.
BINARY = "certutil"

# O apelido da CA no cofre, e o que a saída procura para tirá-la (o docstring do
# módulo diz por que ele não é o CN do certificado).
NICKNAME = "AT local CA"

# A confiança que a CA recebe: `C` no SSL — "confie nesta CA para identificar
# sites" —, e o resto em branco, porque ela não assina e-mail nem código.
TRUST = "C,,"

# Os desfechos. Os dois primeiros são os atos fechados, e a `cli` os transforma
# no código de saída; os outros são as razões de não ter fechado, cada uma dita
# com a sua própria frase.
INSTALLED = "installed"       # a CA foi posta em todo cofre que o alvo pediu
REMOVED = "removed"           # a CA saiu de todo cofre que o alvo pediu
NO_AUTHORITY = "no_authority"  # a CA do AT ainda não existe na pasta
NO_CERTUTIL = "no_certutil"   # quem escreve no NSS não está nesta máquina
NO_STORE = "no_store"         # nenhum cofre do navegador foi encontrado
FAILED = "failed"             # o certutil recusou um dos cofres

# E o desfecho de UM cofre na saída, que não é um desfecho do ato: a CA não
# estava lá, e o cofre terminou como a pessoa pediu. Ele não entra na lista
# acima porque não há código de saída para ele — só há uma frase por cofre.
ABSENT = "absent"


# ------------------------------------------------------------- os cofres ---

def home() -> Path:
    """O lar de quem navega — onde os dois bancos moram.

    É uma função e não `Path.home()` espalhado porque a suíte precisa de um lar
    de mentira: um teste que escrevesse no NSS de verdade do usuário que roda a
    suíte instalaria uma CA na máquina de quem a roda, que é exatamente o que
    nenhum teste pode fazer.
    """
    return Path.home()


def firefox_home() -> Path:
    """`~/.mozilla/firefox` — a pasta onde o Firefox põe os perfis."""
    return home().joinpath(*FIREFOX_HOME)


def chromium_home() -> Path:
    """`~/.pki/nssdb` — o banco que o Chromium e o Chrome leem no Linux."""
    return home().joinpath(*CHROMIUM_HOME)


def _holding(base: Path) -> tuple[Path, ...]:
    """Os perfis de uma pasta que TÊM o banco NSS, em ordem.

    A ordem é a da pasta e não a de escrita: o que se lê no relatório é uma lista
    de caminhos, e dois relatórios da mesma máquina têm de sair iguais.
    """
    try:
        found = base.iterdir()
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return ()
    return tuple(sorted(entry for entry in found
                        if entry.is_dir() and (entry / DB).is_file()))


def firefox_stores() -> tuple[Path, ...]:
    """Um cofre por PERFIL do Firefox — o NSS dele não é um só.

    É a medida que faz esta palavra existir: uma CA posta no cofre do sistema não
    chega ao Firefox, porque cada perfil tem o banco dele.
    """
    return _holding(firefox_home())


def chromium_stores() -> tuple[Path, ...]:
    """O `~/.pki/nssdb`, quando ele existe — um só, compartilhado pelos perfis."""
    where = chromium_home()
    return (where,) if (where / DB).is_file() else ()


def stores(target: str) -> tuple[Path, ...]:
    """Os cofres daquele alvo, nesta máquina. Alvo desconhecido não tem nenhum."""
    if target == FIREFOX:
        return firefox_stores()
    if target == CHROMIUM:
        return chromium_stores()
    return ()


def delivery() -> str:
    """O endereço onde a CA está ao alcance — `https://cert.at.local` (§7a).

    É a estrada da mão, e por isso ela aparece na frase de quem não tem
    `certutil`: quem não pode instalar pelo AT leva a CA pelo nome que a fatia 1
    pôs de pé, e o navegador a importa pela própria tela.
    """
    return caddy.address(environment.cert_host(), environment.PORT)


# ----------------------------------------------------------- o certutil ---

def found() -> str | None:
    """Onde o `certutil` está, ou `None` — a pergunta que decide tudo.

    Um caminho e não um booleano, pela mesma razão que `podman.found`: o que a
    pessoa lê é QUAL programa foi encontrado, e `which` é a mesma pergunta que o
    shell responde.
    """
    return shutil.which(BINARY)


def run(args: Sequence[str]) -> subprocess.CompletedProcess:
    """Uma chamada ao `certutil` — o seam, e a única.

    O binário é resolvido AQUI e nunca pelo chamador, para que nada fora desta
    função tenha de saber onde ele está, ou que existe. A saída é capturada
    porque quem fala com a pessoa é o AT, nas palavras dele (§3): o texto do
    programa é de quem está diagnosticando, e ele sai onde a pessoa pediu, não
    passado adiante.

    O `stderr` capturado tem um efeito que vale dizer: um banco com senha mestre
    faria o `certutil` perguntar, e a pergunta sai no terminal da pessoa, não no
    relatório. Não há o que AT faça por ela — a senha é dela.
    """
    return subprocess.run(  # noqa: S603 — o binário do sistema, resolvido acima
        [found() or BINARY, *(str(part) for part in args)],
        capture_output=True,
        text=True,
    )


def _db(store: Path) -> list[str]:
    """O argumento que diz QUAL banco — o SQLite do `cert9.db`."""
    return ["-d", f"sql:{store}"]


def _has(store: Path) -> bool:
    """Se a CA do AT já está naquele cofre.

    É o que separa "tirei" de "não estava lá" na saída: as duas terminam com o
    cofre sem a CA, e só uma delas é uma remoção. E é a pergunta que NÃO é feita
    na entrada — ver `_add`.
    """
    return run([*_db(store), "-L", "-n", NICKNAME]).returncode == 0


def _add(store: Path, cert: Path) -> bool:
    """Põe a CA naquele cofre — limpando o apelido antes.

    **A limpeza primeiro é o que torna a instalação a mesma de novo**, e ela é
    deliberada: uma autoridade que nasceu de novo tem outro certificado, e um
    apelido que já está lá faria o `-A` recusar — deixando o cofre confiando numa
    CA cuja chave ninguém mais tem. Apagar o apelido antes de escrever faz o
    cofre acabar com a CA CERTA, e não com a primeira que ele viu. Um apelido que
    não existe faz o `-D` recusar, e isso é esperado: não há erro a contar.
    """
    run([*_db(store), "-D", "-n", NICKNAME])
    added = run([*_db(store), "-A", "-n", NICKNAME, "-t", TRUST, "-i", str(cert)])
    return added.returncode == 0


def _remove(store: Path) -> str:
    """Tira a CA daquele cofre: `REMOVED`, `ABSENT` ou `FAILED`."""
    if not _has(store):
        return ABSENT
    return REMOVED if run([*_db(store), "-D", "-n", NICKNAME]).returncode == 0 \
        else FAILED


# ------------------------------------------------------------- os atos ---

def _listed(targets: Sequence[str]) -> str:
    return ", ".join(targets)


def _act(act: str, targets: Sequence[str]) -> str:
    """O corpo dos dois atos — as perguntas na ordem em que elas decidem.

    A CA vem primeiro porque sem ela não há o que pôr; o `certutil` depois,
    porque é ele quem decide se o AT consegue falar com os cofres; e os cofres
    por último, porque é a resposta que só faz sentido depois das duas. Uma
    pergunta respondida fora de ordem diria à pessoa que não há cofre numa
    máquina onde o que falta é o programa.
    """
    cert = environment.authority_file()
    if act == INSTALL and not cert.is_file():
        print(tr("services.ca.no_authority", where=cert))
        return NO_AUTHORITY
    if found() is None:
        print(tr("services.ca.no_certutil"))
        print(tr("services.ca.by_hand", url=delivery(), where=cert))
        return NO_CERTUTIL

    chosen = tuple(targets) or TARGETS
    pairs = tuple((target, store) for target in chosen for store in stores(target))
    if not pairs:
        print(tr("services.ca.no_store", targets=_listed(chosen),
                 firefox=firefox_home(), chromium=chromium_home()))
        return NO_STORE

    refused = False
    for target, store in pairs:
        if act == INSTALL:
            if _add(store, cert):
                print(tr("services.ca.installed", target=target, where=store))
            else:
                refused = True
                print(tr("services.ca.failed", target=target, where=store))
            continue
        outcome = _remove(store)
        if outcome == FAILED:
            refused = True
            print(tr("services.ca.failed", target=target, where=store))
        else:
            print(tr(f"services.ca.{outcome}", target=target, where=store))

    if refused:
        # Um cofre que recusou é a palavra não tendo fechado: os outros ficam
        # como ficaram — desfazer o que deu certo seria inventar uma transação
        # que ninguém pediu —, e o código de saída diz que algo não fechou.
        return FAILED
    return INSTALLED if act == INSTALL else REMOVED


def install(targets: Sequence[str] = ()) -> str:
    """Põe a CA do AT nos cofres do navegador — todos os que existem, sem alvo.

    O alvo vazio é o PADRÃO e não um engano: sem ele, a palavra cobre os dois
    bancos que a pessoa tem, que é o que "a CA ao alcance" quer dizer. Nomear um
    alvo a estreita, e é o que quem só quer o Firefox pede.
    """
    return _act(INSTALL, targets)


def uninstall(targets: Sequence[str] = ()) -> str:
    """Tira a CA do AT dos cofres — a volta, e a razão de ela existir.

    Um cofre que só cresce é um cofre que ninguém audita: uma CA que ninguém mais
    usa continua confiando em quem tem a chave dela. A saída é a mesma palavra,
    com o outro ato.
    """
    return _act(UNINSTALL, targets)
