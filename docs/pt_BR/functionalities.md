# Funcionalidades

Uma funcionalidade é o que o [glossário](glossary.md) define: uma capacidade que a pessoa reconhece, com níveis e dependências. A regra que a governa é a do §3 (A postura de segurança). Este documento não repete nenhuma das duas — carrega o que é de cada funcionalidade: os níveis, o que cada nível custa, e o que ela arrasta.

## O que existe hoje

O piso é `S`. Toda funcionalidade nasce nele, e o que o derruba é sempre uma escolha. As funções graduadas que o fundador nomeia estão todas em `S` hoje, e escrever isso é o que impede a primeira letra de parecer arbitrária.

## Notificações push

A primeira funcionalidade com mais de um jeito de ser usada. O serviço é o `notifier`, e hoje quem o cumpre é o Web Push do próprio PWA (§7f): o service worker do PWA se inscreve no push service do navegador, e o sistema operacional desenha o aviso — não há app à parte nem conta de notificador.

**Os níveis, e o que cada um custa:**

| nível | o que ele é | nota |
|---|---|---|
| desligada | o navegador não se inscreveu, e não há notificação nenhuma | `S` |
| inscrita | o PWA se inscreveu no push service, e o AT guarda a inscrição | `S` |

**O que ela arrasta.** A notificação arrasta a permissão do navegador, que a pessoa concede na própria página; e arrasta o push service do navegador de pé, que é de terceiro e o AT não controla — por isso a entrega é de melhor esforço (§7f). **O token de notificador que esta seção graduava morreu com o ntfy**: não há credencial a estreitar nem segundo fator a exigir sobre ela.
