"""候选证据卡（Plan v1 §2.1 落地；设计书
``docs/EVIDENCE_CARD_DESIGN_NOTE_2026-10-15.md``；任务书
``docs/TASK_EVIDENCE_CARD_IMPL_2026-10-15.md``）。

一句话：把系统里**已经在线可得**的确定性事实（池 spec / prepared 假设
装配 / 底物 RDKit 确定性计算），组织成候选证据字段，注入唯一那次
decide 调用的用户载荷——候选集冻结不动（池/检索/排序/去重/run_inputs
零变化），只改信息表达。

范围纪律：
- 纯函数：同输入 ⇒ 同证据 dict（无随机/无时序/全部列表显式定序；
  载荷层 json.dumps sort_keys 兜底）；
- **零金标零题面**：字段只来自系统在线事实（spec / prepared /
  substrate_smiles 的 RDKit 计算 / substrate_profile 在线值）；缺失 =
  字面 ``unknown``（本模块 UNKNOWN 常量），禁止编造（EC / 条件 /
  记录状态等一律不出现——证据面没有任何此类来源）;
- **描述符纪律**（Plan v1）：Gasteiger 部分电荷等计算描述符只作参考
  字段（字段名自带 ``_reference``），不得表述为确定位点/证明——语义
  约束由提示词规则段同步声明（real_model 证据规则段）;
- 不可在线获得的事实**不做**（donor 匹配层级 strict_exact/cn、
  EAWAG/corpus 通道细分——见设计书 §四矛盾停点;P1 修复轮措辞纠正:
  部分通道事实可得〔corpus 路径写 spec.corpus 块、donor_match_kind
  whole/component 在〕,但完整恢复尚未证明,v1 范围不纳入）,不硬造;
- 判分侧/池构建/检索零接触：本模块只被 runflow decide 载荷装配
  （``_call_real_fetch``）消费，decide 与格式反馈轮共用同一入口。

schema：``candidate-evidence-2``（载荷顶层
``candidate_evidence_schema_version`` 披露；演进 ⇒ 显式升版。
P1 修复轮 2026-10-15 由 -1 升 -2：未知系数 null→字面 unknown、
非有限电荷→字面 unknown 属载荷编码语义变化）。
"""

from __future__ import annotations

import copy
import math

from .controlled_vocab import EDIT_OPS
from .hypothesis import PARTICIPANT_ROLE_PRINCIPAL_PRODUCT

# 编辑四操作(单一来源 = controlled_vocab;渲染判别用,零字面量)
_OP_BREAK, _OP_FORM, _OP_CHANGE, _OP_ADD = EDIT_OPS

UNKNOWN = "unknown"

CANDIDATE_EVIDENCE_SCHEMA_VERSION = "candidate-evidence-2"
# 底物描述符表版本（SMARTS 表/极值窗口等计算口径演进 ⇒ 显式升版）
CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION = "candidate-evidence-descr-2"

# 每类官能团最多渲染的命中条数（有界载荷;超出只计 n_hits,截断确定）
_MAX_MATCHES_PER_CLASS = 8
# Gasteiger 极值各端最多渲染的原子数
_MAX_CHARGE_EXTREMES = 3

# 官能团/局部环境档案 SMARTS 表（固定顺序 = 渲染顺序,内容身份一部分;
# 类间允许结构重叠——每类独立如实报告命中,不做互斥归约）。
# 注意:类名只进载荷不进提示词;SMARTS 与 RDKit 版本共同钉住计算口径。
_FUNCTIONAL_GROUP_TABLE: tuple[tuple[str, str], ...] = (
    ("carboxylic_acid", "[CX3](=O)[OX2H1]"),
    ("ester", "[CX3](=O)[OX2H0][#6]"),
    ("amide", "[CX3](=O)[NX3]"),
    ("ketone", "[#6][CX3](=O)[#6]"),
    ("aldehyde", "[CX3H1](=O)[#6]"),
    ("hydroxyl_oh", "[OX2H][#6;!$(C=[OX1])]"),
    ("ether", "[OD2]([#6])[#6]"),
    ("amine_primary", "[NX3;H2;!$(NC=[OX1])][#6]"),
    ("amine_secondary", "[NX3;H1;!$(NC=[OX1])][#6]"),
    ("amine_tertiary", "[NX3;H0;!$(NC=[OX1])]([#6])([#6])[#6]"),
    ("nitrile", "[NX1]#[CX2]"),
    ("nitro", "[$([NX3](=O)=O),$([NX3+](=O)[O-])][#6]"),
    ("thiol", "[SX2H][#6]"),
    ("sulfide", "[SX2]([#6])[#6]"),
    ("halide_f", "[#6][F]"),
    ("halide_cl", "[#6][Cl]"),
    ("halide_br", "[#6][Br]"),
    ("halide_i", "[#6][I]"),
    ("alkene", "[CX3]=[CX3]"),
    ("alkyne", "[CX2]#[CX2]"),
    ("arene_ring", "c1ccccc1"),
)


def _u(value):
    """缺席兜底:None/缺键 ⇒ 字面 unknown(禁止空串/None 冒充事实)。"""
    return UNKNOWN if value is None else value


# ---------------------------------------------------------------- 候选级


