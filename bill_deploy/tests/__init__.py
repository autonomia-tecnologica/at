"""The deploy's suite. Stdlib `unittest` only — a test runner is not a dependency.

It is discovered together with `bill/tests` from the repository root:

    python3 -m unittest discover -t .

The two suites are one: `bill`'s and the deploy's are the same product's, and the
one that runs them both is the same command (`bill_deploy/tests/test_boundary.py`
is where the boundary between them is affirmed).
"""
