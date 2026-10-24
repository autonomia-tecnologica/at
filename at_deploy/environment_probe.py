"""What a person (and the report) asks of the runtime: container state, whether an
image is here, whether an address answers, and curl's own configuration.
"""

from __future__ import annotations

import socket

from at_deploy import podman
from at_deploy.environment_base import ABSENT, INSTALLED, MISSING, RUNNING, STOPPED
from at_deploy.environment_models import Image, Service
from at_deploy.environment_paths import container


def _state_of(service: Service) -> str:
    """Whether the service's container is running, stopped, or not there — the
    RUNTIME's answer, which the decisions below read and the report does not."""
    answer = podman.run([
        "container", "inspect", "--format", "{{.State.Running}}",
        container(service.name),
    ])
    if answer.returncode != 0:
        return ABSENT
    return RUNNING if answer.stdout.strip() == "true" else STOPPED


def _here(image: Image) -> bool:
    """Whether the image is in this machine's store — "instalado", measured."""
    return podman.run(["image", "exists", image.reference()]).returncode == 0


def _shown_state(service: Service, image: Image) -> str:
    """The service as a PERSON reads it: running, installed, or not installed.

    It is the runtime's answer folded into the three words a person asks with.
    A container that was stopped, one that was taken down and one that is about
    to be created are the same answer to "is it on?" — and the difference that
    matters is whether the thing is HERE at all, which is the image.
    """
    if _state_of(service) == RUNNING:
        return RUNNING
    return INSTALLED if _here(image) else MISSING


# How long a report waits for an address to answer. It is a question about NOW,
# and a machine that does not answer in a second is a machine that does not
# answer — waiting longer would make `status` slow to say what it already knows.
STATUS_TIMEOUT = 1.0


def published(host: str, port: int) -> bool:
    """Whether something actually ANSWERS at the address.

    **Derived is not the same as true**, and this is where the difference is
    measured. The address comes from the machine's private network — a fact
    about the CONFIGURATION — and the report said "reachable at" from it: a
    folder whose environment was down announced an address while nothing at all
    listened on the port. What is reachable is what answers, and that is asked
    here and never inferred.
    """
    try:
        with socket.create_connection((host, port), timeout=STATUS_TIMEOUT):
            return True
    except OSError:
        return False


def _as_curl_config(headers: dict[str, str],
                    connect: tuple[str, int, str] | None = None) -> str:
    """The headers as curl's own configuration, for its INPUT.

    A value is escaped so that a name carrying a quote is the name and not the
    syntax around it — the same care `_quoted` takes with a name on its way into
    a YAML file. `connect` adds the `connect-to` line, which is how a URL keeps a
    name that nothing resolves while the connection goes to a container that the
    environment's own network knows.
    """
    lines = []
    if connect is not None:
        name, port, target = connect
        lines.append(f'connect-to = "{name}:{port}:{target}:{port}"')
    for name, value in headers.items():
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'header = "{name}: {escaped}"')
    return "\n".join(lines) + "\n"