def _edit_summary(spec: dict) -> dict:
    """spec.edits 的确定性渲染（编辑变化摘要;同一编辑协议事实源）。"""
    edits = spec.get("edits")
    if not isinstance(edits, list):
        return UNKNOWN
    op_counts: dict[str, int] = {}
    bond_order_changes: list[dict] = []
    added_atoms: list[dict] = []
    bonds_broken = 0
    bonds_formed = 0
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        op = str(edit.get("op") or "")
        op_counts[op] = op_counts.get(op, 0) + 1
        if op == _OP_CHANGE:
            bond_order_changes.append({
                "atom1": str(edit.get("atom1") or ""),
                "atom2": str(edit.get("atom2") or ""),
                "from_order": str(edit.get("from_order") or ""),
                "to_order": str(edit.get("to_order") or ""),
            })
        elif op == _OP_ADD:
            added_atoms.append({
                "new_atom_id": str(edit.get("new_atom_id") or ""),
                "element": str(edit.get("element") or ""),
            })
        elif op == _OP_BREAK:
            bonds_broken += 1
        elif op == _OP_FORM:
            bonds_formed += 1
    return {
        "n_edits": len(edits),
        "op_counts": dict(sorted(op_counts.items())),
        "bonds_broken": bonds_broken,
        "bonds_formed": bonds_formed,
        "bond_order_changes": bond_order_changes,
        "added_atoms": added_atoms,
    }


def _participants_evidence(spec: dict, prepared: dict | None) -> dict:
    """完整参与物角色与来源（prepared 假设装配 = 单一构建源直读）。"""
    if not isinstance(prepared, dict):
        return UNKNOWN
    hypothesis = prepared.get("hypothesis")
    participants = getattr(hypothesis, "participants", None)
    if not participants:
        return UNKNOWN
    states = prepared.get("states") or {}
    rows: list[dict] = []
    for participant in participants:
        p = participant.to_dict() if hasattr(participant, "to_dict") \
            else dict(participant)
        state_ref = str(p.get("state_ref") or "")
        state = states.get(state_ref) if isinstance(states, dict) else None
        smiles = getattr(state, "smiles_isomeric", None)
        coefficient = p.get("coefficient")
        rows.append({
            "side": str(p.get("side") or ""),
            "role": str(p.get("role") or ""),
            # P1-1 修复(2026-10-15):系数缺失(合法装配的 None/unknown,
            # recorded_source 库记录无配平系数/production 默认副产物)
            # 渲染层转字面 unknown——底层对象零改动,coefficient_status
            # 原语义保留;已知系数维持原值(原 str 化口径不变)。
            "coefficient": (str(coefficient)
                            if coefficient is not None else UNKNOWN),
            "coefficient_status": str(p.get("coefficient_status") or ""),
            "smiles": _u(smiles),
        })
    return {"participants": rows}


def _source_evidence(spec: dict) -> dict:
    """来源事实:key 前缀/origin_group_key/alignment.ref 确定性派生。

    设计书 §四(P1 修复轮措辞纠正):EAWAG/corpus 通道细分与 donor
    匹配层级——部分通道事实可得但完整恢复尚未证明 ⇒ v1 范围不纳入;
    只呈现 spec 上真实在位的来源字段。
    """
    key = str(spec.get("key") or "")
    origin_group_key = str(spec.get("origin_group_key") or "")
    alignment = spec.get("alignment") if isinstance(
        spec.get("alignment"), dict) else {}
    ref = str(alignment.get("ref") or "")
    if key.startswith("tpl-") or origin_group_key.startswith(
            "analog-template:"):
        source_kind = "analog_template"
    elif key.startswith("rec-") and ref.startswith("recorded-inferred:"):
        source_kind = "recorded_inferred"
    else:
        source_kind = UNKNOWN
    return {
        "source_kind": source_kind,
        "transformation_ref": _u(spec.get("transformation_ref")),
        "origin_group_key": _u(spec.get("origin_group_key")),
        "alignment_ref": _u(alignment.get("ref")),
    }


def _alignment_quality(spec: dict) -> dict:
    """对齐状态与质量/枚举截断信号（spec.compile 在线诊断块直读）。"""
    alignment = spec.get("alignment") if isinstance(
        spec.get("alignment"), dict) else {}
    compile_diag = spec.get("compile") if isinstance(
        spec.get("compile"), dict) else {}
    donor_to_current = alignment.get("donor_to_current")
    stereo_applied = compile_diag.get("stereo_dissolution_applied")
    truncated = compile_diag.get("truncated")
    return {
        "status": _u(alignment.get("status")),
        "mapping_origin": _u(compile_diag.get("mapping_origin")),
        "n_alignments_total": _u(compile_diag.get("n_alignments_total")),
        "n_equivalent_alignments": _u(
            compile_diag.get("n_equivalent_alignments")),
        "enumeration_truncated": _u(truncated),
        "stereo_dissolution_applied": (
            len(stereo_applied) if isinstance(stereo_applied, list)
            else UNKNOWN),
        "n_donor_atoms_mapped": (
            len(donor_to_current)
            if isinstance(donor_to_current, dict) else UNKNOWN),
    }


