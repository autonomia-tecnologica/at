# Arquitetura

A metade derivada do documento fundador: a árvore, a Pasta de Trabalho e a operação. Cada seção aqui é `arquitetura §N`, e as referências `README §N` apontam para o [documento fundador](README.md), que vincula.

## 1. A árvore do repositório

Cada nó com o seu trabalho, e nenhum resolve um caminho por conta própria além do `core` (`README` §4).

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
├── encryption/                segredos: a Frase de Acesso, a Chave do Bill e as chaves derivadas
├── nlu/                       a interpretação: o vocabulário, o casador e a proposta de ação
├── posture/                   a postura: as funções graduadas, as notas e o elo mais fraco
├── ui/
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
│   ├── architecture.md        a derivação: a árvore, a Pasta de Trabalho e a operação
│   ├── functionalities.md     o que a nota mede: as funcionalidades, níveis e notas
│   └── glossary.md            o que um nome significa, termo a termo
└── en_US/                     a tradução: os mesmos documentos, em inglês
    ├── README.md              a tradução do documento fundador, que anda junto
    ├── architecture.md        a tradução dela, que anda junto
    ├── functionalities.md     a tradução dela, que anda junto
    ├── glossary.md            a tradução dela, que anda junto
    └── backlog.md             o documento de trabalho, só em inglês: o que vem a seguir, e o que conta como pronto
