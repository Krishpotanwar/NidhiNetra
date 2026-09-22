"""Phase 1 Stage B: the pair judge.

Reads the near-copy pairs in duplicate_candidates.json, asks a pinned model on Hugging Face
Inference Providers what each pair of descriptions has in common, checks every quote against the
two texts, and stores the answers. It is never part of the build: `cli judge` runs it by hand.
"""
