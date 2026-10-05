#!/usr/bin/env python
"""路二主计算：library_full(4,454, 纯 EAWAG) vs corpus_v1(43,177, rhea+envipath) 覆盖差集。

口径（沿用 CORPUS_LINEAGE 四重验证 + D2 双口径）：
  A. 包级：package 枚举差集（library.package vs corpus parse_note→包名）
  B. 记录级：来源 ID 差集（library btid/reac_id 规范化键 vs corpus record_id 规范化键）
  C. 内容级：配对指纹对撞（精确串 + cn_identity 双口径，donor→product 对）
  D. 全文串扫：血缘标记（复核 EAWAG 纯度）

另附：
  - 差集行退化过滤（CO2 矿化、product==donor、SMILES 不可解析、多组分产物）
  - 差集行 vs 其余证据资产重叠（eawag/donor_product、corpus_templates v1/v2、donor_index）
  - corpus_v1 envipath 侧对 library 的覆盖方向

产物：pool_rescue/eawag_diff_stats.json（池级，无 SMILES，可入仓）
      pool_rescue/intermediates/eawag_diff_rows.tsv（gitignored，行级含 SMILES）
"""
import json
import re
import sys
from collections import defaultdict

sys.path.insert(0, "/Volumes/CC/Enzyme_Agent/dependingv43/src")
from pathway_v43.domain.identity import cn_identity  # noqa: E402
from rdkit import Chem, RDLogger  # noqa: E402

RDLogger.DisableLog("rdApp.*")

REPO = "/Volumes/CC/Enzyme_Agent/dependingv43"
POOL = f"{REPO}/reports/phase_s1_hit60/pool_rescue"
INTER = f"{POOL}/intermediates"

ATOM_MAP_RE = re.compile(r":\d+\]")


def cn_multi(smi):
    """多组分串 → frozenset(cn(每个组分))；None 表示不可解析。"""
    if not smi:
        return None
    parts = [p for p in str(smi).split(".") if p]
    if not parts:
        return None
    out = set()
    for p in parts:
        if Chem.MolFromSmiles(p) is None:
            return None
        c = cn_identity(p)
        if not c:
            return None
        out.add(c)
    return frozenset(out)


def cn_single(smi):
    if not smi:
        return None
    return cn_identity(str(smi))


# ---------- 载入 library_full ----------
lib_rows = []
lib_key = {}          # 规范化记录键 → 行号列表
with open(f"{REPO}/assets/v3_reactions/library/library_full.jsonl") as f:
    for ln, line in enumerate(f, 1):
        r = json.loads(line)
        pkg = r.get("package") or ""
        btid, reac = str(r.get("btid") or ""), str(r.get("reac_id") or "")
        if pkg == "EAWAG-BBD":
            key = f"{btid}#{reac}"
        else:
            key = reac  # SOIL/SEDIMENT/SLUDGE: reac_id = uuid = corpus record_id 后缀
        lib_rows.append({
            "ln": ln, "package": pkg, "btid": btid, "reac_id": reac, "key": key,
            "donor": r.get("donor_smiles"), "product": r.get("product_smiles"),
        })
        lib_key.setdefault(key, []).append(ln)

# ---------- 载入 corpus_v1 envipath ----------
NOTE2PKG = {
    "envipath-eawag-soil": "EAWAG-SOIL",
    "envipath-eawag-sediment": "EAWAG-SEDIMENT",
    "envipath-eawag-sludge": "EAWAG-SLUDGE",
    "envipath-eawag-bbd": "EAWAG-BBD",
    "envipath-educt": "EAWAG-BBD-educt",
}
cor_rows = []
cor_key = {}
with open(f"{REPO}/assets/v3_reactions/corpus_env/corpus_v1.jsonl") as f:
    for ln, line in enumerate(f, 1):
        r = json.loads(line)
        if r.get("source_type") != "envipath":
            continue
        note = r.get("parse_note") or ""
        pkg = NOTE2PKG.get(note, note)
        rid = str(r.get("record_id") or "")
        m = re.match(r"env:EAWAG-(?:SOIL|SEDIMENT|SLUDGE|BBD):(.+)$", rid)
        key = m.group(1) if m else rid
        cor_rows.append({
            "ln": ln, "package": pkg, "key": key,
            "donor": r.get("donor_A_smiles"), "product": r.get("product_B_smiles"),
            "note": note,
        })
        cor_key.setdefault(key, []).append(ln)

