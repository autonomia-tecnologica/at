# Derivação

A metade derivada do documento fundador: a árvore, a Pasta de Trabalho e a operação. Cada seção aqui é `derivation §N`, e as referências `§N` apontam para o artigo com esse id, onde ele estiver.

## 1. A árvore do repositório

Cada nó com o seu trabalho, e nenhum resolve um caminho por conta própria além do `core` (§4).

```
at/                          o produto: o motor, as declarações e a UI
├── core/                      as regras — a Pasta de Trabalho, os ajustes, a primeira execução,
│                              o escritor único, o motor de tabelas, o escopo de projeto,
│                              o catálogo de permissões, os atores e a porta do Cofre para
│                              a tabela `secret`
├── data/                      as tabelas: `data/<tabela>.jsonl` para as linhas e
│   │                          `data/schema/<tabela>.json` para o esquema
│   └── defaults/              as declarações que o produto entrega, escritas na pasta na primeira execução
├── prose/                     todo arquivo que não é dado estruturado: a árvore de `prose/`,
│                              o que um arquivo ali É, e a escrita com a sua revisão
├── services/                  o único serviço que o BINÁRIO carrega: `caddy.py` — o conteúdo,
│                              a extração para `App/`, o Caddyfile que o produto gera e o
│                              processo que termina o TLS (§3, §6)
├── vendor/caddy/              o tarball de release do Caddy, byte a byte como o fornecedor
│                              o publica, e é ele que viaja dentro do binário (§3, §6)
├── encryption/                segredos: a Chave Principal, as chaves derivadas
│                              e os valores que ela protege (`vault`), e `password`, a derivação
│                              que o campo hasheado guarda
├── nlu/                       a interpretação: o vocabulário, o casador e a proposta de ação
├── posture/                   a postura: as funções graduadas, as notas e o elo mais fraco
├── ui/
│   ├── ask.py                 a porta do interpretador: uma frase, uma proposta, e ela roda
│   ├── cli/                   a linha de comando — a superfície que alcança tudo
│   ├── wizard/                o Painel de Controle, em Tkinter
│   └── webapp/                o WebApp: o servidor, a aparência que ele serve e a app Vue
│       ├── app.py             o servidor
│       ├── session.py         a sessão da entrada: o token, o cookie e o registro
│       ├── assets/            `base.css`, os temas (`themes.jsonl`), os desenhos
│       ├── src/               a derivação (Vue 3 + TypeScript) — NÃO viaja no binário
│       ├── dist/              o construído, servido em runtime — vem de `npm run build`
│       ├── vendor/            os arquivos hospedados — fontes e o renderizador —, com o hash que o manifesto pina
│       └── node_modules/      a derivação — NÃO viaja no binário
├── i18n/
│   ├── blocks/<bloco>.json    um arquivo por assunto, as duas línguas lado a lado — o nome do
│   │                          arquivo é o namespace (`blocks/boot.json` guarda `first_run.confirm`)
│   └── vocabulary/            o vocabulário do interpretador, por idioma, empacotado como os blocos
└── tests/                     a suíte do app — `unittest` da stdlib, porque um runner não é
    │                          dependência
    ├── spelling.pt_BR.txt     o que o corretor precisa ignorar em português
    └── spelling.en_US.txt     o mesmo, em inglês

at_deploy/                   o SEGUNDO artefato: o §7 inteiro — o ambiente, a virada entre
│                              os dois caminhos e a única elevação do produto (§3, item 27).
│                              Ele importa o núcleo do `at`, e o `at` não importa nada dele
├── cli.py                     a linha de comando dele: as palavras `services`, e só
├── tree.py                    as palavras que ele oferece — ajuda e despacho leem uma lista só
├── environment.py             o manifesto das imagens fixadas, os serviços e a orquestração
├── podman.py                  o runtime, atrás de uma costura
├── vpn.py                     §7e: de onde o ambiente é alcançado por fora
├── switch.py                  a virada transacional do §6 de um caminho para o outro
└── tests/                     a suíte dele, rodada pelo mesmo comando que a do app

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
    └── glossary.md            a tradução dela, que anda junto
```

