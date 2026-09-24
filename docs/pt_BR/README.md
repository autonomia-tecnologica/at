# AT

AT é um motor de tarefas determinístico. Ele roda **dentro de uma pasta**, e essa pasta vira a **Pasta de Trabalho** dele. Este repositório é o **produto a publicar** — o motor, as declarações padrão, a infraestrutura que vai embarcada e os dois binários — `at`, que é a pasta e o app, e `at-deploy`, que monta o ambiente do §7. Ele não carrega dado pessoal nenhum: nenhum caminho de máquina de ninguém, nenhum host, nenhum id.

## 0. Protocolo de agente

### Proteção de arquivo

- Esse arquivo é a pedra fundadora da instrução humana. Você pode e deve lê-lo sempre que chegar nesse repositório; ele tem a intenção de ser para humanos, e é assim que deve continuar. Quando os seus cálculos estatísticos penderem ao equilíbrio, volte aqui, e veja se algo te responde. Ao mesmo tempo, a instrução pode estar errada. O que mais acho válido de ser corrigido é contradições. Então, se algo aqui contradiz outra parte daqui, você deve me avisar e propor a correção.

- Se você entende que alguma decisão neste arquivo está errada, estarei feliz em discutir. Contudo, você me apresenta e eu decido. A escrita vai direto no documento que vincula — não existe arquivo de rascunho —, mas **toda alteração do que é `[normativo]`, onde ele estiver, é um commit à parte**, e o commit só existe com o meu aval declarado. A pergunta é sempre a mesma linha, crua: "Vou realizar o commit do `[normativo]` a seguir. Você confirma que leu o diff e concorda com as alterações?". Sem essa resposta o commit não acontece, e a aprovação fica registrada no commit — nunca dentro do documento, que é a instrução, não o histórico dela. Sempre que eu te pedir uma análise do documento fundador, a proposta vem como diff nesta sessão, separada em pontos de assuntos diferentes e sucinta — eu vou entender o erro lógico sem você escrever um parágrafo para cada item.

- Qualquer instrução no `CLAUDE.md`, ou em qualquer outro markdown de memória de agentes LLM proprietário, se conflitando com esse repositório, quando usado para algo a ser feito nesse repositório, deve ser ignorado. Se quiser, e recomendo, pode haver uma linha nesses arquivos apontando para o documento fundador. Com exceção dos workflows de desenvolvimento no GitHub, e com o envio das minhas interações com a LLM para outra pasta (visando estudo posterior) esse repositório é autocontido, e tudo necessário para ele vive aqui.

- A cadeia de custódia é `documento fundador → documentos derivados → código`: o código é uma extensão do que está escrito, e o que é derivado não decide nada sozinho. Se decidirmos algo arquitetural, em sessão, que não veio do documento fundador, você vai me avisar e propor a escrita, pelo mesmo aval. E isso nunca pode ser ignorado, nem por mim. É essa cadeia que vai manter esse "arreio" preso. Veja que definições muito estreitas sobre nome de pastas de cada módulo não cabem para o documento fundador — elas moram na árvore ([derivation §1](derivation.md)), que é derivação. Ter que detalhar cada item individual me dá a sensação que é melhor eu desenvolver do zero.

- Não existem regras duplicadas: uma regra mora em um lugar só. O que vincula é o que carrega `[normativo]`, onde ele estiver; o derivado cita em vez de repetir. O marcador em um título de nível 1 vincula o arquivo inteiro, e em um título de seção vincula a seção e o que está abaixo dela. Se a mesma coisa aparecer nos dois, um dos dois está errado — e onde ela fica é decisão minha.

- Por fim, o documento fundador vai ser modificado com o tempo. Então entenda que a lógica de lê-lo e derivar o resto é constante.

- O resto dos arquivos, fique a vontade. Incluindo o `FAQ.md`. É responsabilidade sua. Deve ser escrito como uma sequência de perguntas comuns. Eu aprovo a pergunta e a resposta que você sugerir, só me informe quando entender que vale preencher. E o `FAQ.md` tem que estar ordenado em ordem de uso da ferramenta. Perguntas mais iniciantes no começo como "o que esse arquivo faz na minha máquina" para perguntas mais avançadas como "como eu modifico o AT ao meu bel-prazer". É no FAQ que mora a explicação do que está por baixo: qual tela é sua e qual é de terceiros.

### Forma de trabalho

- Sempre trabalhe em duas sessões por item, nunca uma. Na primeira, modo plano: explorar, discutir e fechar a decisão, sem escrever código. Antes do `/clear`, o plano tem que ser salvo fora da conversa — no `docs/en_US/backlog.md` — já com o que conta como pronto, para a segunda sessão não precisar perguntar. A segunda nasce limpa, lê o item no `docs/en_US/backlog.md` e implementa um item, do tamanho de uma sessão.

