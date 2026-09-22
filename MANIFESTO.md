# Bill

## 0. Protocolo de Agente

### Proteção de arquivo

- Esse arquivo é a pedra fundadora da instrução humana. Você pode e deve lê-lo sempre que chegar nesse repositório; ele tem a intenção de ser para humanos, e é assim que deve continuar. Quando os seus cálculos estatísticos penderem ao equilíbrio, volte aqui, e veja se algo te responde. Ao mesmo tempo, a instrução pode estar errada. O que mais acho válido de ser corrigido é contradições. Então, se algo no Manifesto contradiz outra parte do Manifesto, você deve me avisar e propor a correção.

- Se você entende que alguma decisão no `MANIFESTO.md` está errada, estarei feliz em discutir. Contudo, você me apresenta e eu decido. A escrita vai direto no `MANIFESTO.md` — não existe arquivo de rascunho —, mas **toda alteração do Manifesto é um commit à parte**, e o commit só existe com o meu aval declarado. A pergunta é sempre a mesma linha, crua: "Vou realizar o commit do `MANIFESTO.md` a seguir. Você confirma que leu o diff e concorda com as alterações?". Sem essa resposta o commit não acontece, e a aprovação fica registrada no commit — nunca dentro do `MANIFESTO.md`, que é a instrução, não o histórico dela. Sempre que eu te pedir uma análise do `MANIFESTO.md`, a proposta vem como diff nesta sessão, separada em pontos de assuntos diferentes e sucinta — eu vou entender o erro lógico sem você escrever um parágrafo para cada item.

- O `README.md` é seu harness secundário. Se ele não existe, o crie. Qualquer instrução no `CLAUDE.md`, ou em qualquer outro markdown de memória de agentes LLM proprietário, se conflitando com esse repositório, quando usado para algo a ser feito nesse repositório, deve ser ignorado. Se quiser, e recomendo, pode haver uma linha nesses arquivos apontando para o `README.md`. Com exceção dos workflows de desenvolvimento no GitHub, e com o envio das minhas interações com a LLM para outra pasta (visando estudo posterior) esse repositório é autocontido, e tudo necessário para ele vive aqui.

- Ao ler o README é necessário ver se ele está sustentado as decisões do manifesto. Se não, precisa ser corrigido. O `README.md` é uma extensão do `MANIFESTO.md`. E o código em si é uma extensão do `README.md`. Se decidirmos algo arquitetural, em sessão, que não veio do Manifesto diretamente, você vai me avisar e propor a escrita, pelo mesmo aval. E isso nunca pode ser ignorado, nem por mim. A "cadeia de custódia" MANIFESTO > README > CÓDIGO é o que vai manter esse "arreio" preso. Veja que definições muito estreitas sobre nome de pastas de cada módulo não cabe para o `MANIFESTO.md`. Ter que detalhar cada item individual me dá a sensação que é melhor eu desenvolver do zero.

- Por fim, o Manifesto vai ser modificado com o tempo. Então entenda que a lógica de ler manifesto, derivar README, é constante.

- O resto dos arquivos, fique a vontade. Incluindo o FAQ.md. É responsabilidade sua. Deve ser escrito como uma sequência de perguntas comuns. Eu aprovo a pergunta e a resposta que você sugerir, só me informe quando entender que vale preencher. E o FAQ.md tem que estar ordenado em ordem de uso da ferramenta. Perguntas mais iniciantes no começo como "o que esse arquivo faz na minha máquina" para peguntas mais avançadas como "como eu modifico o Bill ao meu bel-prazer". É no FAQ que mora a explicação do que está por baixo: qual tela é sua e qual é de terceiros.

### Forma de trabalho

