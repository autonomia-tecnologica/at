"""External services, kept as tool-agnostic as the layer can be (§4).

Podman, Caddy, dnsmasq, Authelia, ntfy, LanguageTool and the local LLM belong
here, each behind a declaration rather than a script. Nothing exists yet; the
order of construction is fixed by danger — `auth` comes last.
"""
