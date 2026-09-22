# 5. Interfaces [normativo]

### Linha de comando (`cli`), aplicação web (WebApp) e interface Tkinter (Wizard)

- Ao abrir o Bill, seja em linha de comando, seja direto pela interface gráfica, temos o "Painel de Controle". É uma interface em Tkinter, o Wizard. Aqui são configuradas as "entranhas" do ambiente do Bill, sendo sua primeira camada a aplicação web.

- Chamar o binário direto do terminal carrega a interface Tkinter. Qualquer outro parâmetro passado faz o programa agir como uma `cli`. `bill ajuda`, ou `bill help`, mostra como usar a cli completamente. Você pode modificar nas configurações para o comando `bill` não abrir o Tkinter e sim o `bill help`.

- A linha de comando funciona para tudo do Bill. Qualquer funcionalidade que ele exponha, seja na API REST (utilizada pelo frontend do WebApp), seja no WebApp em si, é acessível pela linha de comando.

- O Wizard é uma tela que permite realizar configurações mais críticas do Bill que eu não queria deixar disponível na rede. Ele tem papéis que não se mudam de lugar: a **primeira subida**, em que a Pasta de Trabalho é confirmada e o primeiro admin é criado; a **instalação de serviços**, e só ele instala; a **volta ao modo Forms**, quando o portão de autenticação cai; e a gestão das chaves principais no modo avançado.

- O `cli` executa apenas localmente, em exceção quando está comunicando com APIs externas para devida configuração. E é ele, ou o Wizard, que devolve o Bill ao modo Forms: as duas são superfícies locais, e é por isso que a volta existe.

- Papel e permissão **não** são assunto do Wizard: isso é tela do WebApp, e o atrito de fazer admin por lá não se paga. O Wizard fica com o que só ele pode fazer.

### A camada de interpretação

- A linguagem natural entra como **recurso** do WebApp e da `cli`, e não como uma quarta superfície: nada se torna possível só por falar. O que a pessoa digita vira uma proposta, e o que ela pode propor é o que ela já pode fazer.

- **O interpretador é determinístico.** Não há LLM no tempo de execução: a LLM ajuda a **escrever** o vocabulário, e o que roda é código com dado. Isso é o que corta o cordão com o token de terceiros, e é por isso que o Bill não precisa de placa de vídeo para entender uma frase.

- O que o interpretador consulta é o **vocabulário**, por idioma, empacotado no produto junto dos blocos de `i18n`, porque traduzir vocabulário e traduzir texto é a mesma tarefa. O vocabulário é dado burro: pares expressão → expressão canônica, com idioma e região, e nada condicional. O que depende de contexto é gramática, e gramática é código do produto.

- **O interpretador propõe; o core valida e escreve.** Uma ação por requisição enquanto não existir uma API de lote; o dia em que existir, o lote é uma ação, com permissão própria. A unidade de tudo é a operação da API do core, e a API REST é uma das portas para ela.

- **O teto de acesso é o que o ator pode; o limiar de risco é o que ele pode sem perguntar.** Toda demanda tem um **risco**, medido pelo core a partir do que o produto declara por ação e por argumento — nunca pelo interpretador, porque quem pede não avalia o próprio risco. O **limiar** mora nas configurações: abaixo dele a ação corre, acima dela a pessoa aprova. O risco de cada ação é ajustável em `settings.json`, e o de uma extensão é aceito no momento de instalar.

- A aprovação chega por notificação, e a notificação é **campainha, não chave**: o toque abre o Bill e a aprovação acontece dentro dele, com a sessão valendo. A credencial não mora na central de notificações. Um job que roda sozinho pode ser aprovado assim, e a aprovação é uma linha na auditoria, separada da demanda que esperou.

- **A função de agente é desligável**, e desligá-la é tirar o interpretador da API do core: quem não quer a camada de linguagem usa o Bill sem ela e não perde mais nada além dela.

- Como o interpretador é determinístico, **a responsabilidade volta para quem pediu**: um mal-entendido é defeito nosso ou frase mal escrita, e o rastro diz quem pediu. O `FAQ.md` diz isso com todas as letras, junto do conselho de que escrever bem é o melhor remédio.

### Aplicação WebApp

O WebApp serve três coisas e nada mais: **a página construída**, **a aparência** (`base.css`, os temas, os desenhos e as fontes hospedadas) e o **JSON** que a página lê. A página não tem regra nenhuma — o servidor decide, a página desenha.

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

- **Os desenhos e as fontes são servidos POR NOME**, por `/icons/<nome>` e `/vendor/<chave>`. Nada é embutido como `data:` — a página roda sob `default-src 'self'`, e um desenho embutido simplesmente nunca apareceria.
- **As dependências hospedadas são pinadas**: `vendor/manifest.json` nomeia o pacote, a versão e o sha256 de cada arquivo, e o servidor confere o hash contra o que foi instalado (§3, Dependência externa).
- **O tema é uma CONSULTA, nunca um caminho**: um id que não nomeia tema nenhum cai no padrão, então uma query string nunca alcança um arquivo que o registro não nomeia.

#### Design System e temas

- O Design System é de desenvolvimento da LLM. Crescimento gradual de componentes.

- O suporte a temas é parte estrutural do Bill. Vários temas me ajudam a testar a força do Design System em cima de diferentes visões. Ao mesmo tempo que me fazem ficar feliz de usar o sistema. PRs de tema são bem-vindas, mas estão totalmente sujeitas ao meu julgamento pessoal e ficarei feliz em compartilhar meu péssimo gosto, se não quiser aceitar uma PR. Mas não se acanhe!

- O tema vale para o WebApp inteiro, **tela de login incluída**: não existe página do Bill que escape do Design System, e a entrada é a primeira impressão que ele tem que causar.

- O portal do Authelia **não** é uma tela do Bill, e não há como vesti-lo com o Design System: o Authelia aceita logo, favicon, textos traduzidos e uma de quatro paletas, e nada além disso. Então o tema dele fica o mais neutro possível, e o `FAQ.md` diz de quem é aquela tela — educar sobre o que a pessoa está usando de fato faz parte do produto.

#### Templates

- Bill usa `Vue`. Por mais que eu não goste de usar muitas dependências externas pelo risco de Supply Chain, e que a maioria disso seja causada por bibliotecas JavaScript, eu gosto do `Vue`. Acho uma perda válida pela gestão de templates que ele traz. Por mais que eu não esteja escrevendo esse código, não me agrada ver a LLM criando arquivos JavaScript individuais para páginas. Dificulta minha legibilidade e sou muito a favor de boa legibilidade.

#### TypeScript e frameworks

- WebApp do Bill é escrito em TypeScript e _transpilado_ usando `ViteJS`. O TypeScript é bem escrito respeitando módulos e domínios, facilitando a gestão humana.
