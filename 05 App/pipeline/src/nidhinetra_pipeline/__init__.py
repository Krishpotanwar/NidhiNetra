"""NidhiNetra pipeline package.

Subpackages, per Execution Plan section 1 workstreams:
  ingest / normalize -- A1 (acquisition ladder, normalization)
  risk                -- A2 (this agent's lane: peer groups, detectors,
                          explanations, ranking)
  graph                -- A3 (fund-flow graph, concentration detection)

This file intentionally stays minimal. It exists only so `risk` (and later
`ingest`/`normalize`/`graph`) is importable as `nidhinetra_pipeline.<name>`.
"""
