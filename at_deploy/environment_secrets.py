"""What AT draws, seals and opens (§4, item 50): the gate's secret, the provider's
three, and the openers the run directory is made with.
"""

from __future__ import annotations

import base64
import secrets
from pathlib import Path

from at.core import files
from at.encryption import vault
from at.services import caddy as caddy_service
from at_deploy.environment_base import CADDY, IDENTITY, IDENTITY_SECRETS, SECRET_BYTES, SealedRefused
from at_deploy.environment_paths import state


def _drawn_files() -> tuple[Path, ...]:
    """Os arquivos que o AT SORTEIA: onde os valores selados moram (item 50).

    O portão do Caddy e os três que o provedor assina, cifra e prova com (§7b):
    os conjuntos são nomeados juntos porque a pergunta que os usa é uma só —
    "há o que selar, ou o que abrir?" —, e ela é feita ANTES de qualquer sorteio.
    """
    return (caddy_service.gate_file(),
            *(state(IDENTITY) / name for name in IDENTITY_SECRETS))


def _text(where: Path) -> str:
    """O texto de um arquivo da pasta, ou vazio quando não há o que ler.

    Ele é tolerante de propósito: quem pergunta é a conferência da Chave Principal, e o
    que ela precisa saber é quais envelopes existem — um arquivo que ainda não
    nasceu não tem nenhum, e não é erro.
    """
    try:
        return where.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        return ""


def _clear(where: Path) -> bool:
    """Se o arquivo existe e guarda um valor EM CLARO — a pasta que nasceu antes do selo.

    É a medida do corte `f` do item 50, e ela não se confunde com a de um
    arquivo ausente: um ausente é um sorteio que vem aí, e um em claro é um
    valor que JÁ viajou. **Um texto sem envelope É o valor** — a mesma regra com
    que quem abre o envelope o lê —, e é por isso que a migração não precisa saber
    o que o valor significa: ele é re-sorteado como qualquer outro, e o que a
    pasta guardava deixa de abrir o que foi copiado dela.
    """
    text = _text(where).strip()
    return bool(text) and not vault.envelopes(text)


def _clear_drawn() -> tuple[Path, ...]:
    """Os arquivos que o AT SORTEIA e que estão em claro na pasta (item 50, corte `f`).

    A lista é a mesma pergunta de `_needs_phrase` feita arquivo a arquivo, e o
    que ela responde é o que a subida vai migrar: **cada um destes é
    re-sorteado e selado**, porque a pasta pode ter sido copiada e o valor que
    já viajou não volta. É isso que separa a migração de um simples selo.
    """
    return tuple(where for where in _drawn_files() if _clear(where))


def _opened(text: str, scope: str, key: bytes | None) -> str:
    """O texto com cada envelope ABERTO — o que o container lê (§4, item 50).

    **Ele é o coração da fatia**: a pasta guarda o envelope, e o diretório de
    execução monta o valor. A Chave Principal já foi conferida contra tudo o que a pasta
    guarda antes de qualquer container subir (`_not_opened`), então um envelope
    que não abre aqui é uma inconsistência — e a resposta para ela é fechada:
    não se monta o que não se abriu (`SealedRefused`).
    """
    found = vault.envelopes(text)
    if not found:
        # O caso comum, e o de uma pasta que nasceu antes do selo: não há o que
        # abrir, e o texto vai como está.
        return text
    if key is None:  # pragma: no cover — `unlock` dá Chave quando há envelope
        raise SealedRefused()
    derived = vault.derived_key(key, scope)
    for envelope in found:
        value = vault.unseal(envelope, derived)
        if value is None:  # pragma: no cover — a Chave Principal já foi conferida
            raise SealedRefused()
        text = text.replace(envelope, value)
    return text


