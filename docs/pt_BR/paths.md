# 6. Os dois caminhos de uso [normativo]

- Existem dois caminhos, e os dois são suportados. Eles diferem no que garantem, e a diferença é declarada aqui para que ninguém decida com informação errada.

### Caminho hospedado

- É o AT e a pasta. O binário é aberto na Pasta de Trabalho, o WebApp sobe pelo comando, o Wizard abre quando não há parâmetro, e a `cli` faz o resto. Não há container nenhum, e a pessoa não precisa de Podman nem de nada além do binário.

- **Não há isolamento**, e o AT não promete nenhum neste caminho: um comprometimento do WebApp é um comprometimento de processo na sua máquina, com acesso ao que o seu usuário tem. Em troca, sair do laço local exige autenticação e TLS, e os dois vêm por padrão.

- `at-cli webapp` sai do laço local por padrão: o Caddy que veio dentro do binário termina o TLS e publica o AT, na frente do Authelia e do ntfy, do mesmo fornecedor e do mesmo jeito — o portão próprio deste caminho. `--no-caddy` é a única saída disso: com a bandeira, o WebApp serve em HTTP e só em `127.0.0.1` — e ele recusa que lhe peçam qualquer outro endereço, porque expor sem TLS é o que a regra acima proíbe. Sem `--no-caddy`, o `--host` nomeia o endereço em que o AT atende, e precisa ser um nome para o qual um certificado se emite: `0.0.0.0` é todos os endereços, e certificado não tem nenhum.

- As integrações (§7) podem existir sem container: quem instala o serviço por conta e aponta o AT para ele usa o serviço, com a ciência de que o estado daquele serviço não é mais assunto do AT — e, portanto, que o backup da pasta não o cobre. A aprovação de uma demanda arriscada, aqui, acontece na própria máquina: o serviço `notifier` é do caminho container.

- Expor o AT pelo caminho hospedado com o Authelia do caminho container é o **modo avançado**, e não é suportado: quem quiser o portão, usa o caminho container.

### Caminho container

- É o **`at-deploy`** montando um ambiente de serviços em containers de imagens fixadas (§7). Aqui existe isolamento, e ele existe por um motivo específico: **conter o raio de explosão de cada serviço**. O comprometimento do `ntfy` alcança a notificação e nada mais; o do corretor alcança o corretor. O que cada serviço expõe é o que ele se propõe a fazer, e nada além.

- Serviço que precisa falar com o AT — e não o AT com ele — tem o escopo delimitado: credencial com papel declarado, e só o que aquele papel permite. Mínimo privilégio, aplicado. No `ntfy`, isso é a ACL por tópico: a única conta que o AT guarda publica e lê, e não alcança nenhum outro tópico. Quem alcança de fora nem chega a isso sozinho: o notificador fica atrás do mesmo Authelia do site — no mesmo nome, numa porta diferente —, provado por Basic na própria requisição, e depois da pergunta é a borda quem carrega a credencial do AT — nunca a da pessoa.

- O caminho container é o que sustenta o portão de autenticação (§7b), e é onde o AT entra como mais um app atrás dele.

- **Quem monta o ambiente é um segundo artefato, e quem serve a pasta continua sendo o `at-cli`.** O `at-deploy` é uma `cli` e um Wizard, como o `at-cli`, e aqui o Wizard é a frente natural: montar é uma SEQUÊNCIA e não uma frase, e ele leva a pessoa passo a passo — checa os requisitos, sobe um serviço, segue para o próximo. Cada passo que ele dá é um que a `cli` dá sozinha, porque a regra de mão única do §5 não se dobra para um segundo artefato. Os dois arquivos são necessários neste caminho, e o `at-cli` serve a pasta com a ferramenta de deploy ausente: é ele que lê o `authenticator` e o segredo do portão, recusa o Forms e fecha quando o portão cai.

### A virada entre os caminhos

- A passagem de um caminho para o outro é uma **virada**, e virada é transacional: o `at-deploy` executa o conjunto de ações e, se alguma não termina com sucesso, volta tudo ao estado anterior. O ambiente não fica pela metade, e o que havia antes continua funcionando.

- No sentido do container, o Forms continua ligado até o Authelia estar **provado** funcionando na frente do AT — não é "o container subiu", é o AT recebendo a identidade que espera, pelo caminho real, com o segredo do portão. Só então o Forms se desliga.

- Se o portão cai depois, já com a virada commitada, o AT **fecha** e avisa: "Portal de autenticação indisponível. Utilize o Wizard para retornar o AT para modo forms." Ele não reabre o Forms sozinho — reabrir sozinho seria trocar a segurança por conveniência, sem ninguém decidir.

- Se o `at-deploy` encontra um ambiente de infraestrutura configurado na pasta mas não encontra o ambiente, ele pergunta: "Foi detectado que você tem um ambiente de infraestrutura configurado nesse ambiente, mas o ambiente de infraestrutura não foi encontrado. Você deseja instalar novamente o Podman/Docker ou restaurar o AT para modo hospedado na máquina?". É a promessa do backup aparecendo na tela: a pasta voltou, e o que faltava era só o chão.
