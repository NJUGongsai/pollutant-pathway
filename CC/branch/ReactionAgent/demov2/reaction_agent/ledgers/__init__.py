"""Ledger builders (final_design §10).

SourceReactionLedger: records what the source database actually documents.
CandidateAnalogyLedger: records donor-derived analogy assumptions for X→Y.

These MUST NOT be mixed. Donor cofactors/stoichiometry in source ledger do
NOT become proven facts about X→Y.
"""

from reaction_agent.ledgers.source_builder import build_source_ledger

__all__ = ["build_source_ledger"]
