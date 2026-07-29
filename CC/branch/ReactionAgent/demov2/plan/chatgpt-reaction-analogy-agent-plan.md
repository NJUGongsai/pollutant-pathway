> **HISTORICAL / NON-AUTHORITATIVE**
> This document is retained for decision history only.
> Current implementation authority: `plan/final_design.md`, `plan/final_plan.md`, `plan/final_discussion.md`.

# ChatGPT Reaction Analogy MCP Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible one-step system that takes only query molecule X, retrieves an adaptive set of complete donor reactions A→B, deterministically generates strict/generalized analogical products, validates a full reaction ledger, and exposes grounded ranked top-K results through MCP to a constrained LLM Agent.

**Architecture:** A versioned reaction evidence snapshot feeds a deterministic reaction-analogy state machine. Scientific computation remains in typed Python components; a small MCP surface exposes high-level, idempotent operations, and the LLM may explain only returned candidate/evidence IDs.

**Tech Stack:** Python 3.12, RDKit, NumPy, Pydantic v2, pytest, JSON Schema 2020-12, MCP Python SDK/FastMCP, optional OpenAI-compatible Agent client.

---

## 0. Scope and execution order

This is a master implementation plan split into independently testable deliveries:

1. **Foundation:** correct reaction roles, fragment lineage, snapshot, leakage-safe benchmark.
2. **Strict kernel:** adaptive retrieval, exact transformation, site enumeration, graph-edit generation and ledger validation.
3. **Generalized/ranking:** exploratory lane, evidence fusion, applicability and abstention.
4. **MCP/Agent:** stable high-level tools and grounded narrative.
5. **Multi-step:** explicitly excluded until one-step acceptance gates pass.

Do not implement generalized generation, MCP, or LLM code before the data-foundation tests pass.

## 1. Target file structure

```text
CC/branch/ReactionAgent/demov2/
├── pyproject.toml
├── reaction_agent/
│   ├── __init__.py
│   ├── schemas.py
│   ├── settings.py
│   ├── chemistry/
│   │   ├── normalize.py
│   │   ├── roles.py
│   │   ├── lineage.py
│   │   ├── transform.py
│   │   ├── sites.py
│   │   ├── generate.py
│   │   └── validate.py
│   ├── evidence/
│   │   ├── store.py
│   │   ├── snapshot.py
│   │   ├── retrieve.py
│   │   └── external.py
│   ├── ranking/
│   │   ├── features.py
│   │   ├── ranker.py
│   │   └── abstention.py
│   ├── service/
│   │   ├── state.py
│   │   ├── predictor.py
│   │   └── manifest.py
│   ├── mcp/
│   │   ├── server.py
│   │   └── resources.py
│   └── agent/
│       ├── policy.py
│       └── reporter.py
├── scripts/
│   ├── build_snapshot.py
│   ├── audit_snapshot.py
│   └── run_benchmark.py
├── tests/
│   ├── fixtures/
│   ├── test_schemas.py
│   ├── test_roles_lineage.py
│   ├── test_snapshot.py
│   ├── test_retrieve.py
│   ├── test_transform_sites.py
│   ├── test_generate_validate.py
│   ├── test_rank_abstain.py
│   ├── test_predictor.py
│   ├── test_mcp_contract.py
│   └── test_agent_grounding.py
└── plan/
    ├── chatgpt-reaction-analogy-agent-design.md
    └── chatgpt-reaction-analogy-agent-plan.md
```

## 2. Global implementation rules

- New code lives under `demov2`; legacy files are read-only until a migration task explicitly names them.
- Every scientific stage returns a typed result or typed failure; never convert exceptions silently to `[]`.
- All candidate structures originate in `chemistry.generate`; Agent/LLM code cannot construct or modify SMILES.
- `ranking_score` is not a probability.
- Snapshot and benchmark inputs are immutable and content-addressed.
- Any source reaction with unresolved A/B lineage is quarantined.
- Benchmark retrieval and scorer references must be train-only.
- Every task ends with focused tests before integration tests.

### Task 1: Bootstrap the isolated demov2 package

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/pyproject.toml`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/__init__.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/settings.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_package.py`

- [ ] **Step 1: Write the package smoke test**

