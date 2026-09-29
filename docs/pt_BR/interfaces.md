# 5. Interfaces [normativo]

### Linha de comando (`cli`), aplicação web (WebApp) e interface Tkinter (Wizard)

- Ao abrir o AT, seja em linha de comando, seja direto pela interface gráfica, temos o "Painel de Controle". É uma interface em Tkinter, o Wizard. Aqui são configuradas as "entranhas" do ambiente do AT, sendo sua primeira camada a aplicação web.

- Chamar o binário direto do terminal carrega a interface Tkinter. Qualquer outro parâmetro passado faz o programa agir como uma `cli`. `at-cli ajuda`, ou `at-cli help`, mostra como usar a cli completamente. Você pode modificar nas configurações para o `at-cli` sem palavra abrir a ajuda em vez do Tkinter.

- A linha de comando funciona para tudo do AT. Qualquer funcionalidade que ele exponha, seja na API REST (utilizada pelo frontend do WebApp), seja no WebApp em si, é acessível pela linha de comando.

- O Wizard é uma tela que permite realizar configurações mais críticas do AT que eu não queria deixar disponível na rede. Ele tem papéis que não se mudam de lugar: a **primeira subida**, em que a Pasta de Trabalho é confirmada e o primeiro admin é criado; a **instalação de serviços**, e só ele instala; a **volta ao modo Forms**, quando o portão de autenticação cai; e a gestão da Chave Principal no modo avançado.

- **A primeira subida acontece na PÁGINA**, e não mais só no terminal: numa pasta sem administrador nenhum, o WebApp serve o formulário que cria o primeiro — nome e Chave Principal (16+, uma frase) —, e só no laço (§3, [Acesso e exposição](rules.md#acesso-e-exposição)). A `cli` mantém a mesma porta, e é a regra desta seção que tudo do `Wizard` seja alcançável por ela: `at-cli admin` pergunta o nome e lê a Chave sem eco, e as duas dizem as MESMAS strings — a do formulário é a do bloco `admin` do catálogo, e não uma segunda frase que possa divergir. O Wizard não perde o papel — a tela do primeiro admin é dele.

- O `cli` executa apenas localmente, em exceção quando está comunicando com APIs externas para devida configuração. E é ele, ou o Wizard, que devolve o AT ao modo Forms: as duas são superfícies locais, e é por isso que a volta existe.

- Papel e permissão **não** são assunto do Wizard: isso é tela do WebApp, e o atrito de fazer admin por lá não se paga. O Wizard fica com o que só ele pode fazer.

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

O painel tem as entradas:

| entrada | o que é |
|---|---|
| **Tarefas** | a **árvore de projetos** — um projeto com a contagem das tarefas que o nomeiam, os subprojetos indentados, e por último o nó **"sem projeto"**, que abre as tarefas que projeto nenhum reivindica. Um projeto abre uma **página** com as tarefas de toda a sua subárvore, cada linha dizendo de que subprojeto ela veio. |
| **Arquivos** | a árvore de `prose/` e a página de um arquivo — lida, e escrita no lugar quando o servidor diz que pode. |
| **Tabelas** | o vocabulário: toda tabela declarada, com a sua contagem. |
| **Pessoas** | os atores e os papéis: quem pode agir, com que teto. Só o admin abre. |
| **Serviços** | cada serviço configurado, o estado dele e os tokens que ele precisa — inclusive o do `ntfy`. |
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

- O tema vale para o WebApp inteiro, **tela de login incluída**: não existe página do AT que escape do Design System, e a entrada é a primeira impressão que ele tem que causar.

- O portal do Authelia **não** é uma tela do AT, e não há como vesti-lo com o Design System: o Authelia aceita logo, favicon, textos traduzidos e uma de quatro paletas, e nada além disso. Então o tema dele fica o mais neutro possível, e o `FAQ.md` diz de quem é aquela tela — educar sobre o que a pessoa está usando de fato faz parte do produto.

#### Templates

- AT usa `Vue`. Por mais que eu não goste de usar muitas dependências externas pelo risco de Supply Chain, e que a maioria disso seja causada por bibliotecas JavaScript, eu gosto do `Vue`. Acho uma perda válida pela gestão de templates que ele traz. Por mais que eu não esteja escrevendo esse código, não me agrada ver a LLM criando arquivos JavaScript individuais para páginas. Dificulta minha legibilidade e sou muito a favor de boa legibilidade.

#### TypeScript e frameworks

- WebApp do AT é escrito em TypeScript e _transpilado_ usando `ViteJS`. O TypeScript é bem escrito respeitando módulos e domínios, facilitando a gestão humana.
