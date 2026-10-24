# 4. Arquitetura [normativo]

### Separação de camadas

- O AT é estruturado em camadas. O `core` trata todas as regras da aplicação. Não é um bloco monolítico: é quebrado em módulos e arquivos conforme o assunto. Mas tudo passa por ele. Nenhuma camada fora do `core` resolve um caminho por conta própria.

- A `ui` é uma forma de camada, mas tem mais. O AT já nasce com três superfícies: `cli`, WebApp e Wizard. Todas só são formas diferentes de interagir com o `core`. Nem tudo feito pelo `cli` está disponível no WebApp. Mas tudo no `WebApp + Wizard` está disponível no cli.

- Outra camada muito importante é `data`. Essa camada fica responsável por acessar as tabelas. Dados estruturados salvos em `.jsonl` dentro da pasta `./data`. A pasta `./data` é criada automaticamente na primeira execução, com as tabelas de sistema vigentes.

- O AT também suporta gerenciar arquivos diversos. É a camada `prose`. Qualquer arquivo que não for estruturado fica a cargo dessa camada. A pasta `./prose`, também criada na primeira execução, vem com um arquivo de boas-vindas gerado pelo `i18n` no idioma ativo escolhido na primeira execução (`Bem-vindo.md` em `pt_BR`, `Welcome.md` em `en_US`), para facilitar os próximos passos.

- Os serviços externos são tratados pela camada `services`. Aqui é para que a camada seja o máximo agnóstica a ferramenta possível: o **serviço** tem nome canônico e a **ferramenta** que o cumpre é trocável. É nesta camada que mora a parte de serviços do produto — cada serviço configurado mora aqui, com o seu estado na pasta.

- Os segredos são gerenciados pela camada `encryption`.

- A interpretação de linguagem natural é a camada `nlu`: ela transforma uma frase em uma **proposta** de ação, e nada mais. Ela não escreve, não decide e não tem teto próprio — quem valida e escreve é o `core`.

- A postura de segurança é a camada `posture`: ela mede o que está configurado, soma as notas por função pelo elo mais fraco e responde à tela e à API. Ela mede; não impede.

### Tabelas

- O AT possui um motor próprio de gestão de dados estruturados. Aqui é usado o termo Tabela, ou `table` internamente. A identidade da tabela é um id, e o id é singular (`task`, `project`, `note`, `reminder`, `secret`, `actor`, `role`, `audit`, `job`): é ele que nomeia a tabela em todo lugar, inclusive no comando (`at-cli task list`) e no esquema. O arquivo de linhas é que vai no plural. Logo `data/tasks.jsonl` é a tabela em si e `data/schema/task.json` o esquema dela.

- As tabelas `task`, `project`, `note`, `reminder`, `secret`, `actor`, `role`, `audit` e `job` são padrão do sistema. Servem para entregar uma funcionalidade inerente. Tabelas de sistema não são deletáveis, e **a deletabilidade de uma linha é declarada no esquema da tabela**: o `audit` declara que nenhuma linha sua se apaga.

- A tabela `job` guarda a **demanda que não pôde correr**, e o ato que o **relógio** conduz: o ato que ela vai cumprir, os argumentos de que ele precisa, o ator que a possui, o instante de que ela trata e o estado da vida dela — `waiting`, `approved`, `refused`, `done` e `scheduled`. O que espera é um **job, e não uma fila**: a demanda que chega no limiar vira uma linha dessa tabela, no estado que diz que espera, e a resposta nomeia qual. Quem espera é **presença, e não tipo**: o ato que a pessoa digita ou clica nunca espera, porque o ato É a aprovação, e o que roda sozinho espera no limiar — é por isso que a demanda do `agente` espera e a da pessoa não. O job corre com a via `engine` e com o ator que o possui, então o teto dele é o daquele ator. A aprovação é uma **linha própria na auditoria**, com o ator e a via por onde ela veio, separada do job que esperou — e nenhum ator de máquina carrega `job:approve` nem `job:refuse`, pelo mesmo motivo que o §3 dá para `audit:read`.

- **O `when` é o instante de que o job trata, e o que ele diz depende de quem o conduz.** A demanda que esperou carrega o instante em que **chegou** e espera por uma pessoa; o job que o **relógio** conduz carrega o **próximo instante em que deve rodar**, e `scheduled` é o estado que diz isso — o quinto, e o único em que um job que se repete descansa. O relógio **lê** o `when` e o **reescreve**: depois de cada rodada o instante avança pela cadência, que é uma só para a pasta e tem o **minuto** por granularidade — a declaração de um job diz QUANDO ele começa, e o ritmo depois disso é do relógio, então o que precisa de intervalo próprio lê o seu, como a escrita do versionamento faz. **O relógio mora no processo do WebApp enquanto ele está de pé**, e mora lá porque hoje quem gerencia um job é o WebApp: ele sai quando o motor sair. A rodada corre com a via `engine` e com o ator dono do job, enfrenta o limiar — o que roda sozinho espera —, e a rodada que termina esperando aprovação **espera como job**: a mesma linha, o mesmo estado, sem um segundo modelo, nem fila nem trava. A rodada que passou com o AT fora **roda na subida seguinte, uma vez só** — o próximo instante é medido da rodada que aconteceu e não do compromisso perdido —, e deixa a linha dela dizendo que foi recuperada.

