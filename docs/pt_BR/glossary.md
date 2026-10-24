# Glossário [normativo]

Cada nome tem um só significado, e nomes que se encostariam não convivem. Sempre que eu inventar um termo, ele é definido aqui antes de ser usado.

| termo | o que é |
|---|---|
| **produto** | o conjunto publicado: este repositório, os binários que ele gera e as declarações que viajam dentro |
| **binário** | cada arquivo que o produto publica: `at-cli`, que é a pasta e o app, e `at-deploy`, que é o §7 — o arquivo do app é `at-cli` no Linux e no macOS e `at-cli.exe` no Windows, e o do deploy é `at-deploy` e `at-deploy.exe`. No Linux e no macOS o nome do arquivo É o comando, e é `at-cli` e não `at` porque a máquina pode já responder por esse |
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
| **plugin** / **extensão** | o que ensina algo ao AT ou acrescenta uma tela a ele; dado puro ou frontend em iframe sandbox, sempre com manifesto e hash |
| **review** | a aceitação de um plugin, amarrada à hash, em um de três modos |
| **Chave Principal** | o que a pessoa sabe e digita — no mínimo 16 caracteres, e é uma frase; é a mesma string que prova o primeiro admin e destrava o Cofre, e dela derivam as **chaves derivadas**, por serviço |
| **manifesto** | a semente deste repositório, visível no histórico do git; e `manifest.json` é só o arquivo que tem esse nome |
| **pin**, **migration**, **migration framework** | ficam em inglês, como o resto do código: fixação de versão e hashing; a mudança de estrutura que roda na primeira subida; e o conjunto delas — a máquina de migração —, o carimbo, a ordem e a regra de que uma publicada não se edita |