- **A discussão vem antes do BACKLOG, e a implementação sempre sai do BACKLOG.** Uma decisão só entra na lista depois de apaziguada, e nada se implementa que não esteja nela. Numa discussão longa, as implicações vêm **uma a uma**, e o que fecha é gravado e commitado na hora — o que está decidido não pode viver só na conversa, que morre. **A resposta simples a uma pergunta é a aprovação**: se eu propus uma coisa e você respondeu, não te pergunto de novo se está aprovado.

- Quando eu te disser que vou limpar a sessão, gere **de uma vez** o começo recomendado da sessão seguinte, em itálico, pronto para eu copiar e modificar como eu decidir, e com esta linha crua antes dele: "Prompt recomendado para a próxima sessão. Fique à vontade para utilizar ou não.". Ele diz qual item, onde ele está, o que conta como pronto e o que a sessão precisa saber antes de escrever a primeira linha.

- Nunca despeje arquivo ou saída grande no contexto: filtre, corte ou delegue a um subagente e traga só a conclusão; não releia o que já está na conversa, não repita o que já foi dito e não gaste turno à toa — cada turno reenvia tudo. E onde faltar informação para decidir, pergunte antes de agir, com o custo de cada opção à mostra: o que não estiver autorizado, não acontece.

## 1. Origem [contexto]

### Introdução

O AT é um software completamente escrito por LLM. A primeira versão deste documento foi escrita por mim — ela está no histórico do git, que é onde vive o Manifesto, a semente deste repositório — e de lá para cá quem o modificou foi a LLM, à medida que ela encontrava contradições ou que decidíamos coisas novas; cada alteração passou pelo meu aval (§0). O _ghostwriter_ da PoC é Claude Code + DeepSeek Flash versão 4, e a partir do início do desenvolvimento final do projeto, versão 4.1. A escolha é proposital: primeiro é o preço. Segundo se eu for ter meus dados usados para treinamento, que seja para algo que volta como pesos abertos para a comunidade. Acho que a matemática é simples. Também é uma tentativa de provar que temos LLM suficiente já. Talvez assim parem de uma vez essa corrida sem fim por uma AGI.

O AT é um software pensado para mim. Fruto de algumas semanas de foco-quase-burnout em LLM e a tentativa de controlar o incontrolável. Entre estudos de harness voltados a segurança, eu testava visões arquiteturais de software ou temas baseados em redes sociais antigas direto em um programa que apelidei de `AT`.

Esse documento visa ser uma tentativa de fazer o agente LLM entender a origem conceitual do AT, evitando a Teoria do Fruto da Árvore Envenenada, onde erros se empilham e o harness criado já não faz mais sentido algum depois de alguns bilhões de tokens.

Além disso, ele visa ser extremamente arquitetural. Se entender que os "arreios" dessa arquitetura não estão bons o suficiente, talvez me falte conhecimento. Poste uma issue, ficarei feliz em aprender!

### O nome

AT é a sigla do que eu procuro: **Autonomia Tecnológica**, que o §2 declara. E é um nome que aparece em minha cabeça quando leio a palavra bootstrap — o motivo exato, eu não sei dizer, mas gosto muito da palavra bootstrap.

