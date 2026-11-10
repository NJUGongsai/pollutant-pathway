"""RA-0 donor reaction corpus v1 — build, load, manifest.

One record per reaction / donor molecule:
  {record_id, source_type, source_id, ec, direction, master_id,
   donor_A_smiles, product_B_smiles, reaction_smiles,
   atom_mapping (always null: RHEA subset has no AAM), mapping_status: 'absent',
   donor_components, product_components, provenance_sha256, parse_note}

Environment note (RA-M1 CORRECTION): RHEA's rxn_subset carries NO atom-atom
mapping (0/37,100 RXN; 4/36,444 reaction-smiles). atom_mapping is therefore
`null` and mapping_status is `absent` — never fabricated. Atom mapping is
deferred to RA-2 (RXNMapper offline / RDKit MCS) under separate scope.
"""
import glob
import os
import re

from ra import envipath
from ra import rhea_sources as rs
from ra.chem import canonical_multi_smiles, canonical_reaction
from ra.io import (
    manifest_write,
    read_json_lines,
    sha256_text,
    stable_json_dump,
    stable_json_lines,
)
from ra.io import stable_json_text

_RXN_ID_RE = re.compile(r"([0-9]+)\.rxn$")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def provenance_sha256(body: dict) -> str:
    """Digest over the deterministic canonical JSON body of a record."""
    return sha256_text(stable_json_text(body))


def _join_ec(ec_maps: dict, file_id: str, master: str | None):
    ecs = ec_maps["direct"].get(file_id) or []
    if master and not ecs:
        ecs = ec_maps["master"].get(master) or []
    return ",".join(sorted(ecs)) if ecs else None


def _make_rhea_record(
    file_id: str,
    parsed: dict,
    tsv_rec,
    ec_maps: dict,
    directions: dict,
) -> dict:
    """Build one RHEA corpus record from RXN parse (+ tsv fallback)."""
    dir_info = directions.get(file_id) or {}
    master = dir_info.get("master")

    if parsed["ok"] and parsed["reactant_smiles"] and parsed["product_smiles"]:
        r_comps = parsed["reactant_smiles"]
        p_comps = parsed["product_smiles"]
        rxn_smiles = canonical_reaction(r_comps, p_comps)
        parse_note = "rxn-parsed"
    elif tsv_rec is not None and tsv_rec["parse_error"] is None:
        r_comps = tsv_rec["reactants"]
        p_comps = tsv_rec["products"]
        rxn_smiles = tsv_rec["reaction_smiles"]
        parse_note = "smiles-fallback"
    else:
        r_comps, p_comps, rxn_smiles = [], [], None
        parse_note = "no-structure"

    body = {
        "record_id": f"rhea:{file_id}",
        "source_type": "rhea",
        "source_id": f"rhea:{file_id}",
        "ec": _join_ec(ec_maps, file_id, master),
        "direction": dir_info.get("direction"),
        "master_id": master,
        "donor_A_smiles": canonical_multi_smiles(r_comps) if r_comps else None,
        "product_B_smiles": canonical_multi_smiles(p_comps) if p_comps else None,
        "reaction_smiles": rxn_smiles,
        "atom_mapping": None,
        "mapping_status": "absent",
        "donor_components": sorted(r_comps),
        "product_components": sorted(p_comps),
        "provenance_sha256": None,
        "parse_note": parse_note,
    }
    # digest over the body WITHOUT the digest field itself (self-consistent)
    body["provenance_sha256"] = provenance_sha256(
        {k: v for k, v in body.items() if k != "provenance_sha256"}
    )
    return body


