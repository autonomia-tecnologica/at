# 3. Regras [normativo]

### Segurança

- Toda decisão de segurança da aplicação mora no `rules.md`, e esta seção é o registro delas. Nenhuma decisão de segurança é tomada sem discussão, e nenhuma é decidida fora daqui: as outras seções descrevem operação e detalham o que está registrado abaixo, mas não decidem segurança por conta própria. Se não está registrado aqui, não existe.

- O isolamento é do caminho container. No caminho hospedado o Bill é um processo na máquina, sem container nenhum em volta, e isso é declarado — não há promessa de conter o raio de explosão de um comprometimento. O que o caminho hospedado oferece em troca é escutar só o laço local por padrão, e exigir autenticação e TLS para sair dele.

- Decisões vigentes. A linha é a decisão; o detalhe vive onde o link aponta:
  - Sem autenticação, o Bill só escuta `127.0.0.1`; exposto exige autenticação — [Acesso e exposição](#acesso-e-exposição).
  - Exposto exige TLS, e TLS só existe com o Caddy: `bill webapp` sem a bandeira é HTTP em laço local — [Acesso e exposição](#acesso-e-exposição).
  - O Bill tem autenticador próprio, com quatro formas de entrar, todas terminando num ator: Forms local, Basic, credencial de máquina e a identidade afirmada pelo portão — [Interfaces](interfaces.md), [Tabelas](architecture.md#tabelas).
  - A credencial do ator mora hasheada na própria linha dele, com `libsodium`; Basic e Forms são a **mesma** credencial, e o que os separa é o transporte — [Tabelas](architecture.md#tabelas).
  - Nenhum segredo mora no `settings.json`: ele guarda permissão e ajuste, nunca credencial — [Configurações gerais](architecture.md#configurações-gerais).
  - Toda função da API do core é protegida por RBAC; a permissão é `objeto:ação`, o papel é um conjunto de permissões, e credencial de máquina tem papel declarado — [Tabelas](architecture.md#tabelas).
  - O primeiro admin nasce na primeira subida, com terminal na frente; sem ator nenhum o Bill não expõe — [Interfaces](interfaces.md).
  - Papel e permissão são tela do WebApp, e só admin mexe neles — [Interfaces](interfaces.md).
  - **Instalar serviço é do Wizard e só dele** — [Interfaces](interfaces.md).
  - Segredo de máquina se guarda hasheado, com papel; segredo que o Bill **usa**, como a credencial de um serviço, se guarda criptografado na tabela `secret` — [Gestão de segredos](architecture.md#gestão-de-segredos).
  - O Bill autentica nos serviços em vez de se aproveitar de estar na mesma máquina: credencial de administração existe onde ela é necessária, e ela conta na postura — [A postura de segurança](#a-postura-de-segurança).
  - Serviço que fala com o Bill recebe escopo delimitado — mínimo privilégio: o comprometimento de um serviço alcança a função dele e nada mais — [Caminho container](paths.md#caminho-container).
  - Identidade que chega pelo portão só vale com o segredo do portão: o Bill sorteia um segredo por instalação, escreve no Caddyfile que ele mesmo gera, e recusa identidade sem ele — [Instalar provedor de identidade como container](container.md#b-instalar-provedor-de-identidade-como-container-obrigatório).
  - O Forms fica ligado até o Authelia estar provado funcionando na frente do Bill; a virada é um conjunto que comita ou volta atrás — [A virada entre os caminhos](paths.md#a-virada-entre-os-caminhos).
  - Portão caído fecha o Bill: ele avisa que o portal de autenticação está indisponível, e a volta ao modo Forms é pelo Wizard ou pela `cli`, os dois locais — [A virada entre os caminhos](paths.md#a-virada-entre-os-caminhos).
  - Toda ação deixa uma linha na tabela `audit`, e a recusa é uma delas — [A auditoria](#a-auditoria).
  - O que se prova se guarda hasheado; o que o Bill usa se guarda criptografado — [Tabelas](architecture.md#tabelas).
  - O estado persistente de todo serviço mora na Pasta de Trabalho; serviço cujo estado não couber lá não entra — [Configurações gerais](architecture.md#configurações-gerais).
  - **Nenhuma extensão executa código hoje.** A primeira classe é dado puro, e código é a última opção — [Extensões](extensions.md).
  - O tema do portal de autenticação não é o do Bill: ele fica o mais neutro possível, e o `FAQ.md` explica o que está por baixo — [Interfaces](interfaces.md).
  - Autenticador, WebApp, corretor, notificador e VPN rodam em containers isolados no caminho container — [Caminho container](container.md).
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

- Com exceção da porta da raiz, todo documento deste repositório mora na **pasta do seu idioma**, no formato POSIX (`pt_BR`, `en_US`), alinhado ao módulo de `i18n` — não é BCP 47. A porta da raiz é um `README.md` fora das pastas, e não tem texto além do título, dos links para as versões em cada língua, e de uma nota curta em `en_US` dirigida a agentes LLM: que leiam no idioma que serve melhor ao modelo, que na dúvida leiam em inglês, e que a trilha inglesa usa os termos e conceitos do mercado de propósito, para um nome significar a mesma coisa aqui e lá fora.

- Os documentos moram em `docs/`, **uma pasta por idioma**, e cada documento tem o par na pasta do outro idioma, com o mesmo nome. **O nome não repete o idioma que a pasta já diz**, e os nomes são minúsculos — só o `README` fica em maiúsculas, por ser o nome que o mundo já conhece.

- **Os dois idiomas mudam sempre juntos**, e o aval de um commit cobre o par. O `pt_BR` é a língua fonte; onde os dois divergirem, vale o `pt_BR`.

- Um **documento de trabalho** mora na pasta do seu idioma e **sem par**: o `docs/en_US/backlog.md` é para o agente, muda todo dia, e traduzir o que muda todo dia é trabalho que ninguém lê.

- Um **gate na suíte** afirma o que essa regra promete: a pasta de cada documento, a existência do par, a mesma estrutura de títulos nos dois, e a ortografia — os dois idiomas passam pelo corretor do repositório, e o que ele ignorar fica numa lista versionada, uma por idioma. Gramática fica com a leitura humana.

- Todo código, incluindo comentários, chaves de objetos, variáveis, métodos e nomes de arquivos serão em Inglês Estadunidense (`en_US`). No geral, os arquivos de código não têm objetivo de serem lidos por usuários finais, apenas auditados por desenvolvedores. Então é mais vantajoso manter a base em inglês para o processamento da LLM. Essa regra vale para o que é versionado no repositório; não vale para os arquivos que o Bill gera na Pasta de Trabalho.

- A interface toda segue `i18n`. Nenhuma string é salva diretamente no código, seja backend ou frontend — `cli`, WebApp e Wizard. A fonte da verdade é o módulo de `i18n`, que organiza os textos em grandes blocos, evitando um `pt_BR.json` gigante que a LLM precisa ler o tempo todo. Os blocos são empacotados no binário; o que fica na Pasta de Trabalho é só o idioma ativo, em `App/i18n/active`.

- Por padrão a LLM deve gerar textos a fim de popular o `i18n` em `pt_BR` originalmente e `en_US` como tradução. Uma chave ausente no idioma ativo cai na fonte e depois nela mesma, então a lacuna fica visível em vez de silenciosa. A chave é um **id estável**, nunca a frase em inglês: renomear um texto não pode renomear uma chave. E a suíte afirma que as duas línguas carregam exatamente as mesmas chaves, para que uma tradução atrasada seja um teste falhando em vez de uma surpresa.

- Na `cli`, mensagens e ajuda saem sempre pelo `i18n`. O comando `bill lang pt_BR --include-subcommands` estende a tradução aos nomes dos subcomandos, o que não é comum, e por isso fica como opcional. A resolução do idioma é `$BILL_LANG` → `App/i18n/active` → locale do sistema → `en_US`, e toda superfície reporta de onde ele veio.

### Código e delivery

- Bill é escrito em Python, e a versão que ele exige mora em `pyproject.toml`, no `requires-python`. Todo seu estilo de código é baseado em `PEP 8`. A ideia é que ele seja entregue em um binário único: Windows, Linux e Mac. Seu versionamento é SemVer, e o binário carrega esse número — no Windows ele sai como `bill.exe`, nos outros como `bill`.

- O binário carrega o **Caddy** dentro de si. O Caddy é um binário estático único, e no caminho hospedado é ele quem termina TLS e publica o Bill; no caminho container ele roda como container, pelo isolamento. Não há variante de release: um artefato só, e o custo em disco é aceito em troca dessa simplicidade. Como o Caddy vai dentro do binário, a versão dele é a do binário — não há pin separado para ele.

- A atualização é substituir o binário. Como ele carrega o manifesto das imagens fixadas, ao subir depois da troca ele re-verifica as imagens dos serviços e re-pina o que estiver defasado — o pin anda só para frente e nunca para trás. Uma instância à frente do pin do binário **avisa e segue**: não é rebaixada. Manter tudo atualizado, e sem falha de segurança, é gestão minha, não do binário.

- Toda atualização que mude estrutura traz a sua **migration**, e ela roda na primeira subida depois da troca do binário. A pasta sabe até onde já migrou, e esse carimbo mora em `App/` — junto do resto do que o Bill escreve —, nunca dentro da declaração publicada. A declaração continua sendo dado puro, que você edita; o que os dois autores assinam fica separado.

- Uma migration **trata o próprio impacto e decide o que fazer com ele**. Nomear uma pasta move um caminho, e o que a pessoa aponta de fora — um vault de outra ferramenta, um script de cópia — é o que quebra depois, quando essa outra coisa for aberta. Por isso o que mexe nas pastas da própria pessoa pergunta antes de mover e diz o que quebra; o que mexe só na pasta do Bill não pergunta, porque não há nada fora para quebrar.

- A migration **nunca sobrescreve o que já existe**: ela adiciona o que falta e reporta o que pulou. Numa colisão, quem manda é a sua edição, e o Bill avisa em vez de escolher por você — a mesma escolha do pin das imagens. E uma migration publicada **não se edita**: pastas já a rodaram, e correção vira a migration seguinte.

- Os comentários no código explicam apenas o que o código não fala por si: por que aquele trecho é necessário e, quando não for óbvio, o que ele faz. Para histórico, usamos `git`. Não é necessário anotar datas de decisões. Veja, o código deve falar por si só (como o [xadrez fala por si só](https://pt.wikipedia.org/wiki/Controv%C3%A9rsia_Magnus_Carlsen%E2%80%93Hans_Niemann)). Se precisarmos de quilos de comentários, talvez ele não esteja tão bem escrito assim.

- **As pastas que a pessoa abre respondem no idioma dela, e são capitalizadas.** `Tabelas/`, `Arquivos/`, `Projetos/`, `App/`, `Compartilhada/` e `Harness/` em `pt_BR`; `Tables/`, `Files/`, `Projects/`, `App/`, `Shared/` e `Harness/` em `en_US`. O nome no disco é a **face**; a máquina lê o **nome interno** — `data`, `prose`, `projects`, `app`, `shared`, `harness` —, declarado num lugar só e resolvido por ele: nome localizado é declaração, nunca um `if` no código que age, e a declaração que uma tabela publica cita o nome interno, nunca a face. Duas pastas são a exceção, e as duas são deliberadas: `App/` não segue o idioma, porque o idioma é registrado dentro dela, e `Harness/` não segue porque o `pt_BR` tomou a palavra inteira — os dois idiomas a escrevem igual.

- **Trocar o idioma renomeia as pastas, e o rename é oferecido e nunca automático.** O Bill diz toda implicação antes de fazer — primeiro o que quebra fora da pasta, porque um vault que outra ferramenta aponta é o que a pessoa não vê quebrar até depois. Quem recusa mantém o nome que tinha: o Bill lê toda grafia que já deu a uma pasta, e diz o que isso custa.

- O binário mora na pasta e essa pasta é do binário. Ela é a Pasta de Trabalho. Se você abrir o binário dentro da pasta de `Downloads`, a pasta de `Downloads` é dele. No primeiro carregamento você será avisado de que: "o Bill foi aberto na pasta <pasta>. Como não existe um arquivo `App/settings.json` aqui, entende-se que é uma nova Pasta de Trabalho. Confirma que o Bill utilize essa pasta? Recomenda-se a utilização de uma pasta vazia, em qualquer local do seu computador. Cancele e mova o arquivo para outra pasta, se não concordar.". Ou algo do gênero.

- O backup da Pasta de Trabalho é a promessa do Bill: **a pasta copiada basta para tudo voltar a funcionar**, sem troca de binário no meio. Por isso nada se regenera sozinho — nem o que foi extraído, nem o que foi baixado —, e a única exceção é o que é específico de plataforma: a pasta que muda de sistema operacional re-extrai o que não serve mais. Tudo o que o Bill escreve mora em `App/`, numa pasta visível justamente para que ninguém a confunda com lixo: ajustes, idioma ativo, contadores, carimbo de migração, o estado dos plugins, o que foi extraído para rodar, cache e o estado dos serviços.

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

- **Nada experimental entra**, nem como ferramenta de desenvolvimento: só componente estável. Versão alpha, beta, release candidate e preview ficam de fora, e o que o fornecedor marca como experimental fica de fora junto — a promessa de que o Bill não muda sob os seus pés não pode depender de uma superfície que o dono dela avisa que vai mudar.

