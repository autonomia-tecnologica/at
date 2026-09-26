# 7. Container path: the steps [normative]

### Configuration steps

- The steps below are the container path. They are not a requirement for using AT: without them, what one has is the hosted path (§6), which is also supported. "Required" here means required for this path.

#### a. Create the container environment (required)

- This is the main switch of the environment. The person needs Podman installed. **`at-deploy`** checks whether it exists and, if it does not, offers the two ways out: install Podman, or continue on the hosted path. It does not install Podman on its own. From there on, **`at-deploy` orchestrates the environment and the services**, which come up as containers from pinned images.

- **The environment is a second artifact.** The whole of §7 — Podman, the VPN, the DNS, the gate's containers, the edge's Caddy, the switch between the two paths and the only elevation in the product — lives in `at-deploy`, and `at-cli` keeps the folder and the app: it reads the same Working Folder and serves it with the deploy tool absent, refusing the Forms on the container path and closing when the gate falls. The boundary between the two is the folder's **state** and not an API — both read it, and the deploy tool is the one that writes the environment's (`App/services/`, the pins, the gate secret) — and the shared core (paths, `i18n`, files, the table engine) is one source and not two. It is why `at-cli` can promise, by what it is, that it never asks for administration permissions: the code that asks is not in it.

- It is a complex function with a lot of room for error and for a security failure. The security decisions around it are in [Security](rules.md#security).

- Podman is the choice for containers. `dnsmasq` and Caddy are the first services. The first to customize the access urls and the second to publish AT, now in a container, for the isolation.

- **The site is a NAME, and the DNS of the environment is what answers for it.** `dnsmasq` answers `at.local` with the address the edge is actually at, and `at.local` is what the Caddy serves when the machine is on no private network. A name, and not the loop, because of two measurements: the gate refuses a cookie domain without a dot that is not an IP, and TLS needs a name to put in the SNI — a client connecting to an ADDRESS sends none, and the edge answers the handshake with an error because it has no certificate it can serve. What the person types is the name, so the machine has to use that DNS.

#### b. Install the identity provider as a container (required)

- AT has an authenticator of its own, and on the container path it is the gate: an external identity provider, here Authelia, in front of everything. It becomes responsible for the authentication of all the services existing here, and AT comes in as one more app — not as an exception.

- Authelia speaks **OIDC** with whoever speaks OIDC, and **forward-auth** with whoever does not. Sonarr, Radarr and Prowlarr do not speak OIDC, and it is forward-auth that gives them the same experience: one login at the portal, the cookie holding for all. AT does not speak OIDC with it either: it comes in through forward-auth, like the others.

- The split is: **who** is an actor belongs to AT, and **how** it is proved that it is them belongs to Authelia. The `actor` table (§4) holds identity, role and the hashed credential — and on the container path whoever uses the Authelia credential is Authelia.

- What Authelia **is not**: a login provider with Google. It does not play the relying party role, and that is a decision of the project, not configuration. Login with third parties is not part of AT.

- Here there is no authentication with AT's face. The portal is Authelia's, and what AT does is ask it to be as neutral as possible, so as not to look like what it is not (§5).

- What AT demands from whoever arrives with an identity is the **gate secret**: a value drawn by `at-deploy` at installation, written into the Caddyfile it generates itself, attached by Caddy to every request carrying an identity, and refused to whoever does not bring it. It is the M2M between Caddy and AT's WebApp, and Authelia never sees it. The file is the folder's state, so `at` reads it too — on the container path it is what makes an identity an identity, and the deploy tool is only what drew it.

- **The folder's own people are what the gate proves, and `at-deploy` is the door that keeps them.** Who is an actor belongs to AT (§4) and how it is proved belongs to Authelia, so changing a credential is one act over both: `at-deploy services credential <name>` writes the credential into the actor's row — hashed, as the Forms and Basic already prove it — derives the `users.yml` from that same row, and brings the provider up again, because Authelia reads that file at START and a derivation rewritten under a standing container is a derivation nothing proves. A person with no credential is not in the file, and giving them the first one is the same act.

- **The restart does not evict whoever is already inside, and that price is declared.** The session secret is drawn once and kept in the folder, and it is what seals the session cookie: the same value across a restart keeps every session that was open, and the registry those sessions live in is the folder's too. So a credential changed because it leaked leaves the sessions it had opened standing until they expire — and the way to end them is a new session secret, which ends every session in the folder with it.

#### c. Install the WebApp as a container (required)

- The WebApp, the main way of using AT, is installed as a container. It aims to reduce the blast radius in a compromised web application.

- **The WebApp answers on the container's network, and the edge reaches it by name.** This is measured and not a preference: an app listening on its own container's loop is reached by nobody — the published port lands on the container's network address and finds nothing there, and the edge is another container, whose `127.0.0.1` is itself. So the app listens on the container's addresses, and what keeps that from being an exposure is the gate secret (§7b): whoever reaches it and brings no secret is refused with `403`.

- **The environment's network is one, and what decides a service's place in it is who it has to talk to.** A container's `127.0.0.1` is itself and nobody else, and two networks do not reach each other at all — measured, no route and no name — so the Caddy (which proxies to the WebApp and asks the gate about every request), the WebApp (which asks the gate whether its portal is standing) and the gate stand together. The DNS is the one service that talks to nobody, and it is the one service on the environment's DMZ, where it cannot reach the WebApp.

- **The WebApp's port is the one AT serves by default, and it is not published.** Exposing moves the address the person reaches, never the one the WebApp listens on — and who reaches it is the edge, on the network the two share, or nobody at all.

#### d. Install the spelling and grammar checker as a container (optional)

- AT's default for text correction is LanguageTool, today the tool that fulfils the `spelling-checker` service (§4). It serves to underline errors on the editing screen. Quite useful.

- This is the checker of the **person's text**, at run time. The checker of the repository's documents is another one, and it is a development tool ([derivation §3](derivation.md)).

#### e. Install a VPN (optional)

- AT allows configuring a VPN. Here it is relevant, because it allows creating a private network so that multiple devices talk to each other. So if the AT WebApp runs on your personal machine, it becomes securely reachable from your phone, anywhere. Here I am using Tailscale. It is proprietary, but it avoids needing a server in the cloud. Headscale support in the future.

#### f. Install the notifier as a container (optional)

- With everything configured, the cherry on the cake is `ntfy`, today the tool that fulfils the `notifier` service (§4). The configured reminders can be notified directly as a Push Notification, and it is through it that the approval of a demand that passed the risk threshold arrives.

- **The notifier is the one service of this section that does not go behind the gate**, and that is a measurement and not a preference: the gate authenticates by redirect and by session cookie, so a headless phone app takes the 302 and never connects — measured, `subscribers=0` behind Authelia and `101` without it. Its authentication is the per-topic token ACL of [the container path](paths.md#container-path). The decision is recorded in [Security](rules.md#security).

- **AT publishes to it with a credential of its own, delimited to the topic.** The scope §3 asks of whoever reaches AT applies here in its mirrored form, and it is measured: with the account granted `write-only` on the topic, the token publishes with a `200`, refuses any other topic with a `403`, and cannot read its own back either, with another `403`. AT makes it when the environment comes up — the account, the scope and the token, through the notifier's own `cli` inside the container, with the password on the command's input and the token out of its output, never in the argv — and keeps it in a `0600` file beside the state of that service until the `secret` table takes it over.

- **The other end of the same ACL is the person's, and the door is `at-deploy services phone`.** The phone does not read with AT's credential, nor AT with the phone's: the account is another one, with `read-only` on the same topic, and it is born when the person asks for it — the phone is not the machine the environment runs on, so it is not a thing bringing the environment up gets to decide. The token is drawn by the notifier, kept at `0600` beside AT's, and **printed once**, because there is no road to a phone except the person's eyes; a second run names the file and never the value. A copied folder carries both ends, and that is what makes it able to publish and to read again (§3, the backup promise).

- This is where the first graded functionality comes in: its levels and what each one costs live in [functionalities](functionalities.md).
