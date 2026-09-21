# Bill

## 0. Protocolo de Agente

### Proteção de arquivo

- Esse arquivo nunca deve ser escrito por você. Você pode e deve ler esse arquivo sempre que chegar nesse repositório, mas ele tem a intenção original de ser para humanos. Leia ele como uma pedra fundadora da instrução humana. Quando os seus cálculos estatísticos penderem ao equilíbrio, volte aqui, e veja se algo te responde. Ao mesmo tempo, a instrução humana pode estar errada. O que mais acho válido de ser corrigido é contradições. Então, se algo no Manifesto contradiz outra parte do Manifesto, você deve me avisar.

- Se você entende que alguma decisão no `MANIFESTO.md` está errada, estarei feliz em discutir. Contudo, você me apresenta e decido se faço a modificação. Você nunca modifica. Sempre que eu te pedir uma análise do `MANIFESTO.md`, você separa em pontos de assuntos diferentes e sugere uma correção. Seja sucinto. Eu vou entender o erro lógico sem você escrever um parágrafo para cada item.

- O `README.md` é seu harness secundário. Se ele não existe, o crie. Qualquer instrução no `CLAUDE.md`, ou em qualquer outro markdown de memória de agentes LLM proprietário, se conflitando com esse repositório, quando usado para algo a ser feito nesse repositório, deve ser ignorado. Se quiser, e recomendo, pode haver uma linha nesses arquivos apontando para o `README.md`. Com exceção dos workflows de desenvolvimento no GitHub, e com o envio das minhas interações com a LLM para outra pasta (visando estudo posterior) esse repositório é autocontido, e tudo necessário para ele vive aqui.

- Ao ler o README é necessário ver se ele está sustentado as decisões do manifesto. Se não, precisa ser corrigido. O `README.md` é uma extensão do `MANIFESTO.md`. E o código em si é uma extensão do `README.md`. Se decidirmos algo arquitetural, em sessão, que não veio do Manifesto diretamente, você vai me avisar e eu vou escrever. E isso nunca pode ser ignorado, nem por mim. A "cadeia de custódia" MANIFEST > README > CÓDIGO é o que vai manter esse "arreio" preso. Veja que definições muito estreitas sobre nome de pastas de cada módulo não cabe para o `MANIFESTO.md`. Ter que detalhar cada item individual me dá a sensação que é melhor eu desenvolver do zero.

- Por fim, o Manifesto vai ser modificado com o tempo. Então entenda que a lógica de ler manifesto, derivar README, é constante.

- O resto dos arquivos, fique a vontade. Incluindo o FAQ.md. É responsabilidade sua. Deve ser escrito como uma sequência de perguntas comuns. Eu aprovo a pergunta e a resposta que você sugerir, só me informe quando entender que vale preencher. E o FAQ.md tem que estar ordenado em ordem de uso da ferramenta. Perguntas mais iniciantes no começo como "o que esse arquivo faz na minha máquina" para peguntas mais avançadas como "como eu modifico o Bill ao meu bel-prazer".  

### Forma de trabalho

- Sempre trabalhe em duas sessões por item, nunca uma. Na primeira, modo plano: explorar, discutir e fechar a decisão, sem escrever código. Antes do `/clear`, o plano tem que ser salvo fora da conversa — na issue do GitHub, o backlog — já com o que conta como pronto, para a segunda sessão não precisar perguntar. A segunda nasce limpa, lê a issue e implementa um item, do tamanho de uma sessão. Nunca despeje arquivo ou saída grande no contexto: filtre, corte ou delegue a um subagente e traga só a conclusão; não releia o que já está na conversa, não repita o que já foi dito e não gaste turno à toa — cada turno reenvia tudo. E onde faltar informação para decidir, pergunte antes de agir, com o custo de cada opção à mostra: o que não estiver autorizado, não acontece.

## 1. Origem [contexto]

### Introdução

