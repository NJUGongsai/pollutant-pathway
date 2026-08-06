"""P3 preflight: capability inventory + evidence inventory (honest)."""
from __future__ import annotations

import platform
import sys

from reaction_agent.p3.capability import (
    probe_automatic_donor,
    probe_chemistry_backend,
    probe_explicit_map_validator,
    probe_mcs_diagnostic,
    probe_real_snapshot,
    probe_strict_atom_mapper,
)
from reaction_agent.p3.fixtures import build_train_view, load_fixture_reactions


def run_p3_preflight(snapshot_path: str | None = None) -> dict:
    """Return a machine-readable preflight report."""
    chemistry = probe_chemistry_backend()
    explicit_validator = probe_explicit_map_validator()
    strict_mapper = probe_strict_atom_mapper()
    mcs_diag = probe_mcs_diagnostic()
    snapshot = probe_real_snapshot(snapshot_path)
    donor = probe_automatic_donor(snapshot.state.value == "available")

    fixture_reactions = load_fixture_reactions()
    train_view = build_train_view(fixture_reactions)

    return {
        "preflight_version": "p3-1",
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "package": "reaction-analogy-agent",
        },
        "capabilities": {
            "chemistry_backend": {
                "state": chemistry.state.value,
                "version": chemistry.version,
            },
            "explicit_map_validator": {
                "state": explicit_validator.state.value,
                "version": explicit_validator.version,
            },
            "strict_atom_mapper": {
                "state": strict_mapper.state.value,
                "detail": strict_mapper.detail,
            },
            "mcs_diagnostic": {
                "state": mcs_diag.state.value,
                "detail": mcs_diag.detail,
            },
            "real_snapshot": {
                "state": snapshot.state.value,
                "detail": snapshot.detail,
            },
            "automatic_donor": {
                "state": donor.state.value,
                "detail": donor.detail,
            },
        },
        "evidence_inventory": {
            "real_snapshot_path": snapshot_path,
            "real_snapshot_available": snapshot.state.value == "available",
            "synthetic_fixture_reactions": sorted(fixture_reactions.keys()),
            "synthetic_fixture_donors": [
                {
                    "donor_id": d.donor_id,
                    "reactions": [r.reaction_id for r in d.reaction_refs],
                    "eligibility": d.donor_eligibility,
                    "molecule": d.structural_smiles,
                }
                for d in train_view.donors
            ],
            "note": (
                "fixture evidence is synthetic_fixture and can only verify "
                "machinery; it cannot satisfy real-evidence Gate items"
            ),
        },
        "real_evidence_gate_status": (
            "BLOCKED" if not (snapshot.state.value == "available" and
                              donor.state.value == "available")
            else "READY"
        ),
    }