- Tabelas de usuário permitem CRUD completa da própria tabela.

- O schema de tabela tem muitas funcionalidades, como campos padrão na exibição e ordem padrão na exibição de tabelas. Os rótulos de exibição que ele carrega são chaves de `i18n`, nunca o texto final. O contador de ids não mora no esquema: ele conta o que aconteceu nesta pasta, e o esquema é publicado — então ele vive em `App/counters.json`, e é escrito antes da linha, porque um id entregue está gasto mesmo se a escrita seguinte falhou.

- O esquema declara **tipos de campo**, e cada tipo tem regra fixa, sem escolha por campo:
  - **hasheado** — guarda o resultado de uma derivação segura, feita com `libsodium`; o valor não volta na leitura, só se confere.
  - **selado** — carrega um valor que o AT **usa**, selado com a chave do próprio serviço ou propósito; ele não volta na leitura, e quem o abre é a chave, não o motor.
  - **instante** — um ponto no tempo: ISO, sempre UTC, sempre com milissegundos (`2026-09-22T13:04:07.123Z`). A localidade é detectada na exibição, nunca guardada.
  - **dia** — um dia do calendário, sem hora e sem fuso, resolvido pela localidade de quem escreve. "Hoje" é o seu hoje.
  - Os tipos comuns — texto, número, data, referência, enumeração — como sempre foram.

- **O que se prova se guarda hasheado; o que o AT usa se guarda criptografado.** A `secret` é da segunda espécie, o `actor` é da primeira.

- **Quem age é um ator**, e todo ator é uma linha da tabela `actor`, com o campo `tipo` valendo `pessoa`, `motor` ou `agente`. A linha carrega a identidade, o papel e a credencial no campo hasheado. O motor age no que é do motor; o `agente` é quem usa o AT sem ser pessoa, e é ele que tem teto próprio — quem digita uma frase é a pessoa, e a via é `nlu`.

- O catálogo de permissões é declarado no código, e não é dado solto: a permissão tem a forma `objeto:ação`, os objetos e as ações são uma lista fechada, e os rótulos de exibição saem do `i18n` como todo o resto. Os objetos vão além das tabelas: as configurações, os serviços, os plugins e o vocabulário do interpretador também são objetos, com permissões próprias. Um papel é uma linha da tabela `role` com um conjunto de permissões, e a tabela `actor` aponta para o papel. Papel que nomeia permissão inexistente não derruba o AT: ele avisa, e o aviso é o que se lê.

### O Cofre

- **O Cofre é onde vive tudo o que o AT fecha.** Para executar certas ações, como acessar APIs de serviços externos, o AT precisa ter acesso a segredos. Todo segredo que o AT **guarda** é escrito na tabela `secret` (`data/secrets.jsonl`) — segredo que só se confere, como a credencial de um ator, mora hasheado na própria linha e não no Cofre (§4, Tabelas: **o que se prova se guarda hasheado, o que o AT usa se guarda no Cofre, criptografado**). Lá estão metadados e o segredo em si, salvo de forma criptografada.

- A criptografia do AT parte de uma **Chave Principal**, que é o que a pessoa sabe e digita: no mínimo 16 caracteres, e é uma frase. "Mariazinha comeu todo o pudim", em minúsculas e sem espaços, é mais seguro que `Mariazinha@123`. Dela derivam as **chaves derivadas**, uma por serviço ou finalidade. A Chave Principal recupera qualquer chave derivada perdida.

- **Não existe um segundo sistema de criptografia no AT.** Toda cifra do produto — o Cofre, o portão, o que cada serviço assina ou cifra para si — passa por esta mesma porta única: a Chave Principal e o que dela se deriva. Um caminho que cifrasse por fora dela, ou que guardasse uma chave pronta em vez de derivá-la da frase quando falta, seria uma criptografia própria que o AT não tem — mesmo chamada de outro nome, mesmo existindo só num dos caminhos de subida.

