# Stale as of 2026-09-01

These files are the output of a `/graphify` run made **before** the folder was
reorganised. They still reference paths that no longer exist:

- `Precision and research first (1)/` was renamed to `05 Design Reference/`
- `04 Prototype/Frontend Design Brief.md` and `Claude Design Prompt.md` were
  deleted as superseded pointer stubs
- `graphify-out/converted/` and the extraction cache were deleted

Nothing here is load-bearing. It is a knowledge graph over the planning docs,
kept because it was built deliberately, not because anything depends on it.

Re-run `/graphify .` to regenerate against the current layout, or delete this
whole folder if it stops being useful.
