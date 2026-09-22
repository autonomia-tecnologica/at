# 6. The two paths of use [normative]

- There are two paths, and both are supported. They differ in what they guarantee, and the difference is declared here so that nobody decides with wrong information.

### Hosted path

- It is Bill and the folder. The binary is opened in the Working Folder, the WebApp comes up through the command, the Wizard opens when there is no parameter, and the `cli` does the rest. There is no container at all, and the person needs neither Podman nor anything beyond the binary.

- **There is no isolation**, and Bill promises none on this path: a compromise of the WebApp is a process compromise on your machine, with access to what your user has. In exchange, the default is not to leave the local loop, and leaving it demands authentication and TLS.

- Leaving the local loop, here, is `bill webapp --include-caddy`: the Caddy that came inside the binary terminates the TLS and publishes Bill. Without the flag, the WebApp serves over HTTP and only on `127.0.0.1`.

- The integrations (§7) can exist without a container: whoever installs the service on their own and points Bill at it uses the service, knowing that the state of that service is no longer Bill's business — and therefore that the folder backup does not cover it. Approving a risky demand, here, happens on the machine itself: the `notifier` service belongs to the container path.

- Exposing Bill on the hosted path with the container path's Authelia is the **advanced mode**, and it is not supported: whoever wants the gate uses the container path.

### Container path

- It is Bill building an environment of services in containers from pinned images (§7). Here there is isolation, and it exists for a specific reason: **containing the blast radius of each service**. A compromise of `ntfy` reaches the notification and nothing else; the checker's reaches the checker. What each service exposes is what it sets out to do, and nothing beyond.

- A service that needs to talk to Bill — and not Bill to the service — has a delimited scope: a credential with a declared role, and only what that role allows. Least privilege, applied. In `ntfy`, that is the per-topic ACL: Bill publishes, the phone reads, and neither token serves for anything else.

- The container path is what sustains the authentication gate (§7b), and it is where Bill comes in as one more app behind it.

### The switch between paths

- Going from one path to the other is a **switch**, and a switch is transactional: Bill executes the set of actions and, if any of them does not end successfully, everything goes back to the previous state. The environment does not stay half done, and what existed before keeps working.

- In the container direction, Forms stays on until Authelia is **proven** to work in front of Bill — it is not "the container came up", it is Bill receiving the identity it expects, through the real path, with the gate secret. Only then does Forms turn off.

- If the gate falls afterwards, with the switch already committed, Bill **closes** and warns: "Portal de autenticação indisponível. Utilize o Wizard para retornar o Bill para modo forms." It does not reopen Forms on its own — reopening on its own would be trading security for convenience, with nobody deciding.

- If Bill finds an infrastructure environment configured in the folder but does not find the environment, it asks: "Foi detectado que você tem um ambiente de infraestrutura configurado nesse ambiente, mas o ambiente de infraestrutura não foi encontrado. Você deseja instalar novamente o Podman/Docker ou restaurar o bill para modo hospedado na máquina?". It is the backup promise showing up on the screen: the folder came back, and what was missing was only the ground.
