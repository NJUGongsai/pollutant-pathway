"""S5b recorded 精确源适配 —— 原生库记录 → PPV1 池候选(W2;契约登记
s5b-recorded-source-1;零模型、零网络)。

复用既有公共接口(不越层抓 engine 私有对象):
- ``V43Engine.expand_raw``(内含 eawag lookup:CN 键命中,单反应首产品行
  + ion/cofactor 过滤声明)—— 检索通道;
- ``engine.identity_block``(library_path/library_sha256:已授权且哈希
  校验的 corpus 身份)—— **源 hash 校验后**逐行回读原生记录;
- ``recorded_eligibility_reasons``(domain/policy,recorded 卡完整资格
  判据)—— 与 legacy 同一事实源;
- ``s5b_compiler.compile_donor_template``(W1 共同编译器,单一构建源)。

与旧卡口径的关键差异(任务书 W2 逐条):

- 旧 "exact" 卡是**电荷归一立体盲 CN** 查询命中且回填 current、
  mapping unavailable —— 卡名 "exact" ≠ PPV1 strict。本模块分层:
  * ``recorded_strict_exact``:原生记录 donor 的**严格结构身份**
    (canonical 含电荷/立体)== 当前底物严格身份,方向 donor→products,
    完整净产物集合(同 (btid, reac_id) 的**全部**库行,不是引擎 lookup
    去重后的首产品行),编译产物与记录逐组分 strict 核对一致;
  * ``recorded_cn_candidate``:CN 命中但严格身份不同(电荷/立体/拼写)
    —— 不升格 strict exact;按 analog 级候选入池(标注分层);
  * ``analog_transfer``:另一底物/相似通道(analog_source,不属本模块)。
- **一个原反应多产品构成同一事件**(候选事件);不同原反应是备选事件,
  不拼共同产物;
- 过滤声明(ion/cofactor filtered)如实透传;过滤过的单产品卡不冒充
  完整 record(完整集合按库回读);
- 无原生映射 ⇒ 确定性结构对应**推断映射**(枚举预算/歧义披露;标
  ``mapping_origin=inferred``,不是原生/机制证据);图差约束:元素
  对应、旧原子保全、离去组分、新原子来源、完整 target(不任意首
  MCS/补原子/删旁群 —— 对应 = 元素标记 any-bond 子结构同构枚举,
  多解同目标合并、异目标歧义拒);
- 无法编译留 ``unsupported`` + 源诊断(不假装 AtomTool 执行成功);
  所有获许可事件仍走共同公共链(prepare→AtomTool→donor→audit→
  admission→store),不直接插事件行。

负控(任务书 W2):源 hash 篡改(库文件 sha ≠ identity 记录)拒;
CN 同而电荷/手性不同 ⇒ recorded_cn_candidate(不 strict);方向反/另
一底物 ⇒ 不属 exact;filtered 单产品行冒完整 ⇒ 完整集合核对拒;
缺产品/来源 ⇒ 结构化拒;映射枚举触顶 ⇒ 歧义披露拒。
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache

from rdkit import Chem, RDLogger

from ..domain.identity import cn_identity
from .chemstate import strict_identity_of
from .s5b_compiler import S5bCompileError, compile_donor_template

RDLogger.DisableLog("rdApp.*")

RECORDED_SOURCE_VERSION = "s5b-recorded-source-1"

# 推断映射的子结构同构枚举上限(触顶 ⇒ 歧义披露拒绝,不静默取首解)
_INFER_MATCH_LIMIT = 200

# 每进程库索引缓存(1.4MB 文本;hash 锚定后复用)
_LIBRARY_CACHE: dict = {}


class RecordedSourceError(RuntimeError):
    """recorded 源契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 库回读


def _library_identity(engine) -> dict:
    block = engine.identity_block or {}
    path = str(block.get("library_path") or "")
    sha = str(block.get("library_sha256") or "")
    if not path or not sha:
        raise RecordedSourceError(
            "引擎身份块缺 library 路径/哈希(recorded 源需要授权且哈希"
            "校验的 corpus 身份;不猜)", {
                "kind": "library_identity_missing"})
    return {"library_path": path, "library_sha256": sha}


