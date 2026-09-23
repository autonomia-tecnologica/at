# Derivação

A metade derivada do documento fundador: a árvore, a Pasta de Trabalho e a operação. Cada seção aqui é `derivation §N`, e as referências `§N` apontam para o artigo com esse id, onde ele estiver.

## 1. A árvore do repositório

Cada nó com o seu trabalho, e nenhum resolve um caminho por conta própria além do `core` (§4).

```
bill/                          o produto: o motor, as declarações e a UI
├── core/                      as regras — a Pasta de Trabalho, os ajustes, a primeira execução,
│                              o escritor único, o motor de tabelas, o escopo de projeto
├── data/                      as tabelas: `data/<tabela>.jsonl` para as linhas e
│   │                          `data/schema/<tabela>.json` para o esquema
│   └── defaults/              as declarações que o produto entrega, escritas na pasta na primeira execução
├── prose/                     todo arquivo que não é dado estruturado: a árvore de `prose/`,
│                              o que um arquivo ali É, e a escrita com a sua revisão
├── services/                  serviços externos, tão agnóstico à ferramenta quanto a camada consegue
├── encryption/                segredos: a Frase de Acesso, a Chave do Bill e as chaves derivadas,
│                              e `password`, a derivação que o campo hasheado guarda
├── nlu/                       a interpretação: o vocabulário, o casador e a proposta de ação
├── posture/                   a postura: as funções graduadas, as notas e o elo mais fraco
├── ui/
│   ├── ask.py                 a porta do interpretador: uma frase, uma proposta, e ela roda
│   ├── cli/                   a linha de comando — a superfície que alcança tudo
│   ├── wizard/                o Painel de Controle, em Tkinter
│   └── webapp/                o WebApp: o servidor, a aparência que ele serve e a app Vue
│       ├── app.py             o servidor
│       ├── assets/            `base.css`, os temas (`themes.jsonl`), os desenhos
│       ├── src/               a derivação (Vue 3 + TypeScript) — NÃO viaja no binário
│       ├── dist/              o construído, servido em runtime — vem de `npm run build`
│       ├── vendor/            as fontes hospedadas, com o hash que o manifesto pina
│       └── node_modules/      a derivação — NÃO viaja no binário
├── i18n/
│   ├── blocks/<bloco>.json    um arquivo por assunto, as duas línguas lado a lado — o nome do
│   │                          arquivo é o namespace (`blocks/boot.json` guarda `first_run.confirm`)
│   └── vocabulary/            o vocabulário do interpretador, por idioma, empacotado como os blocos
└── tests/                     a suíte — `unittest` da stdlib, porque um runner não é dependência
    ├── spelling.pt_BR.txt     o que o corretor deve ignorar em português
    └── spelling.en_US.txt     o mesmo, em inglês

docs/                          os documentos
├── pt_BR/                     a fonte: os documentos escritos em português
│   ├── README.md              o documento fundador, que vincula
│   ├── rules.md               as regras que vinculam (§3)
│   ├── architecture.md        a arquitetura que vincula (§4)
│   ├── interfaces.md          as interfaces: `cli`, WebApp e Wizard (§5)
│   ├── paths.md               os dois caminhos de uso (§6)
│   ├── container.md           o caminho container: os passos (§7)
│   ├── extensions.md          as extensões e os plugins (§8)
│   ├── end-to-end.md          o ambiente de teste end-to-end (§9)
│   ├── derivation.md          a derivação: a árvore, a Pasta de Trabalho e a operação
│   ├── functionalities.md     o que a nota mede: as funcionalidades, níveis e notas
│   └── glossary.md            o que um nome significa, termo a termo
└── en_US/                     a tradução: os mesmos documentos, em inglês
    ├── README.md              a tradução do documento fundador, que anda junto
    ├── rules.md               a tradução dela, que anda junto
    ├── architecture.md        a tradução dela, que anda junto
    ├── interfaces.md          a tradução dela, que anda junto
    ├── paths.md               a tradução dela, que anda junto
    ├── container.md           a tradução dela, que anda junto
    ├── extensions.md          a tradução dela, que anda junto
    ├── end-to-end.md          a tradução dela, que anda junto
    ├── derivation.md          a tradução dela, que anda junto
    ├── functionalities.md     a tradução dela, que anda junto
    ├── glossary.md            a tradução dela, que anda junto
    └── backlog.md             o documento de trabalho, só em inglês: o que vem a seguir, e o que conta como pronto
```