Os dois specs — `at-cli.spec` e `at-deploy.spec` — são o único lugar que diz o que viaja dentro de cada artefato, e são à mão de propósito: os conteúdos — `at/i18n`, `at/data/defaults`, o tarball do Caddy em `at/vendor/caddy/` e os `assets`, `dist` e `vendor` do WebApp — são invisíveis a um grafo de importação, e `at/ui/webapp/` também guarda `node_modules/` e `src/`, que são a derivação e não podem viajar. Um conteúdo deixado de fora falha em silêncio no WebApp (404 e um 500) e em voz alta em todo o resto, porque `tr()` levanta na primeira mensagem de cada comando. O spec do deploy é o curto de propósito: ele não carrega o WebApp, o interpretador nem o Caddy, porque não alcança nenhum deles.

## 2. A Pasta de Trabalho

A pasta em que o binário foi aberto é a pasta do binário, e essa pasta é a Pasta de Trabalho (§3). Na primeira execução o AT descreve a pasta e pergunta antes de escrever qualquer coisa; `App/settings.json` é o que faz uma pasta ser uma pasta configurada.

**O nome no disco é a face; a máquina lê o nome interno.** Cada pasta tem um nome interno — `app`, `data`, `prose`, `projects`, `shared`, `harness` e `cofre` —, e é ele que o motor usa e que as declarações citam. O nome que a pessoa lê vem do idioma ativo, e a tabela de `paths.py` é a única que o conhece: `Tabelas/`, `Biblioteca/`, `Projetos/`, `Compartilhado/` e `Cofre/` em `pt_BR`; `Tables/`, `Library/`, `Projects/`, `Shared/` e `Vault/` em `en_US`. As grafias `Arquivos/` e `Files/` são as aposentadas de `prose/` — a resolução ainda as aceita, e é por isso que uma pasta que não migrou não some. Duas pastas são a exceção, e as duas são deliberadas: a pasta da instância não segue o idioma, porque o idioma mora dentro dela — `App/` nos dois —, e a `Harness/` não segue porque o `pt_BR` tomou a palavra inteira, então os dois idiomas a escrevem igual.

Uma pasta nasce com:

```
README.md                 a pasta se apresentando, para quem trabalha nela
App/settings.json         os ajustes da instância, em chave-valor
App/i18n/active           o idioma escolhido — os catálogos viajam no produto
App/counters.json         o último id entregue, por tabela
App/migrations            até onde esta pasta já migrou
App/extensions/            as extensões, e o estado de review de cada uma
App/services/<serviço>/   o estado persistente de cada serviço (§4)
Tabelas/schema/*.json     as tabelas de sistema, escritas pelo produto
Tabelas/*.jsonl           as linhas (chegam com a primeira escrita)
Biblioteca/               tudo o que não é dado estruturado, com a nota de boas-vindas
Projetos/                 o que pertence a um projeto — nomeada, ainda vazia
Compartilhado/            o que for compartilhado com outras pessoas — nomeada, ainda vazia
Harness/                  o que governa quem trabalha na pasta — nomeada, ainda vazia
Cofre/                    o que sela sozinho — nomeada, ainda vazia
```

A listagem acima é aquilo com que a pasta nasce. `App/services/` chega depois, e só
se um serviço for pedido — mas agora é a casa de TODO serviço, nos DOIS caminhos, e
cada um mora em `App/services/<serviço>/`. O Caddy é o primeiro: `at-cli webapp`
(sem `--no-caddy`) extrai `App/services/caddy/` — o Caddy de dentro do binário, o
carimbo que diz para que plataforma ele serve, o Caddyfile que o AT gera e o
armazenamento do próprio Caddy, a autoridade local dele entre o resto (§6, §12) —, e
mora sob `App/` pelo motivo que o §3 dá: o que foi extraído para rodar é da pasta,
então uma pasta copiada volta com o Caddy e os certificados que ela tinha. O
Authelia do caminho hospedado, o push, o gitleaks e o cache do Jev moram ali também.