def _conditions_and_scope(spec: dict) -> dict:
    """条件与证明范围（在线值;键缺席=unknown,键在位=真值可为空表）。"""
    participant_list_status = spec.get("participant_list_status")
    step_scope = spec.get("step_scope")
    requirements = spec.get("requirements")
    return {
        "requirements": (
            copy.deepcopy(requirements)
            if isinstance(requirements, list) else UNKNOWN),
        "participant_list_status": str(
            participant_list_status if participant_list_status is not None
            else "partial"),
        "step_scope": str(
            step_scope if step_scope is not None else "net_reaction"),
    }


def candidate_evidence_payload(*, spec: dict,
                               prepared: dict | None = None) -> dict:
    """单池条目 → 候选级证据卡（纯函数;零金标零题面）。

    - spec:冻结池条目（plan.pools 成员;只读,本函数不修改）;
    - prepared:prepare_hypothesis 产物（participants/states 单一构建
      源;缺席 ⇒ 参与物面 unknown,不重派生第二套装配）;
    - 任何事实缺席 ⇒ 字面 ``unknown``;输出经 json.dumps(sort_keys)
      渲染后同输入字节全等（Phase C 探针双跑验证）。
    """
    if not isinstance(spec, dict):
        return {"edit_summary": UNKNOWN, "participants": UNKNOWN,
                "source": UNKNOWN, "alignment_quality": UNKNOWN,
                "conditions_and_scope": UNKNOWN}
    evidence: dict = {
        "edit_summary": _edit_summary(spec),
        "source": _source_evidence(spec),
        "alignment_quality": _alignment_quality(spec),
        "conditions_and_scope": _conditions_and_scope(spec),
    }
    participants_evidence = _participants_evidence(spec, prepared)
    if isinstance(participants_evidence, dict):
        evidence["participants"] = participants_evidence.get(
            "participants", UNKNOWN)
    else:
        evidence["participants"] = participants_evidence
    return evidence


# ---------------------------------------------------------------- 底物级


def substrate_evidence_payload(substrate_smiles: str, *,
                               substrate_profile=None) -> dict:
    """底物官能团/局部环境档案 + 参考描述符（RDKit 确定性计算）。

    - substrate_smiles:题面底物（唯一输入;零金标零题面消费）;
    - substrate_profile:runflow decide 已建的底物档案（在线值直读:
      representation_fidelity/condition_keys_known;缺席 ⇒ unknown,
      不重派生第二套条件事实）;
    - 渲染/计算失败 ⇒ 对应字段 unknown（不猜、不伪造）;
    - 描述符纪律:Gasteiger 字段名自带 ``_reference``——参考字段,
      非指派位点/证明（提示词规则段同步声明）。
    """
    from rdkit import Chem
    from rdkit import RDLogger

    RDLogger.DisableLog("rdApp.*")
    evidence: dict = {
        "descriptor_version": CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION,
        "substrate_render_ok": False,
        "functional_groups": [],
        "gasteiger_charges_reference": UNKNOWN,
        "element_counts": UNKNOWN,
        "molecular_formula": UNKNOWN,
    }
    if substrate_profile is not None:
        evidence["representation_fidelity"] = dict(
            getattr(substrate_profile, "representation_fidelity", {}) or {})
        evidence["condition_keys_known"] = list(
            getattr(substrate_profile, "condition_keys_known", []) or [])
    else:
        evidence["representation_fidelity"] = UNKNOWN
        evidence["condition_keys_known"] = UNKNOWN
    try:
        from ..services.atom_tool import render

        current = render(str(substrate_smiles), "S")
        mol = Chem.MolFromSmiles(str(substrate_smiles))
        if current is None or mol is None:
            return evidence
        idx_to_id = {int(idx): str(atom_id) for atom_id, idx
                     in current.atom_id_map.items()}
        evidence["substrate_render_ok"] = True
        # 官能团 SMARTS 命中表(类顺序 = 表定义序;命中按原子 idx 序)
        fg_rows: list[dict] = []
        for class_name, smarts in _FUNCTIONAL_GROUP_TABLE:
            patt = Chem.MolFromSmarts(smarts)
            if patt is None:
                continue
            matches = mol.GetSubstructMatches(patt, uniquify=True)
            if not matches:
                continue
            fg_rows.append({
                "class": class_name,
                "smarts": smarts,
                "n_hits": len(matches),
                "matches": [[idx_to_id.get(int(idx), UNKNOWN)
                             for idx in match]
                            for match in matches[:_MAX_MATCHES_PER_CLASS]],
            })
        evidence["functional_groups"] = fg_rows
        # Gasteiger 部分电荷(参考描述符;极值窗口,原子 ID 可回查)
        try:
            from rdkit.Chem import AllChem

            AllChem.ComputeGasteigerCharges(mol)
            heavy: list[tuple[float, str]] = []
            charges_usable = True
            for atom in mol.GetAtoms():
                idx = atom.GetIdx()
                atom_id = idx_to_id.get(idx)
                if atom_id is None:
                    continue
                charge = float(atom.GetDoubleProp("_GasteigerCharge"))
                # P1-2 修复(2026-10-15):ComputeGasteigerCharges 对部分
                # 元素(如 Se)合法解析但不抛异常地返回非有限值——逐值
                # math.isfinite 核验;任一非有限 ⇒ 整个电荷描述符降
                # unknown(降级合同;分子式/元素组成/官能团等其它事实
                # 照常输出,不全面拒绝合法底物,不许 NaN 冒充事实)。
                if not math.isfinite(charge):
                    charges_usable = False
                    break
                heavy.append((round(charge, 4), atom_id))
            if not charges_usable:
                evidence["gasteiger_charges_reference"] = UNKNOWN
            else:
                heavy.sort()
                evidence["gasteiger_charges_reference"] = {
                    "min": heavy[0][0] if heavy else UNKNOWN,
                    "max": heavy[-1][0] if heavy else UNKNOWN,
                    "mean": (round(sum(c for c, _ in heavy) / len(heavy), 4)
                             if heavy else UNKNOWN),
                    "lowest": [{"atom_id": a, "charge": c}
                               for c, a in heavy[:_MAX_CHARGE_EXTREMES]],
                    "highest": [{"atom_id": a, "charge": c}
                                for c, a in heavy[-_MAX_CHARGE_EXTREMES:]],
                }
        except Exception:  # noqa: BLE001 —— 描述符失败只降级本字段
            evidence["gasteiger_charges_reference"] = UNKNOWN
        # 元素组成/分子式(与 substrate_profile 同一事实源口径)
        try:
            from .audit import element_counts_full

            evidence["element_counts"] = {
                k: int(v) for k, v in sorted(
                    element_counts_full(mol).items())}
        except Exception:  # noqa: BLE001
            evidence["element_counts"] = UNKNOWN
        try:
            from rdkit.Chem.rdMolDescriptors import CalcMolFormula

            evidence["molecular_formula"] = str(CalcMolFormula(mol))
        except Exception:  # noqa: BLE001
            evidence["molecular_formula"] = UNKNOWN
    except Exception:  # noqa: BLE001 —— 渲染失败:字段如实 unknown
        return evidence
    return evidence