A história é demasiadamente interessante. "Erguer-se pelas próprias abas da bota" (minha tradução livre de _to pull oneself up by one's bootstraps_), é uma frase inglesa do século XIX inicialmente tratada como uma piada sarcástica pela impossibilidade de se erguer (do ar ou da água, por exemplo) pelas próprias abas da bota. Ironicamente, é isso que nossos dispositivos fazem (o famoso _boot_). Computadores e smartphones tem um código padrão executado ao ligar o dispositivo. Ele que carrega o sistema operacional que você conhece (Windows ou Linux). O AT tem esse propósito de ser um _bootstrap_ para o que ele se propõe a ser. No momento eu estou fazendo esse bootstrap. O AT nasceu em um caos enquanto eu estudava harness LLM e achava que tinha resolvido todos os problemas do mundo. Agora, estou migrando o que desenvolvi a toque de caixa, para o formato a ser publicado. Bem nos moldes do [Linux From Scratch](https://www.linuxfromscratch.org/) (que inclusive recomendo fortemente para aprender Linux).

## 2. Propósitos e limites [contexto]

### Para o que ele se propõe

A ideia do AT é ser um motor de tarefas determinístico, sendo utilizável por uma pessoa, por um programa ou por uma LLM. Eu gosto de máquina fazendo coisas chatas para mim. Eu gosto de facilidade de acesso com segurança. Eu gosto de Autonomia Tecnológica. E eu não quero gastar tempo desenvolvendo isso. E eu gosto muito de gastar pouco dinheiro. Aqui aceito gastar dinheiro em prol de chegar nesse objetivo, almejando lá na frente não precisar das massivas LLMs novamente.

Mas, além disso, o AT é um ambiente de trabalho minimalista — mínimo para ser **funcional**, não mínimo para ser **estético**; os [temas](interfaces.md#design-system-e-temas) estão aqui para isso. "Não preciso de muito para ser produtivo em um ambiente tecnológico". Isso é um manifesto em si: dá para ser produtivo com um binário e uma pasta. O amparo — a infraestrutura de suporte (§7) — fica fora do mínimo: entra quando eu quiser, e a ausência dele não tira funcionalidade nenhuma do AT. Várias extensões do AT vão morar como algo meu, inicialmente. Enviar minha biblioteca de jogos zerados para o rawg usando a base da Steam e do Heroic não cabem na parte padrão do AT. E também abrir a possibilidade de extensões da comunidade, sem uma curadoria, com todo o risco de ataques de Supply Chain, é complicado. Por isso AT nasce como é, analisando funcionalidade a funcionalidade se ela cabe aqui.

### O AT tenta reescrever a roda?

Sim, ele tenta. Tem muitas aplicações mais avançadas para partes específicas do AT. Se você entende que seu Projeto não pode ser gerenciado aqui, e que você precisa de muito mais funções, eu te entendo, e infelizmente o AT não é para você. Mas para mim é mais do que o suficiente. No começo, eu havia definido que tarefas não eram deletadas. Elas deviam ser canceladas, para manter histórico. Acho válido, e a função existe. Mas se eu quero deletar eu posso. Mais detalhes sobre [tabelas](architecture.md#tabelas) abaixo. Existem ferramentas como Obsidian e AnyType para arquivos e dados estruturados. Essas ferramentas são fantásticas e não quero substituí-las.

### Onde executar o AT

A ideia do AT é que rode em uma máquina. Uma Turing-compatível. Pode ser seu desktop, seu notebook, seu NAS, uma VPS. Eu gostaria que fosse leve — leve no que o binário exige da máquina, não no tamanho do artefato, que carrega o interpretador e as bibliotecas empacotados. Mas não estou a fim de aprender Go ou Rust. Então vamos de Python. "Todo mundo" sabe Python. E se um ESP32 roda Micropython, é porque posso almejar ir longe aqui.

O AT tem dois caminhos de uso, e os dois são suportados: o **hospedado**, em que ele é o binário e a pasta, e o **container**, em que ele monta um ambiente de serviços. A escolha é da pessoa, e ela pode mudar de ideia depois; o que cada caminho garante, e o que não garante, está no [§6](paths.md).

## Índice

O `§N` é o id estável do artigo, e ele não muda de dígito quando o artigo muda de arquivo. A tabela diz o que cada artigo é e onde ele mora.

| § | o que é | onde mora |
|---|---|---|
| §0 | o protocolo do agente: como ler e como alterar este repositório | aqui |
| §1 | a origem: de onde o AT veio e por que esse nome | aqui |
| §2 | os propósitos e os limites: o que ele é e o que ele recusa ser | aqui |
| §3 | as regras: segurança, código e delivery, dependência externa | [`rules.md`](rules.md) |
| §4 | a arquitetura: as camadas, as tabelas e os segredos | [`architecture.md`](architecture.md) |
| §5 | as interfaces: `cli`, WebApp e Wizard | [`interfaces.md`](interfaces.md) |
| §6 | os dois caminhos de uso | [`paths.md`](paths.md) |
| §7 | o caminho container: os passos | [`container.md`](container.md) |
| §8 | as extensões e os plugins | [`extensions.md`](extensions.md) |
| §9 | o ambiente de teste end-to-end | [`end-to-end.md`](end-to-end.md) |
| §10 | a derivação: a árvore, a Pasta de Trabalho e a operação | [`derivation.md`](derivation.md) |
| §11 | o glossário: o que um nome significa | [`glossary.md`](glossary.md) |

## O que ainda não está aqui

`docs/en_US/backlog.md` guarda o que vem a seguir, com o que conta como pronto para cada item.

Três dívidas nasceram das decisões desta sessão, e as três estão nomeadas para não virarem surpresa:

- **O código.** Nada do que ficou decidido aqui está construído: o ator, a auditoria, o filtro de demandas, a postura, o interpretador, os plugins. Tudo tem item no `docs/en_US/backlog.md`.
- **A lista do corretor.** Ela nasceu grande — 220 palavras em português e 141 em inglês —, e o motivo está escrito no cabeçalho dela: o dicionário do corretor vem de frequência de legendas e erra o registro formal, onde "seção", "deleção" e "registrar" não aparecem. Se essa lista crescer sozinha, o gate virou enfeite, e o diff é o lugar de perceber.
- **O `FAQ.md`.** Ele ainda não existe, e agora tem trabalho esperando: dizer o que está por baixo — qual tela é do AT e qual é de terceiros —, e que escrever bem é o melhor remédio contra um mal-entendido do interpretador.
