# 9. Ambiente de teste end-to-end [normativo]

- O teste principal é verificar se, com o Podman instalado, executar as ações do AT funciona perfeitamente. Esse teste acontecerá em VMs Mac, Linux e Windows.

- Ele é **automatizado de ponta a ponta**: nenhuma parte depende de olho ou de mão numa tela. O script sobe a VM, abre o binário e verifica o que voltou — Podman ausente faz o AT oferecer as duas saídas; Podman presente sobe o ambiente com as imagens no pin; uma instância à frente do pin avisa e segue; o AT recusa subir na rede sem autenticação e sobe com ela; o WebApp responde atrás do portão; e a Pasta de Trabalho criada na primeira execução é só o que o §3 descreve.

- O caminho hospedado tem portão próprio, e é barato porque não depende de VM nem de container: a primeira subida pede o admin e não deixa o AT expor sem ele; sem autenticação o AT escuta só `127.0.0.1`; expor sem TLS é recusado; a virada para o container volta atrás inteira quando alguma ação não fecha; e o portão caído fecha o AT com a frase à mostra.

- O interpretador tem a sua própria régua, e ela roda como teste: frases que precisam funcionar, frases que precisam ser recusadas, e frases ambíguas que precisam ser devolvidas em pergunta. Sem LLM, sem rede e sem placa de vídeo.

- O teste **não é o critério de pronto de cada função** — uma função fica pronta pelo que o `docs/pt_BR/backlog.md` diz que ela é. Ele é o portão da primeira publicação no GitHub, e dali em diante.
