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
