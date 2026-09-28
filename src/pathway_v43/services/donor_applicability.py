"""供体变换提取与适用性门禁(Phase C 任务书 §0/§3,C1;零模型、零网络)。

``mapping_status=resolved`` 只证明"找回并对齐",不证明供体反应可迁移到
当前分子。本模块把**来源找回状态**与**化学迁移资格**分为两层:

- 从映射模板 ``mapped_lhs → mapped_rhs`` **确定性提取**反应变化表(保留/
  新增/消失的原子映射号、元素/电荷/氢变化、被断/新成的键及键级变化)。
  提取过程本身就是核验:双侧可解析、映射号双侧唯一、保留原子元素一致 ——
  **不信任** ``qc_flags.bijection`` 声明(假阳性须留拒因);模板不完整记录
  ``unavailable`` 与具体拒因,不补造原子映射。
- 对每个供体枚举当前分子的**全部相关对齐**(全供体优先,失败才以明示的
  反应中心子图策略作保守候选),不取 RDKit 首个匹配;
- 每个对齐在当前分子图副本上**确定性施加**供体变化(断键/成键/键级/
  电荷/氢),逐项检查中心原子与键对应、一阶邻域、键级、形式电荷、可用氢
  与价态可执行性;施加成功且 sanitize 通过才产生预测产物结构。
- 对称对齐施加后得到相同目标 → 按稳定产物合并并保留全部匹配引用;
  得到不同目标或供体互相冲突 → ``ambiguous``,不拿第一个。

全部检查是确定性**结构必要条件**;质子来源、环境条件不在此声称 —— 涉及
增氢/电荷变化的迁移如实列入 ``unverified_conditions``,不写成"环境相容"。
评估结论(本模块)只表达迁移资格;最终模型提案仍须走既有
``validate_event_products``/AtomTool/元素等全部门禁。

 aromatic 语义:对齐用芳香形式(避免 Kekulé 异构体间子结构匹配失败);
键级上下文比较时 aromatic≡aromatic 视为一致,混合芳香/非芳香记失配。
"""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

APPLICABILITY_VERSION = "v43-applicability-3"
# v2(Phase D D1):reactant_similar 检索通道进入评估序(resolved 卡 →
# 相似通道 → 其余卡);未评估供体标 budget_not_assessed;新增相似通道
# 参数与 displaced 留痕。变更拒绝旧 run resume。

# 逐卡/逐父状态(任务书 §1.2:来源找回 ≠ 迁移资格)
APPLICABILITY_APPLICABLE = "applicable"
APPLICABILITY_INAPPLICABLE = "inapplicable"
APPLICABILITY_AMBIGUOUS = "ambiguous"
APPLICABILITY_UNAVAILABLE = "unavailable"
# Phase D D1:预算耗尽而未评估的供体(不是化学失败,不得冒充 inapplicable)
APPLICABILITY_BUDGET_NOT_ASSESSED = "budget_not_assessed"

# fallback 拒因词表(任务书 §3:不把这些情况统称"无证据")
FALLBACK_NO_MAPPING = "no_mapping"
FALLBACK_MAPPING_AMBIGUOUS = "mapping_ambiguous"
FALLBACK_APPLICABILITY_FAILED = "applicability_failed"
FALLBACK_APPLICABILITY_UNKNOWN = "applicability_unknown"
FALLBACK_COMPETING_TRANSFORMS = "multiple_competing_transforms"

ALIGN_FULL = "full_donor_substructure"
ALIGN_CENTER = "reaction_center_substructure"

# 单供体**落盘明细**样本上限(RDKit 确定性顺序)。仅约束写入产物的
# 明细条数:判定必须覆盖全部枚举对齐(竞争目标判定漏掉第 17 个对齐就
# 可能漏掉竞争产物),总数由 ``n_alignments_full``/``n_alignments_center``/
# ``n_alignments_assessed`` 如实留痕。
_MAX_RESULTS_STORED = 16

# 对齐枚举显式上限(Phase C R2 复核:RDKit GetSubstructMatches 缺省
# maxMatches=1000 也会**静默截断**,不显式给出就不能声称"评估全部";
# 触顶时 fail-closed 标 alignment_limit_exceeded,截断集合不得当作
# 唯一适用目标 —— 见 assess_donor。版本化进代码身份。)
_ALIGNMENT_ENUM_LIMIT = 2000

_NONE = "none"
_AROMATIC = "aromatic"
_ORDER_NAME = {
    Chem.BondType.SINGLE: "single",
    Chem.BondType.DOUBLE: "double",
    Chem.BondType.TRIPLE: "triple",
    Chem.BondType.AROMATIC: _AROMATIC,
}
# 施加阶段:aromatic 键级以 SINGLE 落图(占位),由 sanitize 重感知;
# 最终结构以 canonical SMILES 为准
_APPLY_ORDER = {
    "single": Chem.BondType.SINGLE,
    "double": Chem.BondType.DOUBLE,
    "triple": Chem.BondType.TRIPLE,
    _AROMATIC: Chem.BondType.SINGLE,
}


@dataclass
class ApplicabilityPolicy:
    """冻结的评估配置(N、枚举序与 tie-break 进入策略身份)。"""

    max_donor_candidates: int = 3
    card_order: tuple = ("retrieval_rank", "evidence_id")   # 卡枚举序
    donor_order: str = "donor_refs_order_then_asset_line"   # 卡内供体序
    tie_break: str = "full_donor_first_then_first_applicable"
    # Phase D D1:reactant_similar 通道参数(检索在 analog_source 层执行,
    # 这里冻结其身份:非正阈值 = 通道关闭,即 C0 旧检索配置)
    similarity_threshold: float = 0.0
    similarity_top_k: int = 0
    similarity_version: str = ""
    extra_channel_order: str = "after_resolved_before_rest"

    def to_dict(self) -> dict:
        return {
            "max_donor_candidates": self.max_donor_candidates,
            "card_order": list(self.card_order),
            "donor_order": self.donor_order,
            "tie_break": self.tie_break,
            "similarity_threshold": self.similarity_threshold,
            "similarity_top_k": self.similarity_top_k,
            "similarity_version": self.similarity_version,
            "extra_channel_order": self.extra_channel_order,
        }


