#!/usr/bin/env python
"""路一预检：mibPOPdb 中间体/母体 POP 的 SMILES 合法率 + 与我方证据面分子级对撞。

只读本地资产与 mibPOPdb 导出的 TSV；产物落 pool_rescue/（池级统计）与
intermediates/（gitignored，含分子级命中明细）。
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "/Volumes/CC/Enzyme_Agent/dependingv43/src")
from pathway_v43.domain.identity import cn_identity  # noqa: E402
from rdkit import Chem, RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

REPO = "/Volumes/CC/Enzyme_Agent/dependingv43"
POOL = f"{REPO}/reports/phase_s1_hit60/pool_rescue"
INTER = f"{POOL}/intermediates"

# ---------- 1. mibPOPdb TSV 载入 + SMILES 合法率 ----------
def load_tsv(path):
    rows = []
    with open(path) as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            parts = line.rstrip("\n").split("\t")
            while len(parts) < len(header):
                parts.append("")
            rows.append(dict(zip(header, parts)))
    return rows

inter = load_tsv(f"{INTER}/mibpop_intermediates.tsv")   # 593
comps = load_tsv(f"{INTER}/mibpop_compounds.tsv")        # 356

def valid_stats(rows, label):
    n = ok = invalid = empty = 0
    valid_cns = {}
    for r in rows:
        smi = (r.get("smiles") or "").strip()
        if not smi or smi.lower() == "n/a":
            empty += 1
            continue
        n += 1
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            invalid += 1
            continue
        ok += 1
        cn = cn_identity(smi)
        if cn:
            valid_cns.setdefault(cn, []).append(r)
    print(f"[{label}] total={len(rows)} with_smiles={n} rdkit_ok={ok} rdkit_invalid={invalid} empty_or_na={empty} distinct_cn={len(valid_cns)}")
    return valid_cns

inter_cn = valid_stats(inter, "intermediates")
comp_cn = valid_stats(comps, "POP compounds")

# 通路层面
by_path = defaultdict(list)
for r in inter:
    by_path[r["Specifics of degradation"]].append(r)
n_path = len(by_path)
n_path_with_struct = sum(1 for p, rs in by_path.items() if any((r.get("smiles") or "").strip().lower() not in ("", "n/a") for r in rs))
print(f"pathways={n_path}, pathways with >=1 structured intermediate={n_path_with_struct}")

# ---------- 2. 我方证据面（分子级）载入 ----------
def collect_molecules(path, fields):
    exact = set()
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            for fld in fields:
                v = r.get(fld)
                if v:
                    exact.add(str(v))
    return exact

lib_donors = collect_molecules(f"{REPO}/assets/v3_reactions/library/library_full.jsonl", ["donor_smiles"])
lib_products = collect_molecules(f"{REPO}/assets/v3_reactions/library/library_full.jsonl", ["product_smiles"])
corpus_donors = collect_molecules(f"{REPO}/assets/v3_reactions/corpus_env/corpus_v1.jsonl", ["donor_A_smiles"])
corpus_products = collect_molecules(f"{REPO}/assets/v3_reactions/corpus_env/corpus_v1.jsonl", ["product_B_smiles"])
donor_index_mols = collect_molecules(f"{REPO}/assets/v3_reactions/corpus_env/donor_index.jsonl", ["donor_smiles"])

def cn_set(smiles_set):
    out = {}
    for s in smiles_set:
        c = cn_identity(s)
        if c:
            out.setdefault(c, s)
    return out

surfaces = {
    "library_donor": cn_set(lib_donors),
    "library_product": cn_set(lib_products),
    "corpus_donor": cn_set(corpus_donors),
    "corpus_product": cn_set(corpus_products),
    "donor_index": cn_set(donor_index_mols),
}

# corpus_templates v1（剥映射）
import re
ATOM_MAP_RE = re.compile(r":\d+\]")
tpl_pairs = set()
with open(f"{REPO}/assets/analog/corpus_templates_v1.jsonl") as f:
    for line in f:
        r = json.loads(line)
        lhs, rhs = r.get("mapped_lhs"), r.get("mapped_rhs")
        if lhs:
            for s in str(lhs).split("."):
                c = cn_identity(ATOM_MAP_RE.sub("]", s))
                if c:
                    tpl_pairs.add(c)
        if rhs:
            for s in str(rhs).split("."):
                c = cn_identity(ATOM_MAP_RE.sub("]", s))
                if c:
                    tpl_pairs.add(c)
surfaces["corpus_templates_v1"] = {c: c for c in tpl_pairs}

# ---------- 3. 对撞 ----------
def collide(cn_map, label):
    hits = {k: [] for k in surfaces}
    for cn, recs in cn_map.items():
        for name, surf in surfaces.items():
            if cn in surf:
                hits[name].extend(r.get("name") or r.get("Intermediate Name") or "?" for r in recs)
    print(f"\n[{label}] n_distinct_cn={len(cn_map)}")
    for name in surfaces:
        print(f"  vs {name}: {len(hits[name])} hits (dedup molecules: {len(set(hits[name]))})")
    return hits

h_inter = collide(inter_cn, "mibPOPdb intermediates")
h_comp = collide(comp_cn, "mibPOPdb POP compounds")

# ---------- 4. 输出明细（gitignored intermediates/）----------
detail = {
    "intermediate_hits": {name: sorted(set(v)) for name, v in h_inter.items()},
    "compound_hits": {name: sorted(set(v)) for name, v in h_comp.items()},
    "stats": {
        "intermediates_total": len(inter),
        "intermediates_smiles_ok": sum(len(v) for v in inter_cn.values()),
        "compounds_total": len(comps),
        "compounds_smiles_ok": sum(len(v) for v in comp_cn.values()),
        "pathways": n_path,
        "pathways_with_structure": n_path_with_struct,
    },
}
with open(f"{INTER}/mibpop_surface_collision.json", "w") as f:
    json.dump(detail, f, ensure_ascii=False, indent=1)
print(f"\nwritten: {INTER}/mibpop_surface_collision.json")
