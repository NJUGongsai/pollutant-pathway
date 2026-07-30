"""P1-T5 Participant roles & donor eligibility package.

Implements:
- ``load_cofactors()`` — read-only extraction of legacy ``COFACTORS`` with a
  recorded source hash (§11.3). COFACTORS is used ONLY as a prior
  (participant_role_prior / donor_eligibility_prior / retrieval_downweighting_prior),
  NEVER as a destructive stripping rule.
- ``resolve_roles(participants)`` — attaches ``RoleHypothesis`` objects to each
  participant. NEVER deletes a participant (§11.1/§11.5 multiset invariant).
- ``assess_donor_eligibility(participant, mapping_report)`` — independent
  donor-side eligibility assessment (§11.4, distinct from role).

Design references: training/chatgpt_p1_train.md §11.1–§11.5.
"""
from reaction_agent.roles.cofactors import load_cofactors, LEGACY_PATH
from reaction_agent.roles.resolver import resolve_roles, assess_donor_eligibility

__all__ = [
    "load_cofactors",
    "LEGACY_PATH",
    "resolve_roles",
    "assess_donor_eligibility",
]
