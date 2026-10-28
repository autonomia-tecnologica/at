# 5. Interfaces [normativo]

### Linha de comando (`cli`) e aplicação web (WebApp)

- Ao abrir o AT sem nenhuma palavra, o binário sobe o próprio app — como `at-cli webapp` — e abre o navegador nele: o "Painel de Controle" é o WebApp, numa porta efêmera e por trás de um token de uso único que o processo sorteia no boot. Não existe mais uma interface em Tkinter: o que a pessoa vê é a mesma página que `at-cli webapp` serve, só que aberta por ela mesma, sem ninguém digitar porta nem URL.

- Chamar o binário direto do terminal, sem palavra, carrega esse Painel no navegador. Qualquer outro parâmetro passado faz o programa agir como uma `cli`. `at-cli ajuda`, ou `at-cli help`, mostra como usar a cli completamente. `<palavra> help` (por exemplo `at-cli backup help`, `at-deploy container help`) mostra só a subárvore daquela palavra, no mesmo formato. E uma recusa nomeia o que falhou: a sub-palavra desconhecida, ou o argumento que sobrou — nunca o grupo.

- A linha de comando funciona para tudo do AT. Qualquer funcionalidade que ele exponha, seja na API REST (utilizada pelo frontend do WebApp), seja no WebApp em si, é acessível pela linha de comando.

- **`--json` é global** e muda só o que se IMPRIME: em qualquer posição da linha, a `cli` roda a palavra exatamente como roda hoje — as mesmas perguntas, os mesmos efeitos, os mesmos códigos de saída (`0` feito · `1` recusado ou falhou · `2` uso) — e escreve na saída padrão UM objeto JSON, com os acentos como são: `{"ok", "code", "message"}`, em que `ok` é `code == 0` e `message` é o texto que seria impresso. O formato das tabelas é o do WebApp, e não um segundo: `list` traz `table` (o `table_payload`, com as linhas que o filtro deixou, como `--project`), `view` e as escritas (`create`, `edit`, `cancel`, `delete`) trazem `record` (a linha, no formato do registro da página); `version` traz `version` e `secret scan` traz `findings`. Erro, recusa e uso errado saem no mesmo objeto, com `ok` falso e o mesmo código. Sem palavra nenhuma o comando abre o Painel, como abre sem a flag, e não imprime JSON. O `webapp` não espera o fim: o objeto de partida, com `url`, sai na hora em que o servidor anuncia o endereço, e o processo segue servindo; ao encerrar só imprime de novo se falhou.

- Esse Painel sem palavra, no `at-cli`, nasce com Forms desligado — não há ator a provar, e é o token, não o portão, que separa "a pessoa" de "a máquina" na porta de loopback. Ele guarda papéis que não se mudam de lugar e que ficam fora da rede por serem críticos demais para ela: hoje a **primeira subida**, em que a Pasta de Trabalho é confirmada e o primeiro admin é criado. O desenho do que mais entra aí — o que está habilitado, o que está rodando, o que está instalado — é o TASK-130, que nasce como página.

