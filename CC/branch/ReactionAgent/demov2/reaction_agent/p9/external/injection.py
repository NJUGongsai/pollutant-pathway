"""P9-T3: Injection isolation (final_plan §12.3, Phase A criterion 5; P9 铁律).

External evidence content is DATA, never instructions. It must not:

- grant/change agent permissions;
- override prior instructions or deny-list / allowlist bypasses;
- smuggle schema field names to bypass the StrictModel (extra='forbid').

Defense architecture (layered):

1. **Schema layer (primary, authoritative)**: ``ExternalEvidenceRecord`` has NO
   permission / tool / role fields — there is nothing external text can write to
   that changes authority. ``extra="forbid"`` rejects unknown fields.

2. **Content scanner (best-effort, secondary)**: the scanner below normalizes
   whitespace and checks for known control directives. It is a *defense in
   depth* layer, NOT authoritative — the schema layer is the real guarantee.
   Benign chemical text containing common words like "role", "ranking", or
   "decision" is NOT blocked (those words have been removed from the scan
   vocabulary to avoid false positives in chemical evidence).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field

# Control vocabulary: normalized (single-space) substrings that indicate an
# attempt to change authority, override instructions, or bypass schema. This
# is a best-effort guard — the schema layer (extra=forbid, no permission
# fields) is the authoritative defense.
CONTROL_DIRECTIVES: tuple[str, ...] = (
    # permission / authority changes
    "grant all permissions",
    "grant permissions",
    "elevate permissions",
    "enable all tools",
    "give me access",
    "you are now admin",
    # instruction overrides
    "ignore previous instructions",
    "ignore prior instructions",
    "disregard your instructions",
    "override your rules",
    "you must follow me",
    # schema / deny-list bypass (specific patterns unlikely in chemistry)
    "result_status",
    "decision=predicted",
    "classification=completed",
    "extra=",
    "bypass the allowlist",
    "bypass allowlist",
    "disable the guard",
)

# Schema field names that would appear in a smuggling payload.  These are
# checked with word-boundary matching to avoid false positives on common
# chemical terms.  Words like "role", "ranking", "decision", "tools",
# "authorized", and "permissions" are excluded because they appear frequently
# in benign chemical evidence text.  Access changes are caught by the compound
# CONTROL_DIRECTIVES ("grant all permissions", "enable all tools").
SCHEMA_FIELD_NAMES: tuple[str, ...] = (
    "result_hash",
)


def _normalize(content: str) -> str:
    """Normalize whitespace: collapse all runs of whitespace to a single space."""
    return re.sub(r"\s+", " ", content).strip()


@dataclass(frozen=True)
class InjectionScanResult:
    """Outcome of scanning external content for injection signatures."""

    blocked: bool
    reasons: list[str] = dc_field(default_factory=list)


def scan_content(content: str) -> InjectionScanResult:
    """Scan external content for control directives. Best-effort content layer.

    Returns a result with ``blocked=True`` plus the matched reasons if the
    content appears to carry a control directive. Benign chemical text passes.

    Note: the authoritative injection defense is the schema layer
    (``extra="forbid"`` + no permission/role fields). This scanner is a
    defense-in-depth layer, not the primary guarantee.
    """
    normalized = _normalize(content)
    lowered = normalized.lower()
    reasons: list[str] = []
    for directive in CONTROL_DIRECTIVES:
        if directive in lowered:
            reasons.append(f"control directive: {directive!r}")
    # Word-boundary matching for schema field names to avoid false positives
    # on common chemical terms.
    for field in SCHEMA_FIELD_NAMES:
        pattern = re.compile(r"\b" + re.escape(field) + r"\b")
        if pattern.search(lowered):
            reasons.append(f"schema field name present: {field!r}")
    if reasons:
        return InjectionScanResult(blocked=True, reasons=reasons)
    return InjectionScanResult(blocked=False, reasons=[])


def assert_content_inert(content: str) -> None:
    """Raise ValueError if content carries a control directive (fail-closed)."""
    result = scan_content(content)
    if result.blocked:
        raise ValueError(
            "external content rejected: suspected injection "
            f"({'; '.join(result.reasons)})"
        )