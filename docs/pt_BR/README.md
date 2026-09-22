# Bill

Bill é um motor de tarefas determinístico. Ele roda **dentro de uma pasta**, e essa pasta vira a **Pasta de Trabalho** dele. Este repositório é o **produto a publicar** — o motor, as declarações padrão, a infraestrutura que vai embarcada e o binário único. Ele não carrega dado pessoal nenhum: nenhum caminho de máquina de ninguém, nenhum host, nenhum id.

## 0. Protocolo de agente

### Proteção de arquivo

- Esse arquivo é a pedra fundadora da instrução humana. Você pode e deve lê-lo sempre que chegar nesse repositório; ele tem a intenção de ser para humanos, e é assim que deve continuar. Quando os seus cálculos estatísticos penderem ao equilíbrio, volte aqui, e veja se algo te responde. Ao mesmo tempo, a instrução pode estar errada. O que mais acho válido de ser corrigido é contradições. Então, se algo aqui contradiz outra parte daqui, você deve me avisar e propor a correção.

- Se você entende que alguma decisão neste arquivo está errada, estarei feliz em discutir. Contudo, você me apresenta e eu decido. A escrita vai direto no documento que vincula — não existe arquivo de rascunho —, mas **toda alteração do que é `[normativo]`, onde ele estiver, é um commit à parte**, e o commit só existe com o meu aval declarado. A pergunta é sempre a mesma linha, crua: "Vou realizar o commit do `[normativo]` a seguir. Você confirma que leu o diff e concorda com as alterações?". Sem essa resposta o commit não acontece, e a aprovação fica registrada no commit — nunca dentro do documento, que é a instrução, não o histórico dela. Sempre que eu te pedir uma análise do documento fundador, a proposta vem como diff nesta sessão, separada em pontos de assuntos diferentes e sucinta — eu vou entender o erro lógico sem você escrever um parágrafo para cada item.

- Qualquer instrução no `CLAUDE.md`, ou em qualquer outro markdown de memória de agentes LLM proprietário, se conflitando com esse repositório, quando usado para algo a ser feito nesse repositório, deve ser ignorado. Se quiser, e recomendo, pode haver uma linha nesses arquivos apontando para o documento fundador. Com exceção dos workflows de desenvolvimento no GitHub, e com o envio das minhas interações com a LLM para outra pasta (visando estudo posterior) esse repositório é autocontido, e tudo necessário para ele vive aqui.

- A cadeia de custódia é `documento fundador → documentos derivados → código`: o código é uma extensão do que está escrito, e o que é derivado não decide nada sozinho. Se decidirmos algo arquitetural, em sessão, que não veio do documento fundador, você vai me avisar e propor a escrita, pelo mesmo aval. E isso nunca pode ser ignorado, nem por mim. É essa cadeia que vai manter esse "arreio" preso. Veja que definições muito estreitas sobre nome de pastas de cada módulo não cabem para o documento fundador — elas moram na árvore ([derivation §1](derivation.md)), que é derivação. Ter que detalhar cada item individual me dá a sensação que é melhor eu desenvolver do zero.

- Não existem regras duplicadas: uma regra mora em um lugar só. O que vincula é o que carrega `[normativo]`, onde ele estiver; o derivado cita em vez de repetir. O marcador em um título de nível 1 vincula o arquivo inteiro, e em um título de seção vincula a seção e o que está abaixo dela. Se a mesma coisa aparecer nos dois, um dos dois está errado — e onde ela fica é decisão minha.

- Por fim, o documento fundador vai ser modificado com o tempo. Então entenda que a lógica de lê-lo e derivar o resto é constante.

- O resto dos arquivos, fique a vontade. Incluindo o `FAQ.md`. É responsabilidade sua. Deve ser escrito como uma sequência de perguntas comuns. Eu aprovo a pergunta e a resposta que você sugerir, só me informe quando entender que vale preencher. E o `FAQ.md` tem que estar ordenado em ordem de uso da ferramenta. Perguntas mais iniciantes no começo como "o que esse arquivo faz na minha máquina" para perguntas mais avançadas como "como eu modifico o Bill ao meu bel-prazer". É no FAQ que mora a explicação do que está por baixo: qual tela é sua e qual é de terceiros.

### Forma de trabalho