# ---------------------------------------------------------------- 变换提取


def _mapped_mol(smiles: str):
    return Chem.MolFromSmiles(smiles) if smiles else None


def _atom_map_no(atom) -> int:
    return atom.GetAtomMapNum()


def _order_name(bond) -> str:
    if bond is None:
        return _NONE
    return _ORDER_NAME.get(bond.GetBondType(), str(bond.GetBondType()))


def extract_donor_transform(mapped_lhs: str, mapped_rhs: str):
    """映射模板 → 反应变化表(确定性;不可提取返回 (None, 拒因))。

    变化表字段:
    - ``retained_atoms``: 两侧同映射号原子 {map: {element, charge_lhs/rhs,
      h_lhs/rhs}}(元素不一致 = 映射损坏,不信任 bijection 声明);
    - ``added_atoms`` / ``removed_atoms``: 单侧映射号(新增原子 / 离去
      原子;离去原子不删除,断键后留在多组分产物中);
    - ``bond_changes``: 两侧键级不同的原子对 [{map1, map2, order_lhs,
      order_rhs}](缺席侧记 ``none``);
    - ``added_bonds``: rhs 中至少一端为新增原子的键(新增原子据此落位)。

    拒因(稳定机读码):transform_unparseable_lhs/rhs、transform_unmapped、
    duplicate_map_no、map_element_changed、transform_no_change。
    """
    lm, rm = _mapped_mol(mapped_lhs), _mapped_mol(mapped_rhs)
    if lm is None:
        return None, "transform_unparseable_lhs"
    if rm is None:
        return None, "transform_unparseable_rhs"
    lhs_maps: dict[int, object] = {}
    for a in lm.GetAtoms():
        n = _atom_map_no(a)
        if n:
            if n in lhs_maps:
                return None, f"duplicate_map_no:{n}:lhs"
            lhs_maps[n] = a
    rhs_maps: dict[int, object] = {}
    for a in rm.GetAtoms():
        n = _atom_map_no(a)
        if n:
            if n in rhs_maps:
                return None, f"duplicate_map_no:{n}:rhs"
            rhs_maps[n] = a
    if not lhs_maps or not rhs_maps:
        return None, "transform_unmapped"

    retained: dict[str, dict] = {}
    for n in sorted(set(lhs_maps) & set(rhs_maps)):
        la, ra = lhs_maps[n], rhs_maps[n]
        if la.GetSymbol() != ra.GetSymbol():
            return None, f"map_element_changed:{n}"
        retained[str(n)] = {
            "element": la.GetSymbol(),
            "charge_lhs": la.GetFormalCharge(),
            "charge_rhs": ra.GetFormalCharge(),
            "h_lhs": la.GetTotalNumHs(),
            "h_rhs": ra.GetTotalNumHs(),
        }
    added = {str(n): {"element": rhs_maps[n].GetSymbol(),
                      "charge": rhs_maps[n].GetFormalCharge()}
             for n in sorted(set(rhs_maps) - set(lhs_maps))}
    removed = {str(n): {"element": lhs_maps[n].GetSymbol()}
               for n in sorted(set(lhs_maps) - set(rhs_maps))}

    def _bonds(mol) -> dict[frozenset, str]:
        out: dict[frozenset, str] = {}
        for b in mol.GetBonds():
            ni, nj = (_atom_map_no(b.GetBeginAtom()),
                      _atom_map_no(b.GetEndAtom()))
            if ni and nj:
                out[frozenset((ni, nj))] = _order_name(b)
        return out

    lb, rb = _bonds(lm), _bonds(rm)
    added_maps = set(rhs_maps) - set(lhs_maps)
    bond_changes, added_bonds = [], []
    for pair in sorted({tuple(sorted(p)) for p in set(lb) | set(rb)},
                       key=lambda p: (p[0], p[1])):
        key = frozenset(pair)
        ol, orr = lb.get(key, _NONE), rb.get(key, _NONE)
        if ol == orr:
            continue
        entry = {"map1": pair[0], "map2": pair[1],
                 "order_lhs": ol, "order_rhs": orr}
        if added_maps & set(pair) and ol == _NONE:
            added_bonds.append(entry)  # 新原子落位键
        else:
            bond_changes.append(entry)

    h_gain = sorted(k for k, v in retained.items()
                    if v["h_rhs"] > v["h_lhs"])
    h_loss = sorted(k for k, v in retained.items()
                    if v["h_rhs"] < v["h_lhs"])
    charge_changed = sorted(k for k, v in retained.items()
                            if v["charge_lhs"] != v["charge_rhs"])
    if not (bond_changes or added_bonds or added or removed
            or h_gain or h_loss or charge_changed):
        return None, "transform_no_change"
    transform = {
        "retained_atoms": retained,
        "added_atoms": added,
        "removed_atoms": removed,
        "bond_changes": bond_changes,
        "added_bonds": added_bonds,
        "h_gain_maps": h_gain,
        "h_loss_maps": h_loss,
        "charge_changed_maps": charge_changed,
    }
    return transform, ""


def _aromatic_form(smiles: str):
    return Chem.MolFromSmiles(smiles or "") if smiles else None


def _kekulized(smiles: str):
    mol = Chem.MolFromSmiles(smiles or "") if smiles else None
    if mol is None:
        return None
    try:
        Chem.Kekulize(mol, clearAromaticFlags=True)
    except Exception:
        pass
    return mol


# ---------------------------------------------------------------- 对齐枚举


def _center_query(donor_mol, center_map_nums: list[int]):
    """反应中心子图查询(映射号∈center_map_nums 的原子及其间键)。

    模板缺 ``center_atoms`` 元数据(空列表)时回退到**全部带映射原子**
    —— 与既有 ``align_donor_mapping`` 的既定语义一致;封存首跑 56 个
    供体引用属此类,缺该回退会把旧路由实际对齐过的模板误判为
    no_alignment。
    """
    if center_map_nums:
        center_idx = [a.GetIdx() for a in donor_mol.GetAtoms()
                      if _atom_map_no(a) in set(center_map_nums)]
    else:
        center_idx = [a.GetIdx() for a in donor_mol.GetAtoms()
                      if _atom_map_no(a) > 0]
    if len(center_idx) < 2:
        return None
    rw = Chem.RWMol()
    idx_map = {}
    for i in center_idx:
        idx_map[i] = rw.AddAtom(Chem.Atom(donor_mol.GetAtomWithIdx(i)))
    for b in donor_mol.GetBonds():
        bi, ei = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if bi in idx_map and ei in idx_map:
            rw.AddBond(idx_map[bi], idx_map[ei], b.GetBondType())
    return rw.GetMol(), idx_map