```

`bill.spec` é o único lugar que diz o que viaja dentro do binário, e é à mão de propósito: três dos conteúdos — `bill/i18n`, `bill/data/defaults` e os `assets`, `dist` e `vendor` do WebApp — são invisíveis a um grafo de importação, e `bill/ui/webapp/` também guarda `node_modules/` e `src/`, que são a derivação e não podem viajar. Um conteúdo deixado de fora falha em silêncio no WebApp (404 e um 500) e em voz alta em todo o resto, porque `tr()` levanta na primeira mensagem de cada comando.

## 2. A Pasta de Trabalho

A pasta em que o binário foi aberto é a pasta do binário, e essa pasta é a Pasta de Trabalho (`README` §3). Na primeira execução o Bill descreve a pasta e pergunta antes de escrever qualquer coisa; `app/settings.json` é o que faz uma pasta ser uma pasta configurada.

Uma pasta nasce com:

```
app/settings.json         os ajustes da instância, em chave-valor
app/i18n/active           o idioma escolhido — os catálogos viajam no produto
app/counters.json         o último id entregue, por tabela
app/plugins/              as extensões, e o estado de review de cada uma
app/services/<serviço>/   o estado persistente de cada serviço (`README` §4)
data/schema/*.json        as tabelas de sistema, escritas pelo produto
data/*.jsonl              as linhas (chegam com a primeira escrita)
prose/                    tudo o que não é dado estruturado, com a nota de boas-vindas
```

Duas recusas são deliberadas:

- **Sem terminal para perguntar, não há pasta criada.** Uma decisão que ninguém pôde responder não é uma decisão; o Bill para com código `1` em vez de assumir.
- **Recusar não cria nada.** O Bill diz onde mover o binário e sai sem erro, porque recusar não é erro.

`BILL_ROOT` aponta o motor para outra pasta. Ele existe para os testes e para rodar a partir do checkout, e é a única variável de ambiente que decide onde o Bill escreve.

Enquanto se desenvolve, este checkout *é* a Pasta de Trabalho: `data/`, `prose/` e `app/` nascem onde devem nascer e são ignorados pelo git.

## 3. Operação

```sh
python3 -m bill help                         # as palavras
python3 -m bill task create --set text="escrever o README" --set priority=high
python3 -m bill task list                    # o corte padrão da tabela; `--all` mostra tudo
python3 -m bill task view 3                  # ou TASK-3, ou tarefa-3
python3 -m bill task edit 3 --set status=done
python3 -m bill pedir "cria uma tarefa pra sexta"   # a proposta, para você conferir
python3 -m bill webapp run                   # laço local, porta 12345; `--port N` muda
.venv/bin/python -m unittest discover -s bill/tests   # a suíte (o venv traz o corretor)
```

As ações de tabela hoje são `list`, `view`, `create` e `edit`. `cancel` e `delete` não estão aqui ainda: as duas precisam do `lifecycle` que uma tabela declara para fechar com histórico, e a deleção precisa da regra da referência — o `audit` é exceção declarada a ela, por ser log e não link.

Superfícies, e o estado de cada uma hoje:

| superfície | como se chega | estado |
|---|---|---|
| `cli` | `bill <palavra>` | `help`, `version`, `webapp` e as tabelas |
| Wizard | `bill`, sem palavra | o Painel de Controle abre, em hello world |
| WebApp | `bill webapp run` | lê e edita as tabelas |

Códigos de saída: `0` sucesso · `1` recusado ou falhou · `2` erro de uso.

Python 3.14.7 sem nenhuma dependência de runtime. Uma dependência chega pinada em versão e hashing (`README` §3), e começar do zero é o que mantém essa promessa barata. Há duas exceções deliberadas, as duas do lado do desenvolvimento: as fontes hospedadas do WebApp, em `bill/ui/webapp/vendor/`, com o hash que o manifesto pina; e o corretor dos documentos, que roda na suíte e por isso é ferramenta, não instalação — ele não pode exigir do outro dev nem do runner nada que não venha pinado dentro do `.venv`.

A suíte roda o gate dos documentos (`README` §3, Internacionalização), e o corretor dele se instala uma vez:

```sh
.venv/bin/pip install --require-hashes -r requirements-dev.txt
```

### A página

A página é uma app **Vue 3 + TypeScript**, construída pelo Vite (`README` §5). A construção é derivação, nunca editada:

```sh
cd bill/ui/webapp
npm ci && npm run build      # escreve dist/, que o servidor serve
npm run typecheck            # vue-tsc
```

Dois ajustes no `vite.config.ts` não são gosto: o polyfill de modulepreload e o limite de asset inline estão DESLIGADOS, porque os dois emitiriam um `<script>` inline ou um `data:` e a política recusaria. E a aparência é injetada no head por um plugin `transformIndexHtml` — o Vite trata `<link rel="stylesheet">` como algo a empacotar e **remove em silêncio** o que não encontra no disco, que é como uma construção já saiu sem uma única regra.

### O binário único

```sh
# só em tempo de construção, nunca dependência de runtime; os dois pinados (`README` §3),
# porque os hooks viajam separados do freezer e flutuam sozinhos
.venv/bin/pip install 'pyinstaller==6.22.3' 'pyinstaller-hooks-contrib==2026.7'
.venv/bin/pyinstaller --clean --noconfirm bill.spec   # escreve dist/bill
```

**Ele constrói só no Linux.** O PyInstaller não é um compilador cruzado e não pode ser: ele congela executando código do interpretador *alvo* em tempo de construção. Então binários de Windows e macOS precisam das suas próprias construções, nos seus próprios runners (`README` §9), e o `bill.spec` é escrito para ser o arquivo que os três compartilham.

O binário é um arquivo só porque é o que o documento fundador promete (`README` §3), e o preço é que todo o conteúdo — Tcl/Tk incluído — é re-extraído a cada execução, então o arranque a frio é mais lento do que seria numa construção em diretório.

A Pasta de Trabalho não depende dessa escolha: `paths.working_folder()` resolve a partir de `sys.executable`, que é o binário lançado também sob `--onedir`, então a pasta em que o binário está é a pasta em que ele trabalha dos dois jeitos. Rode de qualquer lugar e ele continua trabalhando na pasta dele. Repare que `bill` sem palavra abre o Wizard do Tkinter, então uma verificação sem tela quer `bill <palavra>`.
