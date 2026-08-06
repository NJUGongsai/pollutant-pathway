#!/usr/bin/env python3
"""Generate deterministic P1-G10 H2 evidence from the three real G03 rows."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reaction_agent.hashing import canonical_hash  # noqa: E402
from reaction_agent.lineage.required_case import (  # noqa: E402
    REQUIRED_CASE_POLICY_VERSION,
    quarantine_unresolved_required_case,
)
from reaction_agent.mapping.adapter import RealMapperAdapter  # noqa: E402
from reaction_agent.schemas.p1_entities import NormalizedReactionRecord  # noqa: E402


SOURCE = ROOT / "reports" / "data_audit" / "legacy_lineage_audit.json"
OUTPUT = ROOT / "reports" / "p1" / "required_case_quarantine_evidence.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = [
        row for row in source["examples"]
        if row.get("required_case") == "proline_2og"
    ]
    if len(rows) != 3:
        raise RuntimeError(f"expected exactly 3 real proline/2OG rows, got {len(rows)}")

    mapper = RealMapperAdapter(backend="rdkit")
    if not mapper.is_available():
        raise RuntimeError("RDKit diagnostic mapper unavailable; cannot generate H2 evidence")

    cases: list[dict] = []
    for row in sorted(rows, key=lambda item: item["source_id"]):
        report = mapper.map_reaction(NormalizedReactionRecord(
            reaction_id=row["reaction_id"],
            source_record_id=row["source_id"],
            normalized_reaction=row["reaction_smiles"],
            raw_reaction=row["reaction_smiles"],
            direction="forward",
        ))
        disposition = quarantine_unresolved_required_case(row, report)
        formal = report.formal_mapped_source_assignment
        cases.append({
            "source_id": row["source_id"],
            "reaction_id": row["reaction_id"],
            "reaction_smiles": row["reaction_smiles"],
            "legacy_finding": {
                "category": row["category"],
                "reason": row["reason"],
                "legacy_pair": row["legacy_pair"],
                "center_evidence_semantics": row["center_evidence_semantics"],
            },
            "formal_mapping_summary": {
                "mapper_name": report.mapper_name,
                "mapper_version": report.mapper_version,
                "mapping_status": report.mapping_status.value,
                "mapped_heavy_atom_fraction": report.mapped_heavy_atom_fraction,
                "changed_atom_coverage": report.changed_atom_coverage,
                "fallback_method": report.fallback_method,
                "source_assignment_method": report.source_assignment_method.value,
                "mechanistic_atom_origin": None,
                "output_hash": report.output_hash,
                "mapped_atom_pairs": (
                    [pair.model_dump(mode="json") for pair in formal.mapped_atom_pairs]
                    if formal is not None else []
                ),
            },
            "new_pipeline_disposition": disposition.model_dump(mode="json"),
        })

    payload = {
        "evidence_version": "p1-g10-h2-1",
        "source": "reports/data_audit/legacy_lineage_audit.json",
        "source_sha256": _sha256(SOURCE),
        "policy_version": REQUIRED_CASE_POLICY_VERSION,
        "scientific_boundary": (
            "The real rows are present, but the available RDKit MCS output is "
            "formal diagnostic overlap rather than a complete atom map or a "
            "validated multi-lineage resolution. The new pipeline therefore "
            "quarantines all three rows and synthesizes no lineage."
        ),
        "case_count": len(cases),
        "quarantined_count": sum(
            case["new_pipeline_disposition"]["disposition"] == "quarantined"
            for case in cases
        ),
        "production_eligible_count": sum(
            case["new_pipeline_disposition"]["production_eligible"]
            for case in cases
        ),
        "forbidden_lineage_present_count": sum(
            case["new_pipeline_disposition"]["forbidden_lineage_present"]
            for case in cases
        ),
        "resolved_lineage_count": sum(
            len(case["new_pipeline_disposition"]["resolved_lineages"])
            for case in cases
        ),
        "cases": cases,
    }
    payload["evidence_content_hash"] = canonical_hash(payload)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT}")
    print(
        f"cases={payload['case_count']} quarantined={payload['quarantined_count']} "
        f"production={payload['production_eligible_count']} "
        f"forbidden={payload['forbidden_lineage_present_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