def enumerate_alignments(donor_mol, current_mol,
                         center_map_nums: list[int]) -> dict:
    """供体 → 当前分子的**全部**子结构匹配(不取首个;确定性顺序)。

    先全供体;全供体无匹配才用反应中心子图(明示的保守候选策略)。
    ``maxMatches`` 显式给 ``_ALIGNMENT_ENUM_LIMIT``(RDKit 缺省 1000 也
    会静默截断);达到上限时返回 ``_truncated=True``,由 assess_donor
    fail-closed,不得把截断集合当作唯一适用目标。
    返回 {strategy: [{donor_idx: current_idx}, …]},列表不截断(除显式
    上限);``_n_full``/``_n_center`` 记总数,落盘样本上限在存储层。
    """
    if donor_mol is None or current_mol is None:
        return {}
    out: dict[str, list[dict]] = {}
    full = current_mol.GetSubstructMatches(
        donor_mol, uniquify=False, useChirality=False,
        maxMatches=_ALIGNMENT_ENUM_LIMIT)
    if full:
        out[ALIGN_FULL] = [
            {d: c for d, c in enumerate(m)} for m in full]
        out["_n_full"] = len(full)
        out["_truncated"] = len(full) >= _ALIGNMENT_ENUM_LIMIT
        return out
    q = _center_query(donor_mol, center_map_nums or [])
    if q is None:
        return {}
    query, idx_map = q
    matches = current_mol.GetSubstructMatches(
        query, uniquify=False, useChirality=False,
        maxMatches=_ALIGNMENT_ENUM_LIMIT)
    orig_of_pos = {pos: orig for orig, pos in idx_map.items()}
    out[ALIGN_CENTER] = [
        {orig_of_pos[pos]: cur for pos, cur in enumerate(m)}
        for m in matches]
    out["_n_center"] = len(matches)
    out["_truncated"] = len(matches) >= _ALIGNMENT_ENUM_LIMIT
    return out


# ---------------------------------------------------------------- 对齐评估


