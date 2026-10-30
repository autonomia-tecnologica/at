"""A porta do AT para a notificação — que é o Web Push do navegador.

**O ntfy saiu, e com ele a conta, o tópico e a segunda porta.** O que a
notificação do AT é, desde então, é a do PRÓPRIO PWA: o service worker inscrito
no push service do navegador, e o aviso que o sistema operacional desenha. Quem
fala os dois protocolos é `at.core.push`; este módulo é só o nome que o resto do
produto já conhece — o relógio chama `publish`, a página chama `read`, e nada
aqui guarda credencial nem endereço de rede.

**A assinatura antiga ficou de pé para não arrastar o resto.** `publish(title,
body, key)` e `read(key)` existem com o `key` de antes — o `boot` do WebApp
ainda lê a chave derivada do escopo do notificador (`keys.notifier_key`), e um
processo que nunca a recebeu continua podendo publicar: o Web Push não sela
nada com ela, porque não há envelope entre o AT e o navegador. O parâmetro é
aceito e ignorado, e um dia sai junto com a última chamada que o passe.
"""

from __future__ import annotations

from at.core import push

# O que todo aviso do AT diz de si — o mesmo vocabulário de antes, agora na
# fatia que o navegador desenha.
TITLE = "AT"
TAGS = "bell"

# Os campos que a página desenha de uma notificação (`push.inbox`).
FIELDS = push.FIELDS


def publish(
    title: str,
    body: str,
    key: bytes | None = None,
    data: dict | None = None,
    actions: list[dict] | None = None,
) -> tuple[bool, str]:
    """Manda um aviso a toda inscrição. `(ok, detalhe)`.

    `key` é aceito por compatibilidade e não usado: a cifra do Web Push é
    contra a chave do NAVEGADOR, e não há nada que o AT sele com a chave
    derivada aqui. `data` e `actions` vão como vêm: o primeiro é o que o clique
    carrega consigo e o segundo são os botões que o sistema desenha na
    notificação. `(False, "no_subscribers")` é um aviso que não saiu porque
    ninguém se inscreveu — o lembrete tenta de novo, como sempre.
    """
    return push.send(title, body, urgency="high", data=data, actions=actions)


def read(key: bytes | None = None) -> tuple[list[dict], str]:
    """O que a página lista: as últimas notificações que SAÍRAM.

    **Uma leitura não é um tópico remoto e não pode falhar por rede** — o ntfy
    guardava a mensagem do outro lado, e agora quem guarda é o próprio AT, num
    arquivo da pasta. Por isso `recusa` é sempre vazia: o que existe é o que
    saiu, e não há terceiro a quem perguntar.
    """
    return push.inbox(), ""