# ================================================================
# v2（P2 离线实施，2026-10-21）
# ================================================================
# 冻结设计：docs/TASK_EVIDENCE_CARD_V2_DESIGN_2026-10-17.md（SHA-256
# 37d85958e02ca5263abb4c0f1a7a98a2177cea73ab451dcd77e74a43f332c4f4）
# + docs/EVIDENCE_CARD_V2_DESIGN_CODEX_FINAL_2026-10-18.md。
#
# v2 与 v1 的边界（off 路径零漂移）：
# - 不修改 v1 的任何函数/常量/表；v1 调用方不传 v2 参数 ⇒ 输出逐字节同；
# - v2 只由 runflow 的 evidence_card_version="v2" 分支消费；
# - v2 字段面严格按任务书 §三：删 Gasteiger/分子式/元素组成/冗余来源
#   与数组；participants 保真紧凑；alignment 只留 status；新增主产物级
#   FG 类集合 delta 与分子式/碳氧化态 delta。
#
# 描述符纪律（v2 版）：FG 类名/命中数、formula 差值、碳氧化态都只是
# 图级确定性事实，不是指派位点/机制/配平/氧化还原证明；提示词 v2 段
# 同步声明。零金标零题面：只消费 spec / prepared / substrate_smiles /
# substrate_profile 在线事实，缺失一律字面 unknown。

CANDIDATE_EVIDENCE_SCHEMA_VERSION_V2 = "candidate-evidence-3"
CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2 = "candidate-evidence-descr-3"

# v2 官能团表：类顺序 = 渲染顺序/内容身份一部分；允许跨类重叠。
# 质子化容忍（设计 §四.1 前置）：羧酸/羧酸根、伯/仲/叔胺/铵共用同一
# 类。化学修复（2026-10-21 化学复审 P1/P2）：
# - carboxylic_acid 要求羧基碳的另一个取代基是 C 或 H（甲酸经 H1
#   分支），排除碳酸/碳酸氢盐/碳酸酯/氨基甲酸(酯)等「C(=O)O」但
#   另一取代基为 O/N 的碳酸衍生物；否则 carbonate 一个碳会给 2 个
#   假阳性 hit（v2 相对 v1 的回归）。
# - 胺类排除 N–C(=X)（X = O/S/N）：除酰胺 C=O 外，同时排除硫代
#   酰胺/硫脲（C=S）、脒/胍（C=N），避免胍基 N 被拆成多个胺类。
# 其余 17 类 SMARTS 与 v1 表逐字同。
_FUNCTIONAL_GROUP_TABLE_V2: tuple[tuple[str, str], ...] = (
    ("carboxylic_acid",
     "[$([CX3H1](=O)[OX2H1,OX1-]),"
     "$([CX3](=O)([OX2H1,OX1-])[#6])]"),
    ("ester", "[CX3](=O)[OX2H0][#6]"),
    ("amide", "[CX3](=O)[NX3]"),
    ("ketone", "[#6][CX3](=O)[#6]"),
    ("aldehyde", "[CX3H1](=O)[#6]"),
    ("hydroxyl_oh", "[OX2H][#6;!$(C=[OX1])]"),
    ("ether", "[OD2]([#6])[#6]"),
    ("amine_primary",
     "[$([NX3;H2]),$([NX4+;H3]);!$(N[#6]=[O,S,N])][#6]"),
    ("amine_secondary",
     "[$([NX3;H1]),$([NX4+;H2]);!$(N[#6]=[O,S,N])]([#6])[#6]"),
    ("amine_tertiary",
     "[$([NX3;H0]),$([NX4+;H1]);!$(N[#6]=[O,S,N])]([#6])([#6])[#6]"),
    ("nitrile", "[NX1]#[CX2]"),
    ("nitro", "[$([NX3](=O)=O),$([NX3+](=O)[O-])][#6]"),
    ("thiol", "[SX2H][#6]"),
    ("sulfide", "[SX2]([#6])[#6]"),
    ("halide_f", "[#6][F]"),
    ("halide_cl", "[#6][Cl]"),
    ("halide_br", "[#6][Br]"),
    ("halide_i", "[#6][I]"),
    ("alkene", "[CX3]=[CX3]"),
    ("alkyne", "[CX2]#[CX2]"),
    ("arene_ring", "c1ccccc1"),
)