`bill.spec` é o único lugar que diz o que viaja dentro do binário, e é à mão de propósito: três dos conteúdos — `bill/i18n`, `bill/data/defaults` e os `assets`, `dist` e `vendor` do WebApp — são invisíveis a um grafo de importação, e `bill/ui/webapp/` também guarda `node_modules/` e `src/`, que são a derivação e não podem viajar. Um conteúdo deixado de fora falha em silêncio no WebApp (404 e um 500) e em voz alta em todo o resto, porque `tr()` levanta na primeira mensagem de cada comando.

## 2. A Pasta de Trabalho

A pasta em que o binário foi aberto é a pasta do binário, e essa pasta é a Pasta de Trabalho (§3). Na primeira execução o Bill descreve a pasta e pergunta antes de escrever qualquer coisa; `App/settings.json` é o que faz uma pasta ser uma pasta configurada.

**O nome no disco é a face; a máquina lê o nome interno.** Cada pasta tem um nome interno — `app`, `data`, `prose`, `projects`, `shared` e `harness` —, e é ele que o motor usa e que as declarações citam. O nome que a pessoa lê vem do idioma ativo, e a tabela de `paths.py` é a única que o conhece: `Tabelas/`, `Arquivos/`, `Projetos/` e `Compartilhada/` em `pt_BR`; `Tables/`, `Files/`, `Projects/` e `Shared/` em `en_US`. Duas pastas são a exceção, e as duas são deliberadas: a pasta da instância não segue o idioma, porque o idioma mora dentro dela — `App/` nos dois —, e a `Harness/` não segue porque o `pt_BR` tomou a palavra inteira, então os dois idiomas a escrevem igual.

Uma pasta nasce com:

```
AGENT.md                  a pasta se apresentando, para quem trabalha nela
App/settings.json         os ajustes da instância, em chave-valor
App/i18n/active           o idioma escolhido — os catálogos viajam no produto
App/counters.json         o último id entregue, por tabela
App/migrations            até onde esta pasta já migrou
App/plugins/              as extensões, e o estado de review de cada uma
App/services/<serviço>/   o estado persistente de cada serviço (§4)
Tabelas/schema/*.json     as tabelas de sistema, escritas pelo produto
Tabelas/*.jsonl           as linhas (chegam com a primeira escrita)
Arquivos/                 tudo o que não é dado estruturado, com a nota de boas-vindas
Projetos/                 o que pertence a um projeto — nomeada, ainda vazia
Compartilhada/            o que for compartilhado com outras pessoas — nomeada, ainda vazia
Harness/                  o que governa quem trabalha na pasta — nomeada, ainda vazia
```

A nota na raiz é o arquivo que a pasta carrega para quem trabalha dentro dela: ela
diz o que a pasta é, o que ela guarda e como chegar ao resto, e cita o documento
fundador em vez de repetir regra (§0). O **nome** dela não segue o idioma — uma
nota cujo nome anda com a tradução é uma nota que um modelo deixa de achar —,
enquanto o texto segue. Ela é escrita uma vez, como a nota de boas-vindas, e uma
pasta que já existia a ganha por migração.

**A migração.** Atualizar o Bill é trocar o binário dentro da pasta, então toda versão que muda a estrutura da pasta traz a migração dela e ela roda na primeira subida depois da troca (§3). O carimbo é `App/migrations`, e ele mora com o resto do que o Bill escreve, nunca na declaração publicada. As migrações são, hoje, cinco: `.bill/` → `app/`, `app/` → `App/`, as pastas da pessoa para o idioma ativo, o `AGENT.md` com que a pasta se apresenta, e a `Harness/`. A terceira pergunta antes, porque renomear quebra o que aponta para elas de fora do Bill; quem recusa mantém o nome que tinha, e a resolução lê as duas grafias. As outras quatro mexem só no que o Bill escreve, e nenhuma delas sobrescreve nada.

Uma pasta que ainda não migrou **é encontrada pelo nome velho**: `paths.instance_dir()` lê o que está no disco antes de decidir, para que uma pasta com `.bill/` não seja lida como pasta nova — que era o defeito que a migração número um existia para fechar.

Duas recusas são deliberadas:

- **Sem terminal para perguntar, não há pasta criada.** Uma decisão que ninguém pôde responder não é uma decisão; o Bill para com código `1` em vez de assumir.
- **Recusar não cria nada.** O Bill diz onde mover o binário e sai sem erro, porque recusar não é erro.

`BILL_ROOT` aponta o motor para outra pasta. Ele existe para os testes e para rodar a partir do checkout, e é a única variável de ambiente que decide onde o Bill escreve.

Enquanto se desenvolve, este checkout *é* a Pasta de Trabalho: as pastas nascem onde devem nascer, na grafia do idioma ativo, e todas as grafias são ignoradas pelo git.

## 3. Operação

