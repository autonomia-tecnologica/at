# Funcionalidades

Uma funcionalidade é o que o [glossário](glossary.md) define: uma capacidade que a pessoa reconhece, com níveis e dependências. A regra que a governa é a do §3 (A postura de segurança). Este documento não repete nenhuma das duas — carrega o que é de cada funcionalidade: os níveis, o que cada nível custa, e o que ela arrasta.

## O que existe hoje

O piso é `S`. Toda funcionalidade nasce nele, e o que o derruba é sempre uma escolha. As funções graduadas que o fundador nomeia estão todas em `S` hoje, e escrever isso é o que impede a primeira letra de parecer arbitrária.

## Notificações push

A primeira funcionalidade com mais de um jeito de ser usada. O serviço é o `notifier`, e hoje quem o cumpre é o `ntfy` (§7f).

**Os níveis, e o que cada um custa:**

| nível | o que ele é | nota |
|---|---|---|
| desligada | nada é instalado, e não há notificação nenhuma | `S` |
| instalado | o container do `ntfy` existe e roda | `S` |
| como serviço | o Bill o tem configurado | `S` |
| token só de leitura | o token só lê | `S` |
| token de leitura e escrita, sem segundo fator | o token lê e escreve, e nada além dele confirma quem o usa | `A` |
| idem, com o serviço de token (TOTP) | o segundo fator fecha o token | `S` |

**O que ela arrasta.** A notificação arrasta instalar o `ntfy`; instalar arrasta tê-lo como serviço configurado, porque instalado e não configurado não notifica ninguém; e o token aberto arrasta habilitar o serviço de token (TOTP).