- Sempre trabalhe em duas sessões por item, nunca uma. Na primeira, modo plano: explorar, discutir e fechar a decisão, sem escrever código. Antes do `/clear`, o plano tem que ser salvo fora da conversa — no `docs/en_US/backlog.md` — já com o que conta como pronto, para a segunda sessão não precisar perguntar. A segunda nasce limpa, lê o item no `docs/en_US/backlog.md` e implementa um item, do tamanho de uma sessão.

- **A discussão vem antes do BACKLOG, e a implementação sempre sai do BACKLOG.** Uma decisão só entra na lista depois de apaziguada, e nada se implementa que não esteja nela. Numa discussão longa, as implicações vêm **uma a uma**, e o que fecha é gravado e commitado na hora — o que está decidido não pode viver só na conversa, que morre. **A resposta simples a uma pergunta é a aprovação**: se eu propus uma coisa e você respondeu, não te pergunto de novo se está aprovado.

- Quando eu te disser que vou limpar a sessão, gere **de uma vez** o começo recomendado da sessão seguinte, em itálico, pronto para eu copiar e modificar como eu decidir, e com esta linha crua antes dele: "Prompt recomendado para a próxima sessão. Fique à vontade para utilizar ou não.". Ele diz qual item, onde ele está, o que conta como pronto e o que a sessão precisa saber antes de escrever a primeira linha.

- Nunca despeje arquivo ou saída grande no contexto: filtre, corte ou delegue a um subagente e traga só a conclusão; não releia o que já está na conversa, não repita o que já foi dito e não gaste turno à toa — cada turno reenvia tudo. E onde faltar informação para decidir, pergunte antes de agir, com o custo de cada opção à mostra: o que não estiver autorizado, não acontece.

## 1. Origem [contexto]

### Introdução

O Bill é um software completamente escrito por LLM. A primeira versão deste documento foi escrita por mim — ela está no histórico do git, que é onde vive o Manifesto, a semente deste repositório — e de lá para cá quem o modificou foi a LLM, à medida que ela encontrava contradições ou que decidíamos coisas novas; cada alteração passou pelo meu aval (§0). O _ghostwriter_ da PoC é Claude Code + DeepSeek Flash versão 4, e a partir do início do desenvolvimento final do projeto, versão 4.1. A escolha é proposital: primeiro é o preço. Segundo se eu for ter meus dados usados para treinamento, que seja para algo que volta como pesos abertos para a comunidade. Acho que a matemática é simples. Também é uma tentativa de provar que temos LLM suficiente já. Talvez assim parem de uma vez essa corrida sem fim por uma AGI.

O Bill é um software pensado para mim. Fruto de algumas semanas de foco-quase-burnout em LLM e a tentativa de controlar o incontrolável. Entre estudos de harness voltados a segurança, eu testava visões arquiteturais de software ou temas baseados em redes sociais antigas direto em um programa que apelidei de `Bill`.

Esse documento visa ser uma tentativa de fazer o agente LLM entender a origem conceitual do Bill, evitando a Teoria do Fruto da Árvore Envenenada, onde erros se empilham e o harness criado já não faz mais sentido algum depois de alguns bilhões de tokens.

Além disso, ele visa ser extremamente arquitetural. Se entender que os "arreios" dessa arquitetura não estão bons o suficiente, talvez me falte conhecimento. Poste uma issue, ficarei feliz em aprender!

### O nome

Bill é um nome que aparece em minha cabeça quando leio a palavra bootstrap. O motivo exato, eu não sei dizer. Mas gosto muito da palavra bootstrap.