def draw_gate(key: bytes) -> str:
    """Draw the gate's secret, once, and SEAL it — §7b's drawing (§4).

    **It is the deploy's act and it moved here with the rest of §7** (item 27):
    §7b says AT draws a secret per installation, and the installation is the
    environment's, which is the deploy tool's. The FILE it writes is still the
    Caddy's own — `App/services/caddy/gate`, beside the Caddyfile that is its only writer
    — and both artifacts read it: `at-cli` refuses the identity that arrives
    without it, and the WebApp's check is what turns the M2M into a door.

    **O que ele escreve é o ENVELOPE do cofre, e não o valor** (item 50): a
    pasta é copiada sem criptografia, então o que ela guarda de um valor que o
    AT sorteou é o que só a Chave Principal abre. O escopo da chave é o Caddy —
    o valor é dele, o arquivo é dele, e é o `Caddyfile` dele que o carrega —, e
    quem o abre para o container é o `up`, no diretório de execução.

    **A key é obrigatória, e o chamador só a tem quando há o que sortear**: o
    `up` pergunta a Chave Principal exatamente quando um destes arquivos falta
    (`_needs_phrase`), então um sorteio sem Chave seria um valor em claro na
    pasta — o que esta fatia existe para não haver. O que já está lá não é
    sorteado de novo.

    **A secret already drawn and SEALED is not drawn again**, and that is the
    whole of the function: rotating it would take the running Caddy and the
    running WebApp apart — the first would attach a value the second no longer
    takes, and every identity would be refused (`webapp.gate_refused`) until both
    were restarted from the same file. Whoever wants a new secret removes this
    one and brings the environment up again, which is the same act as changing
    it, said out loud.

    **Um portão em CLARO é a única exceção, e é a migração** (item 50, corte
    `f`): a pasta que nasceu antes do selo guarda o valor sem envelope, e
    mantê-lo seria manter o que já pode ter sido copiado. Ele é re-sorteado como
    um que faltasse — a subida reinicia os dois leitores de qualquer modo, e é
    por isso que a rotação aqui não abre a janela que a de cima abre.

    **O que ele responde é o ENVELOPE**, e não o valor: é o que ficou na pasta, e
    é ele que o `Caddyfile` carrega — quem precisa do valor claro é o container,
    e quem o escreve no diretório de execução é o `up` (`_materialize_gate`).

    It is the CALLER that decides when — `up` draws it at installation, which is
    the moment §7b names — because a file written on import would be a secret in
    the folder of whoever never asked for one.
    """
    held = _held(caddy_service.gate_file())
    if held and vault.envelopes(held):
        return held
    drawn = secrets.token_urlsafe(caddy_service.GATE_BYTES)
    envelope = vault.seal(drawn, vault.derived_key(key, CADDY))
    files.atomic_write_text(caddy_service.gate_file(), f"{envelope}\n")
    return envelope


def _drawn(service: str, name: str, key: bytes) -> str:
    """A secret drawn once and SEALED, in the service's own state folder (§4).

    The same rule `draw_gate` follows and for the same reason: a value a service
    signs or proves with has to outlive the container, and one drawn per start
    would take everything it had issued down with it. Whoever wants a new one
    removes the file and brings the environment up again. **Um em CLARO é
    re-sorteado**, pela mesma exceção do `draw_gate`: ele é a pasta que nasceu
    antes do selo (item 50, corte `f`), e o `encryption` que ele redesenha é o
    que torna ilegível o que o provedor cifrou com o antigo.

    **O escopo da chave é o SERVIÇO** (§4: uma por serviço ou finalidade), e os
    três que ele desenha são dele — o provedor os assina, cifra e prova. É por
    isso que o escopo pode ser lido do arquivo depois: quem compõe um texto sabe
    de quem é o valor que está compondo (`_materialize`).
    """
    held = _held(state(service) / name)
    if held and vault.envelopes(held):
        return held
    drawn = secrets.token_urlsafe(SECRET_BYTES)
    envelope = vault.seal(drawn, vault.derived_key(key, service))
    files.atomic_write_text(state(service) / name, f"{envelope}\n")
    return envelope


def _held(where: Path) -> str:
    """O texto que um arquivo da pasta guarda — vazio quando ele não está lá."""
    try:
        return where.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _kept(service: str, name: str) -> str:
    """O que a pasta guarda para aquele valor: o envelope, ou o que já estava lá.

    **Quem SORTEIA é o `up`, antes de qualquer escritor** (`_drawn`), e o
    escritor só LÊ: o selo precisa da chave derivada, e o escritor não a tem —
    `Service.writes` é uma função de nenhum argumento, e o que ela compõe é o
    arquivo com o que a pasta guarda, que é o envelope. Quem o abre para o
    container é o `_materialize`.

    Um valor que não está lá sai vazio, e o serviço que o lê recusa: o `up`
    sorteia antes de escrever, então isto é uma inconsistência e não um estado —
    e a resposta para ela é fechada, como a de todo valor que falta.
    """
    return _held(state(service) / name)


def _derived_b64(key: bytes, scope: str) -> str:
    """A derived key, encoded for the one trip it takes: inside an env var."""
    return base64.urlsafe_b64encode(vault.derived_key(key, scope)).decode("ascii")