- O escopo de uma chave derivada é um **nome** — o nome canônico de um serviço, ou uma finalidade escrita como um —, e o Cofre não guarda catálogo de nomes: os serviços são do §7 e dos plugins, e uma lista aqui seria o Cofre nomeando um mundo que não é dele. O que ele recusa é escopo que não é nome, e o que ele sustenta é que dois nomes que diferem numa letra são duas chaves.

- É recomendado guardar a Chave Principal fora da máquina, em um local seguro. Imprimir e armazenar em documentos pessoais de difícil acesso, por exemplo.

- Em criptografia, não existe mágica. Ou você digita a Chave Principal toda vez que o AT precisa de um segredo, ou digita uma vez e ela vale enquanto o AT estiver de pé, ou o AT guarda o que precisa para destravar sozinho. **A escolha é graduada, e a nota de segurança diz o preço de cada uma:** digitar quando o AT sobe é `S`; guardar destravado na pasta do usuário do sistema (`~/.at/` no Unix, `%APPDATA%` no Windows) é `A`; guardar dentro da Pasta de Trabalho é `B` — e a última é permitida, porque aí o backup da pasta leva tudo.

- O AT roda sozinho quando precisa: job agendado não pede senha a cada execução, e a definição e o estado dele moram na tabela `job` (§4, Tabelas). O que ele não faz é escolher por você onde a chave mora.

- A Chave Principal é a credencial do primeiro admin: a mesma string prova quem entra e destrava o Cofre. O que se confere é a derivação — o hash dela, guardado na linha do ator —, e não a chave: por isso entrar não exige destravar o Cofre, e é por isso que o que se prova mora hasheado na linha e não na `secret`.

### Configurações gerais

- As configurações do AT moram dentro de `App/settings.json`, dentro da pasta de trabalho. Aí moram propriedades em formato chave-valor. `i18n` não mora aqui: os blocos de tradução são empacotados no binário e o idioma ativo mora em `App/i18n/active`.

- **As configurações são alcançáveis pela API do core** (`setting:read` e `setting:edit` são permissões), porque é por ali que passa tudo o que age — inclusive a leitura do **limiar de risco** que valia no instante em que uma demanda correu, que é o que a linha da auditoria registra. A porta é uma só: `list` e `view` são a leitura e `edit` é a escrita, a `cli` a alcança por `setting list|view|edit` (§5: a `cli` alcança tudo), e o que o AT escreve para si — a versão da forma — a porta recusa.

- Nenhum segredo mora no `settings.json`. Ele guarda permissão e ajuste — como a permissão de um ator entrar por Basic, ou o limiar de risco —, nunca a credencial em si.

- O Wizard Tkinter exibe as possibilidades de instalação do ambiente. No modo avançado habilitado, o Wizard apresenta a renderização do arquivo de configurações, permitindo modificar quaisquer uma. Segue a escolha de designer de algumas ferramentas, como VS Code, que possuem a base das configurações em JSON, mas permitem a alteração na UI.

- Cada serviço pode ter dados persistidos. Nesse caso, eles moram em `App/services/<serviço>`, como `App/services/vpn` ou `App/services/spelling-checker`. O nome do serviço é canônico e não muda com a ferramenta que o cumpre: `spelling-checker` é o serviço, LanguageTool é quem o cumpre hoje (§7d) — como um processo que o próprio AT sobe e desce, e não como container —, e o que um dia o substituir não renomeia pastas nem chaves. O que é rótulo de exibição é chave de `i18n`.

- Essa pasta não é conveniência, é condição de entrada: um serviço só entra no §7 se o estado persistente dele couber aí dentro. Serviço que guarda a vida dele em algum volume que ninguém copia deixa o backup da pasta mentir.

- **A pasta nasce sob versionamento, e o histórico é o do AT.** Na primeira execução o AT faz o `git init` na raiz da Pasta de Trabalho, escreve o `.gitignore` que ele mesmo gera e toma a primeira versão; daí em diante, toda ação que muda a pasta é versionada por ele, com uma versão nomeada pela frase do motor — é por isso que o `git log` se lê como a história da própria tabela. **O AT versiona onde o repositório é dele**: a pasta que já carrega um repositório próprio não é sobrescrita nem conduzida. **Versionar não é fazer backup** — a cópia que sobrevive à máquina é outra coisa, ainda devida.

- **A cadência do versionamento é uma configuração.** `versioning_interval` diz quantos minutos a pasta pode passar sem ganhar uma versão enquanto o AT é usado; `0` é a pessoa pedindo uma versão a cada escrita, e a pasta que nunca escolheu é periódica. O número é lido uma vez pelo `core`, e é a mesma leitura que governa as duas pontas: a escrita só versiona quando o intervalo passou — e o que esperou não se perde, porque a versão seguinte carrega a pasta inteira —, e a pasta que ficou para trás diz isso na `cli` e na página, no idioma ativo.

