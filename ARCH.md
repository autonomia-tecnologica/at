# Arquitetura

Camadas, direção das dependências e dono de cada efeito deste repositório. O `HARNESS.md` instalado
vence em segurança e isolamento. O contrato de produto está em `docs/pt_BR/architecture.md` (§4); este
arquivo é o mapa do código que o cumpre.

Onde código e este documento discordarem, vale o que está aqui: ou o código se corrige, ou a
divergência entra em `## Dívidas conhecidas`, com o motivo.

## Camadas

| camada | pasta/arquivos | responsabilidade | proibido |
|---|---|---|---|
| Base | `at/core/paths.py`, `at/core/files.py`, `at/core/clock.py` | único dono da resolução de caminho e da escrita atômica; relógio | importar qualquer outro módulo de `at/` (salvo `i18n` local em `paths`) |
| Cofre | `at/encryption/` | Chave Principal, chaves derivadas, libsodium, hash de senha | importar `core`, `data`, `ui`, `services` |
| Dados e texto | `at/data/`, `at/prose/`, `at/i18n/`, `at/convert/` | tabelas `.jsonl` e esquema; arquivos não estruturados; texto por idioma; conversão de formato | importar `ui`, `services`, `nlu`; importar do `core` além de `paths`/`files` (e `data`, no caso de `prose`) |
| Núcleo | `at/core/` (o resto: tabelas, permissões, atores, auditoria, jobs, migração, versionamento, backup, boot, instalação, busca, extensões) | toda regra da aplicação; valida e escreve; nenhuma outra camada resolve caminho nem decide permissão | importar `ui` ou `at_deploy` |
| Interpretação | `at/nlu/` | frase → **proposta** de ação, e nada mais | escrever; decidir; ter teto próprio |
| Serviços | `at/services/` | ferramenta externa por serviço canônico (`authelia`, `caddy`, `gitleaks`, `spelling-checker`); estado em `App/services/<serviço>` | importar `ui`; conter serviço fora do conjunto fechado do §7 |
| Superfícies | `at/ui/cli/`, `at/ui/webapp/`, `at/ui/ask_*.py`, `at/ui/words.py` | cli, WebApp e frases do `ask`; só formas de falar com o `core` | resolver caminho; decidir permissão; escrever tabela por fora do `core` |
| Operação | `at_deploy/` | instalação do ambiente: podman, systemd, VPN, borda, assistente | ser importado por `at/`; cifrar por fora de `at.encryption` |
| Release | `release/` | build, SBOM, piso de versões, binários do release | ser importado por `at/` ou `at_deploy/`; virar dependência de runtime |
| Freios | `at/tests/`, `at_deploy/tests/` | provas executáveis | ser importados por código de produção |

## Direção de dependência

`A → B` significa "A pode importar B". De cima para baixo:

`ui` → `nlu`, `services` → `core` → `data`/`prose`/`i18n`/`convert` → base (`paths`, `files`) ;
`encryption` é folha ; `at_deploy` → `at` (nunca o inverso) ; `release` → `at.services`.

Permitido:

- cada camada importa a de baixo e a própria;
- `ui.cli` importa `ui.webapp` só localmente (`webapp`, `serve`), com o motivo no ponto de import;
- `at_deploy` importa `at.core`, `at.i18n`, `at.encryption`, `at.services` e as palavras de
  `at.ui.words`; qualquer outro `at.ui` é dívida (abaixo).

Proibido:

- `at/` importar `at_deploy` ou `release` (freio: `at_deploy/tests/test_boundary.py`);
- `at/services` importar `at.ui`;
- `data`, `i18n`, `convert` importarem do `core` mais que `paths` e `files`;
- ciclo entre camadas fora das dívidas nomeadas; ciclo dentro de uma camada sem import local e motivo;
- `at/ui` importar `at_deploy`; código de produção importar `tests`.

## Dono único por efeito

| efeito | dono | como pedir |
|---|---|---|
| resolução de caminho da Pasta de Trabalho | `at/core/paths.py` | `paths.*`; ninguém monta caminho por conta própria |
| escrita de arquivo | `at/core/files.py` (`atomic_write_text/bytes`), tabelas por `at/data/store.py`, prosa por `at/prose/` | chamar a porta; escrita crua só nas dívidas nomeadas |
| decisão de permissão e teto de risco | `at/core/permissions_*`, `at/core/risk.py`, `at/core/gate.py` | a superfície encaminha; não decide |
| auditoria | `at/core/audit.py` | toda ação que muda estado passa por ela |
| cifra e segredo | `at/encryption/` + tabela `secret` | uma só porta: Chave Principal e o que dela deriva |
| texto ao usuário | `at/i18n` | `tr("chave", ...)`; texto não nasce no código |
| versionamento da pasta (`git`) | `at/core/versioning.py` | única costura com o `git` |
| processo externo de serviço | `at/services/<serviço>.py` | o `core` pede ao serviço pelo nome canônico |
| `podman`, `systemctl`, `sudo` | `at_deploy/podman.py`, `at_deploy/systemd.py`, `at_deploy/environment.py` | só no deploy; o app não eleva |
| migração de forma da pasta | `at/core/migrations_*` | declarar a migração; ninguém renomeia pasta de instância |