- Sempre trabalhe em duas sessões por item, nunca uma. Na primeira, modo plano: explorar, discutir e fechar a decisão, sem escrever código. Antes do `/clear`, o plano tem que ser salvo fora da conversa — no `BACKLOG.md`, na raiz do repositório — já com o que conta como pronto, para a segunda sessão não precisar perguntar. A segunda nasce limpa, lê o item no `BACKLOG.md` e implementa um item, do tamanho de uma sessão. Nunca despeje arquivo ou saída grande no contexto: filtre, corte ou delegue a um subagente e traga só a conclusão; não releia o que já está na conversa, não repita o que já foi dito e não gaste turno à toa — cada turno reenvia tudo. E onde faltar informação para decidir, pergunte antes de agir, com o custo de cada opção à mostra: o que não estiver autorizado, não acontece.

## 1. Origem [contexto]

### Introdução

O Bill é um software completamente escrito por LLM. Esse Manifesto foi escrito por mim na primeira versão — ela está no histórico do git — e de lá para cá quem o modificou foi a LLM, à medida que ela encontrava contradições ou que decidíamos coisas novas; cada alteração passou pelo meu aval (§0). O _ghostwriter_ da PoC é Claude Code + DeepSeek Flash versão 4, e a partir do início do desenvolvimento final do projeto, versão 4.1. A escolha é proposital: primeiro é o preço. Segundo se eu for ter meus dados usados para treinamento, que seja para algo que volta como pesos abertos para a comunidade. Acho que a matemática é simples. Também é uma tentativa de provar que temos LLM suficiente já. Talvez assim parem de uma vez essa corrida sem fim por uma AGI.

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

