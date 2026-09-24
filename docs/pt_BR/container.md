# 7. Caminho container: os passos [normativo]

### Passos de configuração

- Os passos abaixo são o caminho container. Eles não são requisito para usar o Bill: sem eles, o que se tem é o caminho hospedado (§6), que também é suportado. "Obrigatório" aqui quer dizer obrigatório para este caminho.

#### a. Criar ambiente container (obrigatório)

- Aqui é a virada principal do ambiente. A pessoa precisa ter o Podman instalado. O **`bill-deploy`** verifica se ele existe e, se não existir, oferece as duas saídas: instalar o Podman, ou seguir no caminho hospedado. Ele não instala o Podman sozinho. A partir daí, o **`bill-deploy` orquestra o ambiente e os serviços**, que sobem como containers de imagens fixadas.

- **O ambiente é um segundo artefato.** O §7 inteiro — o Podman, a VPN, o DNS, os containers do portão, o Caddy da borda, a virada entre os dois caminhos e a única elevação do produto — mora no `bill-deploy`, e o `bill` fica com a pasta e com o app: ele lê a mesma Pasta de Trabalho e a serve com a ferramenta de deploy ausente, recusando o Forms no caminho container e fechando quando o portão cai. A fronteira entre os dois é o **estado** da pasta e não uma API — os dois a leem, e a ferramenta de deploy é a que escreve o estado do ambiente (`App/services/`, os pinos, o segredo do portão) —, e o núcleo compartilhado (paths, `i18n`, files, o motor de tabelas) é uma fonte só e não duas. É por isso que o `bill` pode prometer, pelo que ele é, que nunca pede permissão de administração: o código que pede não está nele.

- É uma função complexa com muita possibilidade de erro e de falha de segurança. As decisões de segurança que a cercam estão em [Segurança](rules.md#segurança).

- Podman é o escolhido para containers. `dnsmasq` e o Caddy são os primeiros serviços. O primeiro para customizar as urls de acesso e o segundo para publicar o Bill, agora em container, pelo isolamento.

#### b. Instalar provedor de identidade como container (obrigatório)

- O Bill tem autenticador próprio, e no caminho container ele é o portão: um provedor de identidade externo, aqui o Authelia, à frente de tudo. Ele fica responsável pela autenticação de todos os serviços existentes aqui, e o Bill entra como mais um app — não como exceção.

- O Authelia fala **OIDC** com quem fala OIDC, e **forward-auth** com quem não fala. Sonarr, Radarr e Prowlarr não falam OIDC, e é o forward-auth que lhes dá a mesma experiência: um login no portal, o cookie valendo para todos. O Bill também não fala OIDC com ele: entra por forward-auth, como os outros.

- A divisão é: **quem** é ator é do Bill, e **como** se prova que é ele é do Authelia. A tabela `actor` (§4) guarda identidade, papel e a credencial hasheada — e no caminho container quem usa a credencial do Authelia é o Authelia.

- O que o Authelia **não** é: provedor de login com Google. Ele não faz o papel de relying party, e isso é decisão do projeto, não configuração. Login com terceiros não faz parte do Bill.

- Aqui não há autenticação com a cara do Bill. O portal é do Authelia, e o que o Bill faz é pedir que ele seja o mais neutro possível, para não parecer o que não é (§5).

- O que o Bill exige de quem chega com identidade é o **segredo do portão**: um valor sorteado pelo `bill-deploy` na instalação, escrito no Caddyfile que ele mesmo gera, colado pelo Caddy em todo pedido que carrega identidade, e recusado por quem não o traz. É o M2M entre o Caddy e o WebApp do Bill, e o Authelia nunca o vê. O arquivo é estado da pasta, então o `bill` também o lê — no caminho container é ele que faz de uma identidade uma identidade, e a ferramenta de deploy é só quem o sorteou.

#### c. Instalar WebApp como container (obrigatório)

- O WebApp, principal forma de usar o Bill, é instalado como um container. Visa diminuir o raio de explosão em uma aplicação web comprometida.

#### d. Instalar corretor ortográfico e gramatical como container (opcional)

- O padrão do Bill para correção de textos é LanguageTool, hoje a ferramenta que cumpre o serviço `spelling-checker` (§4). Ela serve para sublinhar os erros na tela de edição. Bem útil.

- Este é o corretor do **texto da pessoa**, em tempo de execução. O corretor dos documentos do repositório é outro, e é ferramenta de desenvolvimento ([derivation §3](derivation.md)).

#### e. Instalar VPN (opcional)

- O Bill permite configurar uma VPN. Aqui ela é relevante, pois permite criar uma rede privada para que múltiplos dispositivos conversem entre si. Logo se o Bill WebApp roda na sua máquina pessoal, fica acessível de forma segura do seu celular, em qualquer lugar. Aqui estou utilizando Tailscale. É proprietário, mas evita que seja necessário um servidor na nuvem. Suporte a Headscale no futuro.

#### f. Instalar notificador como container (opcional)

- Com tudo configurado, a cereja do bolo é o `ntfy`, hoje a ferramenta que cumpre o serviço `notifier` (§4). Os lembretes configurados podem ser notificados diretamente como um Push Notification, e é por ele que chega a aprovação de uma demanda que passou do limiar de risco.

- **O notificador é o único serviço desta seção que não fica atrás do portão**, e isso é uma medição e não uma preferência: o portão autentica por redirecionamento e por cookie de sessão, então um app de celular sem interface toma o 302 e nunca conecta — medido, `subscribers=0` atrás do Authelia e `101` sem ele. A autenticação dele é a ACL por tópico de [o caminho container](paths.md#caminho-container). A decisão está registrada em [Segurança](rules.md#segurança).

- **O Bill publica nele com uma credencial própria, delimitada ao tópico.** O escopo que §3 exige de quem alcança o Bill vale aqui na forma espelhada, e é medido: com a conta com `write-only` no tópico, o token publica com `200`, recusa qualquer outro tópico com `403`, e também não lê o próprio de volta, com outro `403`. O Bill a cria quando o ambiente sobe — a conta, o escopo e o token, pela própria `cli` do notificador dentro do container, com a senha na entrada do comando e o token na saída dele, nunca no argv — e a guarda num arquivo `0600` junto do estado desse serviço, até a tabela `secret` assumir. O token do celular é da pessoa, e é a outra ponta da mesma ACL.

- É aqui que entra a primeira funcionalidade graduada: os níveis dela e o que cada um custa vivem em [funcionalidades](funcionalidades.md).