def load_library_index(engine) -> dict:
    """逐行回读原生库(按 (btid, reac_id) 全产品分组;hash 校验)。

    返回 {reaction_key "btid#reac_id": {donor_smiles, package, products:
    [product_smiles 原样(库行序)]}};库文件实际 sha256 ≠ 引擎身份记录
    ⇒ 拒(源 hash 篡改负控)。进程内 lru 缓存(同一 engine 身份复用)。
    """
    identity = _library_identity(engine)
    cache_key = (identity["library_path"], identity["library_sha256"])
    if cache_key in _LIBRARY_CACHE:
        return _LIBRARY_CACHE[cache_key]
    actual = hashlib.sha256(
        open(identity["library_path"], "rb").read()).hexdigest()
    if actual != identity["library_sha256"]:
        raise RecordedSourceError(
            "库文件哈希与引擎身份记录不符(源 hash 篡改/漂移;授权 corpus"
            " 校验失败,fail-closed 不消费)", {
                "kind": "library_hash_mismatch",
                "library_path": identity["library_path"],
                "expected_sha256": identity["library_sha256"],
                "actual_sha256": actual})
    index: dict[str, dict] = {}
    with open(identity["library_path"], encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not text:
                continue
            record = json.loads(text)
            rid = f"{record.get('btid', '')}#{record.get('reac_id', '')}"
            entry = index.setdefault(rid, {
                "donor_smiles": str(record.get("donor_smiles") or ""),
                "donor_id": str(record.get("donor_id") or ""),
                "package": str(record.get("package") or ""),
                "products": []})
            if not entry["donor_smiles"]:
                entry["donor_smiles"] = str(
                    record.get("donor_smiles") or "")
            product = str(record.get("product_smiles") or "")
            if product and product not in entry["products"]:
                entry["products"].append(product)
    _LIBRARY_CACHE[cache_key] = index
    return index


def reset_library_cache() -> None:
    """测试钩子:清库索引缓存。"""
    _LIBRARY_CACHE.clear()


# ---------------------------------------------------------------- 推断映射


def _any_bond_query(mol):
    """元素标记 + any-bond 查询(结构对应:元素对应约束,键级不约束)。"""
    params = Chem.AdjustQueryParameters.NoAdjustments()
    params.makeBondsGeneric = True
    return Chem.AdjustQueryProperties(Chem.Mol(mol), params)


def _mapped_copy(mol, map_of_idx: dict) -> str:
    """按 idx→map 号写原子映射号的 SMILES(确定性)。"""
    out = Chem.Mol(mol)
    for idx, map_no in map_of_idx.items():
        out.GetAtomWithIdx(idx).SetAtomMapNum(int(map_no))
    return Chem.MolToSmiles(out)


def infer_reaction_mapping(
    donor_smiles: str, product_smiles: list[str],
) -> list[dict]:
    """确定性结构对应(元素标记 any-bond 子结构同构;W2)。

    两个互斥策略(按原子数;连通 donor 不能直接子结构匹配到断开的
    多组分产物并集 —— 产物并集按组分分离匹配):
    - ``n_union <= n_donor``(裂解/离去):逐产物组分在 donor 内枚举
      any-bond 同构,组分间 donor 原子不相交的组合为候选映射;
      未覆盖 donor 原子 = 离去组分;
    - ``n_donor < n_union``(加成/生成):donor(连通)在某单一产物
      组分内枚举同构;未覆盖 union 原子 = 新原子(新原子不可达锚点
      时由编译器诚实拒);
    每个候选 {donor_to_union: {donor_idx: union_idx}, new_union,
    removed_donor, truncated}。约束:元素对应(查询元素标记);不任意
    补原子/删旁群(仅同构像);枚举触顶 ⇒ truncated(调用方拒)。
    """
    donor = Chem.MolFromSmiles(donor_smiles or "")
    if donor is None:
        raise RecordedSourceError(
            f"库记录 donor 不可解析:{donor_smiles!r}",
            {"kind": "record_donor_unparseable"})
    union = Chem.MolFromSmiles(".".join(product_smiles))
    if union is None:
        raise RecordedSourceError(
            "库记录产物并集不可解析(fail-closed,不猜)",
            {"kind": "record_products_unparseable"})
    n_donor, n_union = donor.GetNumAtoms(), union.GetNumAtoms()
    mappings: list[dict] = []
    truncated = False
    if n_union <= n_donor:
        # ---- 裂解/离去:产物组分 ⊆ donor(组分分离不相交组合) ----
        comps = Chem.GetMolFrags(union, asMols=True, sanitizeFrags=True)
        offsets: list[int] = []
        offset = 0
        comp_matches: list[list[tuple]] = []
        for comp in comps:
            offsets.append(offset)
            offset += comp.GetNumAtoms()
            query = _any_bond_query(comp)
            ms = donor.GetSubstructMatches(
                query, uniquify=False, useChirality=False,
                maxMatches=_INFER_MATCH_LIMIT)
            if not ms:
                return []
            comp_matches.append([tuple(m) for m in ms])
        combos: list[dict] = []

        def _combine(i: int, used: set[int], image: dict) -> None:
            if len(combos) >= _INFER_MATCH_LIMIT:
                return
            if i == len(comps):
                combos.append(dict(image))
                return
            comp_global_offset = offsets[i]
            for m in comp_matches[i]:
                if set(m) & used:
                    continue
                for q_idx, d_idx in enumerate(m):
                    image[d_idx] = comp_global_offset + q_idx
                _combine(i + 1, used | set(m), image)

        _combine(0, set(), {})
        truncated = len(combos) >= _INFER_MATCH_LIMIT
        for image in combos:
            removed = [d for d in range(n_donor) if d not in image]
            mappings.append({"donor_to_union": image, "new_union": [],
                             "removed_donor": removed,
                             "truncated": truncated})
    else:
        # ---- 加成:donor ⊆ 单一产物组分 ----
        comps = Chem.GetMolFrags(union, asMols=True, sanitizeFrags=True)
        offset = 0
        query = _any_bond_query(donor)
        for comp in comps:
            ms = comp.GetSubstructMatches(
                query, uniquify=False, useChirality=False,
                maxMatches=_INFER_MATCH_LIMIT)
            for m in ms:
                image = {d: offset + u for d, u in enumerate(m)}
                covered = {image[d] for d in image}
                new = [u for u in range(n_union) if u not in covered]
                mappings.append({
                    "donor_to_union": image, "new_union": new,
                    "removed_donor": [], "truncated": False})
            offset += comp.GetNumAtoms()
            if mappings:
                # 只在能容纳完整 donor 的组分内枚举(首个足够组分;
                # 更小组分必然放不下 —— n_donor < n_union 且 donor
                # 连通,任何容纳它的组分大小 ≥ n_donor)
                break
        truncated = len(mappings) >= _INFER_MATCH_LIMIT
        for entry in mappings:
            entry["truncated"] = truncated
    return mappings


def _record_products_strict(products: list[str]) -> list:
    out = []
    for p in products:
        try:
            out.append(strict_identity_of(str(p)))
        except Exception:
            out.append(None)
    return out


def _executed_components_strict(target_smiles: str) -> list:
    mol = Chem.MolFromSmiles(target_smiles or "")
    if mol is None:
        return []
    out = []
    for frag in Chem.GetMolFrags(mol, asMols=True,
                                  sanitizeFrags=True):
        out.append(Chem.MolToSmiles(frag))
    return out


# ---------------------------------------------------------------- 主入口


def find_recorded_exact(
    *, substrate_smiles: str, engine,
    max_reactions: int = 24,
) -> dict:
    """当前底物的 recorded 精确源候选(W2 主入口)。

    返回 {candidates: [...], diagnostics: {...}}:
    - candidates(检索序,引擎 lookup 置顶序):每项 {record_id, tier
      (recorded_strict_exact|recorded_cn_candidate), donor_smiles,
      products(完整净产物集合,库行序), filter_flags, compile
      (compiled spec | None), compile_reason} —— compile 由
      ``compile_recorded_reaction`` 产生(推断映射,同一迁移结果);
    - diagnostics:n_lookup、n_reactions、strict/cn 计数、编译失败
      分层计数(unsupported 原因直方图)。

    严格分层:donor 严格身份 == 底物严格身份 ⇒ strict exact(编译产物
    逐组分 strict 核对一致才 spec);CN 同而 strict 异 ⇒ cn candidate
    (不升格,标 analog 级);方向 donor→products 由库行序承载。
    """
    raw = engine.expand_raw(str(substrate_smiles), case_id="recorded-source")
    if "error" in raw:
        return {"candidates": [], "diagnostics": {
            "kind": "engine_error", "error": str(raw.get("error"))}}
    index = load_library_index(engine)
    substrate_strict = _strict_of(substrate_smiles)
    substrate_cn = cn_identity(str(substrate_smiles))
    candidates: list[dict] = []
    seen_rids: set[str] = set()
    failure_hist: dict[str, int] = {}
    n_strict = n_cn = 0
    for row in raw.get("lookup") or []:
        for rid in row.get("eawag_reactions") or []:
            rid = str(rid)
            if rid in seen_rids or len(candidates) >= int(max_reactions):
                continue
            seen_rids.add(rid)
            record = index.get(rid)
            if record is None or not record.get("donor_smiles") \
                    or not record.get("products"):
                failure_hist["record_missing_or_incomplete"] = \
                    failure_hist.get("record_missing_or_incomplete", 0) + 1
                continue
            donor_strict = _strict_of(record["donor_smiles"])
            donor_cn = cn_identity(record["donor_smiles"])
            if donor_strict == substrate_strict:
                tier = "recorded_strict_exact"
                n_strict += 1
            elif donor_cn is not None and donor_cn == substrate_cn:
                tier = "recorded_cn_candidate"
                n_cn += 1
            else:
                # 引擎 lookup CN 键命中但库 donor CN 不同(索引键归一差
                # 异):按 analog 级披露,不升格
                tier = "recorded_cn_candidate"
                n_cn += 1
            compiled = compile_recorded_reaction(
                substrate_smiles=str(substrate_smiles),
                donor_smiles=record["donor_smiles"],
                products=list(record["products"]),
                record_id=rid)
            if compiled.get("status") != "compiled":
                reason = str(compiled.get("reason") or "unknown")
                failure_hist[reason] = failure_hist.get(reason, 0) + 1
            candidates.append({
                "record_id": rid,
                "tier": tier,
                "donor_smiles": record["donor_smiles"],
                "package": record.get("package", ""),
                "products": list(record["products"]),
                "filter_flags": {
                    "ion_filtered": bool(row.get("ion_filtered")),
                    "cofactor_filtered": bool(row.get("cofactor_filtered")),
                    "filtered": bool(row.get("filtered")),
                },
                "compile": compiled.get("spec"),
                "compile_status": str(compiled.get("status")),
                "compile_reason": str(compiled.get("reason") or ""),
                "compile_detail": dict(compiled.get("detail") or {}),
            })
    return {"candidates": candidates, "diagnostics": {
        "recorded_source_version": RECORDED_SOURCE_VERSION,
        "n_lookup_rows": len(raw.get("lookup") or []),
        "n_reactions": len(seen_rids),
        "n_strict_exact": n_strict,
        "n_cn_candidate": n_cn,
        "compile_failure_histogram": dict(sorted(failure_hist.items())),
    }}


def _strict_of(smiles: str) -> str | None:
    try:
        return strict_identity_of(str(smiles))
    except Exception:
        return None


def compile_recorded_reaction(
    *, substrate_smiles: str, donor_smiles: str,
    products: list[str], record_id: str,
) -> dict:
    """库记录(donor + 完整净产物集合)→ PPV1 池 spec(推断映射)。

    - 结构对应:元素标记 any-bond 同构枚举(有界;W2 约束);
    - 每个候选映射构建 mapped_lhs/mapped_rhs(map 号联结),走
      ``compile_donor_template``(W1 共同编译器,单一构建源);
    - 同目标映射合并;异目标 ⇒ ambiguous(歧义披露拒绝);
    - strict exact 校验(调用方 find_recorded_exact 之后的最终门):
      编译执行产物按组分 strict 身份多重集 == 库记录产物多重集;
      离去组分缺产物/过滤缺失 ⇒ product_set_mismatch(诚实拒)。
    - 中心 = 推断变换的变化原子(键变化端点 + 新增/离去;推断映射的
      反应中心,非机制证据);
    - mapping_origin=inferred(spec 与诊断如实标注)。
    """
    mappings = infer_reaction_mapping(donor_smiles, products)
    if not mappings:
        return {"status": "unsupported", "reason": "no_structure_correspondence",
                "detail": {"record_id": record_id}}
    if mappings[0].get("truncated"):
        return {"status": "unsupported",
                "reason": "mapping_enumeration_truncated",
                "detail": {"record_id": record_id,
                           "note": "结构同构枚举触顶(歧义不可闭合,拒绝)"}}
    compiled_specs: list[dict] = []
    reasons: set[str] = set()
    for mapping in mappings:
        donor_to_union = mapping["donor_to_union"]
        new_union = mapping["new_union"]
        removed_donor = mapping["removed_donor"]
        # map 号:donor idx → 1..N;union 新原子 → N+1..
        donor_map = {idx: i + 1 for i, idx in enumerate(
            sorted(donor_to_union) + sorted(removed_donor))}
        union_map = {donor_to_union[d]: donor_map[d] for d in donor_to_union}
        n_donor = donor_map and max(donor_map.values()) or 0
        for k, u_idx in enumerate(sorted(new_union)):
            union_map[u_idx] = n_donor + 1 + k
        donor_mol = Chem.MolFromSmiles(donor_smiles)
        union_mol = Chem.MolFromSmiles(".".join(products))
        if donor_mol is None or union_mol is None:
            return {"status": "unsupported", "reason":
                    "record_unparseable", "detail": {"record_id": record_id}}
        mapped_lhs = _mapped_copy(donor_mol, donor_map)
        mapped_rhs = _mapped_copy(union_mol, union_map)
        # 中心 = 变化原子(键变化端点 + 新增 + 离去)
        center = _changed_maps(mapped_lhs, mapped_rhs)
        out = compile_donor_template(
            mapped_lhs=mapped_lhs, mapped_rhs=mapped_rhs,
            center_atoms=center, substrate_smiles=substrate_smiles,
            record_id=record_id, mapping_origin="inferred",
            alignment_ref=f"recorded-inferred:{record_id}",
            key_prefix="rec")
        if out.get("status") == "compiled":
            compiled_specs.append(out)
        else:
            reasons.add(str(out.get("reason")))
    if not compiled_specs:
        return {"status": "unsupported",
                "reason": (sorted(reasons)[0] if reasons
                           else "no_compilable_mapping"),
                "detail": {"record_id": record_id,
                           "all_reasons": sorted(reasons)[:8]}}
    targets = {spec["spec"]["expectation"]["target_smiles"]
               for spec in compiled_specs}
    if len(targets) > 1:
        return {"status": "unsupported", "reason": "ambiguous_mapping",
                "detail": {"record_id": record_id,
                           "competing_targets": sorted(targets)[:8],
                           "n_mappings": len(mappings)}}
    chosen = compiled_specs[0]
    spec = chosen["spec"]
    # ---- strict exact 最终门:执行产物组分 == 库记录产物(多重集) ----
    executed = sorted(_executed_components_strict(
        spec["expectation"]["target_smiles"]))
    recorded = sorted(x for x in
                      _record_products_strict(products) if x)
    if executed != recorded:
        return {"status": "unsupported",
                "reason": "product_set_mismatch",
                "detail": {"record_id": record_id,
                           "executed_components": executed[:8],
                           "recorded_components": recorded[:8],
                           "note": ("执行产物组分与库记录净产物集合不一致"
                                    "(离去组分缺行/过滤缺失/对应错误;"
                                    "不冒充完整 record")}}
    spec = dict(spec)
    spec.pop("coefficient", None)  # 库记录无配平系数 ⇒ unknown
    spec["compile"] = dict(spec.get("compile") or {})
    spec["compile"].update({
        "mapping_origin": "inferred",
        "record_products": list(products),
        "verified_product_set": True,
        "n_mappings": len(mappings),
        "n_equivalent_mappings": len(compiled_specs),
    })
    chosen = dict(chosen)
    chosen["spec"] = spec
    return chosen


def _changed_maps(mapped_lhs: str, mapped_rhs: str) -> list[int]:
    """推断变换的变化原子 map 号(**供体 lhs 侧**:键差端点 + 离去)。

    新增原子(rhs 独有 map)不在此列 —— 编译器自动把新增原子并入中心
    与对齐(W1);此处给 lhs 侧中心即可。"""
    from .s5b_compiler import extract_mapped_transform

    try:
        transform = extract_mapped_transform(mapped_lhs, mapped_rhs)
    except S5bCompileError:
        return []
    center: set[int] = set()
    for ch in transform["bond_changes"]:
        center.add(int(ch["map1"]))
        center.add(int(ch["map2"]))
    center |= set(transform["removed_maps"])
    # 只取 lhs(供体)侧 map;新增原子(rhs 独有)由编译器自动并入中心
    lhs_maps = set(transform["lhs"].maps)
    return sorted(center & lhs_maps)