Mas, além disso, o Bill é um ambiente de trabalho minimalista — mínimo para ser **funcional**, não mínimo para ser **estético**; os [temas](#design-system-e-temas) estão aqui para isso. "Não preciso de muito para ser produtivo em um ambiente tecnológico". Isso é um manifesto em si: dá para ser produtivo com um binário e uma pasta. O amparo — a LLM local (§7g) e a infraestrutura de suporte (§7) — fica fora do mínimo: entra quando eu quiser, e a ausência dele não tira funcionalidade nenhuma do Bill. Várias extensões do Bill vão morar como algo meu, inicialmente. Enviar minha biblioteca de jogos zerados para o rawg usando a base da Steam e do Heroic não cabem na parte padrão do Bill. E também abrir a possibilidade de extensões da comunidade, sem uma curadoria, com todo o risco de ataques de Supply Chain, é complicado. Por isso Bill nasce como é, analisando funcionalidade a funcionalidade se ela cabe aqui.

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
  - O Bill tem autenticador próprio, com quatro formas de entrar, todas terminando num usuário da tabela `user`: Forms local, Basic, credencial de máquina e a identidade afirmada pelo portão — [Interfaces](#5-interfaces-normativo), [Tabelas](#tabelas).
  - A credencial do usuário mora hasheada na própria linha dele, com `libsodium`; Basic e Forms são a **mesma** credencial, e o que os separa é o transporte — [Tabelas](#tabelas).
  - Nenhum segredo mora no `settings.json`: ele guarda permissão e ajuste, nunca credencial — [Configurações gerais](#configurações-gerais).
  - Toda função da API é protegida por RBAC; a permissão é `objeto:ação`, o papel é um conjunto de permissões, e credencial de máquina tem papel declarado — [Tabelas](#tabelas).
  - O primeiro admin nasce na primeira subida, com terminal na frente; sem usuário nenhum o Bill não expõe — [Interfaces](#5-interfaces-normativo).
  - Papel e permissão são tela do WebApp, e só admin mexe neles — [Interfaces](#5-interfaces-normativo).
  - Segredo de máquina se guarda hasheado, com papel; segredo que o Bill **usa**, como chave de API de serviço externo, se guarda criptografado na tabela `secret` — [Gestão de segredos](#gestão-de-segredos).
  - Serviço que fala com o Bill recebe escopo delimitado — mínimo privilégio: o comprometimento de um serviço alcança a função dele e nada mais — [Caminho container](#7-caminho-container-os-passos-normativo).
  - Identidade que chega pelo portão só vale com o segredo do portão: o Bill sorteia um segredo por instalação, escreve no Caddyfile que ele mesmo gera, e recusa identidade sem ele — [Instalar provedor de identidade como container](#b-instalar-provedor-de-identidade-como-container-obrigatório).
  - O Forms fica ligado até o Authelia estar provado funcionando na frente do Bill; a virada é um conjunto que comita ou volta atrás — [A virada entre os caminhos](#a-virada-entre-os-caminhos).
  - Portão caído fecha o Bill: ele avisa que o portal de autenticação está indisponível, e a volta ao modo Forms é pelo Wizard ou pela `cli`, os dois locais — [A virada entre os caminhos](#a-virada-entre-os-caminhos).
  - O estado persistente de todo serviço mora na Pasta de Trabalho; serviço cujo estado não couber lá não entra — [Caminho container](#7-caminho-container-os-passos-normativo).
  - O tema do portal de autenticação não é o do Bill: ele fica o mais neutro possível, e o `FAQ.md` explica o que está por baixo — [Interfaces](#5-interfaces-normativo).
  - Autenticador, WebApp, corretor, notificador e VPN rodam em containers isolados no caminho container — [Caminho container](#7-caminho-container-os-passos-normativo).
  - A execução é sem privilégio, com elevação só por pedido explícito — [Permissão de acesso](#permissão-de-acesso).
  - Pacotes e imagens são fixados em versão e hashing — [Dependência externa](#dependência-externa).

### Acesso e exposição

- Sem nenhuma forma de autenticação configurada, o Bill escuta apenas `127.0.0.1`. Não há exceção, e não há modo "só nesta rede interna": ou há autenticação, ou o Bill não sai do laço local.

- Expor exige autenticação **e** TLS. Como o TLS é do Caddy, e o Caddy é embarcado (§3, Código e delivery), a exposição no caminho hospedado acontece por `bill webapp --include-caddy`: sem a bandeira, o comando serve o WebApp em HTTP, e só em laço local. No caminho container quem fica na borda é o Caddy em container, pelo isolamento.

- O Bill não entrega HSTS, por motivo óbvio: ele serve com certificado próprio, e HSTS transformaria o aviso do navegador em erro sem saída. É o preço de não depender de um domínio público, e de não poder garantir TLS confiável.

### Internacionalização

- Com exceção do Manifesto, que é originalmente escrito em `pt_BR`, do `FAQ.md`, também nessa língua, e das traduções desses dois arquivos, todos os outros markdowns desse repositório devem ser escritos em inglês. Futuras traduções do `MANIFESTO.md` moram em `MANIFESTO/` e do `FAQ.md` em `FAQ/` — e esses dois diretórios são a exceção à regra do inglês, não o contrário. Os códigos de idioma seguem o formato POSIX (`pt_BR`, `en_US`), alinhados ao módulo de `i18n`. Não é BCP 47.

- Todo código, incluindo comentários, chaves de objetos, variáveis, métodos e nomes de arquivos serão em Inglês Estadunidense (`en_US`). No geral, os arquivos de código não têm objetivo de serem lidos por usuários finais, apenas auditados por desenvolvedores. Então é mais vantajoso manter a base em inglês para o processamento da LLM. Essa regra vale para o que é versionado no repositório; não vale para os arquivos que o Bill gera na Pasta de Trabalho.

- A interface toda segue `i18n`. Nenhuma string é salva diretamente no código, seja backend ou frontend — `cli`, WebApp e Wizard. A fonte da verdade é o módulo de `i18n`, que organiza os textos em grandes blocos, evitando um `pt_BR.json` gigante que a LLM precisa ler o tempo todo. Os blocos são empacotados no binário; o que fica na Pasta de Trabalho é só o idioma ativo, em `app/i18n/active`.

- Por padrão a LLM deve gerar textos a fim de popular o `i18n` em `pt_BR` originalmente e `en_US` como tradução. Essa separação se faz com objetivo de que, na maior parte do tempo, estarei dando foco nos textos em `pt_BR` e não tanto para `en_US`.

- Na `cli`, mensagens e ajuda saem sempre pelo `i18n`. O comando `bill lang pt_BR --include-subcommands` estende a tradução aos nomes dos subcomandos, o que não é comum, e por isso fica como opcional. A resolução do idioma é `$BILL_LANG` → `app/i18n/active` → locale do sistema → `en_US`, e toda superfície reporta de onde ele veio.

### Código e delivery

- Bill é escrito em `Python 3.14`. Todo seu estilo de código é baseado em `PEP 8`. A ideia é que ele seja entregue em um binário único: Windows, Linux e Mac. Seu versionamento é SemVer, e o artefato carrega esse número — no Windows ele sai como `bill.exe`, nos outros como `bill`.

- O binário carrega o **Caddy** dentro de si. O Caddy é um binário estático único, e no caminho hospedado é ele quem termina TLS e publica o Bill; no caminho container ele roda como container, pelo isolamento. Não há variante de release: um artefato só, e o custo em disco é aceito em troca dessa simplicidade. Como o Caddy vai dentro do binário, a versão dele é a do artefato — não há pin separado para ele.

- A atualização é substituir o binário. Como ele carrega o manifesto das imagens fixadas, ao subir depois da troca ele re-verifica as imagens dos serviços e re-pina o que estiver defasado — o pin anda só para frente e nunca para trás. Uma instância à frente do pin do binário **avisa e segue**: não é rebaixada. Manter tudo atualizado, e sem falha de segurança, é gestão minha, não do binário.

- Toda atualização que mude estrutura traz a sua **migration**, e ela roda na primeira subida depois da troca do binário. A pasta sabe até onde já migrou, e esse carimbo mora em `app/` — junto do resto do que o Bill escreve —, nunca dentro da declaração publicada. A declaração continua sendo dado puro, que você edita; o que os dois autores assinam fica separado.

- A migration **nunca sobrescreve o que já existe**: ela adiciona o que falta e reporta o que pulou. Numa colisão, quem manda é a sua edição, e o Bill avisa em vez de escolher por você — a mesma escolha do pin das imagens. E uma migration publicada **não se edita**: pastas já a rodaram, e correção vira a migration seguinte.

- Os comentários no código explicam apenas o que o código não fala por si: por que aquele trecho é necessário e, quando não for óbvio, o que ele faz. Para histórico, usamos `git`. Não é necessário anotar datas de decisões. Veja, o código deve falar por si só (como o [xadrez fala por si só](https://pt.wikipedia.org/wiki/Controv%C3%A9rsia_Magnus_Carlsen%E2%80%93Hans_Niemann)). Se precisarmos de quilos de comentários, talvez ele não esteja tão bem escrito assim.

- O binário mora na pasta e essa pasta é do binário. Ela é a Pasta de Trabalho. Se você abrir o binário dentro da pasta de `Downloads`, a pasta de `Downloads` é dele. No primeiro carregamento você será avisado de que: "o Bill foi aberto na pasta <pasta>. Como não existe um arquivo `app/settings.json` aqui, entende-se que é uma nova Pasta de Trabalho. Confirma que o Bill utilize essa pasta? Recomenda-se a utilização de uma pasta vazia, em qualquer local do seu computador. Cancele e mova o arquivo para outra pasta, se não concordar.". Ou algo do gênero.

- O backup da Pasta de Trabalho é a promessa do Bill: **a pasta copiada basta para tudo voltar a funcionar**, sem troca de binário no meio. Por isso nada se regenera sozinho — nem o que foi extraído, nem o que foi baixado —, e a única exceção é o que é específico de plataforma: a pasta que muda de sistema operacional re-extrai o que não serve mais. Tudo o que o Bill escreve mora em `app/`, numa pasta visível justamente para que ninguém a confunda com lixo: ajustes, idioma ativo, contadores, carimbo de migração, o que foi extraído para rodar, cache e o estado dos serviços.

- Sem terminal para perguntar não há primeira execução: o Bill encerra com código `1` em vez de assumir uma pasta. E recusar não cria nada — o Bill diz onde mover o binário e sai sem erro, porque recusar não é erro.

### Permissão de acesso

- O Bill, por padrão, é arquitetado para ser executado sem permissões de administração (i.e. não usa `root` ou `Administrador`). Contudo, montar o ambiente do §7 inevitavelmente exige elevação em algum momento. Nesses casos a elevação de privilégio acontecerá por um pedido explícito, com a razão à mostra.

- A lista fechada do que exige elevação não se escreve antes da função: ela nasce com a implementação que a pede. Cada item que entrar nela é uma decisão de segurança e passa por esta seção.

### Portabilidade

- O dado é sempre POSIX. `LF` ou `/`. Conversões para Windows apenas para exibição (como na mensagem de boas-vindas da Pasta de Trabalho, acima) ou para as `syscalls`.

### Dependência externa

- Dependência a pacotes e imagens são fixadas em versão e hashing — seja de pacotes, seja de imagens externas.

- O Caddy é a exceção declarada, e não por descuido: ele vai embarcado no binário, então quem o pina é o próprio artefato, com o SemVer do Bill.

## 4. Arquitetura [normativo]

### Separação de camadas

- O Bill é estruturado em camadas. O `core` trata todas as regras da aplicação. Não é um bloco monolítico: é quebrado em módulos e arquivos conforme o assunto. Mas tudo passa por ele.

- A `ui` é uma forma de camada, mas tem mais. O Bill já nasce com três: `cli`, WebApp e Wizard. Todas só são formas diferentes de interagir com o `core`. Nem tudo feito pelo `cli` está disponível no WebApp. Mas tudo no `WebApp + Wizard` está disponível no cli.

- Outra camada muito importante é `data`. Essa camada fica responsável por acessar as tabelas. Dados estruturados salvos em `.jsonl` dentro da pasta `./data`. A pasta `./data` é criada automaticamente na primeira execução, com as tabelas de sistema vigentes.

- O Bill também suporta gerenciar arquivos diversos. É a camada `prose`. Qualquer arquivo que não for estruturado fica a cargo dessa camada. A pasta `./prose`, também criada na primeira execução, vem com um arquivo de boas-vindas gerado pelo `i18n` no idioma ativo escolhido na primeira execução (`Bem-vindo.md` em `pt_BR`, `Welcome.md` em `en_US`), para facilitar os próximos passos.

- Os serviços externos são tratados pela camada `services`. Aqui é para que a camada seja o máximo agnóstica a ferramenta possível.

- Os segredos são gerenciados pela camada `encryption`.

### Tabelas

- O Bill possui um motor próprio de gestão de dados estruturados. Aqui é usado o termo Tabela, ou `table` internamente. A identidade da tabela é um id, e o id é singular (`task`, `project`, `reminder`, `secret`, `user`, `role`): é ele que nomeia a tabela em todo lugar, inclusive no comando (`bill task list`) e no esquema. O arquivo de linhas é que vai no plural. Logo `data/tasks.jsonl` é a tabela em si e `data/schema/task.json` o esquema dela.

- As tabelas `task`, `project`, `reminder`, `secret`, `user` e `role` são padrão do sistema. Servem para entregar uma funcionalidade inerente. Tabelas de sistema não são deletáveis, mas suas linhas são.

- Tabelas de usuário permitem CRUD completa da própria tabela. 

- O schema de tabela tem muitas funcionalidades, como campos padrão na exibição e ordem padrão na exibição de tabelas. Os rótulos de exibição que ele carrega são chaves de `i18n`, nunca o texto final. O contador de ids não mora no esquema: ele conta o que aconteceu nesta pasta, e o esquema é publicado — então ele vive em `app/counters.json`, e é escrito antes da linha, porque um id entregue está gasto mesmo se a escrita seguinte falhou.

- O esquema declara **tipos de campo**, e um deles é o **campo hasheado**. Um campo hasheado nunca guarda o valor que você entregou: ele guarda o resultado de uma derivação segura, feita com `libsodium`, e o valor não volta na leitura — só se confere. Tudo o que entra num campo desse tipo usa o mesmo método, sem exceção e sem escolha por campo, porque método de hash não é preferência de quem escreve o esquema. É ali que mora a credencial do usuário.

- A separação é esta, e vale para todo o Bill: **o que se prova se guarda hasheado, e o que o Bill usa se guarda criptografado** — a `secret` é da segunda espécie, o `user` é da primeira.

- O catálogo de permissões é declarado no código, e não é dado solto: a permissão tem a forma `objeto:ação`, os objetos e as ações são uma lista fechada, e os rótulos de exibição saem do `i18n` como todo o resto. Um papel é uma linha da tabela `role` com um conjunto de permissões, e a tabela `user` aponta para o papel. Papel que nomeia permissão inexistente não derruba o Bill: ele avisa, e o aviso é o que se lê.

### Gestão de segredos

- Para executar certas ações, como acessar APIs de serviços externos, o Bill precisa ter acesso a segredos. Todo segredo que o Bill **guarda** é escrito na tabela `secret` — segredo que só se confere, como credencial de usuário, mora hasheado na própria linha (§4, Tabelas). Lá estão metadados e o segredo em si, salvo de forma criptografada. Qualquer dado sensível a ser salvo em alguma tabela pode ser salvo de forma criptografada.

- A criptografia do bill é a partir de uma chave principal gerada a partir de uma frase de acesso. Essa frase de acesso precisa ter no mínimo 16 caracteres, mas é uma frase. Mariazinha comeu todo o pudim, escrito em letras minúsculas sem espaços é mais seguro que Mariazinha@123. Bill usa `libsodium` para essa gestão.

- É recomendado guardar essa chave, fora da máquina, em um local seguro. Imprimir e armazenar em documentos pessoais de difícil acesso, por exemplo.

- Em criptografia, não existe mágica. Ou você digita sua chave todas às vezes em que o motor precisar fazer algo que depende de um segredo, ou digita ela uma vez durante o período que a aplicação estiver ativa, ou salva sua chave principal em disco. Não é seguro, mas autonomia é autonomia. Cada chave intermediária é gerada a partir da chave principal. A chave principal te permite recuperar acesso a qualquer chave intermediária perdida. Cada chave intermediária tem o escopo definido para o que ela se propõe. Cada serviço ou cada finalidade.

- Nem tudo o que autentica passa por aqui, e isso é de propósito: a verificação de uma credencial de entrada não pode depender da frase de acesso, senão o Bill só sobe quando alguém digita a frase. Por isso o que se confere é hasheado, e é por isso que a credencial não mora na `secret`.

### Configurações gerais

- As configurações do bill moram dentro de `app/settings.json`, dentro da pasta de trabalho. Aí moram propriedades em format chave-valor. `i18n` não mora aqui: os blocos de tradução são empacotados no binário e o idioma ativo mora em `app/i18n/active`.

- Nenhum segredo mora no `settings.json`. Ele guarda permissão e ajuste — como a permissão de um usuário entrar por Basic —, nunca a credencial em si.

- O Wizard Tkinter exibe as possibilidades de instalação do ambiente. No modo avançado habilitado, o Wizard apresenta a renderização do arquivo de configurações, permitindo modificar quaisquer uma. Segue a escolha de designer de algumas ferramentas, como VS Code, que possuem a base das configurações em JSON, mas permitem a alteração na UI.

- Cada serviço pode ter dados persistidos. Nesse caso, eles moram em `app/services/<serviço>`, como `app/services/vpn` ou `app/services/spelling-checker`. O nome do serviço é canônico e não muda com a ferramenta que o cumpre: `spelling-checker` é o serviço, LanguageTool é quem o cumpre hoje (§7d), e o que um dia o substituir não renomeia pastas nem chaves. O que é rótulo de exibição é chave de `i18n`.

- Essa pasta não é conveniência, é condição de entrada: um serviço só entra no §7 se o estado persistente dele couber aí dentro. Serviço que guarda a vida dele em algum volume que ninguém copia deixa o backup da pasta mentir.

## 5. Interfaces [normativo]

### Linha de comando (`cli`), aplicação web (WebApp) e interface Tkinter (Wizard)

- Ao abrir o Bill, seja em linha de comando, seja direto pela interface gráfica, temos o "Painel de Controle". É uma interface em Tkinter, o Wizard. Aqui são configuradas as "entranhas" do ambiente do Bill, sendo sua primeira camada a aplicação web.

- Chamar o binário direto do terminal carrega a interface Tkinter. Qualquer outro parâmetro passado faz o programa agir como uma `cli`. `bill ajuda`, ou `bill help`, mostra como usar a cli completamente. Você pode modificar nas configurações para o comando `bill` não abrir o Tkinter e sim o `bill help`.

- A linha de comando funciona para tudo do Bill. Qualquer funcionalidade que ele exponha, seja na API REST (utilizada pelo frontend do WebApp), seja no WebApp em si, é acessível pela linha de comando.

- O Wizard é uma tela que permite realizar configurações mais críticas do Bill que eu não queria deixar disponível na rede. Ele tem dois papéis que não se mudam de lugar: a **primeira subida**, em que a Pasta de Trabalho é confirmada e o primeiro admin é criado, e a **volta ao modo Forms**, quando o portão de autenticação cai. No mais, instalar serviços, gerenciar chaves principais e editar as configurações no modo avançado.

- O `cli` executa apenas localmente, em exceção quando está comunicando com APIs externas para devida configuração. E é ele, ou o Wizard, que devolve o Bill ao modo Forms: as duas são superfícies locais, e é por isso que a volta existe.

- Papel e permissão **não** são assunto do Wizard: isso é tela do WebApp, e o atrito de fazer admin por lá não se paga. O Wizard fica com o que só ele pode fazer.

### Aplicação WebApp

#### Design System e temas

- O Design System é de desenvolvimento da LLM. Crescimento gradual de componentes.

- O suporte a temas é parte estrutural do Bill. Vários temas me ajudam a testar a força do Design System em cima de diferentes visões. Ao mesmo tempo que me fazem ficar feliz de usar o sistema. PRs de tema são bem-vindas, mas estão totalmente sujeitas ao meu julgamento pessoal e ficarei feliz em compartilhar meu péssimo gosto, se não quiser aceitar uma PR. Mas não se acanhe!

- O tema vale para o WebApp inteiro, tela de login incluída: não existe página do Bill que escape do Design System, e a entrada é a primeira impressão que ele tem que causar.

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

- As integrações (§7) podem existir sem container: quem instala o serviço por conta e aponta o Bill para ele usa o serviço, com a ciência de que o estado daquele serviço não é mais assunto do Bill — e, portanto, que o backup da pasta não o cobre.

- Expor o Bill pelo caminho hospedado com o Authelia do caminho container é o **modo avançado**, e não é suportado: quem quiser o portão, usa o caminho container.

### Caminho container

- É o Bill montando um ambiente de serviços em containers de imagens fixadas (§7). Aqui existe isolamento, e ele existe por um motivo específico: **conter o raio de explosão de cada serviço**. O comprometimento do `ntfy` alcança a notificação e nada mais; o do corretor alcança o corretor. O que cada serviço expõe é o que ele se propõe a fazer, e nada além.

- Serviço que precisa falar com o Bill — e não o Bill com ele — tem o escopo delimitado: credencial com papel declarado, e só o que aquele papel permite. Mínimo privilégio, aplicado.

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

- A divisão é: **quem** é usuário é do Bill, e **como** se prova que é ele é do Authelia. A tabela `user` (§4) guarda identidade, papel e a credencial hasheada — e no caminho container quem usa a credencial do Authelia é o Authelia.

- O que o Authelia **não** é: provedor de login com Google. Ele não faz o papel de relying party, e isso é decisão do projeto, não configuração. Login com terceiros não faz parte do Bill.

- Aqui não há autenticação com a cara do Bill. O portal é do Authelia, e o que o Bill faz é pedir que ele seja o mais neutro possível, para não parecer o que não é (§5).

- O que o Bill exige de quem chega com identidade é o **segredo do portão**: um valor sorteado pelo Bill na instalação, escrito no Caddyfile que ele mesmo gera, colado pelo Caddy em todo pedido que carrega identidade, e recusado por quem não o traz. É o M2M entre o Caddy e o WebApp do Bill, e o Authelia nunca o vê.

#### c. Instalar WebApp como container (obrigatório)

- O WebApp, principal forma de usar o Bill, é instalado como um container. Visa diminuir o raio de explosão em uma aplicação web comprometida.

#### d. Instalar corretor ortográfico e gramatical como container (opcional)

- O padrão do Bill para correção de textos é LanguageTool, hoje a ferramenta que cumpre o serviço `spelling-checker` (§4). Ela serve para sublinhar os erros na tela de edição. Bem útil.

#### e. Instalar VPN (opcional)

- O Bill permite configurar uma VPN. Aqui ela é relevante, pois permite criar uma rede privada para que múltiplos dispositivos conversem entre si. Logo se o Bill WebApp roda na sua máquina pessoal, fica acessível de forma segura do seu celular, em qualquer lugar. Aqui estou utilizando Tailscale. É proprietário, mas evita que seja necessário um servidor na nuvem. Suporte a Headscale no futuro.

#### f. Instalar notificador como container (opcional)

- Com tudo configurado, a cereja do bolo é o `ntfy`. Os lembretes configurados podem ser notificados diretamente como um Push Notification.

#### g. Instalar LLM local (opcional)

- O Bill pode ter uma LLM local para tarefas simples. Como o objetivo do Bill é não depender de uma LLM externa para ser um agente, a ideia de ter um serviço LLM local para às vezes pedir para criar uma tarefa é muito melhor que ter que pagar token para isso.

- A LLM já é pré-configurada com "habilidades". Você pede, ela entende as funções que ela tem pré-definido, e executa. Qual LLM usar depende da placa de vídeo disponível.

#### h. Instalar chatbot local (opcional)

- Se executar uma LLM minimamente capaz de entender inputs não for possível, é disponibilizado um chatbot. Ele realiza inferências no texto para tentar direcionar para a tarefa mais próxima. Mais propenso a erros, mas capaz de executar em qualquer máquina.

## 8. Ambiente de teste end-to-end [normativo]

- O teste principal é verificar se, com o Podman instalado, executar as ações do Bill funciona perfeitamente. Esse teste acontecerá em VMs Mac, Linux e Windows.

- Ele é **automatizado de ponta a ponta**: nenhuma parte depende de olho ou de mão numa tela. O script sobe a VM, abre o binário e verifica o que voltou — Podman ausente faz o Bill oferecer as duas saídas; Podman presente sobe o ambiente com as imagens no pin; uma instância à frente do pin avisa e segue; o Bill recusa subir na rede sem autenticação e sobe com ela; o WebApp responde atrás do portão; e a Pasta de Trabalho criada na primeira execução é só o que o §3 descreve.

- O caminho hospedado tem portão próprio, e é barato porque não depende de VM nem de container: a primeira subida pede o admin e não deixa o Bill expor sem ele; sem autenticação o Bill escuta só `127.0.0.1`; expor sem TLS é recusado; a virada para o container volta atrás inteira quando alguma ação não fecha; e o portão caído fecha o Bill com a frase à mostra.

- O teste **não é o critério de pronto de cada função** — uma função fica pronta pelo que o `BACKLOG.md` diz que ela é. Ele é o portão da primeira publicação no GitHub, e dali em diante.