_CLASS_ORDER_V2: dict[str, int] = {
    name: i for i, (name, _smarts) in enumerate(_FUNCTIONAL_GROUP_TABLE_V2)}

# 碳氧化态可用元素域（保守：N/S/P/金属等不猜；只做甲酰基式平均碳
# 氧化态，且两侧均含碳）。H=+1、O=-2、卤素=-1、总形式电荷入式。
_CARBON_OXIDATION_ELEMENTS_V2 = frozenset(
    {"C", "H", "O", "F", "Cl", "Br", "I"})

# 碳氧化态 unknown 的内部原因码（化学复审 P6/P7）。
# 载荷仍只渲染字面 "unknown"（不新增字段、不改 schema/descriptor）：
# 逐值原因外显属字段结构变更，按任务约束留待契约轮，不在本单擅自加。
# 这些码用于实现自证/证据探针/报告中的 unknown reason 清单。
_CARBON_OXIDATION_REASON_COMPUTED = "computed"
_CARBON_OXIDATION_REASON_UNAVAILABLE = "value_unavailable"
_CARBON_OXIDATION_REASON_NO_CARBON = "no_carbon"
_CARBON_OXIDATION_REASON_ELEMENT_OUT_OF_DOMAIN = "element_out_of_domain"
_CARBON_OXIDATION_REASON_OPEN_SHELL = "open_shell"
_CARBON_OXIDATION_REASON_PEROXIDE_OO_BOND = "peroxide_oo_bond"
_CARBON_OXIDATION_REASON_HYPERVALENT_HALOGEN = "hypervalent_halogen"

# Pauling 电负性（只用于卤素氧化态守卫；域内元素齐全）。
_PAULING_ELECTRONEGATIVITY_V2: dict[str, float] = {
    "F": 3.98, "O": 3.44, "Cl": 3.16, "N": 3.04, "Br": 2.96,
    "I": 2.66, "C": 2.55, "H": 2.20,
}
_HALOGEN_ELEMENTS_V2 = ("F", "Cl", "Br", "I")


def _halogen_oxidation_state_v2(atom) -> int | None:
    """按 Pauling 电负性归属键电子，估单个卤素的整数氧化态。

    供「卤素 = -1」假设守卫使用：只有氧化态确为 -1 的卤素（C–X、
    卤离子）才允许沿用甲酰基式公式；高价卤素（ClO4 的 +7、三配位
    氯鎓的 -2、次氯酸酯 O–Cl 的 +1 等）一律返回 None ⇒ 上层降
    unknown，不猜值。非整数键级/域外邻居返回 None（保守）。
    """
    symbol = atom.GetSymbol()
    if symbol not in _HALOGEN_ELEMENTS_V2:
        return None
    electronegativity_self = _PAULING_ELECTRONEGATIVITY_V2[symbol]
    oxidation_state = int(atom.GetFormalCharge())
    for bond in atom.GetBonds():
        neighbor = bond.GetOtherAtom(atom)
        electronegativity_other = _PAULING_ELECTRONEGATIVITY_V2.get(
            neighbor.GetSymbol())
        if electronegativity_other is None:
            return None
        order = float(bond.GetBondTypeAsDouble())
        if order not in (1.0, 2.0, 3.0):
            return None
        if electronegativity_other > electronegativity_self:
            oxidation_state += int(order)
        elif electronegativity_other < electronegativity_self:
            oxidation_state -= int(order)
    # 卤素上的隐式 H（极少见）比卤素电负性低，按得电子减 1。
    oxidation_state -= int(atom.GetNumImplicitHs())
    return oxidation_state


def _has_peroxide_bond_v2(mol) -> bool:
    """是否存在 O–O 单键（过氧化物/氢过氧化物/过氧酸）。

    O–O 键两端的 O 各为 -1（不是甲酰基式假设的 -2）；存在即降
    unknown（化学复审 C2）。
    """
    from rdkit import Chem

    for bond in mol.GetBonds():
        if bond.GetBondType() != Chem.BondType.SINGLE:
            continue
        begin = bond.GetBeginAtom().GetSymbol()
        end = bond.GetEndAtom().GetSymbol()
        if begin == "O" and end == "O":
            return True
    return False


def _has_open_shell_v2(mol) -> bool:
    """是否存在未成对电子（自由基/卡宾/开放壳层）。

    RDKit 可解析开放壳层，但「H=+1/O=-2/卤素=-1」的闭壳簿记不适用
    （例：phenoxyl 的 O 自由基是 -1 而非 -2）；存在即降 unknown
    （化学复审 C4）。
    """
    return any(int(atom.GetNumRadicalElectrons()) > 0
               for atom in mol.GetAtoms())


