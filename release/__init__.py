"""The release: what the product is BUILT on, and the proof that it was.

Not a layer of the product — nothing here travels inside the artifacts, and
`pyproject.toml` does not publish this package. What lives here is the half of
§3 that the code cannot carry: the release is one file per platform, its
portability is decided where it is built, and where that is has to be a
declaration rather than a habit.

Two pieces, and they are one subject:

- `builder.json` — the machine the release is built on, pinned like every other
  external dependency (version AND hashing), and the glibc floor the release
  promises;
- `floor.py` — the measurement that makes the promise falsifiable: the artifact's
  real floor is read off what it carries, and a release that needs more than it
  declared does not leave the builder.
"""