No caminho container quem escreve em `App/services/` é o `at-deploy up`: `images.json`
guarda o pino em que ESTA pasta está, por serviço, e a pasta de cada serviço carrega o
que ele lê — `caddy/Caddyfile`, o Caddyfile que o AT gera, com o armazenamento do lado
de dentro do container. Nada sobe sem o Podman: o AT verifica se ele existe e, não
existindo, oferece as duas saídas — instalar, ou seguir no caminho hospedado. As
imagens são fixadas em versão e hashing, como o §3 exige, então o pino da pasta e o do
binário são comparados a cada subida — e uma instância À FRENTE do pino do binário
avisa e prossegue, porque não é rebaixada.

A nota na raiz é o arquivo que a pasta carrega para quem trabalha dentro dela: ela
diz o que a pasta é, o que ela guarda e como chegar ao resto, e cita o documento
fundador em vez de repetir regra (§0). É o `README.md` — o **nome** dela não
segue o idioma, porque uma nota cujo nome anda com a tradução é uma nota que um
modelo deixa de achar —, enquanto o texto segue. Ela é escrita uma vez, como a
nota de boas-vindas, e uma pasta que já existia a ganha por migração; o `AGENT.md`
que uma versão anterior escrevia é removido por migração.

**A migração.** Atualizar o AT é trocar o binário dentro da pasta, então toda versão que muda a estrutura da pasta traz a migração dela e ela roda na primeira subida depois da troca (§3). O carimbo é `App/migrations`, e ele mora com o resto do que o AT escreve, nunca na declaração publicada. As migrações são, hoje, trinta e três: `.bill/` → `app/`, `app/` → `App/`, as pastas da pessoa para o idioma ativo, o `AGENT.md` com que a pasta se apresentava, a `Harness/`, as declarações das tabelas que a versão introduz, e o papel do administrador alcançando as permissões que uma versão acrescentou ao catálogo — duas vezes, porque o catálogo cresceu duas vezes e migração publicada nunca se edita. A última aposenta aquele `AGENT.md`: como a migração que o escreveu não se edita, a remoção entra como passo novo, e ela apaga o arquivo sempre que existe — sem perguntar, porque o `README.md` é o único que fica. A terceira pergunta antes, porque renomear quebra o que aponta para elas de fora do AT; quem recusa mantém o nome que tinha, e a resolução lê as duas grafias. As demais mexem só no que o AT escreve, e nenhuma delas sobrescreve nada — a sexta nomeia as tabelas que aquela versão traz, e não o diretório inteiro, para não trazer de volta a declaração que uma pessoa apagou; o que só completa não traz mais do que o que a pasta nunca teve a CHANCE de carregar.

Uma pasta que ainda não migrou **é encontrada pelo nome velho**: `paths.instance_dir()` lê o que está no disco antes de decidir, para que uma pasta com `.bill/` não seja lida como pasta nova — que era o defeito que a migração número um existia para fechar.

Duas recusas são deliberadas:

- **Sem terminal para perguntar, não há pasta criada.** Uma decisão que ninguém pôde responder não é uma decisão; o AT para com código `1` em vez de assumir.
- **Recusar não cria nada.** O AT diz onde mover o binário e sai sem erro, porque recusar não é erro.

`AT_ROOT` aponta o motor para outra pasta. Ele existe para os testes e para rodar a partir do checkout, e é a única variável de ambiente que decide onde o AT escreve.

Enquanto se desenvolve, este checkout *é* a Pasta de Trabalho: as pastas nascem onde devem nascer, na grafia do idioma ativo, e todas as grafias são ignoradas pelo git.

## 3. Operação