## Idioma e contratos

- Código em inglês: identificadores, comentários, docstrings.
- Texto ao usuário por `i18n`, pt_BR como idioma principal e `en_US` na trilha dos documentos; rótulos
  de esquema e de permissão são chaves, nunca o texto final.
- Este `ARCH.md` é em pt-BR, como o `BACKLOG.md`.
- Contratos externos continuam strings: nomes de tabela (singular), permissões `objeto:ação`, estados
  de `job`, campo `tipo` do `actor`.

## Dívidas conhecidas

| dívida | motivo | direção da correção |
|---|---|---|
| `at/services/authelia.py:330` importa `at.ui.webapp.look` (local) | o serviço pega a aparência do portal no WebApp | mover o que o portal precisa para `at/core` ou para os dados do serviço; `services` sem `ui` |
| `core` ↔ `nlu`: `core/assist.py`, `jev.py`, `actions_audit.py` importam `nlu`; `nlu/__init__.py:92` importa `core.assist` (local) | `assist` e o `jev` nasceram no `core` e usam o interpretador | `nlu` só devolve proposta; mover o ponto de encontro (`assist`) para `nlu` ou para a superfície |
| `core/scanner.py:95` importa `services.gitleaks` | resolver o binário do gitleaks | o `core` pedir ao serviço por nome, via registro, sem import direto |
| `core/search.py:31` importa `prose.listing`; `prose` importa `core` | a busca lê a prosa | busca declara o que lê; `prose` expõe só a listagem |
| `core` ↔ `data`, `core` ↔ `i18n`: o pacote de baixo importa `core.paths`/`files` | `paths` e `files` moram no `core` por história | extrair `paths`, `files`, `clock` para um pacote base e fechar o ciclo |
| `at_deploy` importa `at.ui.words`, `at.ui.webapp.keys` e `at.ui.webapp.app` (`environment.py:109`, `tree.py:13`, `environment_webapp.py:10`, `host.py:55`) | o deploy reaproveita palavras e chaves do WebApp | mover o que é compartilhado para `core`; o deploy só importa `core`/`i18n`/`encryption`/`services` |
| escrita crua fora de `files`: `core/boot.py:154`, `hooks.py:100`, `extensions.py:183`, `backup.py:151,188,365`, `strongbox.py:146`, `install.py:162`, `migrations_folders.py`, `migrations_later.py`, `i18n/__init__.py:94` | cada uma tem formato próprio (binário selado, link, rename de migração) | passar por `files.atomic_*` ou declarar a exceção com motivo no código e no teste |
| extração de binário com `os.replace` em `services/authelia.py:184`, `caddy.py:225`, `gitleaks.py:200`, `spelling_checker.py:141` | cada serviço baixa a própria ferramenta | uma porta única de extração em `services` |
| `subprocess` fora de `services`/`at_deploy`: `core/versioning.py` (`git`), `core/scanner.py`, `core/backup.py` (`rclone`), `ui/webapp/local.py` (Chromium) | ferramentas sem serviço próprio | versionamento fica (única costura declarada); o resto vira serviço ou entra na allowlist do teste |
| `test_boundary.py` só cobre `at` → `at_deploy` | os demais limites deste arquivo não têm freio | `at/tests/test_architecture.py` (ver Manutenção) |

## Manutenção

- Mudou camada, dono ou dívida, este arquivo muda no mesmo commit do código.
- A migração que fecha uma dívida tira a linha daqui e a linha da allowlist do teste no mesmo commit.
- Falta o freio: `at/tests/test_architecture.py`, por AST, reprovando `ARCH.md` ausente, pacote de `at/`
  não citado, os imports proibidos acima e escrita ou `subprocess` fora das portas, com allowlist
  que espelha as dívidas. Enquanto ele não existe, as regras valem por revisão.
- Quando o freio não couber, a dívida é declarada aqui com motivo e vira item do `BACKLOG.md`.