- **A primeira subida acontece na PÁGINA**, e não mais só no terminal: numa pasta sem administrador nenhum, o WebApp serve o formulário que cria o primeiro — nome e Chave Principal (16+, uma frase) —, e só no laço (§3, [Acesso e exposição](rules.md#acesso-e-exposição)). A `cli` mantém a mesma porta, e é a regra desta seção que tudo do Painel seja alcançável por ela: `at-cli admin` pergunta o nome e lê a Chave sem eco, e as duas dizem as MESMAS strings — a do formulário é a do bloco `admin` do catálogo, e não uma segunda frase que possa divergir.

- O `at-deploy` tem o seu próprio Painel — a sequência de §7 (`up`, `credential`, `switch`) que instala o ambiente, devolve o AT ao modo Forms e passa a Chave Principal no reinício do portão (`at_deploy/wizard.py`) — e perdeu a janela do mesmo jeito: a sequência fica no código, sem nenhuma tela que a desenhe, até a tela que o TASK-130 trouxer para ela também.

- O `cli` executa apenas localmente, em exceção quando está comunicando com APIs externas para devida configuração. E é ele, pelas mesmas palavras que os dois Painéis andam por dentro, que devolve o AT ao modo Forms.

- Papel e permissão **não** são assunto de nenhum dos dois Painéis: isso é tela do WebApp em rede, e o atrito de fazer admin por lá não se paga. Cada Painel fica com o que só ele pode fazer, fora da rede.

### A camada de interpretação

- A linguagem natural entra como **recurso** do WebApp e da `cli`, e não como uma quarta superfície: nada se torna possível só por falar. O que a pessoa digita vira uma proposta, e o que ela pode propor é o que ela já pode fazer.

- **O interpretador é determinístico.** Não há LLM no tempo de execução: a LLM ajuda a **escrever** o vocabulário, e o que roda é código com dado. Isso é o que corta o cordão com o token de terceiros, e é por isso que o AT não precisa de placa de vídeo para entender uma frase.

- O que o interpretador consulta é o **vocabulário**, por idioma, empacotado no produto junto dos blocos de `i18n`, porque traduzir vocabulário e traduzir texto é a mesma tarefa. O vocabulário é dado burro: pares expressão → expressão canônica, com idioma e região, e nada condicional. O que depende de contexto é gramática, e gramática é código do produto.

- **O interpretador propõe; o core valida e escreve.** Uma ação por requisição enquanto não existir uma API de lote; o dia em que existir, o lote é uma ação, com permissão própria. A unidade de tudo é a operação da API do core, e a API REST é uma das portas para ela.

- **O teto de acesso é o que o ator pode; o limiar de risco é o que ele pode sem perguntar.** Toda demanda tem um **risco**, medido pelo core a partir do que o produto declara por ação e por argumento — nunca pelo interpretador, porque quem pede não avalia o próprio risco. O **limiar** mora nas configurações: abaixo dele a ação corre, acima dela a pessoa aprova. O risco de cada ação é ajustável em `settings.json`, e o de uma extensão é aceito no momento de instalar.

- A aprovação chega por notificação, e a notificação é **campainha, não chave**: o toque abre o AT e a aprovação acontece dentro dele, com a sessão valendo. A credencial não mora na central de notificações. Um job que roda sozinho pode ser aprovado assim: a demanda que não pôde correr espera como uma linha da tabela `job` (§4, Tabelas), a aprovação é uma **linha própria na auditoria**, com o ator e a via por onde ela veio, separada do job que esperou — e ela é um ato com permissão própria, `job:approve` e `job:refuse`, que nenhum ator de máquina carrega.

- **A função de agente é desligável**, e desligá-la é tirar o interpretador da API do core: quem não quer a camada de linguagem usa o AT sem ela e não perde mais nada além dela.

- Como o interpretador é determinístico, **a responsabilidade volta para quem pediu**: um mal-entendido é defeito nosso ou frase mal escrita, e o rastro diz quem pediu. O `FAQ.md` diz isso com todas as letras, junto do conselho de que escrever bem é o melhor remédio.

### Aplicação WebApp

O WebApp serve três coisas e nada mais: **a página construída**, **a aparência** (`base.css`, os temas, os desenhos, as fontes hospedadas e o renderizador) e o **JSON** que a página lê. A página não tem regra nenhuma — o servidor decide, a página desenha.

**A casca e a página.** Uma sidebar que, no desktop, é um trilho de 56px que empurra o conteúdo (a largura não anima), uma barra de topo de 56px e, dentro de `#body`, um único `.page`: é o dono da margem (gutter de 32px, 24px até 960px, 16px até 640px) e da largura máxima de 1200px. Cada tela abre com um cabeçalho de página (o título). Nenhum componente leva margem externa própria.

O painel tem as entradas:

| entrada | o que é |
|---|---|
| **Tarefas** | a **árvore de projetos** — um projeto com a contagem das tarefas que o nomeiam, os subprojetos indentados, e por último o nó **"sem projeto"**, que abre as tarefas que projeto nenhum reivindica. Um projeto abre uma **página** com as tarefas de toda a sua subárvore, cada linha dizendo de que subprojeto ela veio. |
| **Biblioteca** | a árvore de `prose/` e a página de um arquivo — lida, e escrita no lugar quando o servidor diz que pode. |
| **Tabelas** | o vocabulário: toda tabela declarada, com a sua contagem. |
| **Pessoas** | os atores e os papéis: quem pode agir, com que teto. Só o admin abre. |
| **Serviços** | cada serviço configurado, o estado dele e os tokens que ele precisa. |
| **Extensões** | os plugins encontrados na pasta, a hash de cada um, o modo de review e os bloqueadores. É aqui que se instala. |
| **Postura** | a nota de segurança, função por função, e **quais funções estão impedindo de subir**. |
| **Configurações** | o pé do painel: o idioma, o tema, o movimento, o limiar de risco e os ajustes que a API do core expõe. |

**Não existe uma entrada "Projetos" separada.** A dobra de Tarefas *é* a árvore de projetos: um projeto é um escopo de tarefas, e a árvore é como se chega a elas — uma segunda linha seria a mesma porta com outro nome.

- **Os desenhos, as fontes e o renderizador são servidos POR NOME**, por `/icons/<nome>` e `/vendor/<chave>`. Nada é embutido como `data:` — a página roda sob `default-src 'self'`, e um desenho embutido simplesmente nunca apareceria.
- **As dependências hospedadas são pinadas**: `vendor/manifest.json` nomeia o pacote, a versão e o sha256 de cada arquivo, e o servidor confere o hash contra o que foi instalado (§3, Dependência externa).
- **O tema é uma CONSULTA, nunca um caminho**: um id que não nomeia tema nenhum cai no padrão, então uma query string nunca alcança um arquivo que o registro não nomeia.

#### Pessoas: onde o teto se move

A entrada **Pessoas** guarda as duas tabelas de sistema do teto de acesso, e cada linha abre a tela dela. Nada aqui é texto livre: a permissão é `objeto:ação` sobre uma **lista fechada**, e o que a pessoa marca é marcado a partir dela.

- **A tela do `role` desenha a lista fechada como marcações** — os objetos, e as ações que cada um aceita — e escreve o conjunto de volta pela rota de tabela que a `cli` já percorre. Um papel que nomeia uma permissão que o catálogo não tem **não derruba o AT**: o dizer do §4 é desenhado na tela, ao lado do papel, até que alguém a tire de lá.
- **A tela do `actor` é onde a credencial de máquina é minada.** Um token não é algo que uma pessoa digita, então o AT o sorteia, a linha guarda a derivação e o token aparece **uma vez** — ele nunca é lido de volta. A mesma tela dá à máquina um token novo, que é o preço de um perdido ou vazado, e o **revoga**: a linha fica, porque um ator é o nome que a auditoria vai carregar, e a porta simplesmente para de abrir.
- **Nada disso é uma segunda regra.** As telas são alcançáveis por quem carrega a permissão — o papel do administrador carrega o catálogo inteiro por construção — e todo o resto é recusado pelo servidor, nas palavras dele.

#### Design System e temas

- O Design System é de desenvolvimento da LLM. Crescimento gradual de componentes.

- O suporte a temas é parte estrutural do AT. Vários temas me ajudam a testar a força do Design System em cima de diferentes visões. Ao mesmo tempo que me fazem ficar feliz de usar o sistema. PRs de tema são bem-vindas, mas estão totalmente sujeitas ao meu julgamento pessoal e ficarei feliz em compartilhar meu péssimo gosto, se não quiser aceitar uma PR. Mas não se acanhe!

- **Tipografia por papel, uma família de interface**: a Nunito Sans (hospedada) é a única família da interface, com a pilha mono do sistema para código (`--font-mono`); a Quicksand sai da interface e sobrevive só como `--font-brand` (a telha da marca). A escala é `--type-caption` 12, `--type-body-sm` 13, `--type-body` 14 (o corpo de toda a interface), `--type-body-lg` / `--type-title` 16, `--type-page` 20 e `--type-display` 28; os pesos são 400, 500 e 600, e o título de bloco é 16/600. `base.css` não tem tamanho de fonte em literal (só `font-size: 0` do glifo do `.caret`); os temas congelados seguem com `--font-sans` e `--font-display` próprios.
- **O texto tem três papéis, e só três**: `--text-primary`, `--text-secondary` e `--text-tertiary`. Cada tema declara os três, e o contraste de cada um vale sobre **todas** as superfícies do tema (no claro: 15,6 / 9,2 / 6,1 no pior caso; no escuro: 16,3 / 8,2 / 6,4). Nenhum texto usa cor de borda, e `test_design.py` calcula essas razões direto dos hex do tema. O texto de um estado (`--success-text`, `--warning-text`, `--danger-text`, `--info-text`) é distinto do preenchimento do estado (`--success` etc., para barra e ponto) e lê sobre o `-soft` correspondente com pelo menos 4,5:1.

- **Os controles têm uma altura só**: `--control-h` (36px; 44px com ponteiro grosso) vale para `.btn`, `.input` e `select`, então um campo e um botão na mesma linha se alinham. `.btn` tem os tamanhos `-sm`/`-lg` e a variante `-ghost`; o campo é um bloco só (`.input` e as famílias de formulário, diálogo e popover); `.check` e `.radio` são desenhados pelo sistema, sem o checkbox nativo; e o foco é um só, `--focus-ring`.

- **O movimento só usa `opacity` e `transform`**, em tokens: `--dur-1..4` (80, 120, 180 e 240ms) e `--ease-enter`, `--ease-exit`, `--ease-move`. Tudo o que entra também sai (popover, diálogo, véu, toast e dica têm animação de saída, mais curta que a de entrada); a troca de tela é um fade (`<Transition mode="out-in">` só sobre a página, nunca sobre a `nav`); o switch e as barras animam por `transform`, e hover e foco de todo controle têm transição. A exceção declarada é `.foldable`. Com `prefers-reduced-motion` tudo é instantâneo.
- **Densidade e estado vazio.** A densidade é uma preferência deste navegador (`at.density`, como o movimento), escolhida em Configurações > Aparência: confortável (padrão, linha de tabela de 46px) ou compacta (36px, controles de 32px em ponteiro fino). Vive em `html[data-density="compact"]` no `base.css`, que só sobrescreve os tokens `--density-*`, `--cell-pad*` e `--control-h`; o `boot.js` a aplica antes da primeira pintura. Todo estado vazio de órfãos, projeto, lembretes e notas é o componente `EmptyState` (ícone, título, uma linha de texto e a ação já visível na tela).

- **O espécime (`/design`).** Uma página interna que mostra todo token e componente do sistema (papéis de texto, escala de tipo, rampas de cor, botões, campos, check e radio, chips de estado, cartões, tabela, popover, diálogo, toast, estado vazio, densidade) no tema e no lado vestidos, com os seletores de tema, lado e densidade no topo. Tem endereço e nenhuma linha no painel; o `base.css` mantém os comentários abaixo de 10% das linhas, então o sistema se revisa ali e não tela por tela.

- O tema vale para o WebApp inteiro, **tela de login incluída**: não existe página do AT que escape do Design System, e a entrada é a primeira impressão que ele tem que causar.

- O portal do Authelia **não** é uma tela do AT, e não há como vesti-lo com o Design System: o Authelia aceita logo, favicon, textos traduzidos e uma de quatro paletas, e nada além disso. O que o AT escreve no `asset_path` é o `logo.png`, o `favicon.ico` e, em `locales/en` e `locales/pt-BR`, só o título (`Login - AT · {{authelia}}` / `Entrar - AT · {{authelia}}`): o Authelia exige o `{{authelia}}` em cada texto, então o nome dele fica e o AT entra ao lado. Então o tema dele fica o mais neutro possível, e o `FAQ.md` diz de quem é aquela tela — educar sobre o que a pessoa está usando de fato faz parte do produto.

#### Templates

- AT usa `Vue`. Por mais que eu não goste de usar muitas dependências externas pelo risco de Supply Chain, e que a maioria disso seja causada por bibliotecas JavaScript, eu gosto do `Vue`. Acho uma perda válida pela gestão de templates que ele traz. Por mais que eu não esteja escrevendo esse código, não me agrada ver a LLM criando arquivos JavaScript individuais para páginas. Dificulta minha legibilidade e sou muito a favor de boa legibilidade.

#### TypeScript e frameworks

- WebApp do AT é escrito em TypeScript e _transpilado_ usando `ViteJS`. O TypeScript é bem escrito respeitando módulos e domínios, facilitando a gestão humana.