def _carbon_oxidation_state_detail_v2(
        mol, counts: dict[str, int] | None,
        charge: int | None) -> tuple[float | None, str]:
    """平均碳氧化态 + 内部原因码（单一计算源；None ⇒ 载荷 unknown）。

    公式：C_ox = (q − H + 2O + X) / C（H=+1、O=-2、X=卤素=-1）。
    声明域：元素 ⊆ {C,H,O,F,Cl,Br,I} 且 C>0；此外按化学复审
    P6/P7 增加守卫——O–O 单键、非 -1 价卤素、开放壳层一律 unknown
    （不拿「元素在域内」冒充「值可靠」）。原因码只用于内部自证，
    不进载荷（避免字段结构变更）。
    """
    if not isinstance(counts, dict) or charge is None:
        return None, _CARBON_OXIDATION_REASON_UNAVAILABLE
    if set(counts) - _CARBON_OXIDATION_ELEMENTS_V2:
        return None, _CARBON_OXIDATION_REASON_ELEMENT_OUT_OF_DOMAIN
    n_carbon = int(counts.get("C", 0))
    if n_carbon <= 0:
        return None, _CARBON_OXIDATION_REASON_NO_CARBON
    if mol is not None:
        if _has_open_shell_v2(mol):
            return None, _CARBON_OXIDATION_REASON_OPEN_SHELL
        if _has_peroxide_bond_v2(mol):
            return None, _CARBON_OXIDATION_REASON_PEROXIDE_OO_BOND
        for atom in mol.GetAtoms():
            if atom.GetSymbol() not in _HALOGEN_ELEMENTS_V2:
                continue
            if _halogen_oxidation_state_v2(atom) != -1:
                return None, _CARBON_OXIDATION_REASON_HYPERVALENT_HALOGEN
    n_h = int(counts.get("H", 0))
    n_o = int(counts.get("O", 0))
    n_x = sum(int(counts.get(e, 0)) for e in _HALOGEN_ELEMENTS_V2)
    value = round(
        (int(charge) - n_h + 2 * n_o + n_x) / n_carbon, 4)
    return value, _CARBON_OXIDATION_REASON_COMPUTED


def _avg_carbon_oxidation_state_v2(
        mol, counts: dict[str, int] | None,
        charge: int | None) -> float | None:
    """甲酰基式平均碳氧化态；不可靠形态一律 None（调用方渲染 unknown）。

    约定：H=+1、O=-2、卤素=-1、总形式电荷 q；C_ox =
    (q - H + 2O + X) / C。只在两侧均含 C 且元素 ⊆ {C,H,O,F,Cl,Br,I}
    时计算（N/S/P/金属等氧化态依环境而变，不猜）；O–O、非 -1 价
    卤素、开放壳层同样不猜（见 detail 函数）。
    """
    return _carbon_oxidation_state_detail_v2(mol, counts, charge)[0]


def _ordered_classes_v2(classes) -> list[str]:
    """按 v2 表定义序输出类集合（确定性；未知类排最后按字典序）。"""
    return sorted(set(classes), key=lambda c: (_CLASS_ORDER_V2.get(
        str(c), len(_CLASS_ORDER_V2)), str(c)))


def _fg_class_hits_v2(mol) -> dict[str, int]:
    """完整内部匹配的官能团类→命中数（不套 v1 的 8 条渲染截断）。

    同一类可有多条 SMARTS 替代（质子化容忍）；先对每条 pattern 取
    uniquify 命中，再按原子索引元组去重——不同替代命中的同一匹配只
    计一次。跨类重叠独立计数（不互斥）。
    """
    from rdkit import Chem

    out: dict[str, int] = {}
    for class_name, smarts in _FUNCTIONAL_GROUP_TABLE_V2:
        patt = Chem.MolFromSmarts(smarts)
        if patt is None:
            continue
        matches = {
            tuple(int(idx) for idx in match)
            for match in mol.GetSubstructMatches(patt, uniquify=True)}
        if matches:
            out[class_name] = len(matches)
    return out


def _element_counts_v2(mol) -> dict[str, int] | None:
    from .audit import element_counts_full

    try:
        return {str(k): int(v) for k, v in
                sorted(element_counts_full(mol).items())}
    except Exception:  # noqa: BLE001 —— 事实不可得 ⇒ 调用方降 unknown
        return None


def _formal_charge_v2(mol) -> int | None:
    try:
        return int(sum(atom.GetFormalCharge() for atom in mol.GetAtoms()))
    except Exception:  # noqa: BLE001
        return None


def _molecule_facts_v2(mol) -> dict:
    """RDKit mol → v2 图级事实（pure read；不修改 mol）。"""
    counts = _element_counts_v2(mol)
    charge = _formal_charge_v2(mol)
    return {
        "class_hits": _fg_class_hits_v2(mol),
        "element_counts": counts,
        "formal_charge": charge,
        "carbon_oxidation_state": _avg_carbon_oxidation_state_v2(
            mol, counts, charge),
    }