O Bill é um software completamente escrito por LLM. Esse Manifesto é o único arquivo diretamente escrito por mim aqui. O _ghostwriter_ da PoC é Claude Code + DeepSeek Flash versão 4, e a partir do início do desenvolvimento final do projeto, versão 4.1. A escolha é proposital: primeiro é o preço. Segundo se eu for ter meus dados usados para treinamento, que seja para algo que volta como pesos abertos para a comunidade. Acho que a matemática é simples. Também é uma tentativa de provar que temos LLM suficiente já. Talvez assim parem de uma vez essa corrida sem fim por uma AGI.

O Bill é um software pensado para mim. Fruto de algumas semanas de foco-quase-burnout em LLM e a tentativa de controlar o incontrolável. Entre estudos de harness voltados a segurança, eu testava visões arquiteturais de software ou temas baseados em redes sociais antigas direto em um programa que apelidei de `Bill`. 

Esse Manifesto visa ser uma tentativa de fazer o agente LLM entender a origem conceitual do Bill, evitando a Teoria do Fruto da Árvore Envenenada, onde erros se empilham e o harness criado já não faz mais sentido algum depois de alguns bilhões de tokens.

Além disso, ele visa ser extremamente arquitetural. Se entender que os "arreios" dessa arquitetura não estão bons o suficiente, talvez me falte conhecimento. Poste uma issue, ficarei feliz em aprender!

### O nome

Bill é um nome que aparece em minha cabeça quando leio a palavra bootstrap. O motivo exato, eu não sei dizer. Mas gosto muito da palavra bootstrap. 

