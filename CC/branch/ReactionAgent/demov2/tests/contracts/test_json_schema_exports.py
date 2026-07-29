"""JSON Schema export contract tests."""

import json
import os
import pytest
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
)

ALL_SCHEMAS = [
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
]

SCHEMAS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "schemas", "json",
)


@pytest.mark.contract
@pytest.mark.parametrize("s", ALL_SCHEMAS, ids=[x.__name__ for x in ALL_SCHEMAS])
def test_json_schema_exportable(s):
    js = s.model_json_schema()
    assert isinstance(js, dict)
    assert len(json.dumps(js)) > 0


@pytest.mark.contract
@pytest.mark.parametrize("s", ALL_SCHEMAS, ids=[x.__name__ for x in ALL_SCHEMAS])
def test_json_schema_additional_properties_false(s):
    js = s.model_json_schema()
    assert js.get("additionalProperties") is False


@pytest.mark.contract
@pytest.mark.parametrize("s", ALL_SCHEMAS, ids=[x.__name__ for x in ALL_SCHEMAS])
def test_json_schema_has_title(s):
    js = s.model_json_schema()
    assert "title" in js


@pytest.mark.contract
@pytest.mark.parametrize("s", ALL_SCHEMAS, ids=[x.__name__ for x in ALL_SCHEMAS])
def test_json_schema_export_is_fresh(s):
    """Exported JSON must match current model schema."""
    json_path = os.path.join(SCHEMAS_DIR, f"{s.__name__}.json")
    if not os.path.isfile(json_path):
        pytest.fail(f"Missing export: {s.__name__}.json — run export_json_schemas.py")
    with open(json_path) as f:
        exported = json.load(f)
    current = s.model_json_schema()
    exported_props = set(exported.get("properties", {}).keys())
    current_props = set(current.get("properties", {}).keys())
    assert exported_props == current_props, (
        f"{s.__name__}: stale JSON Schema (diff: {exported_props ^ current_props})"
    )