def assess_alignment(transform: dict, alignment: dict, strategy: str,
                     *, donor_mol, current_mol, current_kek,
                     current_h: dict[int, int],
                     current_charge: dict[int, int]) -> dict:
    """把供体变化确定性施加到一个对齐上,逐项检查结构必要条件。

    返回 {ok, strategy, alignment, reasons, unverified_conditions,
    product_smiles}。检查(全部确定性、可复算):
    - element_correspondence:对齐原子元素一致(全供体匹配自动成立,
      中心子图对齐必须显式核对);
    - bond_context:变化键在当前分子的存在性与键级同供体 lhs 一致
      (center_bond_missing / bond_context_mismatch / bond_order_mismatch;
      aromatic≡aromatic 视为一致);
    - charge_context:供体中电荷不变的原子,当前电荷须一致;电荷变化的
      原子施加 delta 并如实记入 unverified_conditions;
    - hydrogen:失氢原子当前可用氢须充足(insufficient_hydrogen);增氢
      按显式 H 施加并记入 unverified_conditions(质子来源未知);
    - valence:施加后的分子必须 RDKit sanitize 通过(valence_infeasible);
    - hydrogen_outcome:保留原子最终总氢 = 当前氢 + donor delta(不符 =
      一阶邻域上下文分歧,如当前分子多出供体没有的重原子取代基)。
    """
    reasons: list[str] = []
    unverified: list[str] = []
    d2c = alignment
    retained = transform["retained_atoms"]

    map_to_donor_idx: dict[int, int] = {}
    for a in donor_mol.GetAtoms():
        n = _atom_map_no(a)
        if n:
            map_to_donor_idx[n] = a.GetIdx()

    def cur_idx_of(map_no: int):
        d_idx = map_to_donor_idx.get(map_no)
        if d_idx is None or d_idx not in d2c:
            return None
        return d2c[d_idx]

    # 1) 元素对应(中心对齐的关键约束;全供体匹配自动成立)
    for map_str, spec in retained.items():
        ci = cur_idx_of(int(map_str))
        if ci is not None and \
                current_mol.GetAtomWithIdx(ci).GetSymbol() != spec["element"]:
            reasons.append(f"element_correspondence_mismatch:map{map_str}")

    # 施加工作图 = 当前分子(kekulé)+ 新增原子(不影响既有键上下文)
    rw = Chem.RWMol(Chem.Mol(current_kek))
    added_idx: dict[int, int] = {}
    for map_str, spec in transform["added_atoms"].items():
        atom = Chem.Atom(spec["element"])
        if spec["charge"]:
            atom.SetFormalCharge(spec["charge"])
        added_idx[int(map_str)] = rw.AddAtom(atom)

    def endpoint(map_no: int):
        """键端点解析:保留对齐原子 → 当前 idx;新增原子 → 新 idx。"""
        ci = cur_idx_of(map_no)
        if ci is not None:
            return ci
        return added_idx.get(map_no)

    # 2) 键上下文:存在性与键级(变化键的 lhs 端点必须都是保留对齐原子)
    for ch in transform["bond_changes"]:
        i, j = int(ch["map1"]), int(ch["map2"])
        lhs_order = ch["order_lhs"]
        if lhs_order == _NONE:
            continue  # 新成键在施加步处理
        ci, cj = cur_idx_of(i), cur_idx_of(j)
        if ci is None or cj is None:
            reasons.append(f"alignment_missing_endpoint:map{i}~map{j}")
            continue
        bond = rw.GetBondBetweenAtoms(ci, cj)
        if bond is None:
            reasons.append(f"center_bond_missing:map{i}~map{j}")
            continue
        if lhs_order == _AROMATIC:
            cur_bond = current_mol.GetBondBetweenAtoms(ci, cj)
            if cur_bond is not None and not cur_bond.GetIsAromatic():
                reasons.append(
                    f"bond_order_mismatch:map{i}~map{j}:"
                    "donor_aromatic_current_aliphatic")
        else:
            cur_bond = current_mol.GetBondBetweenAtoms(ci, cj)
            if cur_bond is not None and cur_bond.GetIsAromatic():
                reasons.append(
                    f"bond_order_mismatch:map{i}~map{j}:"
                    "donor_aliphatic_current_aromatic")
            elif _order_name(bond) != lhs_order:
                reasons.append(
                    f"bond_order_mismatch:map{i}~map{j}:"
                    f"current_{_order_name(bond)}_donor_{lhs_order}")

    # 3) 电荷上下文
    for map_str, spec in retained.items():
        ci = cur_idx_of(int(map_str))
        if ci is None:
            continue
        if spec["charge_lhs"] == spec["charge_rhs"]:
            if current_charge.get(ci, 0) != spec["charge_lhs"]:
                reasons.append(
                    f"charge_context_mismatch:map{map_str}:"
                    f"current_{current_charge.get(ci, 0)}"
                    f"_donor_{spec['charge_lhs']}")
        else:
            delta = spec["charge_rhs"] - spec["charge_lhs"]
            rw.GetAtomWithIdx(ci).SetFormalCharge(
                current_charge.get(ci, 0) + delta)
            unverified.append(
                f"charge_change_applied:map{map_str}:delta{delta:+d}"
                "(环境依赖,未验证)")

    if reasons:
        return {"ok": False, "strategy": strategy, "alignment": {str(d): c for d, c in d2c.items()},
                "reasons": reasons, "unverified_conditions": unverified,
                "product_smiles": ""}

    # 4) 施加键变化
    for ch in transform["bond_changes"]:
        i, j = int(ch["map1"]), int(ch["map2"])
        ci, cj = endpoint(i), endpoint(j)
        order_lhs, order_rhs = ch["order_lhs"], ch["order_rhs"]
        if order_lhs != _NONE and order_rhs == _NONE:
            rw.RemoveBond(ci, cj)  # 断键(存在性已核对)
        elif order_lhs == _NONE and order_rhs != _NONE:
            if ci is None or cj is None:
                reasons.append(f"alignment_missing_endpoint:map{i}~map{j}")
                continue
            if rw.GetBondBetweenAtoms(ci, cj) is not None:
                reasons.append(
                    f"bond_context_mismatch:map{i}~map{j}:"
                    "current_bonded_donor_lhs_unbonded")
                continue
            rw.AddBond(ci, cj, _APPLY_ORDER[order_rhs])
        else:
            bond = rw.GetBondBetweenAtoms(ci, cj)
            if bond is None:
                reasons.append(f"center_bond_missing:map{i}~map{j}")
                continue
            bond.SetBondType(_APPLY_ORDER[order_rhs])
    # 新增原子落位键(至少一端是新增原子)
    for ch in transform["added_bonds"]:
        ci, cj = endpoint(int(ch["map1"])), endpoint(int(ch["map2"]))
        if ci is None or cj is None:
            reasons.append(
                f"added_bond_missing_endpoint:map{ch['map1']}"
                f"~map{ch['map2']}")
            continue
        rw.AddBond(ci, cj, _APPLY_ORDER[ch["order_rhs"]])

    if reasons:
        return {"ok": False, "strategy": strategy, "alignment": {str(d): c for d, c in d2c.items()},
                "reasons": reasons, "unverified_conditions": unverified,
                "product_smiles": ""}

    # 5) 失氢可用性(施加前核对,拒因更具体)
    for map_str in transform["h_loss_maps"]:
        spec = retained[map_str]
        ci = cur_idx_of(int(map_str))
        if ci is None:
            continue
        need = spec["h_lhs"] - spec["h_rhs"]
        have = current_h.get(ci, 0)
        if have < need:
            reasons.append(
                f"insufficient_hydrogen:map{map_str}:need{need}_have{have}")
    if reasons:
        return {"ok": False, "strategy": strategy, "alignment": {str(d): c for d, c in d2c.items()},
                "reasons": reasons, "unverified_conditions": unverified,
                "product_smiles": ""}

    mol = rw.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        reasons.append(f"valence_infeasible:{type(exc).__name__}")
        return {"ok": False, "strategy": strategy, "alignment": {str(d): c for d, c in d2c.items()},
                "reasons": reasons, "unverified_conditions": unverified,
                "product_smiles": ""}

    # 6) 氢结算:保留原子最终总氢 = 当前氢 + donor delta;强制结算后
    #    sanitize 必须通过(价态不允许即不可迁移)
    h_gain_maps = set(transform["h_gain_maps"])
    for map_str, spec in retained.items():
        ci = cur_idx_of(int(map_str))
        if ci is None:
            continue
        delta = spec["h_rhs"] - spec["h_lhs"]
        want = current_h.get(ci, 0) + delta
        if want < 0:
            reasons.append(
                f"hydrogen_outcome_mismatch:map{map_str}:negative_{want}")
            continue
        atom = mol.GetAtomWithIdx(ci)
        if atom.GetTotalNumHs() != want:
            atom.SetNoImplicit(True)
            atom.SetNumExplicitHs(want)
            if map_str in h_gain_maps:
                unverified.append(
                    f"h_gain:map{map_str}(质子来源未知,未验证)")
    if reasons:
        return {"ok": False, "strategy": strategy, "alignment": {str(d): c for d, c in d2c.items()},
                "reasons": reasons, "unverified_conditions": unverified,
                "product_smiles": ""}
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        reasons.append(f"valence_infeasible:{type(exc).__name__}")
        return {"ok": False, "strategy": strategy, "alignment": {str(d): c for d, c in d2c.items()},
                "reasons": reasons, "unverified_conditions": unverified,
                "product_smiles": ""}

    return {"ok": True, "strategy": strategy, "alignment": {str(d): c for d, c in d2c.items()},
            "reasons": [], "unverified_conditions": unverified,
            "product_smiles": Chem.MolToSmiles(mol)}


# ---------------------------------------------------------------- 供体评估