```sh
python3 -m bill help                         # as palavras
python3 -m bill task create --set text="escrever o README" --set priority=high
python3 -m bill task list                    # o corte padrão da tabela; `--all` mostra tudo
python3 -m bill task view 3                  # ou TASK-3, ou tarefa-3
python3 -m bill task edit 3 --set status=done
python3 -m bill pedir "cria uma tarefa pra sexta"   # a proposta, e a resposta
python3 -m bill webapp run                   # laço local, porta 12345; `--port N` muda
.venv/bin/python -m unittest discover -s bill/tests   # a suíte (o venv traz o corretor)
```

As ações de tabela são `list`, `view`, `create`, `edit`, `cancel` e `delete`. O `cancel` fecha uma linha COM histórico — o status terminal, onde o motivo cai e se ele é obrigatório vêm todos do `lifecycle` que a tabela declara —, enquanto o `delete` tira a linha, recusando enquanto outra linha a nomeia e sem devolver o número. Quem nomeia uma linha é lido das declarações, nunca de uma varredura da pasta, e uma tabela que não declara `lifecycle` não tem fechamento e o diz.

Superfícies, e o estado de cada uma hoje:

| superfície | como se chega | estado |
|---|---|---|
| `cli` | `bill <palavra>` | `help`, `version`, `webapp`, `ask` e as tabelas |
| Wizard | `bill`, sem palavra | o Painel de Controle abre, em hello world |
| WebApp | `bill webapp run` | lê e edita as tabelas, e alcança o interpretador pelo chat e pelo balão |

Códigos de saída: `0` sucesso · `1` recusado ou falhou · `2` erro de uso.

Python 3.14.7 com **uma** dependência de runtime: `PyNaCl`, a ligação do `libsodium`, pinada em versão e hashing no `requirements.txt` (§3). A derivação do campo hasheado é a do `libsodium`, e ele não é a biblioteca padrão, então o preço está nomeado em vez de evitado. A wheel carrega o `libsodium` dentro dela, então o binário continua autossuficiente e nada é pedido da máquina que o roda. Há mais duas exceções deliberadas, as duas do lado do desenvolvimento: as fontes hospedadas do WebApp, em `bill/ui/webapp/vendor/`, com o hash que o manifesto pina; e o corretor dos documentos, que roda na suíte e por isso é ferramenta, não instalação — ele não pode exigir do outro dev nem do runner nada que não venha pinado dentro do `.venv`.

Essa dependência se instala primeiro, sob a mesma regra:

```sh
.venv/bin/pip install --require-hashes -r requirements.txt
```

A suíte roda o gate dos documentos (§3, Internacionalização), e o corretor dele se instala uma vez:

```sh
.venv/bin/pip install --require-hashes -r requirements-dev.txt
```

### A página

A página é uma app **Vue 3 + TypeScript**, construída pelo Vite (§5). A construção é derivação, nunca editada:

```sh
cd bill/ui/webapp
npm ci && npm run build      # escreve dist/, que o servidor serve
npm run typecheck            # vue-tsc
```

Dois ajustes no `vite.config.ts` não são gosto: o polyfill de modulepreload e o limite de asset inline estão DESLIGADOS, porque os dois emitiriam um `<script>` inline ou um `data:` e a política recusaria. E a aparência é injetada no head por um plugin `transformIndexHtml` — o Vite trata `<link rel="stylesheet">` como algo a empacotar e **remove em silêncio** o que não encontra no disco, que é como uma construção já saiu sem uma única regra.

### O binário único

```sh
# só em tempo de construção, nunca dependência de runtime; os dois vivem nos
# requirements de desenvolvimento, com versão e hash (§3), porque os hooks
# viajam separados do freezer e flutuam sozinhos
.venv/bin/pip install --require-hashes -r requirements-dev.txt
.venv/bin/pyinstaller --clean --noconfirm bill.spec   # escreve dist/bill
```

**Ele constrói só no Linux.** O PyInstaller não é um compilador cruzado e não pode ser: ele congela executando código do interpretador *alvo* em tempo de construção. Então binários de Windows e macOS precisam das suas próprias construções, nos seus próprios runners (§9), e o `bill.spec` é escrito para ser o arquivo que os três compartilham.

O binário é um arquivo só porque é o que o documento fundador promete (§3), e o preço é que todo o conteúdo — Tcl/Tk incluído — é re-extraído a cada execução, então o arranque a frio é mais lento do que seria numa construção em diretório.

A Pasta de Trabalho não depende dessa escolha: `paths.working_folder()` resolve a partir de `sys.executable`, que é o binário lançado também sob `--onedir`, então a pasta em que o binário está é a pasta em que ele trabalha dos dois jeitos. Rode de qualquer lugar e ele continua trabalhando na pasta dele. Repare que `bill` sem palavra abre o Wizard do Tkinter, então uma verificação sem tela quer `bill <palavra>`.
