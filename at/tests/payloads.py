"""Helper for the tests that read the REAL vendored payloads.

The payloads under `at/vendor/*` are pinned by `manifest.json` and are not
versioned; `python3 -m release.fetch` pulls them. A clone that has not fetched
skips the tests that need the bytes (no test touches the network).
"""

from __future__ import annotations


def needs(test, service, *names: str) -> None:
    """Skip `test` unless the service's payload (or each named file) is on disk."""
    if names:
        absent = [name for name in names if not (service.PAYLOAD / name).is_file()]
    else:
        absent = [] if service.payload() is not None else [f"{service.__name__} (this platform)"]
    if absent:
        test.skipTest("vendored payload not fetched, run `python3 -m release.fetch`: "
                      + ", ".join(absent))


def required(service):
    """Class decorator: the whole case unpacks or runs the real payload."""
    import unittest

    return unittest.skipUnless(
        service.payload() is not None,
        f"vendored {service.__name__.rsplit('.', 1)[-1]} not fetched, "
        f"run `python3 -m release.fetch`",
    )