def substrate_facts_v2(substrate_smiles: str) -> dict:
    """底物 v2 图级事实（单一计算源；供底物卡与候选 delta 共用）。

    返回普通 dict（无 RDKit 对象）：
    - ``render_ok``：atom_tool render 与 RDKit 解析同时成功；
    - ``class_hits``：完整内部匹配的类→命中数（render 失败时空 dict）；
    - ``element_counts``/``formal_charge``/``carbon_oxidation_state``：
      不可得为 None（调用方渲染 unknown）。
    """
    facts: dict = {
        "render_ok": False,
        "class_hits": {},
        "element_counts": None,
        "formal_charge": None,
        "carbon_oxidation_state": None,
    }
    try:
        from rdkit import Chem, RDLogger

        RDLogger.DisableLog("rdApp.*")
        from ..services.atom_tool import render

        current = render(str(substrate_smiles), "S")
        mol = Chem.MolFromSmiles(str(substrate_smiles))
        if current is None or mol is None:
            return facts
        facts["render_ok"] = True
        facts["class_hits"] = _fg_class_hits_v2(mol)
        counts = _element_counts_v2(mol)
        charge = _formal_charge_v2(mol)
        facts["element_counts"] = counts
        facts["formal_charge"] = charge
        facts["carbon_oxidation_state"] = _avg_carbon_oxidation_state_v2(
            mol, counts, charge)
    except Exception:  # noqa: BLE001 —— 解析/渲染失败：字段如实 unknown
        return facts
    return facts


def substrate_evidence_from_facts_v2(facts: dict, *,
                                     substrate_profile=None) -> dict:
    """``substrate_facts_v2`` 产物 → 底物 v2 档案卡（单一事实源；runflow
    每題只算一次 facts，底物卡与候选 delta 共用）。"""
    facts = facts if isinstance(facts, dict) else {}
    class_hits = facts.get("class_hits") or {}
    evidence: dict = {
        "descriptor_version": CANDIDATE_EVIDENCE_DESCRIPTOR_VERSION_V2,
        "substrate_render_ok": bool(facts.get("render_ok")),
        "functional_groups": [
            {"class": class_name, "n_hits": int(class_hits[class_name])}
            for class_name in _ordered_classes_v2(class_hits)],
    }
    if substrate_profile is not None:
        evidence["representation_fidelity"] = dict(
            getattr(substrate_profile, "representation_fidelity", {}) or {})
        evidence["condition_keys_known"] = list(
            getattr(substrate_profile, "condition_keys_known", []) or [])
    else:
        evidence["representation_fidelity"] = UNKNOWN
        evidence["condition_keys_known"] = UNKNOWN
    return evidence


def substrate_evidence_payload_v2(substrate_smiles: str, *,
                                  substrate_profile=None) -> dict:
    """底物 v2 档案卡：只留 FG 类名+n_hits（无 smarts/matches/Gasteiger/
    分子式/元素组成）。

    - render 失败 ⇒ ``substrate_render_ok=false`` + 空表（不得读作零命中）；
    - 合法但无命中 ⇒ ``substrate_render_ok=true`` + 空表（真实零命中）；
    - ``n_hits`` 来自完整内部匹配（无 8 条截断）。
    """
    return substrate_evidence_from_facts_v2(
        substrate_facts_v2(substrate_smiles),
        substrate_profile=substrate_profile)


def _edit_summary_v2(spec: dict):
    """v2 紧凑编辑摘要：只留 n_edits/op_counts/bond_order_changes。"""
    edits = spec.get("edits")
    if not isinstance(edits, list):
        return UNKNOWN
    op_counts: dict[str, int] = {}
    bond_order_changes: list[dict] = []
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        op = str(edit.get("op") or "")
        op_counts[op] = op_counts.get(op, 0) + 1
        if op == _OP_CHANGE:
            bond_order_changes.append({
                "atom1": str(edit.get("atom1") or ""),
                "atom2": str(edit.get("atom2") or ""),
                "from_order": str(edit.get("from_order") or ""),
                "to_order": str(edit.get("to_order") or ""),
            })
    return {
        "n_edits": len(edits),
        "op_counts": dict(sorted(op_counts.items())),
        "bond_order_changes": bond_order_changes,
    }


def _participants_evidence_v2(spec: dict, prepared: dict | None):
    """v2 保真紧凑参与物：side/role/coefficient/smiles；删
    coefficient_status；不隐藏行数、不补假条目。"""
    if not isinstance(prepared, dict):
        return UNKNOWN
    hypothesis = prepared.get("hypothesis")
    participants = getattr(hypothesis, "participants", None)
    if not participants:
        return UNKNOWN
    states = prepared.get("states") or {}
    rows: list[dict] = []
    for participant in participants:
        p = participant.to_dict() if hasattr(participant, "to_dict") \
            else dict(participant)
        state_ref = str(p.get("state_ref") or "")
        state = states.get(state_ref) if isinstance(states, dict) else None
        smiles = getattr(state, "smiles_isomeric", None)
        coefficient = p.get("coefficient")
        rows.append({
            "side": str(p.get("side") or ""),
            "role": str(p.get("role") or ""),
            "coefficient": (str(coefficient)
                            if coefficient is not None else UNKNOWN),
            "smiles": _u(smiles),
        })
    return rows


