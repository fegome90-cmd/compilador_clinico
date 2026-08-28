"""Clinical safety policy for the compilation pipeline."""

NEVER_AUTO_TERMS: frozenset[str] = frozenset()
"""Terms that must never be auto-confirmed by the pipeline.

Every term here requires explicit human confirmation regardless of
its assessed certainty. Populated by policy configuration; the
pipeline must treat membership as a hard veto.
"""
