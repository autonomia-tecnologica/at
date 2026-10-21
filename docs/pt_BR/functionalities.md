# Funcionalidades

Uma funcionalidade é o que o [glossário](glossary.md) define: uma capacidade que a pessoa reconhece, com níveis e dependências. A regra que a governa é a do §3 (A postura de segurança). Este documento não repete nenhuma das duas — carrega o que é de cada funcionalidade: os níveis, o que cada nível custa, e o que ela arrasta.

## O que existe hoje

O piso é `S`. Toda funcionalidade nasce nele, e o que o derruba é sempre uma escolha. As funções graduadas que o fundador nomeia estão todas em `S` hoje, e escrever isso é o que impede a primeira letra de parecer arbitrária. **A exposição é a função cuja nota é o do que a pessoa configurou** — o alcance e o portão —, e por isso ela é a primeira a poder sair de `S` sem que nada no produto tenha mudado — [Exposição](#exposição).

## Notificações push

A primeira funcionalidade com mais de um jeito de ser usada. O serviço é o `notifier`, e hoje quem o cumpre é o Web Push do próprio PWA (§7f): o service worker do PWA se inscreve no push service do navegador, e o sistema operacional desenha o aviso — não há app à parte nem conta de notificador.

**Os níveis, e o que cada um custa:**

| nível | o que ele é | nota |
|---|---|---|
| desligada | o navegador não se inscreveu, e não há notificação nenhuma | `S` |
| inscrita | o PWA se inscreveu no push service, e o AT guarda a inscrição | `S` |

**O que ela arrasta.** A notificação arrasta a permissão do navegador, que a pessoa concede na própria página; e arrasta o push service do navegador de pé, que é de terceiro e o AT não controla — por isso a entrega é de melhor esforço (§7f). **O token de notificador que esta seção graduava morreu com o ntfy**: não há credencial a estreitar nem segundo fator a exigir sobre ela.

## Exposição

A função que mede quem chega. Ela não olha o caminho, e sim duas coisas: o **alcance** — quem alcança o AT — e o **portão** — o que espera quem chega. O caminho hospedado e o caminho container não têm nota própria: cada um recebe a nota do que estiver configurado nele, e é por isso que o mesmo AT no laço local é `S` nos dois, e o mesmo AT atrás do Caddy sem portão é `A` nos dois — [A postura de segurança](rules.md#a-postura-de-segurança).

**Os níveis, e o que cada um custa:**

| nível | o que ele é | nota |
|---|---|---|
| laço local | `127.0.0.1`, e nada sai dali | `S` |
| rede privada com portão (container) | a rede do ambiente, Authelia na frente, containers isolados (§7b) | `S` |
| rede privada com portão (bundle, sem container) | TLS do Caddy, Authelia vendorizado no mesmo binário, sem isolamento por container | `A` |
| rede privada sem portão | fora do laço, TLS do Caddy e Forms, sem segundo fator | `A` |
| rede pública | alcançável de fora da rede privada | `F` |

**O que ela arrasta.** A exposição arrasta a **declaração** da pessoa: o AT mede o que está configurado e o que foi declarado, e não mede NAT, VPN nem firewall — quem afirma que a rede é privada é a pessoa, e o AT registra isso. Ela arrasta também a **distinção entre o caminho e a configuração**: o que segura o bundle em `A` e não em `S` é a falta de isolamento por container, não a falta de portão ([Caminho hospedado](paths.md#caminho-hospedado)). E **instalar não move a nota**: pacote do SO, binário solto com `at-cli install` ou shim do Windows mudam como o binário chega, não quem o alcança.
