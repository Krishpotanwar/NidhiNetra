"""A2's lane: risk scoring for NidhiNetra.

Public surface: `score_all`. Everything else (peer_groups, detectors,
explain, rank) is composed by it and can be imported directly by tests or
by a future caller that needs a single stage, but `score_all` is the
contract A4 is expected to call.
"""

from .engine import score_all
from .peer_groups import MIN_PEER_GROUP_N, PeerGroup, peer_group_for

__all__ = ["score_all", "PeerGroup", "peer_group_for", "MIN_PEER_GROUP_N"]
