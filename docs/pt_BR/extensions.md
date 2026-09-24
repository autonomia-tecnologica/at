# 8. Extensões e plugins [normativo]

- A extensão existe para ensinar o AT, e a primeira delas é o mapa de gíria: é dado que muda por região, por pessoa e por época, e esperar uma release para ser entendido é caro demais.

- **Nenhuma extensão executa código hoje.** A primeira classe é **dado puro**: uma pasta com uma declaração e os dados, sem uma linha executável. Um plugin de dados não tem presença em execução nenhuma — não é processo, não é leitor: quem lê a frase é o AT, e o plugin só diz como traduzir. Por isso ele não pede permissão de leitura; pedir seria teatro, e aviso de teatro ensina a clicar em "aceito" sem ler o próximo.

- **O plugin carrega um manifesto**, e o manifesto declara o que ele faz no ambiente. As permissões são granulares e a pessoa vê o que está instalando. A primeira permissão da história do AT é sobre o que o plugin **altera**: *"Esse plugin pode alterar suas palavras antes de ser analisado pelo motor (core) do AT."* A frase da permissão é do **produto**, renderizada pelo nome interno no `i18n` do produto — o plugin apenas referencia o id, porque um aviso escrito por quem está sendo avisado não é aviso. O plugin pode acrescentar uma nota de autoria, marcada como dele.

- **A instalação amarra um review a uma hash.** O AT vê o que existe em disco e mantém o estado; copiar para a pasta faz ele **enxergar**, e o ato de instalar é o que conta. A pasta inteira do plugin é hasheada, **só o conteúdo, em ordem canônica** — sem hora de modificação, sem permissão, sem pasta vazia —, e qualquer byte alterado muda a hash, invalida o review e derruba a nota. As aceitações precisam ser feitas de novo, o que fecha o furo clássico de confiar no autor: a coisa que você aprovou e a coisa que roda depois são a mesma, ou o AT sabe que não são.

- O caminho de volta da nota é um **review explícito**, em um de três modos: *eu li o que ele faz*, *eu pedi a uma IA para ler o que ele faz*, *eu confio em quem fez*. Ninguém verifica a declaração — é o único formato possível —, e é por isso que a nota se apresenta como declaração (§3, A postura de segurança).

- O estado dos plugins mora em `app/`, em arquivo, e não nas tabelas. Como a pasta é da pessoa, dá para editar esse estado e mentir para a própria nota: isso não é falha do desenho, porque a hash protege você **do autor**, não o autor de você.

- **Código é a última opção.** Código que executa é código difícil de conter, e antes dele o plano é entregar extensão em formas bem mais estabelecidas.
