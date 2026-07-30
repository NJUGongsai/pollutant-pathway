#!/usr/bin/env python3
"""Export all top-level Pydantic schemas to JSON Schema files.

Output directory: schemas/json/
Each schema produces a .json file named after the class.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reaction_agent.schemas import (
    MappingReport,
    ReactionParticipant,
    ReactionEvidence,
    LineageResolution,
    SourceReactionLedger,
    CandidateAnalogyLedger,
    TransformationHypothesis,
    SiteHypothesis,
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    Candidate,
    PredictionResult,
    ManualAuditRecord,
)

SCHEMAS = [
    MappingReport,
    ReactionParticipant,
    ReactionEvidence,
    LineageResolution,
    SourceReactionLedger,
    CandidateAnalogyLedger,
    TransformationHypothesis,
    SiteHypothesis,
    ProductionSelectionHypothesis,
    AgentProposedHypothesis,
    Candidate,
    PredictionResult,
    ManualAuditRecord,
]

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "schemas", "json",
)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    exported = []
    for schema_cls in SCHEMAS:
        js = schema_cls.model_json_schema()
        filename = f"{schema_cls.__name__}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w") as f:
            json.dump(js, f, indent=2, ensure_ascii=False)
        exported.append(filename)
        print(f"  exported: {filename}")

    print(f"\nExported {len(exported)} JSON Schemas to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