A história é demasiadamente interessante. "Erguer-se pelas próprias abas da bota" (minha tradução livre de _to pull oneself up by one's bootstraps_), é uma frase inglesa do século XIX inicialmente tratada como uma piada sarcástica pela impossibilidade de se erguer (do ar ou da água, por exemplo) pelas próprias abas da bota. Ironicamente, é isso que nossos dispositivos fazem (o famoso _boot_). Computadores e smartphones tem um código padrão executado ao ligar o dispositivo. Ele que carrega o sistema operacional que você conhece (Windows ou Linux). O Bill tem esse propósito de ser um _bootstrap_ para o que ele se propõe a ser. No momento eu estou fazendo esse bootstrap. O Bill nasceu em um caos enquanto eu estudava harness LLM e achava que tinha resolvido todos os problemas do mundo. Agora, estou migrando o que desenvolvi a toque de caixa, para o formato a ser publicado. Bem nos moldes do [Linux From Scratch](https://www.linuxfromscratch.org/) (que inclusive recomendo fortemente para aprender Linux).

Além disso, uma vez um conhecido disse que parece que todos os garçons de filmes de faroeste chamam Bill. Rimos muito, mas acredito que não haja nenhuma base estatística nisso. De qualquer forma, gosto de pensar que estou falando "Ei, Bill. Encha meu copo.". Com um sotaque interiorano, ou só belorizontino mesmo.

## 2. Propósitos e limites [contexto]

### Para o que ele se propõe

A ideia do Bill é ser um motor de tarefas determinístico, sendo utilizável por uma pessoa, por um programa ou por uma LLM. Eu gosto de máquina fazendo coisas chatas para mim. Eu gosto de facilidade de acesso com segurança. Eu gosto de Autonomia Tecnológica. E eu não quero gastar tempo desenvolvendo isso. E eu gosto muito de gastar pouco dinheiro. Aqui aceito gastar dinheiro em prol de chegar nesse objetivo, almejando lá na frente não precisar das massivas LLMs novamente.

Mas, além disso, o Bill é um ambiente de trabalho minimalista — mínimo para ser **funcional**, não mínimo para ser **estético**; os [temas](#design-system-e-temas) estão aqui para isso. "Não preciso de muito para ser produtivo em um ambiente tecnológico". Isso é um manifesto em si: dá para ser produtivo com um binário e uma pasta. O amparo — a infraestrutura de suporte (§7) — fica fora do mínimo: entra quando eu quiser, e a ausência dele não tira funcionalidade nenhuma do Bill. Várias extensões do Bill vão morar como algo meu, inicialmente. Enviar minha biblioteca de jogos zerados para o rawg usando a base da Steam e do Heroic não cabem na parte padrão do Bill. E também abrir a possibilidade de extensões da comunidade, sem uma curadoria, com todo o risco de ataques de Supply Chain, é complicado. Por isso Bill nasce como é, analisando funcionalidade a funcionalidade se ela cabe aqui.

### O Bill tenta reescrever a roda?

Sim, ele tenta. Tem muitas aplicações mais avançadas para partes específicas do Bill. Se você entende que seu Projeto não pode ser gerenciado aqui, e que você precisa de muito mais funções, eu te entendo, e infelizmente o Bill não é para você. Mas para mim é mais do que o suficiente. No começo, eu havia definido que tarefas não eram deletadas. Elas deviam ser canceladas, para manter histórico. Acho válido, e a função existe. Mas se eu quero deletar eu posso. Mais detalhes sobre [tabelas](architecture.md#tabelas) abaixo. Existem ferramentas como Obsidian e AnyType para arquivos e dados estruturados. Essas ferramentas são fantásticas e não quero substituí-las.

### Onde executar o Bill

A ideia do Bill é que rode em uma máquina. Uma Turing-compatível. Pode ser seu desktop, seu notebook, seu NAS, uma VPS. Eu gostaria que fosse leve — leve no que o binário exige da máquina, não no tamanho do artefato, que carrega o interpretador e as bibliotecas empacotados. Mas não estou a fim de aprender Go ou Rust. Então vamos de Python. "Todo mundo" sabe Python. E se um ESP32 roda Micropython, é porque posso almejar ir longe aqui.

O Bill tem dois caminhos de uso, e os dois são suportados: o **hospedado**, em que ele é o binário e a pasta, e o **container**, em que ele monta um ambiente de serviços. A escolha é da pessoa, e ela pode mudar de ideia depois; o que cada caminho garante, e o que não garante, está no [§6](#6-os-dois-caminhos-de-uso-normativo).

## Índice

O `§N` é o id estável do artigo, e ele não muda de dígito quando o artigo muda de arquivo. A tabela diz o que cada artigo é e onde ele mora.

| § | o que é | onde mora |
|---|---|---|
| §0 | o protocolo do agente: como ler e como alterar este repositório | aqui |
| §1 | a origem: de onde o Bill veio e por que esse nome | aqui |
| §2 | os propósitos e os limites: o que ele é e o que ele recusa ser | aqui |
| §3 | as regras: segurança, código e delivery, dependência externa | [`rules.md`](rules.md) |
| §4 | a arquitetura: as camadas, as tabelas e os segredos | [`architecture.md`](architecture.md) |
| §5 | as interfaces: `cli`, WebApp e Wizard | aqui |
| §6 | os dois caminhos de uso | aqui |
| §7 | o caminho container: os passos | aqui |
| §8 | as extensões e os plugins | aqui |
| §9 | o ambiente de teste end-to-end | aqui |
| §10 | a derivação: a árvore, a Pasta de Trabalho e a operação | [`derivation.md`](derivation.md) |
| §11 | o glossário: o que um nome significa | [`glossary.md`](glossary.md) |

## 5. Interfaces [normativo]

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

## 6. Os dois caminhos de uso [normativo]

- Existem dois caminhos, e os dois são suportados. Eles diferem no que garantem, e a diferença é declarada aqui para que ninguém decida com informação errada.

### Caminho hospedado

- É o Bill e a pasta. O binário é aberto na Pasta de Trabalho, o WebApp sobe pelo comando, o Wizard abre quando não há parâmetro, e a `cli` faz o resto. Não há container nenhum, e a pessoa não precisa de Podman nem de nada além do binário.

- **Não há isolamento**, e o Bill não promete nenhum neste caminho: um comprometimento do WebApp é um comprometimento de processo na sua máquina, com acesso ao que o seu usuário tem. Em troca, o padrão é não sair do laço local, e sair dele exige autenticação e TLS.

- Sair do laço local, aqui, é `bill webapp --include-caddy`: o Caddy que veio dentro do binário termina o TLS e publica o Bill. Sem a bandeira, o WebApp serve em HTTP e só em `127.0.0.1`.

- As integrações (§7) podem existir sem container: quem instala o serviço por conta e aponta o Bill para ele usa o serviço, com a ciência de que o estado daquele serviço não é mais assunto do Bill — e, portanto, que o backup da pasta não o cobre. A aprovação de uma demanda arriscada, aqui, acontece na própria máquina: o serviço `notifier` é do caminho container.

- Expor o Bill pelo caminho hospedado com o Authelia do caminho container é o **modo avançado**, e não é suportado: quem quiser o portão, usa o caminho container.

### Caminho container

- É o Bill montando um ambiente de serviços em containers de imagens fixadas (§7). Aqui existe isolamento, e ele existe por um motivo específico: **conter o raio de explosão de cada serviço**. O comprometimento do `ntfy` alcança a notificação e nada mais; o do corretor alcança o corretor. O que cada serviço expõe é o que ele se propõe a fazer, e nada além.

- Serviço que precisa falar com o Bill — e não o Bill com ele — tem o escopo delimitado: credencial com papel declarado, e só o que aquele papel permite. Mínimo privilégio, aplicado. No `ntfy`, isso é a ACL por tópico: o Bill publica, o celular lê, e nenhum dos dois tokens serve para o resto.

- O caminho container é o que sustenta o portão de autenticação (§7b), e é onde o Bill entra como mais um app atrás dele.

### A virada entre os caminhos

- A passagem de um caminho para o outro é uma **virada**, e virada é transacional: o Bill executa o conjunto de ações e, se alguma não termina com sucesso, volta tudo ao estado anterior. O ambiente não fica pela metade, e o que havia antes continua funcionando.

- No sentido do container, o Forms continua ligado até o Authelia estar **provado** funcionando na frente do Bill — não é "o container subiu", é o Bill recebendo a identidade que espera, pelo caminho real, com o segredo do portão. Só então o Forms se desliga.

- Se o portão cai depois, já com a virada commitada, o Bill **fecha** e avisa: "Portal de autenticação indisponível. Utilize o Wizard para retornar o Bill para modo forms." Ele não reabre o Forms sozinho — reabrir sozinho seria trocar a segurança por conveniência, sem ninguém decidir.

- Se o Bill encontra um ambiente de infraestrutura configurado na pasta mas não encontra o ambiente, ele pergunta: "Foi detectado que você tem um ambiente de infraestrutura configurado nesse ambiente, mas o ambiente de infraestrutura não foi encontrado. Você deseja instalar novamente o Podman/Docker ou restaurar o bill para modo hospedado na máquina?". É a promessa do backup aparecendo na tela: a pasta voltou, e o que faltava era só o chão.

## 7. Caminho container: os passos [normativo]

### Passos de configuração

- Os passos abaixo são o caminho container. Eles não são requisito para usar o Bill: sem eles, o que se tem é o caminho hospedado (§6), que também é suportado. "Obrigatório" aqui quer dizer obrigatório para este caminho.

#### a. Criar ambiente container (obrigatório)

- Aqui é a virada principal do ambiente. A pessoa precisa ter o Podman instalado. O Bill verifica se ele existe e, se não existir, oferece as duas saídas: instalar o Podman, ou seguir no caminho hospedado. Ele não instala o Podman sozinho. A partir daí, o Bill orquestra o ambiente e os serviços, que sobem como containers de imagens fixadas.

- É uma função complexa com muita possibilidade de erro e de falha de segurança. As decisões de segurança que a cercam estão em [Segurança](rules.md#segurança).

- Podman é o escolhido para containers. `dnsmasq` e o Caddy são os primeiros serviços. O primeiro para customizar as urls de acesso e o segundo para publicar o Bill, agora em container, pelo isolamento.

#### b. Instalar provedor de identidade como container (obrigatório)

- O Bill tem autenticador próprio, e no caminho container ele é o portão: um provedor de identidade externo, aqui o Authelia, à frente de tudo. Ele fica responsável pela autenticação de todos os serviços existentes aqui, e o Bill entra como mais um app — não como exceção.

- O Authelia fala **OIDC** com quem fala OIDC, e **forward-auth** com quem não fala. Sonarr, Radarr e Prowlarr não falam OIDC, e é o forward-auth que lhes dá a mesma experiência: um login no portal, o cookie valendo para todos. O Bill também não fala OIDC com ele: entra por forward-auth, como os outros.

- A divisão é: **quem** é ator é do Bill, e **como** se prova que é ele é do Authelia. A tabela `actor` (§4) guarda identidade, papel e a credencial hasheada — e no caminho container quem usa a credencial do Authelia é o Authelia.

- O que o Authelia **não** é: provedor de login com Google. Ele não faz o papel de relying party, e isso é decisão do projeto, não configuração. Login com terceiros não faz parte do Bill.

- Aqui não há autenticação com a cara do Bill. O portal é do Authelia, e o que o Bill faz é pedir que ele seja o mais neutro possível, para não parecer o que não é (§5).

- O que o Bill exige de quem chega com identidade é o **segredo do portão**: um valor sorteado pelo Bill na instalação, escrito no Caddyfile que ele mesmo gera, colado pelo Caddy em todo pedido que carrega identidade, e recusado por quem não o traz. É o M2M entre o Caddy e o WebApp do Bill, e o Authelia nunca o vê.

#### c. Instalar WebApp como container (obrigatório)

- O WebApp, principal forma de usar o Bill, é instalado como um container. Visa diminuir o raio de explosão em uma aplicação web comprometida.

#### d. Instalar corretor ortográfico e gramatical como container (opcional)

- O padrão do Bill para correção de textos é LanguageTool, hoje a ferramenta que cumpre o serviço `spelling-checker` (§4). Ela serve para sublinhar os erros na tela de edição. Bem útil.

- Este é o corretor do **texto da pessoa**, em tempo de execução. O corretor dos documentos do repositório é outro, e é ferramenta de desenvolvimento ([derivation §3](derivation.md)).

#### e. Instalar VPN (opcional)

- O Bill permite configurar uma VPN. Aqui ela é relevante, pois permite criar uma rede privada para que múltiplos dispositivos conversem entre si. Logo se o Bill WebApp roda na sua máquina pessoal, fica acessível de forma segura do seu celular, em qualquer lugar. Aqui estou utilizando Tailscale. É proprietário, mas evita que seja necessário um servidor na nuvem. Suporte a Headscale no futuro.

#### f. Instalar notificador como container (opcional)

- Com tudo configurado, a cereja do bolo é o `ntfy`, hoje a ferramenta que cumpre o serviço `notifier` (§4). Os lembretes configurados podem ser notificados diretamente como um Push Notification, e é por ele que chega a aprovação de uma demanda que passou do limiar de risco.

- É aqui que entra a primeira funcionalidade graduada: os níveis dela e o que cada um custa vivem em [funcionalidades](functionalities.md).

## 8. Extensões e plugins [normativo]

- A extensão existe para ensinar o Bill, e a primeira delas é o mapa de gíria: é dado que muda por região, por pessoa e por época, e esperar uma release para ser entendido é caro demais.

- **Nenhuma extensão executa código hoje.** A primeira classe é **dado puro**: uma pasta com uma declaração e os dados, sem uma linha executável. Um plugin de dados não tem presença em execução nenhuma — não é processo, não é leitor: quem lê a frase é o Bill, e o plugin só diz como traduzir. Por isso ele não pede permissão de leitura; pedir seria teatro, e aviso de teatro ensina a clicar em "aceito" sem ler o próximo.

- **O plugin carrega um manifesto**, e o manifesto declara o que ele faz no ambiente. As permissões são granulares e a pessoa vê o que está instalando. A primeira permissão da história do Bill é sobre o que o plugin **altera**: *"Esse plugin pode alterar suas palavras antes de ser analisado pelo motor (core) do Bill."* A frase da permissão é do **produto**, renderizada pelo nome interno no `i18n` do produto — o plugin apenas referencia o id, porque um aviso escrito por quem está sendo avisado não é aviso. O plugin pode acrescentar uma nota de autoria, marcada como dele.

- **A instalação amarra um review a uma hash.** O Bill vê o que existe em disco e mantém o estado; copiar para a pasta faz ele **enxergar**, e o ato de instalar é o que conta. A pasta inteira do plugin é hasheada, **só o conteúdo, em ordem canônica** — sem hora de modificação, sem permissão, sem pasta vazia —, e qualquer byte alterado muda a hash, invalida o review e derruba a nota. As aceitações precisam ser feitas de novo, o que fecha o furo clássico de confiar no autor: a coisa que você aprovou e a coisa que roda depois são a mesma, ou o Bill sabe que não são.

- O caminho de volta da nota é um **review explícito**, em um de três modos: *eu li o que ele faz*, *eu pedi a uma IA para ler o que ele faz*, *eu confio em quem fez*. Ninguém verifica a declaração — é o único formato possível —, e é por isso que a nota se apresenta como declaração (§3, A postura de segurança).

- O estado dos plugins mora em `app/`, em arquivo, e não nas tabelas. Como a pasta é da pessoa, dá para editar esse estado e mentir para a própria nota: isso não é falha do desenho, porque a hash protege você **do autor**, não o autor de você.

- **Código é a última opção.** Código que executa é código difícil de conter, e antes dele o plano é entregar extensão em formas bem mais estabelecidas.

## 9. Ambiente de teste end-to-end [normativo]

- O teste principal é verificar se, com o Podman instalado, executar as ações do Bill funciona perfeitamente. Esse teste acontecerá em VMs Mac, Linux e Windows.

- Ele é **automatizado de ponta a ponta**: nenhuma parte depende de olho ou de mão numa tela. O script sobe a VM, abre o binário e verifica o que voltou — Podman ausente faz o Bill oferecer as duas saídas; Podman presente sobe o ambiente com as imagens no pin; uma instância à frente do pin avisa e segue; o Bill recusa subir na rede sem autenticação e sobe com ela; o WebApp responde atrás do portão; e a Pasta de Trabalho criada na primeira execução é só o que o §3 descreve.

- O caminho hospedado tem portão próprio, e é barato porque não depende de VM nem de container: a primeira subida pede o admin e não deixa o Bill expor sem ele; sem autenticação o Bill escuta só `127.0.0.1`; expor sem TLS é recusado; a virada para o container volta atrás inteira quando alguma ação não fecha; e o portão caído fecha o Bill com a frase à mostra.

- O interpretador tem a sua própria régua, e ela roda como teste: frases que precisam funcionar, frases que precisam ser recusadas, e frases ambíguas que precisam ser devolvidas em pergunta. Sem LLM, sem rede e sem placa de vídeo.

- O teste **não é o critério de pronto de cada função** — uma função fica pronta pelo que o `docs/en_US/backlog.md` diz que ela é. Ele é o portão da primeira publicação no GitHub, e dali em diante.

## O que ainda não está aqui

`docs/en_US/backlog.md` guarda o que vem a seguir, com o que conta como pronto para cada item.

Três dívidas nasceram das decisões desta sessão, e as três estão nomeadas para não virarem surpresa:

- **O código.** Nada do que ficou decidido aqui está construído: o ator, a auditoria, o filtro de demandas, a postura, o interpretador, os plugins. Tudo tem item no `docs/en_US/backlog.md`.
- **A lista do corretor.** Ela nasceu grande — 220 palavras em português e 141 em inglês —, e o motivo está escrito no cabeçalho dela: o dicionário do corretor vem de frequência de legendas e erra o registro formal, onde "seção", "deleção" e "registrar" não aparecem. Se essa lista crescer sozinha, o gate virou enfeite, e o diff é o lugar de perceber.
- **O `FAQ.md`.** Ele ainda não existe, e agora tem trabalho esperando: dizer o que está por baixo — qual tela é do Bill e qual é de terceiros —, e que escrever bem é o melhor remédio contra um mal-entendido do interpretador.
