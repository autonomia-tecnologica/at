"""The deploy's suite. Stdlib `unittest` only — a test runner is not a dependency.

It is discovered together with `at/tests` from the repository root:

    python3 -m unittest discover -t .

The two suites are one: `at-cli`'s and the deploy's are the same product's, and the
one that runs them both is the same command (`at_deploy/tests/test_boundary.py`
is where the boundary between them is affirmed).
"""
