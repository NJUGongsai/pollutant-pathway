"""AtomTool — SMILES ↔ MoleCode 往返与受限编辑核验(确定性,零模型)。

表示基础是本仓 vendored 的 MoleCode molecule 子集(来源/许可见
``vendor/molecode/PROVENANCE.md``;初始化时逐文件核验哈希,fail-closed)。

职责(任务书 §3):
- SMILES → 带稳定原子标识(MoleCode 原子 ID)的编辑视图;渲染期保留
  ``atom_id_map``(RDKit atom idx ↔ MoleCode ID),映射/编辑核验据此进行;
- MoleCode → SMILES;往返身份核对:canonical SMILES(含立体)逐字符一致,
  不一致即判定表示有损 → 拒绝并给原因(如实探测,不做悄悄替代);
- 编辑引用核验:模型编辑引用的原子 ID 必须存在于当前 MoleCode;目标
  MoleCode 不得丢失既有原子 ID(原子守恒的表示层检查);
- 明确测试过的表示能力边界(手性/电荷/芳香/多组分可无损;同位素有损 →
  拒)由 tests/test_atom_tool.py 固定,任何回归都会被往返核对当场拒绝。

MoleCode 只是编辑视图;化学状态以可解析分子图及其 canonical SMILES 为准
(ARCHITECTURE §4)。本工具零模型、零网络。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

from ..domain.identity import cn_identity  # noqa: E402

_VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor" / "molecode"

# vendored 子集逐文件 SHA256(与 vendor/molecode/MANIFEST.sha256 一致;
# 换上游版本必须同步改这里并记录 PROVENANCE, resume 身份随之变化)
VENDOR_FILES: dict[str, str] = {
    "molecule/__init__.py":
        "0dd0d21d18bd181117fbf4418dbcaf09336303ba350d1ea235266aefc4ee223a",
    "molecule/rdkit_to_mermaid.py":
        "195a65e84fd77bb20f0aae61b256620b2489a68d146aa0b9f0909e1e94f37299",
    "molecule/mermaid_to_rdkit.py":
        "561ce966ba1195ed750ed66fc4023d9f501a9e580a509f4723506a270789b12c",
    "prompts/__init__.py":
        "f8160966acc0126d36121a02a0d3d0a2375c4d1010e9177fed32039e5b3bcf5d",
    "prompts/molecule_system_prompt.py":
        "ed4c654143c1802153377ec6de6f77c3d2d4845b4e107d1d0cf239cd34322e8e",
    "prompts/markush_system_prompt.py":
        "1377960f68d86ce7f3d946a9304aebd705887795593da184da6ce527b2617d58",
    "LICENSE":
        "d768cb92822c0e97bb6c0f9efab6a5f0a093f58a439959b02db687abfedc980e",
}

VENDOR_UPSTREAM_COMMIT = "a4df3b04552b829ff816467b9620757a5dad765b"

# MoleCode 原子 ID 形如 <Name>_<Symbol>_<n>[_R|_S];Symbol 是元素符号
ATOM_ID_RE = re.compile(
    r"\b(?P<name>[A-Za-z][A-Za-z0-9]*)_(?P<elem>[A-Za-z]{1,2})_(?P<n>\d+)"
    r"(?:_(?P<cip>[RS]))?\b"
)

ATOMTOOL_VERSION = "v43-atomtool-1"

# 编辑协议 v2(Phase C 任务书 §4/C2):新增 change_bond_order;add_atom
# 必须显式给 new_atom_id(元素须与 ID 内嵌元素一致);废除 remove_atom。
# 每条操作在**当前图副本上按列表顺序执行**,逐步核验前提;最终提案仍须
# 经过 validation 全部门禁 —— 本协议只核"编辑可执行且与目标一致"。
# Phase C R2 复核:严格四操作,旧别名 remove_bond/add_bond 不再接受
# (任务书 §4:未知操作/未知字段必须有稳定拒因;提示词声明"仅以下四种")。
EDIT_PROTOCOL_VERSION = "v43-editproto-2"

_EDIT_OPS = ("break_bond", "form_bond", "change_bond_order", "add_atom")
# 逐操作允许字段表(多余字段 = edit_invalid:unknown_field:<name>:edit[i])
_EDIT_OP_FIELDS: dict[str, frozenset] = {
    "break_bond": frozenset({"op", "atom1", "atom2"}),
    "form_bond": frozenset({"op", "atom1", "atom2"}),
    "change_bond_order": frozenset(
        {"op", "atom1", "atom2", "from_order", "to_order"}),
    "add_atom": frozenset({"op", "atom1", "element", "new_atom_id"}),
}
_BOND_TOKENS = {
    "single": Chem.BondType.SINGLE,
    "double": Chem.BondType.DOUBLE,
    "triple": Chem.BondType.TRIPLE,
}
_ELEMENT_RE = re.compile(r"^[A-Z][a-z]?$")


def _element_known(symbol: str) -> bool:
    """元素符号必须命中 RDKit 周期表且非通配(atomic number ≥ 1)。

    Phase C R3:``_ELEMENT_RE`` 只核形状,``Xx``/``Zz`` 等形似元素会漏过,
    直到执行器 ``Chem.Atom(...)`` 才抛未捕获异常 —— 资格判断必须与执行器
    同一事实源(RDKit 周期表),哑原子 "*" 同样拒绝(add_atom 不造占位)。
    """
    try:
        return Chem.GetPeriodicTable().GetAtomicNumber(str(symbol)) >= 1
    except Exception:
        return False


class AtomToolError(ValueError):
    """结构/表示/编辑核验失败(fail-closed)。reason 为稳定机读码。"""

    def __init__(self, reason: str, message: str, detail: dict | None = None):
        super().__init__(f"{reason}:{message}")
        self.reason = reason
        self.detail = detail or {}


@dataclass
class MoleculeRender:
    """SMILES 的 MoleCode 渲染结果(编辑视图 + 原子 ID 对照表)。"""

    smiles: str                 # 输入 SMILES(原样)
    canonical_smiles: str       # RDKit canonical(含立体)
    molecode: str               # Mermaid 文本
    atom_id_map: dict[str, int] = field(default_factory=dict)  # ID → atom idx
    idx_atom_map: dict[int, str] = field(default_factory=dict)  # idx → ID

    @property
    def atom_ids(self) -> list[str]:
        return sorted(self.atom_id_map, key=lambda a: self.atom_id_map[a])


def verify_vendor_integrity() -> dict:
    """核验 vendored MoleCode 子集哈希(任务书 §3:记录来源并锁定实现)。

    任何文件缺失/被改 → AtomToolError(fail-closed;MoleCode 实现是 run
    身份的一部分,被改即不得运行)。
    """
    for rel, expected in VENDOR_FILES.items():
        path = _VENDOR_ROOT / rel
        if not path.is_file():
            raise AtomToolError(
                "vendor_integrity",
                f"vendored MoleCode 文件缺失:{rel}",
                {"file": rel, "vendor_root": str(_VENDOR_ROOT)},
            )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise AtomToolError(
                "vendor_integrity",
                f"vendored MoleCode 哈希不符:{rel}",
                {"file": rel, "expected": expected[:12], "actual": actual[:12]},
            )
    return {
        "implementation": "molecode",
        "upstream_commit": VENDOR_UPSTREAM_COMMIT,
        "vendor_root": str(_VENDOR_ROOT),
        "files": dict(VENDOR_FILES),
        "manifest_sha256": hashlib.sha256(
            "\n".join(f"{v}  {k}" for k, v in sorted(VENDOR_FILES.items()))
            .encode()
        ).hexdigest(),
    }


@lru_cache(maxsize=1)
def _verified_vendor() -> tuple:
    verify_vendor_integrity()
    from pathway_v43.vendor.molecode.molecule import (  # noqa: F401
        MolToMermaidConverter,
        mermaid_to_mol,
    )
    return MolToMermaidConverter, mermaid_to_mol


def _canonical(mol) -> str:
    return Chem.MolToSmiles(mol)


def render(smiles: str, name: str = "M") -> MoleculeRender:
    """SMILES → MoleCode 渲染(带原子 ID 对照)。不可解析 → fail-closed。"""
    _MolToMermaidConverter, _ = _verified_vendor()
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        raise AtomToolError(
            "unparseable_smiles", f"SMILES 不可解析:{smiles!r}",
            {"smiles": smiles},
        )
    conv = _MolToMermaidConverter(subgraph_name=name)
    text = conv.convert(mol)
    id_to_idx = {aid: idx for idx, aid in conv.atom_id_map.items()}
    return MoleculeRender(
        smiles=smiles, canonical_smiles=_canonical(mol), molecode=text,
        atom_id_map=id_to_idx, idx_atom_map=dict(conv.atom_id_map),
    )


def molecode_to_mol(text: str):
    """MoleCode → RDKit Mol;解析失败返回 None(如实,不抛不猜)。"""
    _, mermaid_to_mol = _verified_vendor()
    try:
        return mermaid_to_mol(text or "")
    except Exception:
        return None


def molecode_to_smiles(text: str) -> str | None:
    mol = molecode_to_mol(text)
    return _canonical(mol) if mol is not None else None


def roundtrip(smiles: str, name: str = "M") -> MoleculeRender:
    """SMILES → MoleCode → SMILES 并核对身份;有损即拒(representation_lossy)。

    身份核对 = canonical SMILES(含立体/电荷)逐字符一致;探明的有损情形
    (如同位素)在此被拒绝,绝不以未经验证的 SMILES 替代。
    """
    render_ = render(smiles, name)
    back = molecode_to_mol(render_.molecode)
    if back is None:
        raise AtomToolError(
            "molecode_unparseable",
            "MoleCode 回读失败(往返断裂)",
            {"smiles": smiles},
        )
    back_can = _canonical(back)
    if back_can != render_.canonical_smiles:
        raise AtomToolError(
            "representation_lossy",
            f"MoleCode 往返身份不一致:渲染前={render_.canonical_smiles!r} "
            f"回读={back_can!r};表示能力边界(如同位素/不支持特征)必须拒绝",
            {"before": render_.canonical_smiles, "after": back_can},
        )
    return render_


def parse_atom_ids(text: str) -> set[str]:
    """从 MoleCode 文本提取原子 ID 集合(节点行+键行都覆盖)。"""
    return {m.group(0) for m in ATOM_ID_RE.finditer(text or "")}


def check_target_molecode(current: MoleculeRender, target_text: str) -> dict:
    """核验模型给出的目标 MoleCode(受限编辑结果)。

    确定性检查(表示层;化学门禁在 validation/gates):
    - 目标可解析(否则 molecode_unparseable);
    - 目标原子 ID ⊇ 当前原子 ID(编辑不得使既有原子凭空消失;
      mapping_inconsistent:atom_removed 点名缺失 ID);
    - 同名 ID 元素一致(ID 内嵌元素符号;不一致说明模型改写了标识体系,
      mapping_inconsistent:element_mismatch)。
    返回 {ok, target_smiles, added_atom_ids, removed_atom_ids, reasons}。
    """
    reasons: list[str] = []
    target_mol = molecode_to_mol(target_text)
    if target_mol is None:
        return {"ok": False, "reasons": ["molecode_unparseable:目标 MoleCode 无法解析"]}
    cur_ids = set(current.atom_id_map)
    tgt_ids = parse_atom_ids(target_text)
    missing = sorted(cur_ids - tgt_ids)
    for aid in missing:
        reasons.append(f"mapping_inconsistent:atom_removed:{aid}")
    # 元素一致性:同名 ID 的元素符号必须一致
    for aid in sorted(cur_ids & tgt_ids):
        cur_elem = _id_element(aid)
        tgt_elem = _id_element(aid)
        if cur_elem and tgt_elem and cur_elem != tgt_elem:
            reasons.append(
                f"mapping_inconsistent:element_mismatch:{aid}"
                f"({cur_elem}->{tgt_elem})"
            )
    added = sorted(tgt_ids - cur_ids)
    return {
        "ok": not reasons,
        "reasons": reasons,
        "target_smiles": _canonical(target_mol),
        "added_atom_ids": added,
        "removed_atom_ids": missing,
    }


def _id_element(atom_id: str) -> str | None:
    m = ATOM_ID_RE.match(atom_id)
    return m.group("elem") if m else None


def check_edit_references(current: MoleculeRender,
                          edits: list[dict]) -> tuple[bool, list[str]]:
    """核验模型编辑列表引用的原子/键是否存在于当前 MoleCode(任务书 §3)。

    编辑形状(宽松接受,引用核验从严):
      {"op": "break_bond"|"remove_bond", "atom1": ID, "atom2": ID}
      {"op": "form_bond"|"add_bond", "atom1": ID, "atom2": ID}
      {"op": "remove_atom"|"delete_atom", "atom": ID}
      {"op": "add_atom", "element": "O", "atom1": ID}   # 新原子挂到既有原子
    """
    reasons: list[str] = []
    ids = set(current.atom_id_map)
    bonds = {
        frozenset((current.idx_atom_map[b.GetBeginAtomIdx()],
                   current.idx_atom_map[b.GetEndAtomIdx()]))
        for b in Chem.MolFromSmiles(current.smiles).GetBonds()
    } if Chem.MolFromSmiles(current.smiles) is not None else set()
    for i, edit in enumerate(edits or []):
        op = str(edit.get("op", "")).lower()
        a1, a2 = edit.get("atom1"), edit.get("atom2")
        single = edit.get("atom")
        referenced = [x for x in (a1, a2, single) if x is not None]
        if not referenced:
            reasons.append(f"edit_invalid:missing_atom_reference:edit[{i}]")
            continue
        for ref in referenced:
            if ref not in ids:
                reasons.append(f"edit_invalid:unknown_atom:{ref}")
        if op in ("break_bond", "remove_bond", "form_bond", "add_bond"):
            if a1 in ids and a2 in ids:
                pair = frozenset((a1, a2))
                if op in ("break_bond", "remove_bond") and pair not in bonds:
                    reasons.append(
                        f"edit_invalid:bond_not_present:{a1}~{a2}")
                if op in ("form_bond", "add_bond") and pair in bonds:
                    reasons.append(f"edit_invalid:bond_already_present:{a1}~{a2}")
    return (not reasons), reasons


def validate_edits(current: MoleculeRender, edits: list) -> dict:
    """编辑列表结构化校验(v2 协议;不执行,拓扑前提留给执行步)。

    校验:op 合法(严格四操作;旧别名 remove_bond/add_bond 一律
    unknown_op)、**逐操作字段表**(未声明字段 = unknown_field:<name>)、
    必填字段齐、引用原子 ID 存在、键级 token 合法、add_atom 的
    new_atom_id 合法(格式/元素一致/不冲突/列表内唯一)且 element 命中
    周期表(形状合法的 ``Xx`` 在此拒,不再漏到执行器抛异常)。
    引用按列表时点判定:先前 add_atom 声明的新 ID 可被后续操作引用
    (先增后引合法,与执行器一致)。键是否存在**不在本步判定** ——
    编辑按列表顺序执行,先断后成等序列的拓扑前提只在执行时点的图上
    成立。拒因稳定机读码,均带操作索引 edit[i]。
    """
    reasons: list[str] = []
    ids = set(current.atom_id_map)
    seen_new: set[str] = set()
    n = len(edits or [])
    for i, edit in enumerate(edits or []):
        tag = f"edit[{i}]"
        if not isinstance(edit, dict):
            reasons.append(f"edit_invalid:not_an_object:{tag}")
            continue
        op = str(edit.get("op", "")).lower()
        if op not in _EDIT_OPS:
            reasons.append(f"edit_invalid:unknown_op:{op or 'missing'}:{tag}")
            continue
        # 逐操作字段表:未声明字段一律显式拒绝(任务书 §4;R2 复核)
        for field in sorted(set(edit) - _EDIT_OP_FIELDS[op]):
            reasons.append(f"edit_invalid:unknown_field:{field}:{tag}")
        a1, a2 = edit.get("atom1"), edit.get("atom2")
        if a1 is None or (a2 is None and op != "add_atom"):
            reasons.append(f"edit_invalid:missing_atom_reference:{tag}")
            continue
        # 引用合法性按列表时点判定:既有原子或本列表**先前 add_atom 已声明**
        # 的新 ID 都可用(先增后引与执行器一致);引用未声明/后声明仍拒。
        for ref in (a1, a2):
            if ref is not None and ref not in ids \
                    and str(ref) not in seen_new:
                reasons.append(f"edit_invalid:unknown_atom:{ref}:{tag}")
        if op == "change_bond_order":
            for field in ("from_order", "to_order"):
                v = edit.get(field)
                if v is None:
                    reasons.append(f"edit_invalid:missing_field:{field}:{tag}")
                elif str(v).lower() not in _BOND_TOKENS:
                    reasons.append(
                        f"edit_invalid:bad_bond_order:{v}:{tag}")
        elif op == "add_atom":
            element = edit.get("element")
            element_ok = bool(element) \
                and _ELEMENT_RE.match(str(element)) is not None \
                and _element_known(str(element))
            if not element_ok:
                reasons.append(
                    f"edit_invalid:bad_element:{element!r}:{tag}")
            new_id = edit.get("new_atom_id")
            if not new_id:
                reasons.append(f"edit_invalid:missing_field:new_atom_id:{tag}")
                continue
            new_id = str(new_id)
            m = ATOM_ID_RE.match(new_id)
            if m is None or m.group(0) != new_id:
                reasons.append(
                    f"edit_invalid:bad_new_atom_id_format:{new_id}:{tag}")
                continue
            if new_id in ids or new_id in seen_new:
                reasons.append(
                    f"edit_invalid:new_atom_id_conflict:{new_id}:{tag}")
                continue
            if element and _id_element(new_id) and \
                    _id_element(new_id).lower() != str(element).lower():
                reasons.append(
                    f"edit_invalid:new_atom_id_element_mismatch:{new_id}:{tag}")
                continue
            # 元素非法的新原子不注册:后续引用它的编辑按 unknown_atom 拒,
            # 与执行器("非法元素不入图")保持同一语义
            if element_ok:
                seen_new.add(new_id)
    return {"ok": not reasons, "reasons": reasons, "protocol_version":
            EDIT_PROTOCOL_VERSION, "n_edits": n,
            "new_atom_ids": sorted(seen_new)}


def execute_edits(current: MoleculeRender, edits: list) -> dict:
    """在当前分子图副本上**按列表顺序**执行编辑(事务式;任务书 §4)。

    每步以更新后的图核验拓扑前提(键存在/不存在、原键级);中间态允许
    暂时不满足完整价态(事务内暂存),但每步前提必须成立,最终 sanitize
    必须成功。旧原子 ID 不消失、不变元素;新增原子按 new_atom_id 入图。
    失败 fail-closed,拒因带操作索引 edit[i]。
    """
    mol = Chem.MolFromSmiles(current.smiles)
    if mol is None:
        return {"ok": False, "reasons": ["internal:substrate_unparseable"],
                "product_smiles": "", "atom_id_map": {},
                "protocol_version": EDIT_PROTOCOL_VERSION,
                "n_edits": len(edits or [])}
    try:
        Chem.Kekulize(mol, clearAromaticFlags=True)
    except Exception:
        pass  # 少数结构无法 kekulize:按芳香形式继续(键级前提将如实失配)
    rw = Chem.RWMol(mol)
    id_to_idx = dict(current.atom_id_map)
    idx_to_id = {v: k for k, v in id_to_idx.items()}
    reasons: list[str] = []

    def bond_between(a1, a2):
        i1, i2 = id_to_idx.get(a1), id_to_idx.get(a2)
        if i1 is None or i2 is None:
            return None
        return rw.GetBondBetweenAtoms(i1, i2)

    for i, edit in enumerate(edits or []):
        tag = f"edit[{i}]"
        op = str(edit.get("op", "")).lower()
        a1, a2 = edit.get("atom1"), edit.get("atom2")
        if op == "break_bond":
            bond = bond_between(a1, a2)
            if bond is None:
                reasons.append(
                    f"edit_execution_failed:bond_not_present:{a1}~{a2}:{tag}")
                continue
            rw.RemoveBond(id_to_idx[a1], id_to_idx[a2])
        elif op == "form_bond":
            if bond_between(a1, a2) is not None:
                # 硬拒绝(任务书 §4):form_bond 对已有键仍报
                # bond_already_present;键级变化必须显式走 change_bond_order
                reasons.append(
                    f"edit_execution_failed:bond_already_present:"
                    f"{a1}~{a2}:{tag}")
                continue
            rw.AddBond(id_to_idx[a1], id_to_idx[a2], Chem.BondType.SINGLE)
        elif op == "change_bond_order":
            bond = bond_between(a1, a2)
            if bond is None:
                reasons.append(
                    f"edit_execution_failed:bond_not_present:{a1}~{a2}:{tag}")
                continue
            frm = str(edit.get("from_order", "")).lower()
            to = str(edit.get("to_order", "")).lower()
            have = _order_token_of(bond.GetBondType())
            if have != frm:
                reasons.append(
                    f"edit_execution_failed:bond_order_mismatch:"
                    f"{a1}~{a2}:expected_{frm}_have_{have}:{tag}")
                continue
            bond.SetBondType(_BOND_TOKENS[to])
        elif op == "add_atom":
            element = str(edit.get("element", ""))
            new_id = str(edit.get("new_atom_id", ""))
            anchor = id_to_idx.get(a1)
            if anchor is None:
                reasons.append(
                    f"edit_execution_failed:unknown_atom:{a1}:{tag}")
                continue
            # 防御(Phase C R3):非法元素在这里必须落结构化拒因,
            # 不能让 RDKit 异常逃逸成节点崩溃(预校验已挡,此处兜底)
            try:
                idx = rw.AddAtom(Chem.Atom(element))
            except Exception:
                reasons.append(
                    f"edit_execution_failed:bad_element:{element}:{tag}")
                continue
            rw.AddBond(anchor, idx, Chem.BondType.SINGLE)
            id_to_idx[new_id] = idx
            idx_to_id[idx] = new_id
        else:  # validate_edits 应已拒绝;防御
            reasons.append(f"edit_execution_failed:unknown_op:{op}:{tag}")
    if reasons:
        return {"ok": False, "reasons": reasons, "product_smiles": "",
                "atom_id_map": {}, "protocol_version": EDIT_PROTOCOL_VERSION,
                "n_edits": len(edits or [])}
    out = rw.GetMol()
    try:
        Chem.SanitizeMol(out)
    except Exception as exc:
        reasons.append(
            f"edit_execution_failed:sanitize_failed:"
            f"{type(exc).__name__}:edit[last]")
        return {"ok": False, "reasons": reasons, "product_smiles": "",
                "atom_id_map": {}, "protocol_version": EDIT_PROTOCOL_VERSION,
                "n_edits": len(edits or [])}
    # 身份核对:旧原子 ID 不得变元素(执行器本身不改元素;此处防御 ID 图)
    for aid, idx in id_to_idx.items():
        elem = _id_element(aid)
        if elem and out.GetAtomWithIdx(idx).GetSymbol().lower() \
                != elem.lower() and idx_to_id.get(idx) == aid:
            reasons.append(f"internal:element_identity_drift:{aid}")
    if reasons:
        return {"ok": False, "reasons": reasons, "product_smiles": "",
                "atom_id_map": {}, "protocol_version": EDIT_PROTOCOL_VERSION,
                "n_edits": len(edits or [])}
    return {"ok": True, "reasons": [], "product_smiles": Chem.MolToSmiles(out),
            "atom_id_map": id_to_idx,
            "protocol_version": EDIT_PROTOCOL_VERSION,
            "n_edits": len(edits or [])}


def _order_token_of(bond_type) -> str:
    for token, bt in _BOND_TOKENS.items():
        if bt == bond_type:
            return token
    return str(bond_type)


def _id_graph_from_mol(mol, id_to_idx: dict) -> dict:
    """(kekulé 化后的)分子图 → ID 级带标签图 {ids, elements, charges,
    bonds: {frozenset(id,id): order_token}}。"""
    try:
        Chem.Kekulize(mol, clearAromaticFlags=True)
    except Exception:
        pass
    idx_to_id = {v: k for k, v in id_to_idx.items()}
    elements, charges = {}, {}
    for aid, idx in id_to_idx.items():
        atom = mol.GetAtomWithIdx(idx)
        elements[aid] = atom.GetSymbol()
        charges[aid] = atom.GetFormalCharge()
    bonds = {}
    for b in mol.GetBonds():
        a1 = idx_to_id.get(b.GetBeginAtomIdx())
        a2 = idx_to_id.get(b.GetEndAtomIdx())
        if a1 and a2:
            bonds[frozenset((a1, a2))] = _order_token_of(b.GetBondType())
    return {"ids": set(id_to_idx), "elements": elements,
            "charges": charges, "bonds": bonds}


_LABEL_CHARGE_RE = re.compile(r"\((\d*)([+-])\)$")
_LABEL_RE = re.compile(r"^([A-Z][a-z]?)(?:H(\d*))?(?:\((\d*[+-])\))?$")


def _label_parse(label: str) -> tuple[str, int, int]:
    """MoleCode 节点标签 → (元素, 显式 H 数, 形式电荷)。"""
    m = _LABEL_RE.match((label or "").strip())
    if m is None:
        return "", 0, 0
    element = m.group(1)
    h_digits = m.group(2)
    if h_digits is None:
        h = 0
    elif h_digits == "":
        h = 1
    else:
        h = int(h_digits)
    charge = 0
    ch = m.group(3)
    if ch:
        if ch in ("+", "-"):
            charge = 1 if ch == "+" else -1
        else:
            charge = int(ch[:-1]) if ch[-1] == "+" else -int(ch[:-1])
    return element, h, charge


def check_target_consistency(current: MoleculeRender,
                             execution: dict, target_text: str) -> dict:
    """目标 MoleCode 独立解析并与**执行结果图**逐项对账(任务书 §4)。

    - 目标可解析(否则 molecode_unparseable);
    - 既有原子 ID 不消失、元素一致(mapping_inconsistent:*);
    - ID 级带标签图对账:原子 ID 集合、元素、形式电荷、键集合与键级
      (两侧 kekulé 归一)逐项一致 —— 文本中正则搜到 ID 不算结构相符;
    - 最终 canonical SMILES(含立体)一致(target_edit_mismatch)。
    """
    reasons: list[str] = []
    if not execution.get("ok"):
        return {"ok": False,
                "reasons": ["target_check_skipped:execution_failed"],
                "target_smiles": ""}
    from pathway_v43.vendor.molecode.molecule.mermaid_to_rdkit import (
        MermaidMolParser,
    )

    parser = MermaidMolParser()
    target_mol = parser.parse_mermaid_graph(target_text or "")
    if target_mol is None:
        return {"ok": False,
                "reasons": ["molecode_unparseable:目标 MoleCode 无法解析"],
                "target_smiles": ""}
    tgt_ids = parse_atom_ids(target_text or "")
    cur_ids = set(current.atom_id_map)
    for aid in sorted(cur_ids - tgt_ids):
        reasons.append(f"mapping_inconsistent:atom_removed:{aid}")
    for aid in sorted(cur_ids & tgt_ids):
        cur_elem = _id_element(aid)
        tgt_elem = _id_element(aid)
        if cur_elem and tgt_elem and cur_elem != tgt_elem:
            reasons.append(
                f"mapping_inconsistent:element_mismatch:"
                f"{aid}({cur_elem}->{tgt_elem})")
    exec_mol = Chem.MolFromSmiles(execution["product_smiles"])
    exec_graph = _id_graph_from_mol(exec_mol, execution["atom_id_map"])
    # 目标侧 ID 级图:解析器自持 atoms(id→label)/bonds(id,id,token)
    tgt_elements, tgt_charges = {}, {}
    for aid, label in (parser.atoms or {}).items():
        element, _h, charge = _label_parse(label)
        tgt_elements[aid] = element
        tgt_charges[aid] = charge
    tgt_bonds = {}
    for entry in parser.bonds or []:
        a1, a2, token = entry[0], entry[1], entry[2]
        order = {"---": "single", "===": "double", "-.-": "triple"}.get(
            token, "aromatic")
        tgt_bonds[frozenset((a1, a2))] = order
    if not reasons:
        if exec_graph["ids"] != set(tgt_elements):
            missing = sorted(exec_graph["ids"] - set(tgt_elements))
            extra = sorted(set(tgt_elements) - exec_graph["ids"])
            if missing:
                reasons.append(
                    f"target_edit_mismatch:atom_id_sets_differ:"
                    f"missing_in_target:{','.join(missing[:6])}")
            if extra:
                reasons.append(
                    f"target_edit_mismatch:atom_id_sets_differ:"
                    f"extra_in_target:{','.join(extra[:6])}")
        else:
            for aid in sorted(exec_graph["ids"]):
                if exec_graph["elements"][aid] != tgt_elements.get(aid):
                    reasons.append(
                        f"target_edit_mismatch:element:"
                        f"{aid}({exec_graph['elements'][aid]}"
                        f"!={tgt_elements.get(aid)})")
                if exec_graph["charges"][aid] != tgt_charges.get(aid):
                    reasons.append(
                        f"target_edit_mismatch:formal_charge:{aid}"
                        f"({exec_graph['charges'][aid]}"
                        f"!={tgt_charges.get(aid)})")
            only_exec = sorted({k for k in exec_graph["bonds"]
                                if k not in tgt_bonds})
            only_tgt = sorted({k for k in tgt_bonds
                               if k not in exec_graph["bonds"]})
            for k in only_exec[:4]:
                reasons.append(
                    f"target_edit_mismatch:bond_in_execution_not_target:"
                    f"{'~'.join(sorted(k))}")
            for k in only_tgt[:4]:
                reasons.append(
                    f"target_edit_mismatch:bond_in_target_not_execution:"
                    f"{'~'.join(sorted(k))}")
            for k in sorted(set(exec_graph["bonds"]) & set(tgt_bonds)):
                if exec_graph["bonds"][k] != tgt_bonds[k]:
                    reasons.append(
                        f"target_edit_mismatch:bond_order:"
                        f"{'~'.join(sorted(k))}"
                        f"({exec_graph['bonds'][k]}!={tgt_bonds[k]})")
    target_smiles = Chem.MolToSmiles(target_mol)
    if not reasons and target_smiles != execution["product_smiles"]:
        reasons.append(
            f"target_edit_mismatch:canonical_smiles_diff:"
            f"executed={execution['product_smiles']!r}"
            f"_target={target_smiles!r}")
    return {"ok": not reasons, "reasons": reasons,
            "target_smiles": target_smiles,
            "n_target_atoms": len(tgt_elements)}


def align_donor_mapping(donor_mol, current_mol, center_map_nums=None,
                        center_only: bool = False):
    """供体分子 → 当前分子的确定性原子对齐(类比映射找回的对齐步)。

    - center_only=False:全供体子结构匹配(full_donor_substructure);
    - center_only=True:只取反应中心子图(reaction_center_substructure)。
      中心原子 = ``AtomMapNum ∈ center_map_nums``(corpus 索引的
      ``center_atoms`` 即映射编号;缺席时退化为全部带映射原子,
      中心原子数 <2 拒绝)。
    取 RDKit GetSubstructMatches 的首个确定性匹配。
    返回 (match_map | None, strategy):match_map = {query_idx: current_idx}。
    """
    if donor_mol is None or current_mol is None:
        return None, None
    query = donor_mol
    if center_only:
        if center_map_nums:
            center_idx = [a.GetIdx() for a in donor_mol.GetAtoms()
                          if a.GetAtomMapNum() in set(center_map_nums)]
        else:
            center_idx = [a.GetIdx() for a in donor_mol.GetAtoms()
                          if a.GetAtomMapNum() > 0]
        if len(center_idx) < 2:
            return None, None
        query = Chem.RWMol()
        idx_map = {}
        for i in center_idx:
            idx_map[i] = query.AddAtom(Chem.Atom(donor_mol.GetAtomWithIdx(i)))
        for bond in donor_mol.GetBonds():
            bi, ei = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
            if bi in idx_map and ei in idx_map:
                query.AddBond(idx_map[bi], idx_map[ei], bond.GetBondType())
        query = query.GetMol()
    matches = current_mol.GetSubstructMatches(query, uniquify=False,
                                              useChirality=False)
    if not matches:
        return None, None
    match = matches[0]  # RDKit 确定性顺序
    if center_only:
        # query 是重建子图:按构造位置回译为**原始供体原子 idx**
        orig_of_pos = {pos: orig for orig, pos in idx_map.items()}
        return ({orig_of_pos[pos]: cur for pos, cur in enumerate(match)},
                "deterministic_first_match")
    return ({d: c for d, c in enumerate(match)}, "deterministic_first_match")


def element_delta(substrate_smiles: str, product_smiles: str) -> dict:
    """重原子元素计数差 product - substrate(氢不计;多组分取并)。"""

    def heavy(smi: str) -> dict[str, int]:
        mol = Chem.MolFromSmiles(smi) if smi else None
        counts: dict[str, int] = {}
        if mol:
            for a in mol.GetAtoms():
                if a.GetSymbol() == "H":
                    continue
                counts[a.GetSymbol()] = counts.get(a.GetSymbol(), 0) + 1
        return counts

    sub, prod = heavy(substrate_smiles), heavy(product_smiles)
    delta: dict[str, int] = {}
    for el in sorted(set(sub) | set(prod)):
        d = prod.get(el, 0) - sub.get(el, 0)
        if d:
            delta[el] = d
    return delta


def identity_of(smiles: str) -> str | None:
    return cn_identity(smiles)