```sh
python3 -m at help                         # as palavras
python3 -m at task create --set text="escrever o README" --set priority=high
python3 -m at task list                    # o corte padrão da tabela; `--all` mostra tudo
python3 -m at task view 3                  # ou TASK-3, ou tarefa-3
python3 -m at task edit 3 --set status=done
python3 -m at admin                        # o primeiro administrador: nome, e a credencial sem eco
python3 -m at pedir "cria uma tarefa pra sexta"   # a proposta, e a resposta
python3 -m at webapp run                   # exposto por padrão, com o TLS do Caddy na `--port`
                                             # e o `--host` dizendo o endereço em que atende
python3 -m at webapp --no-caddy            # laço local, porta 12345; `--port N` muda
python3 -m at_deploy services up           # o caminho container: os serviços no pino
python3 -m at_deploy services status       # o que está de pé, e em que imagem
python3 -m at_deploy services down         # abaixo; a pasta fica
python3 -m at_deploy services credential <nome>   # a credencial que o portão prova, e o provedor reiniciado
.venv/bin/python -m unittest discover -t .   # as duas suítes (o venv traz o corretor)
```

As ações de tabela são `list`, `view`, `create`, `edit`, `cancel` e `delete`. O `cancel` fecha uma linha COM histórico — o status terminal, onde o motivo cai e se ele é obrigatório vêm todos do `lifecycle` que a tabela declara —, enquanto o `delete` tira a linha, recusando enquanto outra linha a nomeia e sem devolver o número. Quem nomeia uma linha é lido das declarações, nunca de uma varredura da pasta, e uma tabela que não declara `lifecycle` não tem fechamento e o diz.

Superfícies, e o estado de cada uma hoje:

| superfície | como se chega | estado |
|---|---|---|
| `cli` | `at-cli <palavra>` | `help`, `version`, `webapp`, `admin`, `lang`, `ask` e as tabelas |
| `cli` do deploy | `at-deploy <palavra>` | `help`, `version` e as seis palavras de `services` mais a do operador — `credential`; ele não carrega WebApp, e o Wizard dele é a fatia 3 do item 27 |
| Wizard | — | fora do ar enquanto o item 9 não chega à fatia 3: `at-cli` sem palavra imprime o `help` |
| WebApp | `at-cli webapp run` | lê e edita as tabelas, alcança o interpretador pelo chat e pelo balão, recusa subir numa pasta sem administrador e — havendo um — pede a credencial e não responde nada da API antes de ela ser provada; e é onde o teto se MOVE: a entrada Pessoas, com as telas do ator e do papel, a lista fechada contra a qual um papel se escreve, e a credencial de máquina que o AT mina |

`at-cli webapp` expõe por padrão, na exposição para a qual o §3 exige TLS: o
Caddy que veio dentro do binário o termina, com o certificado do próprio AT, e
o WebApp fica em `127.0.0.1` atrás dele. `--no-caddy` volta ao laço local em
HTTP. O que o `--host` nomeia muda com a bandeira — o nome para o qual o
certificado é emitido por padrão, porque certificado se emite para um nome e
`0.0.0.0` não é um; e o laço que ele pode amarrar com `--no-caddy`.

Códigos de saída: `0` sucesso · `1` recusado ou falhou · `2` erro de uso.