stats = {"library": {}, "corpus_envipath": {}, "A_package": {}, "B_record": {},
         "C_pairs": {}, "degeneracy": {}, "overlap_other_assets": {}, "reverse": {}}

# ---------- A. 包级 ----------
lib_pkgs = sorted({r["package"] for r in lib_rows})
cor_pkgs = sorted({r["package"] for r in cor_rows})
stats["library"] = {"rows": len(lib_rows), "packages": lib_pkgs,
                    "by_package": dict(sorted(defaultdict(int, {p: sum(1 for r in lib_rows if r["package"] == p) for p in lib_pkgs}).items()))}
stats["corpus_envipath"] = {"rows": len(cor_rows), "packages": cor_pkgs,
                            "by_package": {p: sum(1 for r in cor_rows if r["package"] == p) for p in cor_pkgs}}
stats["A_package"] = {
    "library_only": sorted(set(lib_pkgs) - set(cor_pkgs)),
    "corpus_only": sorted(set(cor_pkgs) - set(lib_pkgs)),
    "common": sorted(set(lib_pkgs) & set(cor_pkgs)),
}

# ---------- B. 记录级（按包） ----------
for pkg in lib_pkgs:
    lk = {r["key"] for r in lib_rows if r["package"] == pkg}
    ck = {r["key"] for r in cor_rows if r["package"] == pkg}
    stats["B_record"][pkg] = {
        "library_keys": len(lk), "corpus_keys": len(ck),
        "library_minus_corpus": len(lk - ck), "corpus_minus_library": len(ck - lk),
        "intersection": len(lk & ck),
    }

lib_keys_all = {r["key"] for r in lib_rows}
cor_keys_all = {r["key"] for r in cor_rows}
stats["B_record"]["ALL"] = {
    "library_keys": len(lib_keys_all), "corpus_keys": len(cor_keys_all),
    "library_minus_corpus": len(lib_keys_all - cor_keys_all),
    "corpus_minus_library": len(cor_keys_all - lib_keys_all),
    "intersection": len(lib_keys_all & cor_keys_all),
}

# ---------- C. 配对指纹（精确串 + cn 双口径） ----------
def pair_exact(d, p):
    return (str(d or ""), str(p or "")) if p else None

def pair_cn(d, p):
    cd = cn_single(d)
    cp = cn_multi(p)
    if cd is None or cp is None:
        return None
    return (cd, cp)

cor_exact_pairs = set()
cor_cn_pairs = set()
cor_donor_only_cn = set()
for r in cor_rows:
    if r["product"]:
        pe = pair_exact(r["donor"], r["product"])
        if pe:
            cor_exact_pairs.add(pe)
        pc = pair_cn(r["donor"], r["product"])
        if pc:
            cor_cn_pairs.add(pc)
    else:
        c = cn_single(r["donor"])
        if c:
            cor_donor_only_cn.add(c)

diff_rows = []
n_pair_in_corpus_cn = n_pair_in_corpus_exact = 0
n_donor_in_corpus_donoronly = 0
n_key_in_corpus = 0
for r in lib_rows:
    in_corpus_key = r["key"] in cor_keys_all
    pe = pair_exact(r["donor"], r["product"])
    pc = pair_cn(r["donor"], r["product"])
    in_pair_exact = pe in cor_exact_pairs if pe else False
    in_pair_cn = pc in cor_cn_pairs if pc else False
    cd = cn_single(r["donor"])
    donor_in_donoronly = cd in cor_donor_only_cn if cd else False
    if in_corpus_key:
        n_key_in_corpus += 1
    if in_pair_exact:
        n_pair_in_corpus_exact += 1
    if in_pair_cn:
        n_pair_in_corpus_cn += 1
    if donor_in_donoronly:
        n_donor_in_corpus_donoronly += 1
    if not (in_corpus_key or in_pair_cn):
        diff_rows.append({**r, "in_corpus_key": in_corpus_key, "pair_cn": pc,
                          "pair_exact": pe, "donor_in_donoronly": donor_in_donoronly})