def assess_donor(donor_ref: dict, substrate_smiles: str) -> dict:
    """一个供体模板 → 变换提取 + 全对齐枚举 + 逐对齐评估。

    status:applicable(唯一目标)/ ambiguous(对齐给出不同目标)/
    inapplicable(全部对齐被拒)/ unavailable(变换不可提取)。
    供体反应物与当前分子相同 → 精确查找领域,不算类比(与
    analog_source.align 同语义),记 inapplicable:donor_same_as_substrate。
    """
    record_id = str(donor_ref.get("record_id", ""))
    base = {
        "record_id": record_id,
        "donor_index": donor_ref.get("index", ""),
        "asset_file": donor_ref.get("asset_file", ""),
        "asset_sha256": donor_ref.get("asset_sha256", ""),
        "line_no": donor_ref.get("line_no"),
        "mapping_quality": donor_ref.get("mapping_quality", ""),
        # R1 修复(v43-applicability-3):供体映射模板随评估结果透传 ——
        # 相似通道等资格块自有供体不在检索产物 evidences 中,prediction
        # 任务组装需要从 selected 直接取到完整 donor 引用(pb_0117 事故:
        # selected 缺映射 → 任务组装失败)
        "mapped_lhs": donor_ref.get("mapped_lhs", ""),
        "mapped_rhs": donor_ref.get("mapped_rhs", ""),
        # Phase D D1:找回通道与相似度留痕沿评估结果透传(审计链:
        # 答卷 → 资格块 → 供体 ref → 通道/分数/版本)
        "find_channels": list(donor_ref.get("find_channels") or []),
        "similarity": donor_ref.get("similarity"),
        "similarity_version": donor_ref.get("similarity_version", ""),
        "similarity_rank": donor_ref.get("similarity_rank"),
    }
    from ..domain.identity import cn_identity

    reactant = donor_ref.get("reactant_smiles") or ""
    if reactant and substrate_smiles and \
            cn_identity(reactant) == cn_identity(substrate_smiles):
        return {**base, "status": APPLICABILITY_INAPPLICABLE,
                "transform_reason": "donor_same_as_substrate",
                "transform": None, "n_alignments_full": 0,
                "n_alignments_center": 0, "n_alignments_assessed": 0,
                "results": [],
                "reject_reasons": ["donor_same_as_substrate"],
                "unverified_conditions": [], "target_smiles": "",
                "selected_result": None}
    transform, reason = extract_donor_transform(
        donor_ref.get("mapped_lhs", ""), donor_ref.get("mapped_rhs", ""))
    if transform is None:
        return {**base, "status": APPLICABILITY_UNAVAILABLE,
                "transform_reason": reason, "transform": None,
                "n_alignments_full": 0, "n_alignments_center": 0,
                "n_alignments_assessed": 0,
                "results": [], "reject_reasons": [reason],
                "unverified_conditions": [], "target_smiles": "",
                "selected_result": None}

    current_mol = _aromatic_form(substrate_smiles)
    current_kek = _kekulized(substrate_smiles)
    donor_mol = _aromatic_form(donor_ref.get("mapped_lhs", ""))
    if current_mol is None or current_kek is None or donor_mol is None:
        return {**base, "status": APPLICABILITY_UNAVAILABLE,
                "transform_reason": "substrate_or_donor_unparseable",
                "transform": transform, "n_alignments_full": 0,
                "n_alignments_center": 0, "n_alignments_assessed": 0,
                "results": [],
                "reject_reasons": ["substrate_or_donor_unparseable"],
                "unverified_conditions": [], "target_smiles": "",
                "selected_result": None}
    current_h = {a.GetIdx(): a.GetTotalNumHs() for a in current_mol.GetAtoms()}
    current_charge = {a.GetIdx(): a.GetFormalCharge()
                      for a in current_mol.GetAtoms()}
    center = [int(x) for x in (donor_ref.get("center_atoms") or [])]
    aligns = enumerate_alignments(donor_mol, current_mol, center)
    n_full = aligns.pop("_n_full", 0)
    n_center = aligns.pop("_n_center", 0)
    truncated = bool(aligns.pop("_truncated", False))
    results: list[dict] = []
    for strategy, matches in aligns.items():
        for m in matches:
            results.append(assess_alignment(
                transform, m, strategy, donor_mol=donor_mol,
                current_mol=current_mol, current_kek=current_kek,
                current_h=current_h, current_charge=current_charge))
    if not results:
        return {**base, "status": APPLICABILITY_INAPPLICABLE,
                "transform": transform, "transform_reason": "",
                "n_alignments_full": n_full, "n_alignments_center": n_center,
                "n_alignments_assessed": 0,
                "alignment_enum_truncated": truncated,
                "results": [], "reject_reasons": ["no_alignment"],
                "unverified_conditions": [], "target_smiles": "",
                "selected_result": None}
    if truncated and not any(r["ok"] for r in results):
        # 触顶且已评估部分全败:上限之外仍可能有可通过的对齐,
        # inapplicable 是假阴性 → 如实记不可判定(unavailable)
        return {**base, "status": APPLICABILITY_UNAVAILABLE,
                "transform": transform, "transform_reason": "",
                "n_alignments_full": n_full, "n_alignments_center": n_center,
                "n_alignments_assessed": len(results),
                "alignment_enum_truncated": True,
                "results": results[:_MAX_RESULTS_STORED],
                "reject_reasons": ["alignment_limit_exceeded"],
                "unverified_conditions": [], "target_smiles": "",
                "selected_result": None}
    ok_results = [r for r in results if r["ok"]]
    reject_reasons = sorted({
        r.split(":")[0] for res in results if not res["ok"]
        for r in res["reasons"]})
    unverified = sorted({
        c for r in ok_results for c in r["unverified_conditions"]})
    if not ok_results:
        return {**base, "status": APPLICABILITY_INAPPLICABLE,
                "transform": transform, "transform_reason": "",
                "n_alignments_full": n_full, "n_alignments_center": n_center,
                "n_alignments_assessed": len(results),
                "alignment_enum_truncated": False,
                # 判定基于全部对齐;落盘明细只留样本(reject_reasons 已聚合)
                "results": results[:_MAX_RESULTS_STORED],
                "reject_reasons": reject_reasons,
                "unverified_conditions": [], "target_smiles": "",
                "selected_result": None}
    targets = {r["product_smiles"] for r in ok_results}
    if len(targets) > 1 or truncated:
        # Phase C R2:截断集合不得当作唯一适用目标 —— 即使已评估部分
        # 只剩一个目标,上限之外仍可能有竞争对齐 → ambiguous + 显式标记
        return {**base,
                "status": APPLICABILITY_AMBIGUOUS,
                "transform": transform, "transform_reason": "",
                "n_alignments_full": n_full, "n_alignments_center": n_center,
                "n_alignments_assessed": len(results),
                "alignment_enum_truncated": truncated,
                # 竞争目标集合来自全部已评估对齐;明细落盘留样本
                "results": results[:_MAX_RESULTS_STORED],
                "reject_reasons": (["alignment_limit_exceeded"]
                                   if truncated else []),
                "unverified_conditions": unverified, "target_smiles": "",
                "selected_result": None,
                "competing_targets": sorted(targets)}
    first = ok_results[0]
    slim_results = [
        {k: v for k, v in r.items() if k != "alignment"}
        for r in results[:_MAX_RESULTS_STORED]]
    selected = {
        "strategy": first["strategy"],
        "alignment": {str(d): c for d, c in first["alignment"].items()},
        "n_aligned": len(first["alignment"]),
        "n_equivalent_alignments": len(ok_results),
    }
    return {**base, "status": APPLICABILITY_APPLICABLE,
            "transform": transform, "transform_reason": "",
            "n_alignments_full": n_full, "n_alignments_center": n_center,
            "n_alignments_assessed": len(results),
            "alignment_enum_truncated": False,
            "results": slim_results, "reject_reasons": [],
            "unverified_conditions": unverified,
            "target_smiles": first["product_smiles"],
            "selected_result": selected}