def _make_envipath_record(source_id: str, educt: str, verified: bool) -> dict:
    body = {
        "record_id": f"{source_id}#{sha256_text(educt)[:8]}",
        "source_type": "envipath",
        "source_id": source_id,
        "ec": None,
        "direction": None,
        "master_id": None,
        "donor_A_smiles": educt,
        "product_B_smiles": None,
        "reaction_smiles": None,
        "atom_mapping": None,
        "mapping_status": "absent",
        "donor_components": [educt],
        "product_components": [],
        "provenance_sha256": None,
        "parse_note": "envipath-educt",
    }
    body["provenance_sha256"] = provenance_sha256(
        {k: v for k, v in body.items() if k != "provenance_sha256"}
    )
    return body


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def build_corpus(srcs: dict, out_dir: str) -> dict:
    rxn_dir = srcs["rxn_dir"]
    tsv_path = srcs["reaction_smiles_tsv"]
    ec_path = srcs["rhea2ec_tsv"]
    direc_path = srcs["directions_tsv"]
    env_path = srcs["envipath_json"]

    os.makedirs(out_dir, exist_ok=True)

    tsv_records = rs.load_reaction_smiles_tsv(tsv_path)
    ec_maps = rs.load_rhea2ec(ec_path)
    directions = rs.load_directions(direc_path)
    env_donors, env_failed = envipath.load_envipath_donors(env_path)

    mapping_rxn = rs.scan_mapping_absence(rxn_dir)
    mapping_smiles = rs.scan_smiles_mapping(tsv_path)

    # ---- RHEA records (RXN primary, tsv fallback; tsv-only ids included) ----
    rxn_files = sorted(glob.glob(os.path.join(rxn_dir, "*.rxn")))
    rxn_ids = set()
    parsed_ok = 0
    parse_failed = 0
    rxn_parse_fail_samples: list = []
    rhea_records: list = []

    for f in rxn_files:
        m = _RXN_ID_RE.search(os.path.basename(f))
        if not m:
            continue
        file_id = m.group(1)
        rxn_ids.add(file_id)
        parsed = rs.parse_rxn_file(f)
        if parsed["ok"]:
            parsed_ok += 1
        else:
            parse_failed += 1
            if len(rxn_parse_fail_samples) < 10:
                rxn_parse_fail_samples.append(
                    {"file": os.path.basename(f), "error": parsed["error"]}
                )
        rhea_records.append(
            _make_rhea_record(file_id, parsed, tsv_records.get(file_id), ec_maps, directions)
        )

    # reactions present in the fallback smiles tsv but absent from the RXN dir
    tsv_only_ids = sorted(set(tsv_records) - rxn_ids)
    via_smiles = 0
    for file_id in tsv_only_ids:
        tsv_rec = tsv_records[file_id]
        if tsv_rec["parse_error"] is not None:
            parse_failed += 1
            continue
        via_smiles += 1
        rhea_records.append(
            _make_rhea_record(
                file_id,
                {"ok": False, "error": "no-rxn-file", "reactant_smiles": [], "product_smiles": [], "aam_atoms": 0, "reaction_smiles": None},
                tsv_rec,
                ec_maps,
                directions,
            )
        )

    # ---- enviPath donor records ----
    env_records = [
        _make_envipath_record(d["source_id"], d["educt"], d["verified"]) for d in env_donors
    ]

    all_records = sorted(rhea_records + env_records, key=lambda r: r["record_id"])

    # ---- donor molecule index (retrieval targets) ----
    donor_index: dict = {}
    for rec in all_records:
        for donor_smiles in rec["donor_components"]:
            key = (donor_smiles, rec["record_id"])
            if key not in donor_index:
                donor_index[key] = {
                    "donor_smiles": donor_smiles,
                    "donor_record_id": rec["record_id"],
                    "source_type": rec["source_type"],
                    "source_id": rec["source_id"],
                }
    donor_index_sorted = [donor_index[k] for k in sorted(donor_index)]

    # ---- output ----
    corpus_path = os.path.join(out_dir, "corpus_v1.jsonl")
    donidx_path = os.path.join(out_dir, "donor_index.jsonl")
    broken_path = os.path.join(out_dir, "broken.jsonl")

    stable_json_lines(all_records, corpus_path)
    stable_json_lines(donor_index_sorted, donidx_path)

    broken = [
        {"record_id": rec["record_id"], "parse_note": rec["parse_note"]}
        for rec in all_records
        if rec["parse_note"] == "no-structure"
    ]
    broken += [
        {
            "record_id": f"{f['source_id']}#unparsed",
            "smiles": f["smiles"],
            "error": f["error"],
        }
        for f in env_failed
    ]
    broken_sorted = sorted(broken, key=lambda b: b["record_id"])
    stable_json_lines(broken_sorted, broken_path)

    unique_donors = sorted({e["donor_smiles"] for e in donor_index_sorted})
    stats = {
        "rxn_files_total": len(rxn_files),
        "rxn_parsed_ok": parsed_ok,
        "rxn_parse_failed": parse_failed,
        "rxn_parse_fail_samples": rxn_parse_fail_samples,
        "reactions_via_smiles_fallback": via_smiles,
        "tsv_total_lines": mapping_smiles["smiles_lines"],
        "tsv_only_ids_used": len(tsv_only_ids),
        "envipath_donor_records": len(env_donors),
        "envipath_parse_failed": len(env_failed),
        "records_total": len(all_records),
        "records_rhea": len(rhea_records),
        "records_envipath": len(env_records),
        "records_broken": len(broken_sorted),
        "donor_index_entries": len(donor_index_sorted),
        "donor_index_unique_smiles": len(unique_donors),
        "mapping": {
            "rxn_files": mapping_rxn["files"],
            "rxn_with_aam": mapping_rxn["with_aam"],
            "rxn_aam_atoms": mapping_rxn["aam_atoms"],
            "smiles_lines": mapping_smiles["smiles_lines"],
            "smiles_with_aam": mapping_smiles["smiles_with_aam"],
        },
    }
    stable_json_dump(stats, os.path.join(out_dir, "stats.json"))
    manifest_write(out_dir, ["corpus_v1.jsonl", "donor_index.jsonl", "broken.jsonl", "stats.json"])
    return stats


# --------------------------------------------------------------------------
# loaders
# --------------------------------------------------------------------------

def read_records(path: str):
    return read_json_lines(path)


def load_donor_index(path: str) -> list:
    return list(read_json_lines(path))


def load_stats(path: str) -> dict:
    import json

    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)