stats["C_pairs"] = {
    "note": "library 行四口径命中 corpus 的计数（key=记录ID, pair_exact=精确串对, pair_cn=规范化对, donoronly=仅给体侧 educt 记录）",
    "n_lib_rows": len(lib_rows),
    "n_key_in_corpus": n_key_in_corpus,
    "n_pair_in_corpus_exact": n_pair_in_corpus_exact,
    "n_pair_in_corpus_cn": n_pair_in_corpus_cn,
    "n_lib_donor_in_corpus_educt_donors": n_donor_in_corpus_donoronly,
    "n_diff_rows(key与pair_cn均不在corpus)": len(diff_rows),
}

# ---------- 退化过滤（对差集行） ----------
CO2_CANDIDATES = {"C(=O)=O", "O=C=O", "CO", "C(=O)[O-]", "O=C[O-]", "[O-]C=O"}
def degenerate_flags(row):
    flags = []
    pc = row["pair_cn"]
    if pc is None:
        flags.append("smiles_unparseable")
        return flags, None, None
    cd, cp = pc
    n_comp = len(cp)
    prod_first = next(iter(cp))
    if prod_first in {"C(=O)=O", "O=C=O"}:
        flags.append("product_co2_mineralization")
    if n_comp > 1:
        flags.append("multi_component_product")
    if cd in cp:
        flags.append("product_contains_donor_identity")
    if Chem.MolFromSmiles(row["donor"] or "") is None:
        flags.append("donor_unparseable")
    return flags, cd, cp

deg = defaultdict(int)
usable_rows = []
for row in diff_rows:
    flags, cd, cp = degenerate_flags(row)
    for fl in flags:
        deg[fl] += 1
    row["degenerate_flags"] = flags
    if not flags:
        usable_rows.append(row)
stats["degeneracy"] = {
    "n_diff_rows": len(diff_rows),
    "flags": dict(deg),
    "n_clean_after_degeneracy": len(usable_rows),
}

# ---------- 差集行 vs 其余证据资产 ----------
# eawag/donor_product.jsonl（BBD 给体-产物对）
dp_pairs_exact, dp_pairs_cn = set(), set()
with open(f"{REPO}/assets/v3_reactions/eawag/donor_product.jsonl") as f:
    for line in f:
        r = json.loads(line)
        pe = pair_exact(r.get("donor_smiles"), r.get("product_smiles"))
        if pe:
            dp_pairs_exact.add(pe)
        pc = pair_cn(r.get("donor_smiles"), r.get("product_smiles"))
        if pc:
            dp_pairs_cn.add(pc)

# corpus_templates v1/v2（mapped_lhs→mapped_rhs，剥映射后 cn 对）
def tpl_pair_sets(path):
    ex, cn = set(), set()
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            lhs, rhs = r.get("mapped_lhs"), r.get("mapped_rhs")
            if not (lhs and rhs):
                continue
            lhs_s = ATOM_MAP_RE.sub("]", str(lhs))
            rhs_s = ATOM_MAP_RE.sub("]", str(rhs))
            ex.add((lhs_s, rhs_s))
            pc = pair_cn(lhs_s, rhs_s)
            if pc:
                cn.add(pc)
    return ex, cn

tpl_v1_ex, tpl_v1_cn = tpl_pair_sets(f"{REPO}/assets/analog/corpus_templates_v1.jsonl")
tpl_v2_ex, tpl_v2_cn = tpl_pair_sets(f"{REPO}/assets/analog/corpus_templates_v2.jsonl")

# donor_index 给体分子
di_cn = set()
with open(f"{REPO}/assets/v3_reactions/corpus_env/donor_index.jsonl") as f:
    for line in f:
        r = json.loads(line)
        c = cn_single(r.get("donor_smiles"))
        if c:
            di_cn.add(c)

