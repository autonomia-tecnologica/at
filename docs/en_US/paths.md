# 6. The two paths of use [normative]

- There are two paths, and both are supported. They differ in what they guarantee, and the difference is declared here so that nobody decides with wrong information.

### Hosted path

- It is AT and the folder. The binary is opened in the Working Folder, the WebApp comes up through the command, the Wizard opens when there is no parameter, and the `cli` does the rest. There is no container at all, and the person needs neither Podman nor anything beyond the binary.

- **There is no isolation**, and AT promises none on this path: a compromise of the WebApp is a process compromise on your machine, with access to what your user has. In exchange, the default is not to leave the local loop, and leaving it demands authentication and TLS.

- Leaving the local loop, here, is `at-cli webapp --include-caddy`: the Caddy that came inside the binary terminates the TLS and publishes AT. Without the flag, the WebApp serves over HTTP and only on `127.0.0.1` — and it refuses to be asked for any other address, because exposure without TLS is what the rule above forbids. `--host` names the address AT answers on, and with the flag it has to be a name a certificate can be issued for: `0.0.0.0` is every address, and a certificate has none.

- The integrations (§7) can exist without a container: whoever installs the service on their own and points AT at it uses the service, knowing that the state of that service is no longer AT's business — and therefore that the folder backup does not cover it. Approving a risky demand, here, happens on the machine itself: the `notifier` service belongs to the container path.

- Exposing AT on the hosted path with the container path's Authelia is the **advanced mode**, and it is not supported: whoever wants the gate uses the container path.

### Container path

- It is **`at-deploy`** building an environment of services in containers from pinned images (§7). Here there is isolation, and it exists for a specific reason: **containing the blast radius of each service**. A compromise of `ntfy` reaches the notification and nothing else; the checker's reaches the checker. What each service exposes is what it sets out to do, and nothing beyond.

- A service that needs to talk to AT — and not AT to the service — has a delimited scope: a credential with a declared role, and only what that role allows. Least privilege, applied. In `ntfy`, that is the per-topic ACL: the one account AT holds publishes and reads, and reaches no other topic. Who reaches it from outside at all is the gate's business now, not the ACL's alone: `ntfy.at.local` sits behind the same Authelia as the site, proved by Basic on the request itself, and past that ask the edge is what carries AT's own credential — never the person's.

- The container path is what sustains the authentication gate (§7b), and it is where AT comes in as one more app behind it.

- **The environment is built by a second artifact, and the folder is still served by `at-cli`.** `at-deploy` is a `cli` and a Wizard, the way `at-cli` is, and here the Wizard is the natural front: deploying is a SEQUENCE and not a sentence, and it walks the person through it step by step — it checks the requirements, brings one service up, moves on to the next. Every step it takes is one the `cli` takes alone, because §5's one-way rule does not bend for a second artifact. Both files are needed on this path, and `at-cli` serves the folder with the deploy tool absent: it is `at-cli` that reads `authenticator` and the gate secret, refuses the Forms and closes when the gate falls.

### The switch between paths

- Going from one path to the other is a **switch**, and a switch is transactional: `at-deploy` executes the set of actions and, if any of them does not end successfully, everything goes back to the previous state. The environment does not stay half done, and what existed before keeps working.

- In the container direction, Forms stays on until Authelia is **proven** to work in front of AT — it is not "the container came up", it is AT receiving the identity it expects, through the real path, with the gate secret. Only then does Forms turn off.

- If the gate falls afterwards, with the switch already committed, AT **closes** and warns: "Portal de autenticação indisponível. Utilize o Wizard para retornar o AT para modo forms." It does not reopen Forms on its own — reopening on its own would be trading security for convenience, with nobody deciding.

- If `at-deploy` finds an infrastructure environment configured in the folder but does not find the environment, it asks: "Foi detectado que você tem um ambiente de infraestrutura configurado nesse ambiente, mas o ambiente de infraestrutura não foi encontrado. Você deseja instalar novamente o Podman/Docker ou restaurar o AT para modo hospedado na máquina?". It is the backup promise showing up on the screen: the folder came back, and what was missing was only the ground.
