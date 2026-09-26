# 3. Regras [normativo]

### Segurança

- Toda decisão de segurança da aplicação mora no `rules.md`, e esta seção é o registro delas. Nenhuma decisão de segurança é tomada sem discussão, e nenhuma é decidida fora daqui: as outras seções descrevem operação e detalham o que está registrado abaixo, mas não decidem segurança por conta própria. Se não está registrado aqui, não existe.

- O isolamento é do caminho container. No caminho hospedado o AT é um processo na máquina, sem container nenhum em volta, e isso é declarado — não há promessa de conter o raio de explosão de um comprometimento. O que o caminho hospedado oferece em troca é escutar só o laço local por padrão, e exigir autenticação e TLS para sair dele.

- Decisões vigentes. A linha é a decisão; o detalhe vive onde o link aponta:
  - O AT responde em `127.0.0.1` por padrão, e é isso que este produto recomenda; outro endereço é ajuste da pasta, e o que ele custa é o que a nota de segurança do ambiente avalia — [Acesso e exposição](#acesso-e-exposição).
  - Exposto exige TLS, e TLS só existe com o Caddy: `at-cli webapp` sem a bandeira serve HTTP, e quem sai do laço é o Caddy — [Acesso e exposição](#acesso-e-exposição).
  - O AT tem autenticador próprio, com quatro formas de entrar, todas terminando num ator: Forms local, Basic, credencial de máquina e a identidade afirmada pelo portão — [Interfaces](interfaces.md), [Tabelas](architecture.md#tabelas).
  - A credencial do ator mora hasheada na própria linha dele, com `libsodium`; Basic e Forms são a **mesma** credencial, e o que os separa é o transporte — [Tabelas](architecture.md#tabelas).
  - Nenhum segredo mora no `settings.json`: ele guarda permissão e ajuste, nunca credencial — [Configurações gerais](architecture.md#configurações-gerais).
  - Toda função da API do core é protegida por RBAC; a permissão é `objeto:ação`, o papel é um conjunto de permissões, e credencial de máquina tem papel declarado — [Tabelas](architecture.md#tabelas).
  - O primeiro admin nasce na primeira subida, com terminal na frente; sem ator nenhum o AT não expõe — [Interfaces](interfaces.md).
  - Papel e permissão são tela do WebApp, e só admin mexe neles — [Interfaces](interfaces.md).
  - **Instalar serviço é do Wizard e só dele** — [Interfaces](interfaces.md).
  - Segredo de máquina se guarda hasheado, com papel; segredo que o AT **usa**, como a credencial de um serviço, se guarda criptografado na tabela `secret` — [Gestão de segredos](architecture.md#gestão-de-segredos).
  - Segredo que o AT usa é **selado com a chave do próprio serviço ou propósito**: a chave se deriva da Chave do Cofre e se recupera só dela, e o que um escopo selou outro não abre — [Gestão de segredos](architecture.md#gestão-de-segredos).
  - O AT autentica nos serviços em vez de se aproveitar de estar na mesma máquina: credencial de administração existe onde ela é necessária, e ela conta na postura — [A postura de segurança](#a-postura-de-segurança).
  - Serviço que fala com o AT recebe escopo delimitado — mínimo privilégio: o comprometimento de um serviço alcança a função dele e nada mais — [Caminho container](paths.md#caminho-container).
  - Identidade que chega pelo portão só vale com o segredo do portão: o AT sorteia um segredo por instalação, escreve no Caddyfile que ele mesmo gera, e recusa identidade sem ele — [Instalar provedor de identidade como container](container.md#b-instalar-provedor-de-identidade-como-container-obrigatório).
  - O portão prova a credencial que a linha do ator já carrega: o AT escreve para o provedor de identidade as pessoas da própria pasta, com a derivação que a linha guarda, e os nomes e as derivações ficam dentro da Pasta de Trabalho, que é o que o backup cobre — [Instalar provedor de identidade como container](container.md#b-instalar-provedor-de-identidade-como-container-obrigatório).
  - **Trocar a credencial de uma pessoa é um ato só, sobre a linha e sobre o portão**: a credencial vai para a linha do ator, o `users.yml` é derivado dela, e o provedor sobe de novo para que a derivação nova seja a que ele prova. **O reinício não derruba as sessões já abertas**: o segredo de sessão é sorteado uma vez e guardado, e é ele que cifra o cookie, então uma credencial trocada porque vazou deixa as sessões que ela abriu valendo até expirarem. O caminho para encerrá-las é um segredo de sessão novo, que encerra toda sessão da pasta junto — [Instalar provedor de identidade como container](container.md#b-instalar-provedor-de-identidade-como-container-obrigatório).
  - **O notificador fica fora do portão**, e isso é uma medição: o portão autentica por redirecionamento e por cookie de sessão, então um app de celular sem interface toma o 302 e nunca conecta — medido, `subscribers=0` atrás do Authelia e `101` sem ele. A autenticação dele é a ACL por tópico — [Instalar notificador como container](container.md#f-instalar-notificador-como-container-opcional).
  - A credencial do próprio AT no notificador é **delimitada ao tópico** — ela publica e não faz mais nada —, e ela mora num arquivo `0600` dentro da pasta de estado desse serviço, nunca no argv e nunca impressa. A tabela `secret` é onde ela pertence e ela ainda não mora lá: o arquivo é o que vale até o notificador ser apontado para a tabela — [Instalar notificador como container](container.md#f-instalar-notificador-como-container-opcional).
  - **O token do celular é da pessoa, e o `at-deploy` o imprime uma vez.** Ele é o único valor que o `at-deploy` imprime, e o é porque precisa chegar a um celular e não há outro caminho até lá; o produto entrega uma credencial à pessoa uma vez, e é a mesma regra que a credencial de máquina já segue na página. O escopo dele é o espelho do escopo do AT: `read-only` no tópico, e nada além dele — [Instalar notificador como container](container.md#f-instalar-notificador-como-container-opcional).
  - **O certificado do notificador é o do AT, e quem confia nele é o APP do celular e não o aparelho.** O certificado da borda vem de uma CA local (`tls internal`), e um app moderno do Android **ignora a CA que a pessoa instalou no sistema** — medido —, então o que a pessoa importa é a CA do AT (o `root.crt` que a borda guarda dentro da pasta de estado do Caddy) na gestão de certificados do próprio app, e nunca no cofre do aparelho. A estrada é o nome, na 443, e nunca outra porta — [Instalar notificador como container](container.md#f-instalar-notificador-como-container-opcional).
  - **A leitura do celular é provada pelo nome ao fim do ato, e o token fica.** O `at-deploy services phone` pergunta as duas metades à borda — com o token do celular o tópico responde, e sem token nenhum recusa —, e o ato não fecha quando alguma não fecha: um token que existe num arquivo não é um celular que lê. O token não é reemitido nem apagado por causa disso; quem não fecha é a leitura — [Instalar notificador como container](container.md#f-instalar-notificador-como-container-opcional).
  - O Forms fica ligado até o Authelia estar provado funcionando na frente do AT; a virada é um conjunto que comita ou volta atrás — [A virada entre os caminhos](paths.md#a-virada-entre-os-caminhos).
  - Portão caído fecha o AT: ele avisa que o portal de autenticação está indisponível, e a volta ao modo Forms é pelo Wizard ou pela `cli`, os dois locais — [A virada entre os caminhos](paths.md#a-virada-entre-os-caminhos).
  - Toda ação deixa uma linha na tabela `audit`, e a recusa é uma delas — [A auditoria](#a-auditoria).
  - O que se prova se guarda hasheado; o que o AT usa se guarda criptografado — [Tabelas](architecture.md#tabelas).
  - O estado persistente de todo serviço mora na Pasta de Trabalho; serviço cujo estado não couber lá não entra — [Configurações gerais](architecture.md#configurações-gerais).
  - **Nenhuma extensão executa código hoje.** A primeira classe é dado puro, e código é a última opção — [Extensões](extensions.md).
  - O tema do portal de autenticação não é o do AT: ele fica o mais neutro possível, e o `FAQ.md` explica o que está por baixo — [Interfaces](interfaces.md).
  - Autenticador, WebApp, corretor, notificador e VPN rodam em containers isolados no caminho container — [Caminho container](container.md).
  - A execução é sem privilégio, com elevação só por pedido explícito — [Permissão de acesso](#permissão-de-acesso).
  - Pacotes e imagens são fixados em versão e hashing — [Dependência externa](#dependência-externa).

### Acesso e exposição

- O AT responde em `127.0.0.1`, e esse é o padrão que este produto recomenda e o endereço que ele usa para si. O endereço é um ajuste da instalação — a chave `webapp_host` do `settings.json`, ou o `--host` de uma execução — e **o AT não recusa ouvir fora do laço**. **O motivo de não recusar é que o mesmo endereço significa duas coisas e o app não tem como distingui-las**: o `0.0.0.0` de um container está dentro de uma rede, atrás da borda e do portão (§7b, §7c), e o `0.0.0.0` de uma máquina está numa LAN. Quem responde por um endereço é a rede em volta dele, e é a nota de segurança do ambiente que avalia isso; ouvir fora do laço não é o que este produto recomenda.

- Expor exige autenticação **e** TLS. Como o TLS é do Caddy, e o Caddy é embarcado (§3, Código e delivery), a exposição no caminho hospedado acontece por `at-cli webapp --include-caddy`: o Caddy termina o TLS e publica o AT, e o WebApp responde no laço atrás dele. No caminho container quem fica na borda é o Caddy em container, pelo isolamento.

- O AT não entrega HSTS, por motivo óbvio: ele serve com certificado próprio, e HSTS transformaria o aviso do navegador em erro sem saída. É o preço de não depender de um domínio público, e de não poder garantir TLS confiável.

### O modelo de ameaças

- O AT se protege do que ele pode ver, e diz em voz alta o que ele não pode. A primeira barreira é o autenticador do caminho: o Authelia no caminho container, a credencial de Forms no hospedado.

- A segunda barreira é **implícita e não é do AT**: a proteção do próprio celular. Permitir que uma notificação aprove uma ação é confiar que o `ntfy` foi bem configurado **e** que essa configuração está protegida por um aparelho bloqueado. O AT **não audita o celular** — se tem root, se é emulado, se tem bloqueio de tela —, porque isso é trabalho de banco e o AT não é um banco.

- Guardar a credencial do autenticador num cofre de senhas ou no cofre do navegador é escolha da pessoa, e é perigoso. Está escrito aqui em vez de escondido.

- O mesmo vale para fora: backup da pasta que não existe, máquina sem senha, rede aberta. O AT mede o que ele controla e **declara o que não mede**, em vez de dar uma nota que ele não pode sustentar — [A postura de segurança](#a-postura-de-segurança).

### A auditoria

- Toda ação que entra pelo core vira **uma linha** na tabela `audit`: o que foi alterado (`objeto:ação`), onde (a tabela), quando (o instante), quem (o ator), por qual via, o desfecho, e o **limiar de risco** que valia quando a demanda correu. O "porquê" só existe na recusa, onde ele é o motivo, guardado como chave de `i18n`; fora dela, a linha não finge ter intenção. Custo não entra — o limiar não é o preço da ação, e sim a régua contra a qual ela foi medida; o risco da demanda e o valor que a levantou ficam de fora.

- **Tentativa e recusa são linhas**, com o desfecho dizendo o que aconteceu — é a visão de auditoria de ataques. **Leitura não é linha**: ler não é fazer, e auditar leitura faria o rastro crescer mais rápido do que o uso.

- O audit é **log, não referência**: os ids que ele cita são dado bruto, sem `ref`, e por isso ele nunca impede um `delete` (§4, Tabelas). Ele não guarda valor nenhum, e **nada se deleta dele** — a deletabilidade é declarada no esquema, e o `audit` declara que não aceita.

- Só o papel de admin carrega `audit:read`, e nenhum ator de máquina a tem: um `agente` que pudesse ler as próprias recusas aprenderia onde está a parede e ajustaria a próxima tentativa.

### A postura de segurança

- O ambiente tem uma **nota de segurança**, de `F` a `S`, e ela existe para uma coisa: fazer a pessoa ver o preço do que ela monta e melhorar o ambiente dela. Ela não é um cadeado e não impede nada.

- **A nota é por função, e a do ambiente é o elo mais fraco.** Cada função graduada — o destino da Frase de Acesso, a exposição, o segundo fator de quem entra, o escopo das credenciais de serviço, o que o próprio AT carrega, os plugins, o limiar de risco — carrega a sua nota, e para o ambiente ser `S` todas precisam estar em `S`. Um ambiente com uma função ruim não pode se dizer bom, e a tela sempre nomeia **quais funções estão impedindo de subir**.

- **A nota mede o que está configurado e o que você declarou, nunca a verdade.** Ninguém verifica se você leu o que um plugin faz. Isso não é defeito: é o único formato possível, e é por isso que a nota se apresenta como "isto é o que o seu ambiente declara", não como "você está seguro".

- **Todo impasse de segurança se resolve oferecendo as opções e deixando a pessoa aceitar a segurança dela.** A nota informa o preço; quem decide é quem vai viver com ele. Autonomia é também saber a segurança que se quer para si.

- O que o AT **não** mede, ele diz: se não há backup da pasta, se a máquina não tem senha, se o celular não tem bloqueio — o AT não sabe, e prefere dizer isso a inventar uma letra.

### Internacionalização

- Com exceção da porta da raiz, todo documento deste repositório mora na **pasta do seu idioma**, no formato POSIX (`pt_BR`, `en_US`), alinhado ao módulo de `i18n` — não é BCP 47. A porta da raiz é um `README.md` fora das pastas, e não tem texto além do título, dos links para as versões em cada língua, e de uma nota curta em `en_US` dirigida a agentes LLM: que leiam no idioma que serve melhor ao modelo, que na dúvida leiam em inglês, e que a trilha inglesa usa os termos e conceitos do mercado de propósito, para um nome significar a mesma coisa aqui e lá fora.

- Os documentos moram em `docs/`, **uma pasta por idioma**, e cada documento tem o par na pasta do outro idioma, com o mesmo nome. **O nome não repete o idioma que a pasta já diz**, e os nomes são minúsculos — só o `README` fica em maiúsculas, por ser o nome que o mundo já conhece.

- **Os dois idiomas mudam sempre juntos**, e o aval de um commit cobre o par. O `pt_BR` é a língua fonte; onde os dois divergirem, vale o `pt_BR`.

- Um **documento de trabalho** mora na pasta do seu idioma e **sem par**: o `docs/en_US/backlog.md` é para o agente, muda todo dia, e traduzir o que muda todo dia é trabalho que ninguém lê.

- Um **gate na suíte** afirma o que essa regra promete: a pasta de cada documento, a existência do par, a mesma estrutura de títulos nos dois, e a ortografia — os dois idiomas passam pelo corretor do repositório, e o que ele ignorar fica numa lista versionada, uma por idioma. Gramática fica com a leitura humana.

- Todo código, incluindo comentários, chaves de objetos, variáveis, métodos e nomes de arquivos serão em Inglês Estadunidense (`en_US`). No geral, os arquivos de código não têm objetivo de serem lidos por usuários finais, apenas auditados por desenvolvedores. Então é mais vantajoso manter a base em inglês para o processamento da LLM. Essa regra vale para o que é versionado no repositório; não vale para os arquivos que o AT gera na Pasta de Trabalho.

- A interface toda segue `i18n`. Nenhuma string é salva diretamente no código, seja backend ou frontend — `cli`, WebApp e Wizard. A fonte da verdade é o módulo de `i18n`, que organiza os textos em grandes blocos, evitando um `pt_BR.json` gigante que a LLM precisa ler o tempo todo. Os blocos são empacotados no binário; o que fica na Pasta de Trabalho é só o idioma ativo, em `App/i18n/active`.

- Por padrão a LLM deve gerar textos a fim de popular o `i18n` em `pt_BR` originalmente e `en_US` como tradução. Uma chave ausente no idioma ativo cai na fonte e depois nela mesma, então a lacuna fica visível em vez de silenciosa. A chave é um **id estável**, nunca a frase em inglês: renomear um texto não pode renomear uma chave. E a suíte afirma que as duas línguas carregam exatamente as mesmas chaves, para que uma tradução atrasada seja um teste falhando em vez de uma surpresa.

- Na `cli`, mensagens e ajuda saem sempre pelo `i18n`. O comando `at-cli lang pt_BR --include-subcommands` estende a tradução aos nomes dos subcomandos, o que não é comum, e por isso fica como opcional. E `at-cli lang pt_BR --include-app-folders` responde ANTES a pergunta que a troca de idioma faria: as pastas da pessoa são renomeadas na mesma corrida, sem terminal para consultar — a flag é a pessoa dizendo sim, e nada se move sem uma resposta ou uma flag digitada. A resolução do idioma é `$AT_LANG` → `App/i18n/active` → locale do sistema → `en_US`, e toda superfície reporta de onde ele veio.

### Código e delivery

- AT é escrito em Python, e a versão que ele exige mora em `pyproject.toml`, no `requires-python`. Todo seu estilo de código é baseado em `PEP 8`. Ele é entregue em **dois artefatos** — `at-cli`, que é a pasta e o app, e `at-deploy`, que é o §7 —, para Windows, Linux e Mac. Seu versionamento é SemVer, e os dois carregam esse número: é uma release só, que publica os dois arquivos — no Windows eles saem como `at-cli.exe` e `at-deploy.exe`, e no Linux e no macOS como `at-cli` e `at-deploy`. Quem usa o caminho container precisa dos dois; quem fica no hospedado precisa só do `at-cli`. **O do app é `at-cli` e não `at`**, e o item do install logo abaixo diz a razão.

- O `at-cli` carrega o **Caddy** dentro de si. O Caddy é um binário estático único, e no caminho hospedado é ele quem termina TLS e publica o AT; no caminho container ele roda como container, pelo isolamento. Não há variante de release: uma release só, que publica os dois artefatos, e o custo em disco é aceito em troca dessa simplicidade. Como o Caddy vai dentro do `at-cli`, a versão dele é a do artefato — não há pin separado para ele.

- A atualização é substituir os binários. Como o `at-deploy` carrega o manifesto das imagens fixadas, ao subir o ambiente depois da troca ele re-verifica as imagens dos serviços e re-pina o que estiver defasado — o pin anda só para frente e nunca para trás. Uma instância à frente do pin do binário **avisa e segue**: não é rebaixada. Manter tudo atualizado, e sem falha de segurança, é gestão minha, não do binário.

- **O artefato se põe onde os comandos são encontrados, e o que ele cria é um symlink.** `at-cli install` e `at-deploy install` escrevem um link com o nome do comando — `at-cli`, `at-deploy` — apontando para o artefato dentro da Pasta de Trabalho, e o completion do shell ao lado dele. Nada é buscado e nada é copiado: o binário mora na pasta, a atualização é a troca do arquivo, e o link segue — é por isso que a atualização não pede nada ao install, e é por isso que um link não é estado. A pasta padrão é `~/.local/bin` e `--bin` escolhe outra; a escolha fica registrada em `App/install.json`, para o install seguinte usá-la em vez do padrão e a pessoa não acabar com dois links respondendo pelo mesmo nome. O `uninstall` tira o link e o completion de volta, e nunca o que o AT não pôs.

- **O install roda antes de a Pasta de Trabalho ser confirmada, e não cria nenhuma.** Toda outra palavra é sobre a pasta; esta é sobre o arquivo e onde ele fica, então ela lê a pasta de onde o artefato está e liga para ele. Uma pasta que ainda não é do AT não tem onde do AT guardar o registro, e a pessoa é avisada do que isso custa em vez disso — o `App/` não nasce pela porta de trás.

- **O comando é `at-cli` porque `at` não é um nome livre.** `at` é um comando que uma máquina UNIX pode já responder — o agendador `at`/`atd`, a um pacote de distância na maioria dos sistemas e nos repositórios da distribuição em que isto foi escrito —, e o produto não toma um nome que não é só dele. A marca é AT; a palavra que a máquina responde é uma que ela não tinha. O nome do deploy sempre esteve livre, e é por isso que só o do app carrega o sufixo, e é por isso que o arquivo e o comando são a mesma palavra no Linux e no macOS.

- **O install continua DIZENDO o que encontra.** O nome acima é escolhido, não garantido: uma pasta onde já responde outro comando com o nome do link é coisa real, e o install escreve o link e diz qual pasta ganha, na ordem do `PATH`, em vez de recusar — instalar é um pedido explícito na máquina da própria pessoa, e quem decide é quem vai viver com isso (esta seção, Permissão de acesso).

- **O completion é gerado da árvore de palavras**, então uma palavra que a ajuda oferece é uma palavra que completa. No `bash` ele cai onde o `bash-completion` já procura, sem configuração nenhuma; no `zsh` ele cai na pasta de site-functions da própria pessoa, que não está no `fpath` padrão — e o AT imprime a linha que a põe lá em vez de editar um arquivo de configuração de shell que não é dele. Um shell que o AT não conhece é uma frase, e nada é escrito para ele.

- **No Windows o install ainda não existe**, e é a única plataforma onde esta regra não vale: lá um symlink não é um symlink, então "nada é copiado" seria falso. Ele espera, nomeado no backlog — do mesmo jeito que o backup espera.

- Toda atualização que mude estrutura traz a sua **migration**, e ela roda na primeira subida depois da troca do binário. A pasta sabe até onde já migrou, e esse carimbo mora em `App/` — junto do resto do que o AT escreve —, nunca dentro da declaração publicada. A declaração continua sendo dado puro, que você edita; o que os dois autores assinam fica separado.

- Uma migration **trata o próprio impacto e decide o que fazer com ele**. Nomear uma pasta move um caminho, e o que a pessoa aponta de fora — um vault de outra ferramenta, um script de cópia — é o que quebra depois, quando essa outra coisa for aberta. Por isso o que mexe nas pastas da própria pessoa pergunta antes de mover e diz o que quebra; o que mexe só na pasta do AT não pergunta, porque não há nada fora para quebrar.

- A migration **nunca sobrescreve o que já existe**: ela adiciona o que falta e reporta o que pulou. Numa colisão, quem manda é a sua edição, e o AT avisa em vez de escolher por você — a mesma escolha do pin das imagens. E uma migration publicada **não se edita**: pastas já a rodaram, e correção vira a migration seguinte.

- Os comentários no código explicam apenas o que o código não fala por si: por que aquele trecho é necessário e, quando não for óbvio, o que ele faz. Para histórico, usamos `git`. Não é necessário anotar datas de decisões. Veja, o código deve falar por si só (como o [xadrez fala por si só](https://pt.wikipedia.org/wiki/Controv%C3%A9rsia_Magnus_Carlsen%E2%80%93Hans_Niemann)). Se precisarmos de quilos de comentários, talvez ele não esteja tão bem escrito assim.

- **As pastas que a pessoa abre respondem no idioma dela, e são capitalizadas.** `Tabelas/`, `Arquivos/`, `Projetos/`, `App/`, `Compartilhada/` e `Harness/` em `pt_BR`; `Tables/`, `Files/`, `Projects/`, `App/`, `Shared/` e `Harness/` em `en_US`. O nome no disco é a **face**; a máquina lê o **nome interno** — `data`, `prose`, `projects`, `app`, `shared`, `harness` —, declarado num lugar só e resolvido por ele: nome localizado é declaração, nunca um `if` no código que age, e a declaração que uma tabela publica cita o nome interno, nunca a face. Duas pastas são a exceção, e as duas são deliberadas: `App/` não segue o idioma, porque o idioma é registrado dentro dela, e `Harness/` não segue porque o `pt_BR` tomou a palavra inteira — os dois idiomas a escrevem igual.

- **Trocar o idioma renomeia as pastas, e o rename é oferecido e nunca automático.** O AT diz toda implicação antes de fazer — primeiro o que quebra fora da pasta, porque um vault que outra ferramenta aponta é o que a pessoa não vê quebrar até depois. Quem recusa mantém o nome que tinha: o AT lê toda grafia que já deu a uma pasta, e diz o que isso custa.

- O binário mora na pasta e essa pasta é do binário. Ela é a Pasta de Trabalho. Se você abrir o binário dentro da pasta de `Downloads`, a pasta de `Downloads` é dele. No primeiro carregamento você será avisado de que: "o AT foi aberto na pasta <pasta>. Como não existe um arquivo `App/settings.json` aqui, entende-se que é uma nova Pasta de Trabalho. Confirma que o AT utilize essa pasta? Recomenda-se a utilização de uma pasta vazia, em qualquer local do seu computador. Cancele e mova o arquivo para outra pasta, se não concordar.". Ou algo do gênero.

- O backup da Pasta de Trabalho é a promessa do AT: **a pasta copiada basta para tudo voltar a funcionar**, sem troca de binário no meio. Por isso nada se regenera sozinho — nem o que foi extraído, nem o que foi baixado —, e a única exceção é o que é específico de plataforma: a pasta que muda de sistema operacional re-extrai o que não serve mais. Tudo o que o AT escreve mora em `App/`, numa pasta visível justamente para que ninguém a confunda com lixo: ajustes, idioma ativo, contadores, carimbo de migração, o estado dos plugins, o que foi extraído para rodar, cache e o estado dos serviços.

- O AT **não tem watchdog e não se propõe a ter**. Ele está ciente de que tudo pode ser modificado por fora, e se a pessoa sabe modificar, que modifique: o que ele faz é medir o que encontra e dizer o que isso custa, nunca policiar a pasta.

- Sem terminal para perguntar não há primeira execução: o AT encerra com código `1` em vez de assumir uma pasta. E recusar não cria nada — o AT diz onde mover o binário e sai sem erro, porque recusar não é erro.

### Permissão de acesso

- O AT, por padrão, é arquitetado para ser executado sem permissões de administração (i.e. não usa `root` ou `Administrador`). Contudo, montar o ambiente do §7 inevitavelmente exige elevação em algum momento. Nesses casos a elevação de privilégio acontecerá por um pedido explícito, com a razão à mostra.

- A lista fechada do que exige elevação não se escreve antes da função: ela nasce com a implementação que a pede. Cada item que entrar nela é uma decisão de segurança e passa por esta seção.

- **A lista, até agora: a regra de porta baixa, e só ela — e quem pergunta é o `at-deploy`.** O `dnsmasq` da §7a publica DNS em `53` — no laço, ou no endereço da rede privada quando há uma (§7e) —, e uma máquina que carrega o `net.ipv4.ip_unprivileged_port_start` do kernel — todo Linux carrega — recusa essa ligação a um processo comum. O `at-deploy` pergunta, com a razão e o comando exato à mostra, e o que ele pede é o MAIS ESTREITO que funciona: o piso se move para a porta mais baixa que o ambiente publica, nunca para zero. Vale até o próximo boot, e o próximo boot pergunta de novo — um pedido explícito feito outra vez, não uma permissão lembrada pelas costas da pessoa.

- **A CA nos cofres do navegador não entra nesta lista, e isso é uma decisão medida.** `at-deploy ca install` escreve nos bancos NSS da PRÓPRIA pessoa — os perfis do Firefox (`cert9.db` em cada um) e o `~/.pki/nssdb` do Chromium —, e por isso é ato de usuário, sem elevação nenhuma. O cofre DO SISTEMA fica de fora por escolha e não por esquecimento: ele seria a segunda entrada desta lista, e não compraria a promessa da palavra, porque o Firefox não o lê — o NSS dele é por perfil — e o Chromium da máquina onde isto foi escrito usa o `~/.pki/nssdb`. Esta seção pede o MAIS ESTREITO que funciona, e o mais estreito aqui é não pedir nada. O que a palavra não faz sozinha é instalar o `certutil`: onde ele não existe, ela diz as duas saídas — o pacote que a PESSOA instala, ou a importação à mão no navegador — e não instala nada, como o Podman — [Criar ambiente container](container.md#a-criar-ambiente-container-obrigatório).

- **O `at-cli` não consegue perguntar, e isso se lê do artefato.** O ambiente do §7 saiu do `at-cli` inteiro e virou o `at-deploy` (item 27): a elevação MUDOU com ele e não se duplica, então o que esta seção promete sobre rodar sem permissão de administração é propriedade do que o arquivo É e não de como ele se comporta. Os dois artefatos dividem o ESTADO da pasta e não uma API, e a ferramenta de deploy é a que o escreve.

### Portabilidade

- O dado é sempre POSIX. `LF` ou `/`. Conversões para Windows apenas para exibição (como na mensagem de boas-vindas da Pasta de Trabalho, acima) ou para as `syscalls`.

### Dependência externa

- Dependência a pacotes e imagens são fixadas em versão e hashing — seja de pacotes, seja de imagens externas.

- O Caddy é a exceção declarada, e não por descuido: ele vai embarcado no binário, então quem o pina é o próprio binário, com o SemVer do AT.

- **O que pode viajar dentro do artefato é uma questão de licença, e a licença viaja junto.** Um terceiro só entra no binário se a licença dele permitir, e o que ela exigir vem com ele — o aviso de `copyright` e o texto. Como o artefato é UM arquivo e não uma pasta, o aviso não fica ao lado: fica dentro, e sai pela palavra `license` de cada artefato (`at-cli license`, `at-deploy license`), que diz o que AQUELE artefato carrega e nunca o que o outro carrega. A licença do produto é a `MIT` (`LICENSE.md`), e é ela que permite embarcar assim; um terceiro cuja licença não o permita fica de fora, e a decisão de embarcar é tomada com o preço em disco dito.

- **A declaração é uma só, e cada texto é o arquivo do próprio fornecedor.** `at/vendor/licenses/manifest.json` diz, por componente, o nome, a versão, o identificador `SPDX`, quais artefatos o carregam e onde o texto mora; nada é declarado à mão em dois lugares, e é dela que o `SBOM` (item 46) gera as linhas de licença. O que viaja é o arquivo do fornecedor, nunca uma paráfrase — o `LICENSE` de dentro do tarball do Caddy é o mesmo que o projeto guarda ao lado —, e o release promete esses avisos: uma build que perca qualquer um deles é recusada.

- **A máquina onde o release é construído também é dependência, e é pinada como uma.** Um binário congelado carrega a máquina que o construiu: as extensões do interpretador viajam com o artefato, e cada uma guarda a versão da biblioteca contra a qual foi ligada — então o piso de glibc do release é propriedade de ONDE ele foi construído, e não do código. O release declara esse piso, é construído na base que a declaração pina, e é recusado quando o artefato precisa de mais do que prometeu.

- **Nada experimental entra**, nem como ferramenta de desenvolvimento: só componente estável. Versão alpha, beta, release candidate e preview ficam de fora, e o que o fornecedor marca como experimental fica de fora junto — a promessa de que o AT não muda sob os seus pés não pode depender de uma superfície que o dono dela avisa que vai mudar.