A história é demasiadamente interessante. "Erguer-se pelas próprias abas da bota" (minha tradução livre de _to pull oneself up by one's bootstraps_), é uma frase inglesa do século XIX inicialmente tratada como uma piada sarcástica pela impossibilidade de se erguer (do ar ou da água, por exemplo) pelas próprias abas da bota. Ironicamente, é isso que nossos dispositivos fazem (o famoso _boot_). Computadores e smartphones tem um código padrão executado ao ligar o dispositivo. Ele que carrega o sistema operacional que você conhece (Windows ou Linux). O Bill tem esse propósito de ser um _bootstrap_ para o que ele se propõe a ser. No momento eu estou fazendo esse bootstrap. O Bill nasceu em um caos enquanto eu estudava harness LLM e achava que tinha resolvido todos os problemas do mundo. Agora, estou migrando o que desenvolvi a toque de caixa, para o formato a ser publicado. Bem nos moldes do [Linux From Scratch](https://www.linuxfromscratch.org/) (que inclusive recomendo fortemente para aprender Linux).

Além disso, uma vez um conhecido disse que parece que todos os garçons de filmes de faroeste chamam Bill. Rimos muito, mas acredito que não haja nenhuma base estatística nisso. De qualquer forma, gosto de pensar que estou falando "Ei, Bill. Encha meu copo.". Com um sotaque interiorano, ou só belorizontino mesmo.

## 2. Propósitos e limites [contexto]

### Para o que ele se propõe

A ideia do Bill é ser um motor de tarefas determinístico, sendo utilizável por um agente, seja uma LLM externa, local ou a própria pessoa. Eu gosto de máquina fazendo coisas chatas para mim. Eu gosto de facilidade de acesso com segurança. Eu gosto de Autonomia Tecnológica. E eu não quero gastar tempo desenvolvendo isso. E eu gosto muito de gastar pouco dinheiro. Aqui aceito gastar dinheiro em prol de chegar nesse objetivo, almejando lá na frente não precisar das massivas LLMs novamente (talvez apenas pequenas LLMs locais).

Mas, além disso, o Bill é um ambiente de trabalho minimalista. Não em cores, os [temas](#design-system-e-temas) estão aqui para isso. Mas minimalista em "não preciso de muito para ser produtivo em um ambiente tecnológico". Isso é um manifesto em si de que com um binário e uma pasta (e mais alguns serviços). Várias extensões do Bill vão morar como algo meu, inicialmente. Enviar minha biblioteca de jogos zerados para o rawg usando a base da Steam e do Heroic não cabem na parte padrão do Bill. E também abrir a possibilidade de extensões da comunidade, sem uma curadoria, com todo o risco de ataques de Supply Chain, é complicado. Por isso Bill nasce como é, analisando funcionalidade a funcionalidade se ela cabe aqui.

### O Bill tenta reescrever a roda?

Sim, ele tenta. Tem muitas aplicações mais avançadas para partes específicas do Bill. Se você entende que seu Projeto não pode ser gerenciado aqui, e que você precisa de muito mais funções, eu te entendo, e infelizmente o Bill não é para você. Mas para mim é mais do que o suficiente. No começo, eu havia definido que tarefas não eram deletadas. Elas deviam ser canceladas, para manter histórico. Acho válido, e a função existe. Mas se eu quero deletar eu posso. Mais detalhes sobre [tabelas](#tabelas) abaixo. Existem ferramentas como Obsidian e AnyType para arquivos e dados estruturados. Essas ferramentas são fantásticas e não quero substituí-las. 

### Onde executar o Bill

A ideia do Bill é que rode em uma máquina. Uma Turing-compatível. Pode ser seu desktop, seu notebook, seu NAS, uma VPS. Eu gostaria que fosse leve, mas não estou a fim de aprender Go ou Rust. Então vamos de Python. "Todo mundo" sabe Python. E se um ESP32 roda Micropython, é porque posso almejar ir longe aqui.

O Bill por natureza quer montar um ambiente container completo na sua máquina. Por ter a premissa de ser um ambiente autossuficiente, são precisos serviços e aplicações externas que facilitam isso.

## 3. Regras [normativo]

### Segurança

- Toda decisão de segurança da aplicação é feita alta e claramente nesse arquivo. Nenhuma decisão de segurança é tomada sem discussão. Se nao esta descrita aqui, nao existe. 

### Internacionalização

- Com exceção do Manifesto, que é originalmente escrito em `pt_BR`, do `FAQ.md`, também nessa língua, e das traduções desses dois arquivos, todos os outros markdowns desse repositório devem ser escritos em inglês. Futuras traduções do `MANIFESTO.md` moram em `MANIFESTO/` e do `FAQ.md` em `FAQ/`.

- Todo código, incluindo comentários, chaves de objetos, variáveis, métodos e nomes de arquivos serão em Inglês Estadunidense (`en_US`). No geral, os arquivos de código não têm objetivo de serem lidos por usuários finais, apenas auditados por desenvolvedores. Então é mais vantajoso manter a base em inglês para o processamento da LLM. 

- A interface toda segue `i18n`. Nenhuma string é salva diretamente no código, seja backend ou frontend. A fonte da verdade é o módulo de `i18n`, que salva os arquivos separados por grandes blocos, evitando que o arquivo seja um `pt_BR.json` gigante que a LLM precisa ler o tempo todo.

- Por padrão a LLM deve gerar textos a fim de popular o `i18n` em `pt_BR` originalmente e `en_US` como tradução. Essa separação se faz com objetivo de que, na maior parte do tempo, estarei dando foco nos textos em `pt_BR` e não tanto para `en_US`.

- Existe o comando `bill lang pt_BR --include-subcommands`. Dessa forma até a linha de comando do bill fica traduzida. Como isso não é muito comum, fica como opcional.

- Toda interface respeita o `i18n`. `cli`, WebApp e Wizard.

### Código e delivery

- Bill é escrito em `Python 3.14.7,`. Todo seu estilo de código é baseado em `PEP 8`. A ideia é que ele seja entregue em um binário único: Windows, Linux e Mac. Seu versionamento é SemVer, mas o binário sempre é entregue como `bill.exe`, por exemplo. A atualização é basicamente substituir o binário. Se necessário atualização da estrutura, ele o faz na primeira subida depois da atualização.

- Os comentários no código descrevem apenas o que aquilo faz. Para histórico, usamos `git`. Não é necessário anotar datas de decisões. O comentário explica porque aquele trecho de código é necessário e, se o código em si não explica muito bem, o que ele faz. Veja, o código deve falar por si só (como o [xadrez fala por si só](https://pt.wikipedia.org/wiki/Controv%C3%A9rsia_Magnus_Carlsen%E2%80%93Hans_Niemann)). Se precisarmos de quilos de comentários, talvez ele não esteja tão bem escrito assim.

- O binário mora na pasta e essa pasta é do binário. Ela é a Pasta de Trabalho. Se você abrir o binário dentro da pasta de `Downloads`, a pasta de `Downloads` é dele. No primeiro carregamento você será avisado de que: "o Bill foi aberto na pasta `<pasta>`. Como não existe um arquivo `.bill/settings.json` aqui, entende-se que é uma nova Pasta de Trabalho. Confirma que o Bill utilize essa pasta? Recomenda-se a utilização de uma pasta vazia, em qualquer local do seu computador. Cancele e mova o arquivo para outra pasta, se não concordar.". Ou algo do gênero.

### Permissão de acesso

- O Bill, por padrão, é arquitetado para ser executado sem permissões de administração (i.e. não usa `root` ou `Administrador`). Contudo, em alguns momentos, para configurar Podman e VPN, inevitavelmente será necessário. Nesses casos a elevação de privilégio acontecerá por um pedido explícito.

### Portabilidade

- O dado é sempre POSIX. `LF` ou `/`. Conversões para Windows apenas para exibição (como na mensagem da seção anterior) ou para as `syscalls`.

### Dependência externa

- Dependência a pacotes e imagens são fixadas em versão e hashing, seja no uso de imagens externas.

## 4. Arquitetura [normativo]

### Separação de camadas

- O Bill é estruturado em camadas. O `core` trata todas as regras da aplicação, não sendo um bloco de código completo, quebrado em módulos e arquivos conforme o assunto. Mas tudo passa por ele.

- A `ui` é uma forma de camada, mas tem mais. O Bill já nasce com duas: `cli` e WebApp. Ambas só são formas diferentes de interagir com o `core`. Nem tudo feito pelo `cli` está disponível no WebApp. Mas tudo no `WebApp + Wizard` está disponível no cli.

- Outra camada muito importante é `data`. Essa camada fica responsável por acessar as tabelas. Dados estruturados salvos em `.jsonl` dentro da pasta `./data`. A pasta `./data` é criada automaticamente na primeira execução, com as tabelas de sistema vigentes.

- O Bill também suporta gerenciar arquivos diversos. É a camada `prose`. Qualquer arquivo que não for estruturado fica a cargo dessa camada. A pasta `./prose`, também criada na primeira execução, vem arquivo exemplo `Bem-vindo.md` para facilitar os próximos passos.

- Os serviços externos são tratados pela camada `services`. Aqui é para que a camada seja o máximo agnóstica a ferramenta possível. 

- Os segredos são gerenciados pela camada `encryption`.

### Tabelas

- O Bill possui um motor próprio de gestão de dados estruturados. Aqui é usado o termo Tabela, ou `table` internamente. É usado `.jsonl` para armazenar e `.json` para schema. Logo `data/tasks.jsonl` é a tabela em si e `data/schema/tasks.json` o esquema dela.

- As tabelas `tasks`, `projects` e `reminders` são padrão do sistema. Servem para entregar uma funcionalidade inerente. Tabelas de sistema não são deletáveis, mas suas linhas são.

- Tabelas de usuário permitem CRUD completa da própria tabela. 

- O schema de tabela tem muitas funcionalidades, como campos padrão na exibição, ordem padrão na exibição de tabelas, IDs autoincrementais.

### Gestão de segredos

- Para executar certas ações, como acessar APIs de serviços externos, o Bill precisa ter acesso a segredos. Todos os segredos são escritos na tabela `secrets`. Lá estão metadados e o segredo em si, salvo de forma criptografada. Qualquer dado sensível a ser salvo em alguma tabela pode ser salvo de forma criptografada.

- A criptografia do bill é a partir de uma chave principal gerada a partir de uma frase de acesso. Essa frase de acesso precisa ter no mínimo 16 caracteres, mas é uma frase. Mariazinha comeu todo o pudim, escrito em letras minúsculas sem espaços é mais seguro que Mariazinha@123. Bill usa `libsodium` para essa gestão.

- É recomendado guardar essa chave, fora da máquina, em um local seguro. Imprimir e armazenar em documentos pessoais de difícil acesso, por exemplo.

- Em criptografia, não existe mágica. Ou você digita sua chave todas às vezes em que o motor precisar fazer algo que depende de um segredo, ou digita ela uma vez durante o período que a aplicação estiver ativa, ou salva sua chave principal em disco. Não é seguro, mas autonomia é autonomia. Cada chave intermediária é gerada a partir da chave principal. A chave principal te permite recuperar acesso a qualquer chave intermediária perdida. Cada chave intermediária tem o escopo definido para o que ela se propõe. Cada serviço ou cada finalidade.

### Configurações gerais

- As configurações do bill moram dentro de `.bill/settings.json`, dentro da pasta de trabalho. Aí moram propriedades em format chave-valor. `i18n` não mora aqui. 

- O Wizard Tkinter exibe as possibilidades de instalação do ambiente No modo avançado habilitado, o Wizard apresenta a renderização do arquivo de configurações, permitindo modificar quaisquer uma. Segue a escolha de designer de algumas ferramentas, como VS Code, que possuem a base das configurações em JSON, mas permitem a alteração na UI.

- Cada serviço pode ter dados persistidos. Nesse caso, eles moram em `.bill/<serviço>`, como `.bill/vpn` ou `.bill/spelling-checker`.

## 5. Interfaces [normativo]

### Linha de comando (`cli`), aplicação web (WebApp) e interface Tkinter (Wizard)

- O arquivo binário do Bill é único. Ao abrir, seja em linha de comando, seja direto pela interface gráfica, temos o "Painel de Controle". É uma interface em Tkinter, o Wizard. Aqui são configuradas as "entranhas" do ambiente do Bill, sendo sua primeira camada a aplicação web.

- A linha de comando funciona para tudo do Bill. Qualquer funcionalidade que ele exponha, seja na API REST (utilizada pelo frontend do WebApp), seja no WebApp em si, é acessível pela linha de comando.

- O Wizard é uma tela que permite realizar configurações mais críticas do Bill que eu não queria deixar disponível na rede. Instalar serviços e gerenciar chaves principais são algumas dessas funcionalidades separadas.

- O `cli` executa apenas localmente, em exceção quando está comunicando com APIs externas para devida configuração.

### Aplicação WebApp

#### Design System e temas

- O Design System é de desenvolvimento da LLM. Crescimento gradual de componentes.

- Suporte a temas é a uma parte estrutural do Bill. Vários temas me ajudam a testar a força do Design System em cima de diferentes visões. Ao mesmo tempo que me fazem ficar feliz de usar o sistema. PRs de tema são bem-vindas, mas estão totalmente sujeitas ao meu julgamento pessoal e ficarei feliz em compartilhar meu péssimo gosto, se não quiser aceitar uma PR. Mas não se acanhe!

#### Templates

- Bill usa `Vue`. Por mais que eu não goste de usar muitas dependências externas pelo risco de Supply Chain, e que a maioria disso seja causada por bibliotecas JavaScript, eu gosto do `Vue`. Acho uma perda válida pela gestão de templates que ele traz. Por mais que eu não esteja escrevendo esse código, não me agrada ver a LLM criando arquivos JavaScript individuais para páginas. Dificulta minha legibilidade e sou muito a favor de boa legibilidade.

#### TypeScript e frameworks

- WebApp do Bill é escrito em TypeScript e _transpilado_ usando `ViteJS`. O TypeScript é bem escrito respeitando módulos e domínios, facilitando a gestão humana.

## 6. Operação [normativo]

### Passos de configuração

- Os passos de configuração aqui são o caminho padrão para se usar o Bill. Você ainda pode usar a `cli` para diversas tarefas, mas o uso do Bill WebApp segue esse caminho.

#### a. Criar ambiente container (obrigatório)

- Aqui é a virada principal do ambiente. A pessoa precisa ter Podman instalado e o Bill orquestra certas instalações. É uma função complexa com muita possibilidade de erro e de falha de segurança. Logo precisa estar explícito como garantir que tudo aqui funcione corretamente.

- Podman é considerado para containers. `dnsmasq` e `caddy` são os primeiros serviços. O primeiro para customizar as urls de acesso e o segundo para publicar o Bill.

#### b. Instalar autenticador como container (obrigatório)

- O Bill não tem um autenticador padrão. Ele executa totalmente sem senha. Para proteger o Bill é preciso utilizar um autenticador externo. Aqui a recomendação é Authelia. Ele ficará responsável pela autenticação de todos os serviços existentes aqui. Como parte do ambiente seguro, o autenticador é necessário para rodar o Bill.

#### c. Instalar WebApp como container (obrigatório)

- O WebApp, principal forma de usar o Bill, é instalado como um container. Visa diminuir o raio de explosão em uma aplicação web comprometida.

#### d. Instalar corretor ortográfico e gramatical como container (opcional)

- O padrão do Bill para correção de textos é LanguageTool. Ela serve para sublinhar os erros na tela de edição. Bem útil.

#### e. Instalar VPN (opcional)

- O Bill permite configurar uma VPN. Aqui ela é relevante, pois permite criar uma rede privada para que múltiplos dispositivos conversem entre si. Logo se o Bill WebApp roda na sua máquina pessoal, fica acessível de forma segura do seu celular, em qualquer lugar. Aqui estou utilizando Tailscale. É proprietário, mas evita que seja necessário um servidor na nuvem. Suporte a Headscale no futuro.

#### f. Instalar notificador como container (opcional)

- Com tudo configurado, a cereja do bolo é o `ntfy`. Os lembretes configurados podem ser notificados diretamente como um Push Notification.

#### g. Instalar LLM local (opcional)

- O Bill pode ter uma LLM local para tarefas simples. Como o objetivo do Bill é não depender de uma LLM externa para ser um agente, a ideia de ter um serviço LLM local para às vezes pedir para criar uma tarefa é muito melhor que ter que pagar token para isso.

- A LLM já é pré-configurada com "habilidades". Você pede, ela entende as funções que ela tem pré-definido, e executa. Qual LLM usar depende da placa de vídeo disponível.

#### h. Instalar chatbot local (opcional)

### Chatbot local

- Se executar uma LLM minimamente capaz de entender inputs não for possível, é disponibilizado um chatbot. Ele realiza inferências no texto para tentar direcionar para a tarefa mais próxima. Mais propenso a erros, mas capaz de executar em qualquer máquina.

## 7. Modo avançado

- O comando `bill webapp` abre a aplicação web. Você pode configurar como serviço manualmente caso não for usar o modo padrão. O Bill WebApp possui autenticação `basic`. É preciso definir no arquivo de configurações manualmente, ou nas edições avançadas do Wizard. Essa função é utilizada para o Authelia comunicar com Bill WebApp de forma segura, mas não foi pensada para ser usada por usuários finais.

- Chamar o binário direto do terminal carrega a interface Tkinter. Qualquer outro parâmetro passado faz o programa agir como uma `cli`. `bill ajuda`, ou `bill help`, mostra como usar a cli completamente. Você pode modificar nas configurações para o comando `bill` não abrir o Tkinter e sim o `bill help`.

## 8. Ambiente de teste end-to-end

- O teste principal é verificar se ao instalar o Podman e executar as ações do Bill tudo funciona perfeitamente. Esse teste acontecerá em VMs Mac, Linux e Windows.