def evaluate_card(card: dict, substrate_smiles: str,
                  max_donors: int, *, assess_cache: dict | None = None) -> dict:
    """一张预测卡的供体资格(读取真实 donor_refs 逐条核查,不丢歧义卡)。

    评估 donor_refs 前 ``max_donors`` 条(donor_refs 顺序 = 检索来源序,
    冻结 tie-break);多条适用供体给出相同目标 → 合并选首条;不同目标 →
    ambiguous(multiple_competing_transforms)。
    预算外未评估的供体**逐条标 ``budget_not_assessed``**(Phase D D1:
    预算事实不是化学失败,不得冒充 inapplicable)。
    ``assess_cache``:(ref 键, 底物) → assess_donor 结果的共享缓存;
    assess_donor 是确定性纯函数,缓存只省重复计算不改判定(跨卡去重后
    同一供体本就只应评估一次)。
    """
    refs = [r for r in (card.get("donor_refs") or [])
            if r.get("mapped_lhs") and r.get("mapped_rhs")]
    entry = {
        "evidence_id": card.get("evidence_id", ""),
        "retrieval_rank": card.get("retrieval_rank"),
        "mapping_status": card.get("mapping_status", ""),
        "mapping_reason": card.get("mapping_reason", ""),
        "n_donor_refs": len(card.get("donor_refs") or []),
        "n_donor_refs_evaluated": 0,
        "n_budget_not_assessed": 0,
        "donor_evals": [],
        "budget_not_assessed": [],
        "status": APPLICABILITY_UNAVAILABLE,
        "fallback_reason": FALLBACK_NO_MAPPING,
        "reject_reasons": [],
        "unverified_conditions": [],
    }
    if not refs:
        return entry
    n_eval = max(0, int(max_donors))
    evals = []
    for ref in refs[:n_eval]:
        key = _donor_key(ref)
        if assess_cache is not None and (key, substrate_smiles) in assess_cache:
            evals.append(assess_cache[(key, substrate_smiles)])
            continue
        ev = assess_donor(ref, substrate_smiles)
        if assess_cache is not None:
            assess_cache[(key, substrate_smiles)] = ev
        evals.append(ev)
    entry["n_donor_refs_evaluated"] = len(evals)
    entry["donor_evals"] = [
        {k: v for k, v in e.items() if k != "selected_result"}
        for e in evals]
    # 预算外:逐条留 record_id/通道(不是化学失败;重放同预算必同序)
    entry["budget_not_assessed"] = [
        {"record_id": r.get("record_id", ""),
         "asset_sha256": r.get("asset_sha256", ""),
         "line_no": r.get("line_no"),
         "find_channels": list(r.get("find_channels") or []),
         "status": APPLICABILITY_BUDGET_NOT_ASSESSED}
        for r in refs[n_eval:]]
    entry["n_budget_not_assessed"] = len(entry["budget_not_assessed"])
    applicable = [e for e in evals if e["status"] == APPLICABILITY_APPLICABLE]
    ambiguous = [e for e in evals if e["status"] == APPLICABILITY_AMBIGUOUS]
    unavailable = [e for e in evals
                   if e["status"] == APPLICABILITY_UNAVAILABLE]
    inapplicable = [e for e in evals
                    if e["status"] == APPLICABILITY_INAPPLICABLE]
    targets = sorted({e["target_smiles"] for e in applicable})
    if len(targets) > 1:
        entry["status"] = APPLICABILITY_AMBIGUOUS
        entry["fallback_reason"] = FALLBACK_COMPETING_TRANSFORMS
        entry["reject_reasons"] = [f"competing_targets:{len(targets)}"]
        return entry
    if applicable:
        chosen = applicable[0]
        entry["status"] = APPLICABILITY_APPLICABLE
        entry["fallback_reason"] = ""
        entry["unverified_conditions"] = sorted({
            c for e in applicable for c in e["unverified_conditions"]})
        entry["selected"] = {
            "record_id": chosen["record_id"],
            "donor_index": chosen["donor_index"],
            "asset_file": chosen["asset_file"],
            "asset_sha256": chosen["asset_sha256"],
            "line_no": chosen["line_no"],
            "mapping_quality": chosen["mapping_quality"],
            "target_smiles": chosen["target_smiles"],
            "alignment": chosen["selected_result"],
            "transform": chosen["transform"],
            "n_supporting_donors": len(applicable),
            # R1 修复:所选供体的完整引用(映射模板随行)。相似通道的
            # 载体卡 evidence_id 不在检索 evidences 中,prediction 任务
            # 组装据此在任务内合成载体,不再依赖检索产物携带该卡
            "donor_ref": {
                "record_id": chosen["record_id"],
                "donor_index": chosen["donor_index"],
                "asset_file": chosen["asset_file"],
                "asset_sha256": chosen["asset_sha256"],
                "line_no": chosen["line_no"],
                "mapping_quality": chosen["mapping_quality"],
                "mapped_lhs": chosen.get("mapped_lhs", ""),
                "mapped_rhs": chosen.get("mapped_rhs", ""),
                "find_channels": list(chosen.get("find_channels") or []),
                "similarity": chosen.get("similarity"),
                "similarity_version": chosen.get("similarity_version", ""),
                "similarity_rank": chosen.get("similarity_rank"),
            },
        }
        return entry
    if ambiguous:
        entry["status"] = APPLICABILITY_AMBIGUOUS
        entry["fallback_reason"] = FALLBACK_COMPETING_TRANSFORMS
        return entry
    if unavailable and not inapplicable:
        entry["status"] = APPLICABILITY_UNAVAILABLE
        entry["fallback_reason"] = FALLBACK_APPLICABILITY_UNKNOWN
        entry["reject_reasons"] = sorted({
            r for e in unavailable for r in e["reject_reasons"]})
        return entry
    entry["status"] = APPLICABILITY_INAPPLICABLE
    entry["fallback_reason"] = FALLBACK_APPLICABILITY_FAILED
    entry["reject_reasons"] = sorted({
        r for e in inapplicable for r in e["reject_reasons"]})
    return entry