Python 3.14.7 com **uma** dependência de runtime: `PyNaCl`, a ligação do `libsodium`, pinada em versão e hashing no `requirements.txt` (§3). A derivação do campo hasheado é a do `libsodium`, e ele não é a biblioteca padrão, então o preço está nomeado em vez de evitado. A wheel carrega o `libsodium` dentro dela, então o binário continua autossuficiente e nada é pedido da máquina que o roda. Há mais duas exceções deliberadas, as duas do lado do desenvolvimento: os arquivos hospedados do WebApp — as fontes e o renderizador —, em `at/ui/webapp/vendor/`, com o hash que o manifesto pina; e o corretor dos documentos, que roda na suíte e por isso é ferramenta, não instalação — ele não pode exigir do outro dev nem do runner nada que não venha pinado dentro do `.venv`.

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
cd at/ui/webapp
npm ci && npm run build      # escreve dist/, que o servidor serve
npm run typecheck            # vue-tsc
npm run dev                  # o app com hot reload, para trabalhar
```

O `npm run dev` sobe o Vite **e precisa do servidor atrás dele**: o Vite serve a app — os módulos, a recarga ao vivo — e o `at-cli webapp` continua com tudo o que não é a app (as palavras, as tabelas, a aparência, os ícones, os arquivos de terceiros), na sua porta (`AT_WEBAPP_PORT`, o padrão é a do AT — 12345). São dois processos e uma origem só, e é por isso que a aparência entra no head do mesmo jeito: o plugin `transformIndexHtml` roda no dev também, e `/theme.css` e `/base.css` atravessam o proxy.

Dois ajustes no `vite.config.ts` não são gosto: o polyfill de modulepreload e o limite de asset inline estão DESLIGADOS, porque os dois emitiriam um `<script>` inline ou um `data:` e a política recusaria. E a aparência é injetada no head por um plugin `transformIndexHtml` — o Vite trata `<link rel="stylesheet">` como algo a empacotar e **remove em silêncio** o que não encontra no disco, que é como uma construção já saiu sem uma única regra.

### Os dois binários

```sh
# só em tempo de construção, nunca dependência de runtime; os dois vivem nos
# requirements de desenvolvimento, com versão e hash (§3), porque os hooks
# viajam separados do freezer e flutuam sozinhos
.venv/bin/pip install --require-hashes -r requirements-dev.txt
.venv/bin/pyinstaller --clean --noconfirm at-cli.spec          # escreve dist/at
.venv/bin/pyinstaller --clean --noconfirm at-deploy.spec   # escreve dist/at-deploy
```

**Uma release, dois arquivos, e a divisão É o ponto.** O `at-cli` é a pasta e o app — as tabelas, a prosa, o interpretador, o WebApp e o Wizard —, e o `at-deploy` é o §7 inteiro: o Podman, a VPN, os containers do portão, a borda, a virada transacional e a única elevação do produto. É um segundo artefato e não um segundo comando do mesmo porque a promessa que o §3 faz se lê do que o ARQUIVO é: um `at-cli` que NÃO CONSEGUE pedir é uma promessa mais forte do que um `at-cli` que não pede. A elevação MUDOU e não se duplica, e o que separa os dois é o grafo de importação — o `at_deploy` importa o `at`, e o `at` não importa nada do deploy —, que a suíte afirma a partir das fontes. O núcleo compartilhado (`paths`, `i18n`, `files`, o motor de tabelas) viaja nos dois, colhido dos mesmos arquivos: uma fonte e não duas.

Cada binário é um arquivo só porque é o que o documento fundador promete (§3), e o preço é que todo o conteúdo — Tcl/Tk incluído — é re-extraído a cada execução, então o arranque a frio é mais lento do que seria numa construção em diretório. O deploy não carrega Tcl/Tk nem WebApp: o conteúdo dele são os blocos de `i18n` e as declarações das tabelas, porque ele confirma a Pasta de Trabalho exatamente como o `at-cli` e precisa conseguir criar uma.

**Ele constrói só no Linux.** O PyInstaller não é um compilador cruzado e não pode ser: ele congela executando código do interpretador *alvo* em tempo de construção. Então binários de Windows e macOS precisam das suas próprias construções, nos seus próprios runners (§9), e os dois specs são escritos para serem os arquivos que os três compartilham — `at-deploy.spec` não é um segundo alvo do `at-cli.spec`, porque um spec É um artefato e os dois diferem no ponto de entrada, nos conteúdos e nas exclusões.

A Pasta de Trabalho não depende dessa escolha: `paths.working_folder()` resolve a partir de `sys.executable`, que é o binário lançado também sob `--onedir`, então a pasta em que o binário está é a pasta em que ele trabalha dos dois jeitos. Rode de qualquer lugar e ele continua trabalhando na pasta dele. Repare que `at-cli` sem palavra imprime o `help` — o Wizard do Tkinter está fora do ar até a fatia 3 do item 9 —, então uma verificação sem tela quer `at-cli <palavra>`. Os dois artefatos dividem o ESTADO da pasta e não uma API, então `at-deploy up` trabalha na mesma pasta que o `at-cli` serve, e o `at-cli` continua servindo com o deploy ausente.
