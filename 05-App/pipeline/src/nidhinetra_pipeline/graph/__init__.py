"""A3's lane: the fund-flow graph for NidhiNetra.

Public surface: `build_fund_flow_graph` and `find_concentration_clusters`.
See Execution Plan section 3.3 and contracts/fund_flow_graph.schema.json
for the exact output contract; A4 imports `build_fund_flow_graph` by this
exact signature.
"""

from .alias_candidates import AliasCandidateValidationError, build_alias_candidates
from .build_graph import (
    GraphValidationError,
    build_fund_flow_graph,
    find_concentration_clusters,
)

__all__ = [
    "AliasCandidateValidationError",
    "GraphValidationError",
    "build_alias_candidates",
    "build_fund_flow_graph",
    "find_concentration_clusters",
]
