# Bill

Bill é um motor de tarefas determinístico. Ele roda **dentro de uma pasta**, e essa pasta vira a **Pasta de Trabalho** dele. Este repositório é o **produto a publicar** — o motor, as declarações padrão, a infraestrutura que vai embarcada e o binário único. Ele não carrega dado pessoal nenhum: nenhum caminho de máquina de ninguém, nenhum host, nenhum id.

## 0. Protocolo de agente

### Proteção de arquivo

- Esse arquivo é a pedra fundadora da instrução humana. Você pode e deve lê-lo sempre que chegar nesse repositório; ele tem a intenção de ser para humanos, e é assim que deve continuar. Quando os seus cálculos estatísticos penderem ao equilíbrio, volte aqui, e veja se algo te responde. Ao mesmo tempo, a instrução pode estar errada. O que mais acho válido de ser corrigido é contradições. Então, se algo aqui contradiz outra parte daqui, você deve me avisar e propor a correção.

- Se você entende que alguma decisão neste arquivo está errada, estarei feliz em discutir. Contudo, você me apresenta e eu decido. A escrita vai direto no documento que vincula — não existe arquivo de rascunho —, mas **toda alteração dele é um commit à parte**, e o commit só existe com o meu aval declarado. A pergunta é sempre a mesma linha, crua: "Vou realizar o commit do documento fundador a seguir. Você confirma que leu o diff e concorda com as alterações?". Sem essa resposta o commit não acontece, e a aprovação fica registrada no commit — nunca dentro do documento, que é a instrução, não o histórico dela. Sempre que eu te pedir uma análise do documento fundador, a proposta vem como diff nesta sessão, separada em pontos de assuntos diferentes e sucinta — eu vou entender o erro lógico sem você escrever um parágrafo para cada item.

- Qualquer instrução no `CLAUDE.md`, ou em qualquer outro markdown de memória de agentes LLM proprietário, se conflitando com esse repositório, quando usado para algo a ser feito nesse repositório, deve ser ignorado. Se quiser, e recomendo, pode haver uma linha nesses arquivos apontando para o documento fundador. Com exceção dos workflows de desenvolvimento no GitHub, e com o envio das minhas interações com a LLM para outra pasta (visando estudo posterior) esse repositório é autocontido, e tudo necessário para ele vive aqui.

- A cadeia de custódia é `documento fundador → documentos derivados → código`: o código é uma extensão do que está escrito, e o que é derivado não decide nada sozinho. Se decidirmos algo arquitetural, em sessão, que não veio do documento fundador, você vai me avisar e propor a escrita, pelo mesmo aval. E isso nunca pode ser ignorado, nem por mim. É essa cadeia que vai manter esse "arreio" preso. Veja que definições muito estreitas sobre nome de pastas de cada módulo não cabem para o documento fundador — elas moram na árvore ([arquitetura §1](architecture.pt_BR.md)), que é derivação. Ter que detalhar cada item individual me dá a sensação que é melhor eu desenvolver do zero.

- Não existem regras duplicadas: uma regra mora em um lugar só. O que vincula fica no documento fundador; o derivado cita em vez de repetir. Se a mesma coisa aparecer nos dois, um dos dois está errado — e onde ela fica é decisão minha.

- Por fim, o documento fundador vai ser modificado com o tempo. Então entenda que a lógica de lê-lo e derivar o resto é constante.

- O resto dos arquivos, fique a vontade. Incluindo o `FAQ.md`. É responsabilidade sua. Deve ser escrito como uma sequência de perguntas comuns. Eu aprovo a pergunta e a resposta que você sugerir, só me informe quando entender que vale preencher. E o `FAQ.md` tem que estar ordenado em ordem de uso da ferramenta. Perguntas mais iniciantes no começo como "o que esse arquivo faz na minha máquina" para perguntas mais avançadas como "como eu modifico o Bill ao meu bel-prazer". É no FAQ que mora a explicação do que está por baixo: qual tela é sua e qual é de terceiros.

### Forma de trabalho

- Sempre trabalhe em duas sessões por item, nunca uma. Na primeira, modo plano: explorar, discutir e fechar a decisão, sem escrever código. Antes do `/clear`, o plano tem que ser salvo fora da conversa — no `docs/backlog.en_US.md` — já com o que conta como pronto, para a segunda sessão não precisar perguntar. A segunda nasce limpa, lê o item no `docs/backlog.en_US.md` e implementa um item, do tamanho de uma sessão.

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