def _donor_key(ref: dict) -> tuple:
    """供体唯一键(任务书 §2:同一资产 SHA + 行号 + record_id 只评估一次;
    不同记录不得因 SMILES 相同误合并)。"""
    return (str(ref.get("asset_sha256", "")),
            ref.get("line_no"),
            str(ref.get("record_id", "")))


def build_eligibility(evidences: list[dict], substrate_smiles: str,
                      policy: ApplicabilityPolicy | None = None,
                      *, similar_refs: list[dict] | None = None) -> dict:
    """一个父节点的类比资格裁决(纯函数;结果整体不可变落盘)。

    卡评估序(任务书 §2 Phase D):**resolved 卡优先**(唯一模板 + 已对齐,
    证据最充分;新通道不得挤掉)→ **reactant_similar 通道供体**(相似度
    降序,底物-反应物结构相似是类比的前提)→ 其余预测卡((retrieval_rank,
    evidence_id))。供体预算 ``max_donor_candidates`` 跨卡跨通道共享;
    同一 (asset_sha256, line_no, record_id) 只评估一次(多通道召回合并
    find_channels)。

    ``similar_refs``:analog_source.similar_donor_refs 的召回列表(通道
    已按相似度降序);空/缺省 = C0 旧检索配置。新通道挤掉"无新通道时
    本会评估的供体"逐条记入 ``displaced_by_similar_channel``。

    若按纯 rank 序评估,排位靠前的规则卡会先耗尽预算,真正的 resolved
    卡(旧路由实际选中的供体)反而得不到评估 —— 封存首跑 43/66 任务
    属此类预算饥饿,属实现缺陷而非化学事实(Phase C §6.1 已修复)。
    """
    pol = policy or ApplicabilityPolicy()
    predictive = [e for e in evidences
                  if e.get("kind") in ("rule_application", "analog_reaction")]
    resolved_first = sorted(
        (e for e in predictive if e.get("mapping_status") == "resolved"),
        key=lambda e: (e.get("retrieval_rank", 0), e.get("evidence_id", "")))
    rest = sorted(
        (e for e in predictive if e.get("mapping_status") != "resolved"),
        key=lambda e: (e.get("retrieval_rank", 0), e.get("evidence_id", "")))

    # ---- 通道合并:按消费序(resolved → similar → rest)登记供体载体 ----
    # 同一 (asset_sha256, line_no, record_id) 只评估一次:首次出现处为
    # 载体,后续通道召回就地合并 find_channels(标签双向完整)。
    similar_refs = [r for r in (similar_refs or [])
                    if r.get("mapped_lhs") and r.get("mapped_rhs")]
    by_key: dict[tuple, dict] = {}

    def _merge_into(key: tuple, incoming: dict) -> None:
        base = by_key[key]
        for ch in (incoming.get("find_channels") or []):
            if ch not in (base.get("find_channels") or []):
                base.setdefault("find_channels", []).append(ch)
        if incoming.get("similarity") is not None \
                and base.get("similarity") is None:
            base["similarity"] = incoming.get("similarity")
            base["similarity_version"] = incoming.get(
                "similarity_version", "")
            base["similarity_rank"] = incoming.get("similarity_rank")

    def _carrier_cards(base_card: dict, refs_raw: list[dict]) -> list[dict]:
        """按序登记 refs;返回 [card'](donor_refs 已替换为去重合并列表)。"""
        out_refs: list[dict] = []
        for r in refs_raw:
            if not (r.get("mapped_lhs") and r.get("mapped_rhs")):
                continue
            key = _donor_key(r)
            if key in by_key:
                _merge_into(key, r)
                continue
            by_key[key] = r
            out_refs.append(r)
        if not out_refs:
            return []
        card = dict(base_card)
        card["donor_refs"] = out_refs
        return [card]

    similar_base = {
        "evidence_id": "reactant_similar_channel",
        "retrieval_rank": None,
        "mapping_status": "similar_channel",
        "mapping_reason": "reactant_similar:substrate_reactant_similarity",
    }
    similar_active = bool(similar_refs)
    ordered_cards: list[dict] = []
    for card in resolved_first:
        ordered_cards += _carrier_cards(card, card.get("donor_refs") or [])
    if similar_active:
        ordered_cards += _carrier_cards(similar_base, similar_refs)
    for card in rest:
        ordered_cards += _carrier_cards(card, card.get("donor_refs") or [])

    budget = int(pol.max_donor_candidates)
    assess_cache: dict = {}
    cards: list[dict] = []
    for card in ordered_cards:
        if budget <= 0:
            # 预算已尽:剩余卡整体按 budget_not_assessed 留痕(逐 ref)
            entry = {
                "evidence_id": card.get("evidence_id", ""),
                "retrieval_rank": card.get("retrieval_rank"),
                "mapping_status": card.get("mapping_status", ""),
                "mapping_reason": card.get("mapping_reason", ""),
                "n_donor_refs": len(card.get("donor_refs") or []),
                "n_donor_refs_evaluated": 0,
                "n_budget_not_assessed": len(card.get("donor_refs") or []),
                "donor_evals": [],
                "budget_not_assessed": [
                    {"record_id": r.get("record_id", ""),
                     "asset_sha256": r.get("asset_sha256", ""),
                     "line_no": r.get("line_no"),
                     "find_channels": list(r.get("find_channels") or []),
                     "status": APPLICABILITY_BUDGET_NOT_ASSESSED}
                    for r in (card.get("donor_refs") or [])],
                "status": APPLICABILITY_UNAVAILABLE,
                "fallback_reason": FALLBACK_NO_MAPPING,
                "reject_reasons": [],
                "unverified_conditions": [],
            }
            cards.append(entry)
            continue
        entry = evaluate_card(card, substrate_smiles, budget,
                              assess_cache=assess_cache)
        budget -= entry["n_donor_refs_evaluated"]
        cards.append(entry)

    # ---- displaced 留痕:无相似通道时本会评估的供体,被新通道挤掉者 ----
    displaced: list[dict] = []
    if similar_active:
        legacy_evaluated: list[tuple] = []
        legacy_budget = int(pol.max_donor_candidates)
        for card in resolved_first + rest:
            refs = [r for r in (card.get("donor_refs") or [])
                    if r.get("mapped_lhs") and r.get("mapped_rhs")]
            legacy_evaluated.extend(_donor_key(r)
                                    for r in refs[:legacy_budget])
            legacy_budget -= min(len(refs), legacy_budget)
        actual_evaluated = {
            _donor_key(r) for c in cards
            for r in (c.get("donor_evals") or [])
        }
        displaced = [
            {"asset_sha256": k[0], "line_no": k[1], "record_id": k[2]}
            for k in legacy_evaluated if k not in actual_evaluated]

    applicable = [c for c in cards if c["status"] == APPLICABILITY_APPLICABLE]
    targets = sorted({c["selected"]["target_smiles"] for c in applicable})
    block = {
        "schema_version": APPLICABILITY_VERSION,
        "task_kind": "analogy_eligibility",
        "policy": pol.to_dict(),
        "n_predictive_cards": len(predictive),
        "n_cards_evaluated": len(cards),
        "n_similar_channel_refs": len(similar_refs),
        "displaced_by_similar_channel": displaced,
        "cards": cards,
        "status": APPLICABILITY_UNAVAILABLE,
        "fallback_reason": FALLBACK_NO_MAPPING,
        "selected": None,
        "alternatives": [],
    }
    if len(targets) > 1:
        block["status"] = APPLICABILITY_AMBIGUOUS
        block["fallback_reason"] = FALLBACK_COMPETING_TRANSFORMS
        return block
    if applicable:
        chosen = applicable[0]
        block["status"] = APPLICABILITY_APPLICABLE
        block["fallback_reason"] = ""
        block["selected"] = {
            "evidence_id": chosen["evidence_id"],
            **chosen["selected"],
        }
        # 同卡内落选供体的拒因摘要(任务书 §3:保留其它评估过的供体及拒因)
        rejected_donors = [
            {"record_id": e["record_id"], "status": e["status"],
             "reject_reasons": e["reject_reasons"][:6],
             "transform_reason": e.get("transform_reason", "")}
            for e in chosen["donor_evals"]
            if e["record_id"] != chosen["selected"]["record_id"]]
        block["alternatives"] = rejected_donors + [
            {"evidence_id": c["evidence_id"], "status": c["status"],
             "fallback_reason": c["fallback_reason"],
             "reject_reasons": c["reject_reasons"][:6]}
            for c in cards if c is not chosen]
        return block
    # 无适用者:按最具体的拒因落 fallback
    statuses = {c["status"] for c in cards}
    if APPLICABILITY_AMBIGUOUS in statuses:
        block["status"] = APPLICABILITY_AMBIGUOUS
        block["fallback_reason"] = FALLBACK_COMPETING_TRANSFORMS
    elif APPLICABILITY_INAPPLICABLE in statuses:
        block["status"] = APPLICABILITY_INAPPLICABLE
        block["fallback_reason"] = FALLBACK_APPLICABILITY_FAILED
    elif cards and all(c["fallback_reason"] == FALLBACK_NO_MAPPING
                       for c in cards):
        # 所有预测卡都没有带映射的供体引用:no_mapping 是最具体的拒因
        block["status"] = APPLICABILITY_UNAVAILABLE
        block["fallback_reason"] = FALLBACK_NO_MAPPING
    elif cards:
        block["status"] = APPLICABILITY_UNAVAILABLE
        block["fallback_reason"] = (
            FALLBACK_MAPPING_AMBIGUOUS
            if any(c["mapping_status"] == "ambiguous" for c in cards)
            else FALLBACK_APPLICABILITY_UNKNOWN)
        block["reject_reasons"] = sorted({
            r for c in cards for r in (c["reject_reasons"] or [])})[:8]
    return block


# 兼容读取(任务书 §5):旧检索卡/旧决策缺资格块一律按 not_assessed 处理
APPLICABILITY_NOT_ASSESSED = "not_assessed"


def read_applicability_compat(record: dict) -> dict:
    """旧卡/旧决策的兼容读取:缺资格块 → unavailable/not_assessed。

    旧 run 不追写、不追认;新 run 由 classify_evidence 重算并落盘。
    """
    block = record.get("analogy_eligibility") if isinstance(record, dict) \
        else None
    if block is None:
        return {"schema_version": APPLICABILITY_VERSION,
                "status": APPLICABILITY_UNAVAILABLE,
                "fallback_reason": FALLBACK_APPLICABILITY_UNKNOWN,
                "assessed": APPLICABILITY_NOT_ASSESSED}
    return block