ov_dp = ov_tpl = ov_tpl2 = ov_dp_ex = ov_di = 0
for row in diff_rows:
    pe, pc = row.get("pair_exact"), row.get("pair_cn")
    if pc and pc in dp_pairs_cn:
        ov_dp += 1
    if pe and pe in dp_pairs_exact:
        ov_dp_ex += 1
    if pc and (pc in tpl_v1_cn):
        ov_tpl += 1
    if pc and (pc in tpl_v2_cn):
        ov_tpl2 += 1
    cd = pc[0] if pc else None
    if cd and cd in di_cn:
        ov_di += 1

stats["overlap_other_assets"] = {
    "note": "差集行（key/pair_cn 均不在 corpus_v1）与其余证据资产的重叠。library_full 自身即 recorded 路由查找库，差集行 100% 与其重叠（结构性，见报告）。",
    "vs_eawag_donor_product_pair_cn": ov_dp,
    "vs_eawag_donor_product_pair_exact": ov_dp_ex,
    "vs_corpus_templates_v1_pair_cn": ov_tpl,
    "vs_corpus_templates_v2_pair_cn": ov_tpl2,
    "vs_donor_index_donor_molecule": ov_di,
}

# ---------- 反方向：corpus envipath 配对在 library 的覆盖 ----------
cor_pairs_total = 0
cor_pairs_in_lib_cn = 0
lib_cn_pairs = {r["pair_cn"] for r in lib_rows if r.get("pair_cn")} if lib_rows and "pair_cn" in lib_rows[0] else set()
# 重新构建（上面 pair_cn 是 diff_rows 上的字段，这里独立算）
lib_cn_pair_set = set()
for r in lib_rows:
    pc = pair_cn(r["donor"], r["product"])
    if pc:
        lib_cn_pair_set.add(pc)
for r in cor_rows:
    if not r["product"]:
        continue
    cor_pairs_total += 1
    pc = pair_cn(r["donor"], r["product"])
    if pc and pc in lib_cn_pair_set:
        cor_pairs_in_lib_cn += 1
stats["reverse"] = {
    "corpus_envipath_pairs_total": cor_pairs_total,
    "in_library_pair_cn": cor_pairs_in_lib_cn,
}

# ---------- 全文串扫（D，EAWAG 纯度复核） ----------
markers = ["ecreact", "evodex", "brenda", "enzymemap", "metanetx", "pathbank"]
scan_hits = {m: 0 for m in markers}
with open(f"{REPO}/assets/v3_reactions/library/library_full.jsonl") as f:
    blob = f.read().lower()
for m in markers:
    scan_hits[m] = blob.count(m)
stats["D_string_scan_library_full"] = scan_hits

# ---------- 输出 ----------
with open(f"{POOL}/eawag_diff_stats.json", "w") as f:
    json.dump(stats, f, ensure_ascii=False, indent=1)

# 行级明细（gitignored，含 SMILES）
with open(f"{INTER}/eawag_diff_rows.tsv", "w") as f:
    f.write("package\tbtid\treac_id\tkey\tdonor_smiles\tproduct_smiles\tdegenerate_flags\tin_donor_product\tin_tpl_v1\tin_tpl_v2\tdonor_in_donor_index\n")
    for row in diff_rows:
        pc, pe = row.get("pair_cn"), row.get("pair_exact")
        f.write("\t".join([
            row["package"], row["btid"], row["reac_id"], row["key"],
            str(row["donor"]), str(row["product"]),
            ",".join(row["degenerate_flags"]),
            "Y" if (pc and pc in dp_pairs_cn) or (pe and pe in dp_pairs_exact) else "",
            "Y" if (pc and pc in tpl_v1_cn) else "",
            "Y" if (pc and pc in tpl_v2_cn) else "",
            "Y" if (pc and pc[0] in di_cn) else "",
        ]) + "\n")

print(json.dumps(stats, ensure_ascii=False, indent=1))
print(f"\nwritten: {POOL}/eawag_diff_stats.json")
print(f"written: {INTER}/eawag_diff_rows.tsv  ({len(diff_rows)} diff rows)")