Sim, ele tenta. Tem muitas aplicações mais avançadas para partes específicas do Bill. Se você entende que seu Projeto não pode ser gerenciado aqui, e que você precisa de muito mais funções, eu te entendo, e infelizmente o Bill não é para você. Mas para mim é mais do que o suficiente. No começo, eu havia definido que tarefas não eram deletadas. Elas deviam ser canceladas, para manter histórico. Acho válido, e a função existe. Mas se eu quero deletar eu posso. Mais detalhes sobre [tabelas](#tabelas) abaixo. Existem ferramentas como Obsidian e AnyType para arquivos e dados estruturados. Essas ferramentas são fantásticas e não quero substituí-las.

### Onde executar o Bill

A ideia do Bill é que rode em uma máquina. Uma Turing-compatível. Pode ser seu desktop, seu notebook, seu NAS, uma VPS. Eu gostaria que fosse leve — leve no que o binário exige da máquina, não no tamanho do artefato, que carrega o interpretador e as bibliotecas empacotados. Mas não estou a fim de aprender Go ou Rust. Então vamos de Python. "Todo mundo" sabe Python. E se um ESP32 roda Micropython, é porque posso almejar ir longe aqui.

O Bill tem dois caminhos de uso, e os dois são suportados: o **hospedado**, em que ele é o binário e a pasta, e o **container**, em que ele monta um ambiente de serviços. A escolha é da pessoa, e ela pode mudar de ideia depois; o que cada caminho garante, e o que não garante, está no [§6](#6-os-dois-caminhos-de-uso-normativo).

## 3. Regras [normativo]

### Segurança

- Toda decisão de segurança da aplicação mora neste arquivo, e esta seção é o registro delas. Nenhuma decisão de segurança é tomada sem discussão, e nenhuma é decidida fora daqui: as outras seções descrevem operação e detalham o que está registrado abaixo, mas não decidem segurança por conta própria. Se não está registrado aqui, não existe.

- O isolamento é do caminho container. No caminho hospedado o Bill é um processo na máquina, sem container nenhum em volta, e isso é declarado — não há promessa de conter o raio de explosão de um comprometimento. O que o caminho hospedado oferece em troca é escutar só o laço local por padrão, e exigir autenticação e TLS para sair dele.

- Decisões vigentes. A linha é a decisão; o detalhe vive onde o link aponta:
  - Sem autenticação, o Bill só escuta `127.0.0.1`; exposto exige autenticação — [Acesso e exposição](#acesso-e-exposição).
  - Exposto exige TLS, e TLS só existe com o Caddy: `bill webapp` sem a bandeira é HTTP em laço local — [Acesso e exposição](#acesso-e-exposição).
  - O Bill tem autenticador próprio, com quatro formas de entrar, todas terminando num ator: Forms local, Basic, credencial de máquina e a identidade afirmada pelo portão — [Interfaces](#5-interfaces-normativo), [Tabelas](#tabelas).
  - A credencial do ator mora hasheada na própria linha dele, com `libsodium`; Basic e Forms são a **mesma** credencial, e o que os separa é o transporte — [Tabelas](#tabelas).
  - Nenhum segredo mora no `settings.json`: ele guarda permissão e ajuste, nunca credencial — [Configurações gerais](#configurações-gerais).
  - Toda função da API do core é protegida por RBAC; a permissão é `objeto:ação`, o papel é um conjunto de permissões, e credencial de máquina tem papel declarado — [Tabelas](#tabelas).
  - O primeiro admin nasce na primeira subida, com terminal na frente; sem ator nenhum o Bill não expõe — [Interfaces](#5-interfaces-normativo).
  - Papel e permissão são tela do WebApp, e só admin mexe neles — [Interfaces](#5-interfaces-normativo).
  - **Instalar serviço é do Wizard e só dele** — [Interfaces](#5-interfaces-normativo).
  - Segredo de máquina se guarda hasheado, com papel; segredo que o Bill **usa**, como a credencial de um serviço, se guarda criptografado na tabela `secret` — [Gestão de segredos](#gestão-de-segredos).
  - O Bill autentica nos serviços em vez de se aproveitar de estar na mesma máquina: credencial de administração existe onde ela é necessária, e ela conta na postura — [A postura de segurança](#a-postura-de-segurança).
  - Serviço que fala com o Bill recebe escopo delimitado — mínimo privilégio: o comprometimento de um serviço alcança a função dele e nada mais — [Caminho container](#7-caminho-container-os-passos-normativo).
  - Identidade que chega pelo portão só vale com o segredo do portão: o Bill sorteia um segredo por instalação, escreve no Caddyfile que ele mesmo gera, e recusa identidade sem ele — [Instalar provedor de identidade como container](#b-instalar-provedor-de-identidade-como-container-obrigatório).
  - O Forms fica ligado até o Authelia estar provado funcionando na frente do Bill; a virada é um conjunto que comita ou volta atrás — [A virada entre os caminhos](#a-virada-entre-os-caminhos).
  - Portão caído fecha o Bill: ele avisa que o portal de autenticação está indisponível, e a volta ao modo Forms é pelo Wizard ou pela `cli`, os dois locais — [A virada entre os caminhos](#a-virada-entre-os-caminhos).
  - Toda ação deixa uma linha na tabela `audit`, e a recusa é uma delas — [A auditoria](#a-auditoria).
  - O que se prova se guarda hasheado; o que o Bill usa se guarda criptografado — [Tabelas](#tabelas).
  - O estado persistente de todo serviço mora na Pasta de Trabalho; serviço cujo estado não couber lá não entra — [Caminho container](#7-caminho-container-os-passos-normativo).
  - **Nenhuma extensão executa código hoje.** A primeira classe é dado puro, e código é a última opção — [Extensões](#8-extensões-e-plugins-normativo).
  - O tema do portal de autenticação não é o do Bill: ele fica o mais neutro possível, e o `FAQ.md` explica o que está por baixo — [Interfaces](#5-interfaces-normativo).
  - Autenticador, WebApp, corretor, notificador e VPN rodam em containers isolados no caminho container — [Caminho container](#7-caminho-container-os-passos-normativo).
  - A execução é sem privilégio, com elevação só por pedido explícito — [Permissão de acesso](#permissão-de-acesso).
  - Pacotes e imagens são fixados em versão e hashing — [Dependência externa](#dependência-externa).

### Acesso e exposição

- Sem nenhuma forma de autenticação configurada, o Bill escuta apenas `127.0.0.1`. Não há exceção, e não há modo "só nesta rede interna": ou há autenticação, ou o Bill não sai do laço local.

- Expor exige autenticação **e** TLS. Como o TLS é do Caddy, e o Caddy é embarcado (§3, Código e delivery), a exposição no caminho hospedado acontece por `bill webapp --include-caddy`: sem a bandeira, o comando serve o WebApp em HTTP, e só em laço local. No caminho container quem fica na borda é o Caddy em container, pelo isolamento.

- O Bill não entrega HSTS, por motivo óbvio: ele serve com certificado próprio, e HSTS transformaria o aviso do navegador em erro sem saída. É o preço de não depender de um domínio público, e de não poder garantir TLS confiável.

### O modelo de ameaças

- O Bill se protege do que ele pode ver, e diz em voz alta o que ele não pode. A primeira barreira é o autenticador do caminho: o Authelia no caminho container, a credencial de Forms no hospedado.

- A segunda barreira é **implícita e não é do Bill**: a proteção do próprio celular. Permitir que uma notificação aprove uma ação é confiar que o `ntfy` foi bem configurado **e** que essa configuração está protegida por um aparelho bloqueado. O Bill **não audita o celular** — se tem root, se é emulado, se tem bloqueio de tela —, porque isso é trabalho de banco e o Bill não é um banco.

- Guardar a credencial do autenticador num cofre de senhas ou no cofre do navegador é escolha da pessoa, e é perigoso. Está escrito aqui em vez de escondido.

- O mesmo vale para fora: backup da pasta que não existe, máquina sem senha, rede aberta. O Bill mede o que ele controla e **declara o que não mede**, em vez de dar uma nota que ele não pode sustentar — [A postura de segurança](#a-postura-de-segurança).

### A auditoria

- Toda ação que entra pelo core vira **uma linha** na tabela `audit`: o que foi alterado (`objeto:ação`), onde (a tabela), quando (o instante), quem (o ator), por qual via, e o desfecho. O "porquê" só existe na recusa, onde ele é o motivo, guardado como chave de `i18n`; fora dela, a linha não finge ter intenção. Custo não entra.

- **Tentativa e recusa são linhas**, com o desfecho dizendo o que aconteceu — é a visão de auditoria de ataques. **Leitura não é linha**: ler não é fazer, e auditar leitura faria o rastro crescer mais rápido do que o uso.

- O audit é **log, não referência**: os ids que ele cita são dado bruto, sem `ref`, e por isso ele nunca impede um `delete` (§4, Tabelas). Ele não guarda valor nenhum, e **nada se deleta dele** — a deletabilidade é declarada no esquema, e o `audit` declara que não aceita.

- Só o papel de admin carrega `audit:read`, e nenhum ator de máquina a tem: um `agente` que pudesse ler as próprias recusas aprenderia onde está a parede e ajustaria a próxima tentativa.

### A postura de segurança

- O ambiente tem uma **nota de segurança**, de `F` a `S`, e ela existe para uma coisa: fazer a pessoa ver o preço do que ela monta e melhorar o ambiente dela. Ela não é um cadeado e não impede nada.

- **A nota é por função, e a do ambiente é o elo mais fraco.** Cada função graduada — o destino da Frase de Acesso, a exposição, o segundo fator de quem entra, o escopo das credenciais de serviço, o que o próprio Bill carrega, os plugins, o limiar de risco — carrega a sua nota, e para o ambiente ser `S` todas precisam estar em `S`. Um ambiente com uma função ruim não pode se dizer bom, e a tela sempre nomeia **quais funções estão impedindo de subir**.

- **A nota mede o que está configurado e o que você declarou, nunca a verdade.** Ninguém verifica se você leu o que um plugin faz. Isso não é defeito: é o único formato possível, e é por isso que a nota se apresenta como "isto é o que o seu ambiente declara", não como "você está seguro".

- **Todo impasse de segurança se resolve oferecendo as opções e deixando a pessoa aceitar a segurança dela.** A nota informa o preço; quem decide é quem vai viver com ele. Autonomia é também saber a segurança que se quer para si.

- O que o Bill **não** mede, ele diz: se não há backup da pasta, se a máquina não tem senha, se o celular não tem bloqueio — o Bill não sabe, e prefere dizer isso a inventar uma letra.

### Internacionalização

- Com exceção da porta da raiz, todo documento deste repositório carrega o **idioma no próprio nome**, no formato POSIX (`pt_BR`, `en_US`), alinhado ao módulo de `i18n` — não é BCP 47. A porta da raiz é um `README.md` sem idioma, e não tem texto além do título, dos links para as versões em cada língua, e de uma nota curta em `en_US` dirigida a agentes LLM: que leiam no idioma que serve melhor ao modelo, que na dúvida leiam em inglês, e que a trilha inglesa usa os termos e conceitos do mercado de propósito, para um nome significar a mesma coisa aqui e lá fora.

- Os documentos moram em `docs/`, um arquivo por idioma, e cada um linka os irmãos nas outras línguas. **Nenhum documento em inglês existe sem o sufixo de idioma**, e os nomes são minúsculos — só o `README` fica em maiúsculas, por ser o nome que o mundo já conhece.

- **Os dois idiomas mudam sempre juntos**, e o aval de um commit cobre o par. O `pt_BR` é a língua fonte; onde os dois divergirem, vale o `pt_BR`.

- Um **documento de trabalho** mora na mesma pasta, em `en_US` e **sem par**: o `docs/backlog.en_US.md` é para o agente, muda todo dia, e traduzir o que muda todo dia é trabalho que ninguém lê.

- Um **gate na suíte** afirma o que essa regra promete: o nome de cada documento, a existência do par, a mesma estrutura de títulos nos dois, e a ortografia — os dois idiomas passam pelo corretor do repositório, e o que ele ignorar fica numa lista versionada, uma por idioma. Gramática fica com a leitura humana.

- Todo código, incluindo comentários, chaves de objetos, variáveis, métodos e nomes de arquivos serão em Inglês Estadunidense (`en_US`). No geral, os arquivos de código não têm objetivo de serem lidos por usuários finais, apenas auditados por desenvolvedores. Então é mais vantajoso manter a base em inglês para o processamento da LLM. Essa regra vale para o que é versionado no repositório; não vale para os arquivos que o Bill gera na Pasta de Trabalho.

- A interface toda segue `i18n`. Nenhuma string é salva diretamente no código, seja backend ou frontend — `cli`, WebApp e Wizard. A fonte da verdade é o módulo de `i18n`, que organiza os textos em grandes blocos, evitando um `pt_BR.json` gigante que a LLM precisa ler o tempo todo. Os blocos são empacotados no binário; o que fica na Pasta de Trabalho é só o idioma ativo, em `app/i18n/active`.

- Por padrão a LLM deve gerar textos a fim de popular o `i18n` em `pt_BR` originalmente e `en_US` como tradução. Uma chave ausente no idioma ativo cai na fonte e depois nela mesma, então a lacuna fica visível em vez de silenciosa. A chave é um **id estável**, nunca a frase em inglês: renomear um texto não pode renomear uma chave. E a suíte afirma que as duas línguas carregam exatamente as mesmas chaves, para que uma tradução atrasada seja um teste falhando em vez de uma surpresa.

- Na `cli`, mensagens e ajuda saem sempre pelo `i18n`. O comando `bill lang pt_BR --include-subcommands` estende a tradução aos nomes dos subcomandos, o que não é comum, e por isso fica como opcional. A resolução do idioma é `$BILL_LANG` → `app/i18n/active` → locale do sistema → `en_US`, e toda superfície reporta de onde ele veio.

### Código e delivery

- Bill é escrito em `Python 3.14`. Todo seu estilo de código é baseado em `PEP 8`. A ideia é que ele seja entregue em um binário único: Windows, Linux e Mac. Seu versionamento é SemVer, e o binário carrega esse número — no Windows ele sai como `bill.exe`, nos outros como `bill`.

- O binário carrega o **Caddy** dentro de si. O Caddy é um binário estático único, e no caminho hospedado é ele quem termina TLS e publica o Bill; no caminho container ele roda como container, pelo isolamento. Não há variante de release: um artefato só, e o custo em disco é aceito em troca dessa simplicidade. Como o Caddy vai dentro do binário, a versão dele é a do binário — não há pin separado para ele.

- A atualização é substituir o binário. Como ele carrega o manifesto das imagens fixadas, ao subir depois da troca ele re-verifica as imagens dos serviços e re-pina o que estiver defasado — o pin anda só para frente e nunca para trás. Uma instância à frente do pin do binário **avisa e segue**: não é rebaixada. Manter tudo atualizado, e sem falha de segurança, é gestão minha, não do binário.

- Toda atualização que mude estrutura traz a sua **migration**, e ela roda na primeira subida depois da troca do binário. A pasta sabe até onde já migrou, e esse carimbo mora em `app/` — junto do resto do que o Bill escreve —, nunca dentro da declaração publicada. A declaração continua sendo dado puro, que você edita; o que os dois autores assinam fica separado.

- A migration **nunca sobrescreve o que já existe**: ela adiciona o que falta e reporta o que pulou. Numa colisão, quem manda é a sua edição, e o Bill avisa em vez de escolher por você — a mesma escolha do pin das imagens. E uma migration publicada **não se edita**: pastas já a rodaram, e correção vira a migration seguinte.

- Os comentários no código explicam apenas o que o código não fala por si: por que aquele trecho é necessário e, quando não for óbvio, o que ele faz. Para histórico, usamos `git`. Não é necessário anotar datas de decisões. Veja, o código deve falar por si só (como o [xadrez fala por si só](https://pt.wikipedia.org/wiki/Controv%C3%A9rsia_Magnus_Carlsen%E2%80%93Hans_Niemann)). Se precisarmos de quilos de comentários, talvez ele não esteja tão bem escrito assim.

- O binário mora na pasta e essa pasta é do binário. Ela é a Pasta de Trabalho. Se você abrir o binário dentro da pasta de `Downloads`, a pasta de `Downloads` é dele. No primeiro carregamento você será avisado de que: "o Bill foi aberto na pasta <pasta>. Como não existe um arquivo `app/settings.json` aqui, entende-se que é uma nova Pasta de Trabalho. Confirma que o Bill utilize essa pasta? Recomenda-se a utilização de uma pasta vazia, em qualquer local do seu computador. Cancele e mova o arquivo para outra pasta, se não concordar.". Ou algo do gênero.

- O backup da Pasta de Trabalho é a promessa do Bill: **a pasta copiada basta para tudo voltar a funcionar**, sem troca de binário no meio. Por isso nada se regenera sozinho — nem o que foi extraído, nem o que foi baixado —, e a única exceção é o que é específico de plataforma: a pasta que muda de sistema operacional re-extrai o que não serve mais. Tudo o que o Bill escreve mora em `app/`, numa pasta visível justamente para que ninguém a confunda com lixo: ajustes, idioma ativo, contadores, carimbo de migração, o estado dos plugins, o que foi extraído para rodar, cache e o estado dos serviços.

- O Bill **não tem watchdog e não se propõe a ter**. Ele está ciente de que tudo pode ser modificado por fora, e se a pessoa sabe modificar, que modifique: o que ele faz é medir o que encontra e dizer o que isso custa, nunca policiar a pasta.

- Sem terminal para perguntar não há primeira execução: o Bill encerra com código `1` em vez de assumir uma pasta. E recusar não cria nada — o Bill diz onde mover o binário e sai sem erro, porque recusar não é erro.

### Permissão de acesso

- O Bill, por padrão, é arquitetado para ser executado sem permissões de administração (i.e. não usa `root` ou `Administrador`). Contudo, montar o ambiente do §7 inevitavelmente exige elevação em algum momento. Nesses casos a elevação de privilégio acontecerá por um pedido explícito, com a razão à mostra.

- A lista fechada do que exige elevação não se escreve antes da função: ela nasce com a implementação que a pede. Cada item que entrar nela é uma decisão de segurança e passa por esta seção.

### Portabilidade

- O dado é sempre POSIX. `LF` ou `/`. Conversões para Windows apenas para exibição (como na mensagem de boas-vindas da Pasta de Trabalho, acima) ou para as `syscalls`.

### Dependência externa

- Dependência a pacotes e imagens são fixadas em versão e hashing — seja de pacotes, seja de imagens externas.

- O Caddy é a exceção declarada, e não por descuido: ele vai embarcado no binário, então quem o pina é o próprio binário, com o SemVer do Bill.

## 4. Arquitetura [normativo]

### Separação de camadas

- O Bill é estruturado em camadas. O `core` trata todas as regras da aplicação. Não é um bloco monolítico: é quebrado em módulos e arquivos conforme o assunto. Mas tudo passa por ele. Nenhuma camada fora do `core` resolve um caminho por conta própria.

- A `ui` é uma forma de camada, mas tem mais. O Bill já nasce com três superfícies: `cli`, WebApp e Wizard. Todas só são formas diferentes de interagir com o `core`. Nem tudo feito pelo `cli` está disponível no WebApp. Mas tudo no `WebApp + Wizard` está disponível no cli.

- Outra camada muito importante é `data`. Essa camada fica responsável por acessar as tabelas. Dados estruturados salvos em `.jsonl` dentro da pasta `./data`. A pasta `./data` é criada automaticamente na primeira execução, com as tabelas de sistema vigentes.

- O Bill também suporta gerenciar arquivos diversos. É a camada `prose`. Qualquer arquivo que não for estruturado fica a cargo dessa camada. A pasta `./prose`, também criada na primeira execução, vem com um arquivo de boas-vindas gerado pelo `i18n` no idioma ativo escolhido na primeira execução (`Bem-vindo.md` em `pt_BR`, `Welcome.md` em `en_US`), para facilitar os próximos passos.

- Os serviços externos são tratados pela camada `services`. Aqui é para que a camada seja o máximo agnóstica a ferramenta possível: o **serviço** tem nome canônico e a **ferramenta** que o cumpre é trocável. É nesta camada que mora a parte de serviços do produto — cada serviço configurado mora aqui, com o seu estado na pasta.

- Os segredos são gerenciados pela camada `encryption`.

- A interpretação de linguagem natural é a camada `nlu`: ela transforma uma frase em uma **proposta** de ação, e nada mais. Ela não escreve, não decide e não tem teto próprio — quem valida e escreve é o `core`.

- A postura de segurança é a camada `posture`: ela mede o que está configurado, soma as notas por função pelo elo mais fraco e responde à tela e à API. Ela mede; não impede.

### Tabelas

- O Bill possui um motor próprio de gestão de dados estruturados. Aqui é usado o termo Tabela, ou `table` internamente. A identidade da tabela é um id, e o id é singular (`task`, `project`, `reminder`, `secret`, `actor`, `role`, `audit`): é ele que nomeia a tabela em todo lugar, inclusive no comando (`bill task list`) e no esquema. O arquivo de linhas é que vai no plural. Logo `data/tasks.jsonl` é a tabela em si e `data/schema/task.json` o esquema dela.

- As tabelas `task`, `project`, `reminder`, `secret`, `actor`, `role` e `audit` são padrão do sistema. Servem para entregar uma funcionalidade inerente. Tabelas de sistema não são deletáveis, e **a deletabilidade de uma linha é declarada no esquema da tabela**: o `audit` declara que nenhuma linha sua se apaga.

- Tabelas de usuário permitem CRUD completa da própria tabela.

- O schema de tabela tem muitas funcionalidades, como campos padrão na exibição e ordem padrão na exibição de tabelas. Os rótulos de exibição que ele carrega são chaves de `i18n`, nunca o texto final. O contador de ids não mora no esquema: ele conta o que aconteceu nesta pasta, e o esquema é publicado — então ele vive em `app/counters.json`, e é escrito antes da linha, porque um id entregue está gasto mesmo se a escrita seguinte falhou.

- O esquema declara **tipos de campo**, e cada tipo tem regra fixa, sem escolha por campo:
  - **hasheado** — guarda o resultado de uma derivação segura, feita com `libsodium`; o valor não volta na leitura, só se confere.
  - **instante** — um ponto no tempo: ISO, sempre UTC, sempre com milissegundos (`2026-09-22T13:04:07.123Z`). A localidade é detectada na exibição, nunca guardada.
  - **dia** — um dia do calendário, sem hora e sem fuso, resolvido pela localidade de quem escreve. "Hoje" é o seu hoje.
  - Os tipos comuns — texto, número, data, referência, enumeração — como sempre foram.

- **O que se prova se guarda hasheado; o que o Bill usa se guarda criptografado.** A `secret` é da segunda espécie, o `actor` é da primeira.

- **Quem age é um ator**, e todo ator é uma linha da tabela `actor`, com o campo `tipo` valendo `pessoa`, `motor` ou `agente`. A linha carrega a identidade, o papel e a credencial no campo hasheado. O motor age no que é do motor; o `agente` é quem usa o Bill sem ser pessoa, e é ele que tem teto próprio — quem digita uma frase é a pessoa, e a via é `nlu`.

- O catálogo de permissões é declarado no código, e não é dado solto: a permissão tem a forma `objeto:ação`, os objetos e as ações são uma lista fechada, e os rótulos de exibição saem do `i18n` como todo o resto. Os objetos vão além das tabelas: as configurações, os serviços, os plugins e o vocabulário do interpretador também são objetos, com permissões próprias. Um papel é uma linha da tabela `role` com um conjunto de permissões, e a tabela `actor` aponta para o papel. Papel que nomeia permissão inexistente não derruba o Bill: ele avisa, e o aviso é o que se lê.

### Gestão de segredos

- Para executar certas ações, como acessar APIs de serviços externos, o Bill precisa ter acesso a segredos. Todo segredo que o Bill **guarda** é escrito na tabela `secret` — segredo que só se confere, como a credencial de um ator, mora hasheado na própria linha (§4, Tabelas). Lá estão metadados e o segredo em si, salvo de forma criptografada.

- A criptografia do Bill parte de uma **Frase de Acesso**, que é o que a pessoa sabe e digita: no mínimo 16 caracteres, e é uma frase. "Mariazinha comeu todo o pudim", em minúsculas e sem espaços, é mais seguro que `Mariazinha@123`. Dela se deriva a **Chave do Bill**, e dela as **chaves derivadas**, uma por serviço ou finalidade. A Chave do Bill recupera qualquer chave derivada perdida.

- É recomendado guardar a Frase de Acesso fora da máquina, em um local seguro. Imprimir e armazenar em documentos pessoais de difícil acesso, por exemplo.

- Em criptografia, não existe mágica. Ou você digita a Frase de Acesso toda vez que o Bill precisa de um segredo, ou digita uma vez e ela vale enquanto o Bill estiver de pé, ou o Bill guarda o que precisa para destravar sozinho. **A escolha é graduada, e a nota de segurança diz o preço de cada uma:** digitar quando o Bill sobe é `S`; guardar destravado na pasta do usuário do sistema (`~/.bill/` no Unix, `%APPDATA%` no Windows) é `A`; guardar dentro da Pasta de Trabalho é `B` — e a última é permitida, porque aí o backup da pasta leva tudo.

- O Bill roda sozinho quando precisa: job agendado não pede senha a cada execução. O que ele não faz é escolher por você onde a chave mora.

- A verificação de uma credencial de entrada **não** depende da Frase de Acesso, e isso é de propósito: senão o Bill só sobe quando alguém digita a frase. Por isso o que se confere é hasheado, e é por isso que a credencial não mora na `secret`.

### Configurações gerais

- As configurações do bill moram dentro de `app/settings.json`, dentro da pasta de trabalho. Aí moram propriedades em formato chave-valor. `i18n` não mora aqui: os blocos de tradução são empacotados no binário e o idioma ativo mora em `app/i18n/active`.

- **As configurações são alcançáveis pela API do core** (`setting:read` e `setting:edit` são permissões), porque é por ali que passa tudo o que age — inclusive a leitura do **limiar de risco** que valia no instante em que uma demanda correu, que é o que a linha da auditoria registra.

- Nenhum segredo mora no `settings.json`. Ele guarda permissão e ajuste — como a permissão de um ator entrar por Basic, ou o limiar de risco —, nunca a credencial em si.

- O Wizard Tkinter exibe as possibilidades de instalação do ambiente. No modo avançado habilitado, o Wizard apresenta a renderização do arquivo de configurações, permitindo modificar quaisquer uma. Segue a escolha de designer de algumas ferramentas, como VS Code, que possuem a base das configurações em JSON, mas permitem a alteração na UI.

- Cada serviço pode ter dados persistidos. Nesse caso, eles moram em `app/services/<serviço>`, como `app/services/vpn` ou `app/services/spelling-checker`. O nome do serviço é canônico e não muda com a ferramenta que o cumpre: `spelling-checker` é o serviço, LanguageTool é quem o cumpre hoje (§7d), e o que um dia o substituir não renomeia pastas nem chaves. O que é rótulo de exibição é chave de `i18n`.

- Essa pasta não é conveniência, é condição de entrada: um serviço só entra no §7 se o estado persistente dele couber aí dentro. Serviço que guarda a vida dele em algum volume que ninguém copia deixa o backup da pasta mentir.

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

- É uma função complexa com muita possibilidade de erro e de falha de segurança. As decisões de segurança que a cercam estão em [Segurança](#segurança).

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

- Este é o corretor do **texto da pessoa**, em tempo de execução. O corretor dos documentos do repositório é outro, e é ferramenta de desenvolvimento ([arquitetura §3](architecture.pt_BR.md)).

#### e. Instalar VPN (opcional)

- O Bill permite configurar uma VPN. Aqui ela é relevante, pois permite criar uma rede privada para que múltiplos dispositivos conversem entre si. Logo se o Bill WebApp roda na sua máquina pessoal, fica acessível de forma segura do seu celular, em qualquer lugar. Aqui estou utilizando Tailscale. É proprietário, mas evita que seja necessário um servidor na nuvem. Suporte a Headscale no futuro.

#### f. Instalar notificador como container (opcional)

- Com tudo configurado, a cereja do bolo é o `ntfy`, hoje a ferramenta que cumpre o serviço `notifier` (§4). Os lembretes configurados podem ser notificados diretamente como um Push Notification, e é por ele que chega a aprovação de uma demanda que passou do limiar de risco.

- É aqui que entra a primeira funcionalidade graduada: os níveis dela e o que cada um custa vivem em [funcionalidades](functionalities.pt_BR.md).

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

- O teste **não é o critério de pronto de cada função** — uma função fica pronta pelo que o `docs/backlog.en_US.md` diz que ela é. Ele é o portão da primeira publicação no GitHub, e dali em diante.

## 10. A derivação

A árvore, a Pasta de Trabalho e a operação são derivação: mudam quando uma pasta muda, e por isso não vinculam. Vivem em [arquitetura](architecture.pt_BR.md), nos dois idiomas. A cadeia é `documento fundador → documentos derivados → código` (§0).

## 11. Glossário

Cada nome tem um só significado, e nomes que se encostariam não convivem. Sempre que eu inventar um termo, ele é definido aqui antes de ser usado.

| termo | o que é |
|---|---|
| **produto** | o conjunto publicado: este repositório, o binário que ele gera e as declarações que viajam dentro |
| **binário** | o arquivo único que o produto publica |
| **Pasta de Trabalho** | a pasta onde o binário foi aberto e que passa a ser dele |
| **camada** | cada pasta do código com um trabalho só: `core`, `data`, `prose`, `services`, `encryption`, `nlu`, `posture`, `ui`, `i18n` |
| **superfície** | cada forma de uma pessoa alcançar o core: `cli`, WebApp e Wizard |
| **serviço** | a capacidade, com nome canônico (`spelling-checker`, `identity-provider`) |
| **ferramenta** | quem cumpre o serviço hoje (LanguageTool, Authelia), trocável sem renomear nada |
| **tabela**, **esquema**, **linha**, **campo** | as peças do motor de dados |
| **campo hasheado** | campo que guarda a derivação e nunca o valor; só se confere |
| **campo de instante** | campo de um ponto no tempo: ISO, sempre UTC, com milissegundos |
| **campo de dia** | campo de um dia do calendário, sem hora e sem fuso, local na escrita |
| **ator** | a linha de `actor` que age; **pessoa**, **motor** e **agente** são os tipos |
| **teto de acesso** | o limite efetivo do ator; **papel** (`role`) é a linha que concede |
| **auditoria** | a tabela `audit`, o log dos atos |
| **via** | por onde o ato entrou: `cli`, WebApp, Wizard, `nlu`, motor. Porta é a de rede, e só |
| **nlu** | a camada; **interpretador**, quem faz o trabalho dentro dela; **vocabulário**, o dicionário por idioma que ele consulta |
| **teste do interpretador** | a régua: o que precisa funcionar, o que precisa ser recusado, o que precisa ser perguntado de volta |
| **limiar de risco** | o preço a partir do qual a demanda espera aprovação; abaixo dele ela corre |
| **risco da demanda** | o preço de uma demanda, medido pelo core sobre a ação e os argumentos |
| **catálogo de permissões** | a lista fechada `objeto:ação` |
| **postura** | o estado de segurança do ambiente, medido: as funções graduadas e a nota |
| **nota** | a letra de uma função graduada, de `F` a `S`; a do ambiente é o elo mais fraco |
| **funcionalidade** | uma capacidade que a pessoa reconhece, com níveis e dependências |
| **plugin** / **extensão** | o que ensina algo ao Bill; hoje só dado puro, com manifesto e hash |
| **review** | a aceitação de um plugin, amarrada à hash, em um de três modos |
| **Frase de Acesso** | o que a pessoa sabe e digita; dela se deriva a **Chave do Bill** |
| **Chave do Bill** | a chave derivada da Frase de Acesso; dela derivam as **chaves derivadas**, por serviço |
| **manifesto** | a semente deste repositório, visível no histórico do git; e `manifest.json` é só o arquivo que tem esse nome |
| **pin**, **migration** | ficam em inglês, como o resto do código: fixação de versão e hashing, e a mudança de estrutura que roda na primeira subida |

## 12. O que ainda não está aqui

`docs/backlog.en_US.md` guarda o que vem a seguir, com o que conta como pronto para cada item.

Três dívidas nasceram das decisões desta sessão, e as três estão nomeadas para não virarem surpresa:

- **O código.** Nada do que ficou decidido aqui está construído: o ator, a auditoria, o filtro de demandas, a postura, o interpretador, os plugins. Tudo tem item no `docs/backlog.en_US.md`.
- **A lista do corretor.** Ela nasceu grande — 217 palavras em português e 131 em inglês —, e o motivo está escrito no cabeçalho dela: o dicionário do corretor vem de frequência de legendas e erra o registro formal, onde "seção", "deleção" e "registrar" não aparecem. Se essa lista crescer sozinha, o gate virou enfeite, e o diff é o lugar de perceber.
- **O `FAQ.md`.** Ele ainda não existe, e agora tem trabalho esperando: dizer o que está por baixo — qual tela é do Bill e qual é de terceiros —, e que escrever bem é o melhor remédio contra um mal-entendido do interpretador.
