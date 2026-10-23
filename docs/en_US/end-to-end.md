# 9. End-to-end test environment [normative]

- The main test is checking that, with Podman installed, executing AT's actions works perfectly. That test will happen on Mac, Linux and Windows VMs.

- It is **automated end to end**: no part depends on an eye or a hand on a screen. The script brings up the VM, opens the binary and checks what came back — Podman absent makes AT offer the two ways out; Podman present brings the environment up with the images at the pin; an instance ahead of the pin warns and proceeds; AT refuses to go on the network without authentication and goes up with it; the WebApp answers behind the gate; and the Working Folder created on the first run is only what §3 describes.

- The hosted path has a gate of its own, and it is cheap because it depends on neither a VM nor a container: the first start asks for the admin and does not let AT expose without it; without authentication AT listens only on `127.0.0.1`; exposing without TLS is refused; the switch to the container rolls back whole when any action does not close; and the fallen gate closes AT with the sentence on display.

- The interpreter has a ruler of its own, and it runs as a test: sentences that must work, sentences that must be refused, and ambiguous sentences that must be returned as a question. No LLM, no network and no video card.

- The test **is not the criterion of done for each function** — a function is done by what `docs/pt_BR/backlog.md` says it is. It is the gate of the first publication on GitHub, and from there on.