def _principal_product_smiles_v2(spec: dict) -> str | None:
    """取 spec 的指定主产物字段；多组分/空 ⇒ None（delta 降 unknown）。

    编译器 ``compile_donor_template`` 把中心所在组分写入
    ``product_smiles``（s5b_compiler.py:1107 一带）；这里是该字段的
    只读消费，不重新选主产物。
    """
    product = str(spec.get("product_smiles") or "")
    if not product or "." in product:
        return None
    return product


def _functional_group_delta_v2(spec: dict, substrate_facts: dict | None):
    """主产物级 FG 类集合 delta（gained/lost；非命中数变化）。"""
    if not isinstance(substrate_facts, dict) \
            or not substrate_facts.get("render_ok"):
        return UNKNOWN
    substrate_hits = substrate_facts.get("class_hits")
    if not isinstance(substrate_hits, dict):
        return UNKNOWN
    product = _principal_product_smiles_v2(spec)
    if product is None:
        return UNKNOWN
    try:
        from rdkit import Chem, RDLogger

        RDLogger.DisableLog("rdApp.*")
        product_mol = Chem.MolFromSmiles(product)
        if product_mol is None:
            return UNKNOWN
        product_hits = _fg_class_hits_v2(product_mol)
    except Exception:  # noqa: BLE001
        return UNKNOWN
    substrate_classes = set(substrate_hits)
    product_classes = set(product_hits)
    return {
        "scope": PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
        "gained": _ordered_classes_v2(product_classes - substrate_classes),
        "lost": _ordered_classes_v2(substrate_classes - product_classes),
    }


def _product_delta_v2(spec: dict, substrate_facts: dict | None):
    """主产物级分子式/碳氧化态 delta（产物−底物；不可靠 ⇒ unknown）。"""
    if not isinstance(substrate_facts, dict) \
            or not substrate_facts.get("render_ok"):
        return UNKNOWN
    substrate_counts = substrate_facts.get("element_counts")
    if not isinstance(substrate_counts, dict):
        return UNKNOWN
    product = _principal_product_smiles_v2(spec)
    if product is None:
        return UNKNOWN
    try:
        from rdkit import Chem, RDLogger

        RDLogger.DisableLog("rdApp.*")
        product_mol = Chem.MolFromSmiles(product)
        if product_mol is None:
            return UNKNOWN
        product_facts = _molecule_facts_v2(product_mol)
    except Exception:  # noqa: BLE001
        return UNKNOWN
    product_counts = product_facts.get("element_counts")
    if not isinstance(product_counts, dict):
        return UNKNOWN
    formula: dict[str, int] = {}
    for element in sorted(set(substrate_counts) | set(product_counts)):
        diff = int(product_counts.get(element, 0)) - int(
            substrate_counts.get(element, 0))
        if diff:
            formula[element] = diff
    substrate_ox = substrate_facts.get("carbon_oxidation_state")
    product_ox = product_facts.get("carbon_oxidation_state")
    oxidation = (round(float(product_ox) - float(substrate_ox), 4)
                 if substrate_ox is not None and product_ox is not None
                 else UNKNOWN)
    return {
        "scope": PARTICIPANT_ROLE_PRINCIPAL_PRODUCT,
        "formula": formula,
        "carbon_oxidation_state": oxidation,
    }


def candidate_evidence_payload_v2(*, spec: dict,
                                  prepared: dict | None = None,
                                  substrate_facts: dict | None = None) -> dict:
    """单池条目 → v2 候选证据卡（纯函数；零金标零题面）。

    - spec:冻结池条目（plan.pools 成员;只读）;
    - prepared:prepare_hypothesis 产物（参与物单一构建源;缺席 ⇒
      participants=unknown，不重派生第二套装配）;
    - substrate_facts:``substrate_facts_v2`` 产物（runflow 每題算一次
      后传入；缺席 ⇒ FG/formula delta 如实 unknown）;
    - 输出不含 ``source`` 键（S1：卡内来源全删；顶层 transformation_ref
      由 real_model 载荷构建保留）。
    """
    if not isinstance(spec, dict):
        return {
            "edit_summary": UNKNOWN,
            "participants": UNKNOWN,
            "alignment_quality": {"status": UNKNOWN},
            "conditions_and_scope": UNKNOWN,
            "functional_group_delta": UNKNOWN,
            "product_delta": UNKNOWN,
        }
    alignment = spec.get("alignment") if isinstance(
        spec.get("alignment"), dict) else {}
    return {
        "edit_summary": _edit_summary_v2(spec),
        "participants": _participants_evidence_v2(spec, prepared),
        # 只留 status 一枚（v2 冻结裁剪）
        "alignment_quality": {"status": _u(alignment.get("status"))},
        # 条件与证明范围：requirements 缺席=unknown；participant_list_
        # status 必留；step_scope 合并一行（复用 v1 helper，字段面同）
        "conditions_and_scope": _conditions_and_scope(spec),
        # 新增：主产物级 FG 类集合 delta（图级；不扩称完整产物/机制）
        "functional_group_delta": _functional_group_delta_v2(
            spec, substrate_facts),
        # 新增：主产物级分子式/碳氧化态 delta（图级；不可靠=unknown）
        "product_delta": _product_delta_v2(spec, substrate_facts),
    }
