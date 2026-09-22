# 7. Container path: the steps [normative]

### Configuration steps

- The steps below are the container path. They are not a requirement for using Bill: without them, what one has is the hosted path (§6), which is also supported. "Required" here means required for this path.

#### a. Create the container environment (required)

- This is the main switch of the environment. The person needs Podman installed. Bill checks whether it exists and, if it does not, offers the two ways out: install Podman, or continue on the hosted path. It does not install Podman on its own. From there on, Bill orchestrates the environment and the services, which come up as containers from pinned images.

- It is a complex function with a lot of room for error and for a security failure. The security decisions around it are in [Security](rules.md#security).

- Podman is the choice for containers. `dnsmasq` and Caddy are the first services. The first to customize the access urls and the second to publish Bill, now in a container, for the isolation.

#### b. Install the identity provider as a container (required)

- Bill has an authenticator of its own, and on the container path it is the gate: an external identity provider, here Authelia, in front of everything. It becomes responsible for the authentication of all the services existing here, and Bill comes in as one more app — not as an exception.

- Authelia speaks **OIDC** with whoever speaks OIDC, and **forward-auth** with whoever does not. Sonarr, Radarr and Prowlarr do not speak OIDC, and it is forward-auth that gives them the same experience: one login at the portal, the cookie holding for all. Bill does not speak OIDC with it either: it comes in through forward-auth, like the others.

- The split is: **who** is an actor belongs to Bill, and **how** it is proved that it is them belongs to Authelia. The `actor` table (§4) holds identity, role and the hashed credential — and on the container path whoever uses the Authelia credential is Authelia.

- What Authelia **is not**: a login provider with Google. It does not play the relying party role, and that is a decision of the project, not configuration. Login with third parties is not part of Bill.

- Here there is no authentication with Bill's face. The portal is Authelia's, and what Bill does is ask it to be as neutral as possible, so as not to look like what it is not (§5).

- What Bill demands from whoever arrives with an identity is the **gate secret**: a value drawn by Bill at installation, written into the Caddyfile it generates itself, attached by Caddy to every request carrying an identity, and refused to whoever does not bring it. It is the M2M between Caddy and Bill's WebApp, and Authelia never sees it.

#### c. Install the WebApp as a container (required)

- The WebApp, the main way of using Bill, is installed as a container. It aims to reduce the blast radius in a compromised web application.

#### d. Install the spelling and grammar checker as a container (optional)

- Bill's default for text correction is LanguageTool, today the tool that fulfils the `spelling-checker` service (§4). It serves to underline errors on the editing screen. Quite useful.

- This is the checker of the **person's text**, at run time. The checker of the repository's documents is another one, and it is a development tool ([derivation §3](derivation.md)).

#### e. Install a VPN (optional)

- Bill allows configuring a VPN. Here it is relevant, because it allows creating a private network so that multiple devices talk to each other. So if the Bill WebApp runs on your personal machine, it becomes securely reachable from your phone, anywhere. Here I am using Tailscale. It is proprietary, but it avoids needing a server in the cloud. Headscale support in the future.

#### f. Install the notifier as a container (optional)

- With everything configured, the cherry on the cake is `ntfy`, today the tool that fulfils the `notifier` service (§4). The configured reminders can be notified directly as a Push Notification, and it is through it that the approval of a demand that passed the risk threshold arrives.

- This is where the first graded functionality comes in: its levels and what each one costs live in [functionalities](functionalities.md).