```python
from reaction_agent.settings import Settings


def test_settings_require_explicit_snapshot(tmp_path):
    settings = Settings(snapshot_path=tmp_path / "snapshot.jsonl")
    assert settings.snapshot_path.name == "snapshot.jsonl"
    assert settings.max_donor_molecules == 12
    assert settings.recall_pool_size == 200
```

- [ ] **Step 2: Run the test and verify the package does not yet import**

Run:

```bash
cd CC/branch/ReactionAgent/demov2
python -m pytest tests/test_package.py -q
```

Expected: FAIL with `ModuleNotFoundError: reaction_agent`.

- [ ] **Step 3: Add package metadata and settings**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "reaction-analogy-agent"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "numpy>=2.0",
  "pydantic>=2.8",
  "rdkit>=2025.3",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
mcp = ["mcp>=1.10"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

```python
# reaction_agent/settings.py
from pathlib import Path
from pydantic import BaseModel, Field


class Settings(BaseModel):
    snapshot_path: Path
    recall_pool_size: int = Field(default=200, ge=20, le=5000)
    max_donor_molecules: int = Field(default=12, ge=1, le=100)
    max_candidates: int = Field(default=5, ge=1, le=100)
    include_generalized: bool = True
```

- [ ] **Step 4: Run the smoke test**

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add CC/branch/ReactionAgent/demov2/pyproject.toml \
  CC/branch/ReactionAgent/demov2/reaction_agent \
  CC/branch/ReactionAgent/demov2/tests/test_package.py
git commit -m "build: bootstrap reaction analogy demov2"
```

### Task 2: Define stable domain schemas before algorithms

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/schemas.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_schemas.py`

- [ ] **Step 1: Write schema invariants**

```python
import pytest
from pydantic import ValidationError
from reaction_agent.schemas import Candidate, Decision, PredictionResult


def test_candidate_requires_provenance_and_ledger():
    with pytest.raises(ValidationError):
        Candidate(
            candidate_id="c1",
            tier="strict",
            product_smiles="CCCCCCC=O",
            reaction_site=[7],
            donor_reaction_ids=[],
            evidence_ids=[],
        )


def test_abstention_is_normal_result():
    result = PredictionResult(
        schema_version="1.0",
        run_id="run_1",
        status="abstained",
        canonical_query="C",
        candidates=[],
        decision=Decision(kind="abstained", reason_code="NO_APPLICABLE_SITE"),
        manifest_uri="reactionagent://runs/run_1/manifest",
    )
    assert result.decision.reason_code == "NO_APPLICABLE_SITE"
```

- [ ] **Step 2: Run and verify failure**

Expected: FAIL because `reaction_agent.schemas` does not exist.

- [ ] **Step 3: Implement the schemas**

```python
# reaction_agent/schemas.py
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReactionLedger(StrictModel):
    status: Literal["complete", "partial_reaction", "unbalanced_source"]
    reactants: list[str]
    products: list[str]
    atom_balance: dict[str, int]
    charge_delta: int
    unknown_atom_sources: list[str] = []


class ValidationReport(StrictModel):
    molecule_valid: bool
    reaction_valid: bool
    warnings: list[str] = []


class Candidate(StrictModel):
    candidate_id: str
    tier: Literal["strict", "generalized"]
    product_smiles: str
    reaction_site: list[int]
    transformation_type: list[str]
    edit: dict[str, Any]
    donor_reaction_ids: list[str] = Field(min_length=1)
    ledger: ReactionLedger
    validation: ValidationReport
    applicability: Literal["in_domain", "borderline", "out_of_domain"]
    ranking_score: float
    score_components: dict[str, float]
    evidence_ids: list[str] = Field(min_length=1)
    counterevidence_ids: list[str] = []
    warnings: list[str] = []


class Decision(StrictModel):
    kind: Literal["predicted", "abstained", "partial"]
    reason_code: str | None = None

    @model_validator(mode="after")
    def require_reason_for_abstention(self):
        if self.kind == "abstained" and not self.reason_code:
            raise ValueError("abstention requires reason_code")
        return self


class PredictionResult(StrictModel):
    schema_version: Literal["1.0"]
    run_id: str
    status: Literal["completed", "abstained", "partial", "failed"]
    canonical_query: str
    candidates: list[Candidate]
    decision: Decision
    manifest_uri: str
```

- [ ] **Step 4: Run schema tests**

Expected: `2 passed`.

- [ ] **Step 5: Commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/schemas.py \
  CC/branch/ReactionAgent/demov2/tests/test_schemas.py
git commit -m "feat: define reaction analogy result contracts"
```

### Task 3: Replace independent fragment picking with mapped fragment lineage

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/normalize.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/roles.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/lineage.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_roles_lineage.py`

- [ ] **Step 1: Add the known regression reaction**

```python
from reaction_agent.chemistry.lineage import resolve_primary_lineage


RAW_PROLINE_HYDROXYLATION = (
    "O=C(O)CCC(=O)C(=O)O.O=C(O)[C@@H]1CCCN1.O=O"
    ">>"
    "O=C(O)CCC(=O)O.O=C(O)[C@@H]1C[C@H](O)CN1.O=C=O"
)


def test_primary_lineage_does_not_pair_2og_with_hydroxyproline(
    mapped_proline_hydroxylation,
):
    # The fixture runs the configured atom-mapping adapter on
    # RAW_PROLINE_HYDROXYLATION before the lineage resolver is called.
    result = resolve_primary_lineage(mapped_proline_hydroxylation)
    assert result.substrate_smiles == "O=C(O)[C@@H]1CCCN1"
    assert result.product_smiles == "O=C(O)[C@@H]1C[C@H](O)CN1"
    assert "MCS_FALLBACK" not in result.warnings
```

- [ ] **Step 2: Run and verify failure**

Expected: FAIL because the resolver is absent.

- [ ] **Step 3: Implement normalization and mapped-overlap lineage**

Implementation contract:

```python
# reaction_agent/chemistry/lineage.py
from dataclasses import dataclass
from rdkit import Chem


@dataclass(frozen=True)
class LineageResult:
    substrate_smiles: str
    product_smiles: str
    substrate_fragment: int
    product_fragment: int
    mapped_atom_overlap: int
    warnings: tuple[str, ...]


def _mapped_atom_numbers(mol: Chem.Mol) -> set[int]:
    return {a.GetAtomMapNum() for a in mol.GetAtoms() if a.GetAtomMapNum() > 0}


def resolve_primary_lineage(reaction_smiles: str) -> LineageResult:
    left, right = reaction_smiles.split(">>", 1)
    reactants = [Chem.MolFromSmiles(s) for s in left.split(".")]
    products = [Chem.MolFromSmiles(s) for s in right.split(".")]
    if any(m is None for m in reactants + products):
        raise ValueError("INVALID_REACTION_SMILES")

    pairs: list[tuple[int, int, int, int]] = []
    for ri, rmol in enumerate(reactants):
        rmap = _mapped_atom_numbers(rmol)
        for pi, pmol in enumerate(products):
            overlap = len(rmap & _mapped_atom_numbers(pmol))
            heavy = min(rmol.GetNumHeavyAtoms(), pmol.GetNumHeavyAtoms())
            if overlap:
                pairs.append((overlap, heavy, ri, pi))

    if not pairs:
        raise ValueError("AMBIGUOUS_FRAGMENT_LINEAGE")
    overlap, _heavy, ri, pi = max(pairs)
    return LineageResult(
        substrate_smiles=Chem.MolToSmiles(reactants[ri]),
        product_smiles=Chem.MolToSmiles(products[pi]),
        substrate_fragment=ri,
        product_fragment=pi,
        mapped_atom_overlap=overlap,
        warnings=(),
    )
```

For unmapped source records, call a dedicated mapping adapter first. Do not put MCS fallback inside this resolver.

- [ ] **Step 4: Add tests for spectators, cofactors and ambiguity**

Test that:

- unchanged fragments are spectators;
- a cofactor is retained in the record but not selected as primary substrate;
- two equally supported lineages return `AMBIGUOUS_FRAGMENT_LINEAGE`;
- fragment order permutations yield the same canonical A/B.

- [ ] **Step 5: Run tests**

Expected: all lineage tests pass, including the known false-pair regression.

- [ ] **Step 6: Commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/chemistry \
  CC/branch/ReactionAgent/demov2/tests/test_roles_lineage.py
git commit -m "fix: resolve donor products by atom lineage"
```

### Task 4: Build a versioned evidence snapshot with quarantine

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/evidence/store.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/evidence/snapshot.py`
- Create: `CC/branch/ReactionAgent/demov2/scripts/build_snapshot.py`
- Create: `CC/branch/ReactionAgent/demov2/scripts/audit_snapshot.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_snapshot.py`

- [ ] **Step 1: Write snapshot determinism tests**

```python
from reaction_agent.evidence.snapshot import build_snapshot


def test_snapshot_id_is_content_addressed(tmp_path, mapped_records):
    first = build_snapshot(mapped_records, tmp_path / "a")
    second = build_snapshot(reversed(mapped_records), tmp_path / "b")
    assert first.snapshot_id == second.snapshot_id
    assert first.accepted_count + first.quarantined_count == len(mapped_records)
```

- [ ] **Step 2: Implement immutable JSONL records and manifest**

The manifest must contain:

```python
{
    "snapshot_id": "sha256:<digest>",
    "schema_version": "1.0",
    "source_versions": {...},
    "rdkit_version": "...",
    "mapping_version": "...",
    "accepted_count": 0,
    "quarantined_count": 0,
    "quarantine_reasons": {...},
    "content_sha256": "...",
}
```

Sort accepted records by stable `reaction_id` before hashing/writing. Quarantine records with invalid mapping, ambiguous lineage or empty transformation.

- [ ] **Step 3: Add audit output**

`audit_snapshot.py` must report:

```text
raw records
accepted
quarantined by reason
role distribution
mapping coverage
complete/partial/unbalanced
multi-product reactions
duplicate reaction identities
manual-audit sample IDs
```

- [ ] **Step 4: Run tests and a small snapshot smoke build**

Expected: stable snapshot ID across input order and an explicit quarantine file.

- [ ] **Step 5: Commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/evidence \
  CC/branch/ReactionAgent/demov2/scripts/build_snapshot.py \
  CC/branch/ReactionAgent/demov2/scripts/audit_snapshot.py \
  CC/branch/ReactionAgent/demov2/tests/test_snapshot.py
git commit -m "feat: build versioned reaction evidence snapshots"
```

### Task 5: Implement adaptive donor-molecule retrieval

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/evidence/retrieve.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_retrieve.py`

- [ ] **Step 1: Define retrieval behavior**

```python
from reaction_agent.evidence.retrieve import AdaptiveRetriever


def test_retrieval_returns_distinct_donor_molecules(snapshot_store):
    result = AdaptiveRetriever(snapshot_store).retrieve("CCCCCCCCO", max_donors=6)
    donor_keys = [d.donor_molecule_key for d in result.donors]
    assert len(donor_keys) == len(set(donor_keys))
    assert all(d.reaction_ids for d in result.donors)
    assert result.donors == sorted(
        result.donors, key=lambda d: (-d.selection_score, d.donor_molecule_key)
    )
```

- [ ] **Step 2: Implement two-stage retrieval**

Use Morgan similarity for the broad pool, then deterministic MMR:

```python
selection_score = (
    0.45 * global_similarity
    + 0.20 * scaffold_similarity
    + 0.20 * functional_group_coverage
    + 0.10 * local_environment_similarity
    + 0.05 * record_quality
    - 0.20 * redundancy_to_selected
)
```

Keep every component in the returned record. These weights are baseline ranking weights, not calibrated probabilities.

- [ ] **Step 3: Add metamorphic tests**

Assert retrieval is invariant to:

- input atom ordering;
- snapshot record ordering;
- duplicate reaction rows;
- fragment ordering after canonicalization.

- [ ] **Step 4: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/evidence/retrieve.py \
  CC/branch/ReactionAgent/demov2/tests/test_retrieve.py
git commit -m "feat: retrieve adaptive diverse donor sets"
```

### Task 6: Extract strict and generalized transformation hypotheses

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/transform.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_transform_sites.py`

- [ ] **Step 1: Write an alcohol-oxidation transform test**

```python
from reaction_agent.chemistry.transform import extract_transform


def test_extract_strict_alcohol_oxidation(mapped_ethanol_reaction):
    transform = extract_transform(mapped_ethanol_reaction)
    assert transform.tier == "strict"
    assert transform.bond_changes == [
        {"a_map": 1, "b_map": 2, "from": 1.0, "to": 2.0}
    ]
    assert transform.preconditions
    assert transform.atom_sources == {}
```

- [ ] **Step 2: Implement complete edit extraction**

The strict transform must include:

```python
class TransformHypothesis:
    transform_id: str
    tier: Literal["strict", "generalized"]
    reaction_types: tuple[str, ...]
    changed_atom_maps: tuple[int, ...]
    bond_changes: tuple[BondChange, ...]
    atom_additions: tuple[AtomTransfer, ...]
    atom_deletions: tuple[AtomTransfer, ...]
    charge_changes: tuple[ChargeChange, ...]
    stereo_changes: tuple[StereoChange, ...]
    preconditions: tuple[AtomEnvironmentConstraint, ...]
    donor_center_fingerprint: bytes
    relaxed_constraints: tuple[str, ...]
    source_reaction_ids: tuple[str, ...]
```

Never use legacy `EditScript.key()` as this identity. Hash the canonical full transform representation.

- [ ] **Step 3: Derive generalized transforms explicitly**

Generalization may relax only named fields:

```text
radius_2_to_radius_1
substituent_identity_to_element_class
ring_membership
stereo_unspecified
```

It may not relax changed atom elements, required bond existence or edit direction in v1.

- [ ] **Step 4: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/transform.py \
  CC/branch/ReactionAgent/demov2/tests/test_transform_sites.py
git commit -m "feat: extract auditable transformation hypotheses"
```

### Task 7: Enumerate transformation-conditioned sites and generate products

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/sites.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/generate.py`
- Modify: `CC/branch/ReactionAgent/demov2/tests/test_transform_sites.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_generate_validate.py`

- [ ] **Step 1: Test strict transfer to octanol**

```python
from reaction_agent.chemistry.sites import enumerate_sites
from reaction_agent.chemistry.generate import apply_transform


def test_ethanol_oxidation_transfers_to_terminal_octanol(alcohol_transform):
    sites = enumerate_sites("CCCCCCCCO", alcohol_transform)
    products = [apply_transform("CCCCCCCCO", alcohol_transform, s) for s in sites]
    assert "CCCCCCC=O" in {p.product_smiles for p in products if p.valid}
```

- [ ] **Step 2: Implement conditioned site matching**

For each precondition:

1. compile an RDKit query;
2. find all X matches;
3. canonicalize symmetry-equivalent matches;
4. compute local similarity to the donor center;
5. return site records with matched query-to-X mapping.

Do not enumerate atoms without a transform.

- [ ] **Step 3: Implement graph-edit replay**

Apply operations in this order:

```text
validate preconditions
→ remove/change bonds
→ add mapped/source atoms
→ add bonds
→ apply charge changes
→ apply stereo policy
→ sanitize
→ canonicalize
```

Return typed failure codes such as `PRECONDITION_MISMATCH`, `VALENCE_ERROR`, `SANITIZE_ERROR`; never return bare `None`.

- [ ] **Step 4: Add invalid and symmetry tests**

Test:

- no alcohol site returns `NO_APPLICABLE_SITE`;
- equivalent sites do not duplicate canonical products;
- invalid valence is rejected with a typed failure;
- the LLM/Agent package has no import path to graph-edit internals.

- [ ] **Step 5: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/sites.py \
  CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/generate.py \
  CC/branch/ReactionAgent/demov2/tests
git commit -m "feat: generate products from conditioned graph edits"
```

### Task 8: Validate products and build reaction ledgers

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/validate.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_generate_validate.py`

- [ ] **Step 1: Write ledger tests**

```python
from reaction_agent.chemistry.validate import validate_candidate


def test_candidate_preserves_donor_atom_source_ledger(octanal_candidate):
    report = validate_candidate(octanal_candidate)
    assert report.molecule_valid
    assert report.ledger.status in {"complete", "partial_reaction"}
    assert report.ledger.unknown_atom_sources == []


def test_unbalanced_source_is_warning_not_silent_success(unbalanced_candidate):
    report = validate_candidate(unbalanced_candidate)
    assert report.ledger.status == "unbalanced_source"
    assert "SOURCE_REACTION_UNBALANCED" in report.warnings
```

- [ ] **Step 2: Implement molecule and reaction validation**

Molecule validation must report parse, sanitize, valence, aromaticity, fragments, charge and stereo. Reaction validation must compute element counts across the complete donor-derived ledger and track every transferred atom source.

- [ ] **Step 3: Add policy tests**

Test the configured policies for:

- salts/fragments;
- tautomer identity;
- unspecified stereo;
- multiple products;
- atom additions from O2/H2O/co-substrates.

- [ ] **Step 4: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/chemistry/validate.py \
  CC/branch/ReactionAgent/demov2/tests/test_generate_validate.py
git commit -m "feat: validate candidate molecules and reaction ledgers"
```

### Task 9: Rank within tiers and implement explicit abstention

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/ranking/features.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/ranking/ranker.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/ranking/abstention.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_rank_abstain.py`

- [ ] **Step 1: Test tier ordering and score transparency**

```python
from reaction_agent.ranking.ranker import rank_candidates


def test_strict_candidates_rank_before_generalized(strict_candidate, generalized_candidate):
    ranked = rank_candidates([generalized_candidate, strict_candidate])
    assert ranked[0].tier == "strict"
    assert set(ranked[0].score_components) >= {
        "global_similarity",
        "local_similarity",
        "mapping_quality",
        "ledger_completeness",
        "support_consensus",
    }
```

- [ ] **Step 2: Implement deterministic v1 ranking**

Use separate tier weights. Normalize features only from train data. Persist weight version in the manifest. Do not compare raw strict and generalized scores across tiers.

- [ ] **Step 3: Implement abstention reason precedence**

```python
REASON_PRECEDENCE = [
    "INVALID_QUERY",
    "NO_DONOR_IN_DOMAIN",
    "NO_VALID_REACTION_RECORD",
    "AMBIGUOUS_FRAGMENT_LINEAGE",
    "NO_APPLICABLE_SITE",
    "ALL_CANDIDATES_INVALID",
    "ONLY_OUT_OF_DOMAIN_GENERALIZATIONS",
    "CONFLICTING_EVIDENCE",
    "INSUFFICIENT_EVIDENCE",
]
```

An empty reliable lane with generalized hypotheses returns `partial` unless generalized output is disabled; it never returns biological “no reaction”.

- [ ] **Step 4: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/ranking \
  CC/branch/ReactionAgent/demov2/tests/test_rank_abstain.py
git commit -m "feat: add tiered ranking and explicit abstention"
```

### Task 10: Assemble the deterministic one-step predictor and immutable manifest

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/service/state.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/service/manifest.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/service/predictor.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_predictor.py`

- [ ] **Step 1: Write the end-to-end deterministic test**

```python
from reaction_agent.service.predictor import ReactionAnalogyPredictor


def test_predictor_returns_grounded_ranked_candidates(test_snapshot):
    predictor = ReactionAnalogyPredictor.from_snapshot(test_snapshot)
    result = predictor.predict("CCCCCCCCO", max_candidates=5)
    assert result.status in {"completed", "partial"}
    assert all(c.donor_reaction_ids for c in result.candidates)
    assert all(c.evidence_ids for c in result.candidates)
    assert result.manifest_uri.endswith("/manifest")
```

- [ ] **Step 2: Implement the explicit state machine**

Use an enum for the states listed in the design. Every transition writes an event containing:

```text
run_id
state
input_hash
output_hash
started_at
duration_ms
warning_codes
failure_code
component_version
```

- [ ] **Step 3: Freeze the run manifest**

The manifest includes canonical query, snapshot ID, code commit, RDKit version, transform/ranker versions, parameters, seed, candidate IDs and event hashes.

- [ ] **Step 4: Add chaos tests**

Test missing snapshot, corrupt index, mapping timeout and external-evidence timeout. None may be translated into `NO_APPLICABLE_SITE`.

- [ ] **Step 5: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/service \
  CC/branch/ReactionAgent/demov2/tests/test_predictor.py
git commit -m "feat: assemble deterministic one-step predictor"
```

### Task 11: Rebuild leakage-safe evaluation before trusting metrics

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/evaluation/splits.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/evaluation/metrics.py`
- Create: `CC/branch/ReactionAgent/demov2/scripts/run_benchmark.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_evaluation.py`

- [ ] **Step 1: Test evidence isolation**

```python
def test_test_reactions_never_enter_retrieval_or_ranking_evidence(split, evaluator):
    evaluator.run(split)
    forbidden = set(split.test_reaction_ids)
    assert not (forbidden & evaluator.observed_reference_reaction_ids)
```

- [ ] **Step 2: Implement grouped splits**

Provide:

```text
random_sanity
query_scaffold
atom_mapped_transform_family
exact_x_isolation
source_database
time_split
```

Build the evidence index separately for every fold. Do not build one global enzyme/reaction reference cache.

- [ ] **Step 3: Implement stage metrics**

Report:

```text
data role/lineage accuracy
donor recall@K and diversity
transform exact match
site recall@K
generation recall
validity and ledger completeness
product top-K/MRR/nDCG
strict/generalized results separately
abstention reasons and risk–coverage
OOD performance
Agent grounding metrics later
```

- [ ] **Step 4: Add baselines**

Run:

- legacy Morgan top-1;
- legacy Morgan top-5 + template;
- adaptive donor + strict kernel;
- adaptive donor + strict/generalized;
- generation order;
- random ranking;
- DRFP as one feature and without DRFP.

- [ ] **Step 5: Run smoke and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/evaluation \
  CC/branch/ReactionAgent/demov2/scripts/run_benchmark.py \
  CC/branch/ReactionAgent/demov2/tests/test_evaluation.py
git commit -m "test: add leakage-safe analogy benchmark"
```

### Task 12: Expose the validated predictor through a small MCP surface

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/mcp/server.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/mcp/resources.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_mcp_contract.py`

- [ ] **Step 1: Write contract tests**

```python
def test_predict_tool_returns_structured_content(mcp_client):
    response = mcp_client.call_tool(
        "reaction.predict_analogical_products_v1",
        {
            "query": {"structure": "CCCCCCCCO", "format": "smiles"},
            "mode": "database_augmented",
            "max_candidates": 5,
            "include_generalized": True,
            "stereochemistry_policy": "preserve_when_defined",
        },
    )
    payload = response.structuredContent
    assert payload["schema_version"] == "1.0"
    assert payload["run_id"]
    assert payload["manifest_uri"].startswith("reactionagent://runs/")
```

- [ ] **Step 2: Implement four production tools**

Expose:

```text
reaction.predict_analogical_products_v1
reaction.get_run_v1
reaction.get_candidate_evidence_v1
reaction.expand_external_evidence_v1
```

Set tool annotations to read-only, non-destructive and idempotent. Use strict input/output schemas with unknown fields rejected.

- [ ] **Step 3: Implement resource URIs**

```text
reactionagent://runs/{run_id}/manifest
reactionagent://runs/{run_id}/evidence/{evidence_id}
reactionagent://datasets/{snapshot_id}
```

- [ ] **Step 4: Test error semantics**

Protocol/validation errors are errors. `status=abstained` is a successful tool result. Dependency timeouts return typed retriable failures and never become abstention.

- [ ] **Step 5: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/mcp \
  CC/branch/ReactionAgent/demov2/tests/test_mcp_contract.py
git commit -m "feat: expose reaction prediction through MCP"
```

### Task 13: Add the constrained LLM Agent and grounding guard

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/agent/policy.py`
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/agent/reporter.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_agent_grounding.py`

- [ ] **Step 1: Write the no-invention test**

```python
def test_reporter_rejects_unknown_candidate_ids(reporter, completed_run):
    draft = {
        "run_id": completed_run.run_id,
        "candidate_ids": ["invented_candidate"],
        "summary": "A new product",
        "caveats": [],
    }
    result = reporter.validate_draft(draft, completed_run)
    assert result.valid is False
    assert result.reason == "UNKNOWN_CANDIDATE_ID"
```

- [ ] **Step 2: Implement the Agent policy**

The Agent may call the four production MCP tools. Its final structured draft is limited to:

```json
{
  "run_id": "run_...",
  "status": "completed",
  "candidate_ids": ["candidate_1"],
  "summary": "...",
  "caveats": ["..."]
}
```

It cannot return product SMILES, scores or evidence facts outside tool results. The host renders product structures, rankings and key evidence directly from `PredictionResult`.

- [ ] **Step 3: Add adversarial grounding tests**

Test prompts that ask the Agent to:

- invent a product;
- override an invalid candidate;
- call ranking score probability;
- invent a donor or citation;
- ignore abstention.

Expected: host rejects or replaces the draft with a deterministic report.

- [ ] **Step 4: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/agent \
  CC/branch/ReactionAgent/demov2/tests/test_agent_grounding.py
git commit -m "feat: add grounded MCP conversation agent"
```

### Task 14: Add optional external evidence without destabilizing the snapshot

**Files:**
- Create: `CC/branch/ReactionAgent/demov2/reaction_agent/evidence/external.py`
- Test: `CC/branch/ReactionAgent/demov2/tests/test_external_evidence.py`

- [ ] **Step 1: Test separation**

```python
def test_external_evidence_does_not_mutate_primary_ranking(predictor, external_adapter):
    before = predictor.predict("CCCCCCCCO")
    extra = external_adapter.retrieve(before.canonical_query)
    after = predictor.get_run(before.run_id)
    assert [c.candidate_id for c in before.candidates] == [
        c.candidate_id for c in after.candidates
    ]
    assert extra.namespace == "external_evidence"
```

- [ ] **Step 2: Implement provenance-only adapters**

Each adapter returns source URL/ID, retrieval time, raw payload hash, normalized reaction and quality warnings. New records cannot enter the primary index until the next snapshot build.

- [ ] **Step 3: Add timeout and prompt-injection tests**

External text remains untrusted data. Strip/escape instructions and store it as evidence content, never as Agent instructions.

- [ ] **Step 4: Run tests and commit**

```bash
git add CC/branch/ReactionAgent/demov2/reaction_agent/evidence/external.py \
  CC/branch/ReactionAgent/demov2/tests/test_external_evidence.py
git commit -m "feat: add isolated external reaction evidence"
```

## 3. Acceptance sequence

Run in this order:

```bash
cd CC/branch/ReactionAgent/demov2
python -m pytest tests/test_roles_lineage.py -q
python -m pytest tests/test_snapshot.py tests/test_evaluation.py -q
python -m pytest tests/test_transform_sites.py tests/test_generate_validate.py -q
python -m pytest tests/test_rank_abstain.py tests/test_predictor.py -q
python -m pytest tests/test_mcp_contract.py tests/test_agent_grounding.py -q
python -m pytest -q
```

Do not start MCP/Agent work unless the first four command groups pass.

## 4. Required reports

Before declaring demov2 usable, produce:

```text
demov2/reports/data_audit.md
demov2/reports/snapshot_manifest.json
demov2/reports/baseline_comparison.md
demov2/reports/leakage_audit.md
demov2/reports/strict_vs_generalized.md
demov2/reports/risk_coverage.md
demov2/reports/mcp_agent_grounding.md
```

Each report includes the snapshot ID, code commit, dependency versions and exact command.

## 5. Explicit stop conditions

Stop and repair the foundation if:

- manual A/B lineage accuracy is below the agreed quality gate;
- scorer/reference evidence contains test reactions;
- strict generator produces untraceable products;
- source reactions cannot account for transferred atoms;
- equivalent input SMILES change the canonical candidate set;
- the Agent can surface a structure or evidence ID absent from the run;
- an infrastructure failure is reported as “no reliable candidate”.

## 6. Out of scope for this plan

- biological activity probability;
- enzyme–substrate compatibility prediction;
- environmental occurrence probability;
- kinetic values;
- default multi-step pathway generation;
- unrestricted LLM-generated SMILES;
- LLM voting as chemical verification.

Multi-step development receives a separate design and implementation plan only after the one-step acceptance gates pass.
