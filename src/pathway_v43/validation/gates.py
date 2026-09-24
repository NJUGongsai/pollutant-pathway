"""确定性校验门禁 — 进入 PathwayStore 前的最后关卡。

门禁范围(任务书 §1/§3/§4):SMILES 可解析与价态、同一步兄弟候选去重、
路径内循环、方向/来源挂牌、深度与预算;预测提案另加按反应类型的元素
变化检查(外源氧显式规则+例外依据)。门禁**不**声称证明反应机理 ——
元素计数是约束检查,不是机理证明;例外依据随校验产物留痕。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..domain.identity import parseable
from ..domain.models import (
    ATOM_MAPPING_UNAVAILABLE,
    EVIDENCE_KIND_RECORDED,
    PATH_STATUS_FRONTIER,
    PATH_STATUS_REJECTED,
)
from ..domain.pathway import is_in_path_cycle

MAX_DEPTH_HARD = 64  # 防御性硬上限(正常由配置 max_depth 约束)

# 环境降解一步允许的外源元素(如水解/氧化引入的 O;氢不计);
# O 的单步掺入上限沿用 v4 gates.O_INSERT_CAP 的语义(羟化/掺氧一步 ≤2)
ALLOWED_NEW_ELEMENTS = frozenset({"O"})
O_INSERT_CAP = 2


@dataclass
class ProductVerdict:
    position: int
    product_smiles: str
    product_identity: str
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    exceptions: dict = field(default_factory=dict)  # 例外依据(如元素 delta)

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        if not d.get("exceptions"):
            d.pop("exceptions", None)  # 第一阶段产物形状不变(兼容读取)
        return d


def gate_smiles(smiles: str) -> tuple[bool, str]:
    """SMILES 可解析 + 价态合法(RDKit sanitize 内含价态/原子检查)。"""
    if not smiles or not isinstance(smiles, str):
        return False, "unparseable_smiles:空输入"
    if not parseable(smiles):
        return False, f"unparseable_smiles:{smiles[:80]}"
    return True, ""


def gate_direction_source(evidence: dict) -> tuple[bool, str]:
    """方向/来源挂牌:recorded 反应必须来自同规范底物的精确记录。

    match_type 必须标识精确记录命中;来源字段不得为空。
    """
    if evidence.get("kind") == EVIDENCE_KIND_RECORDED:
        if evidence.get("match_type") != "exact_donor_cn_match":
            return False, "direction_or_source:recorded 证据缺少精确底物匹配挂牌"
    if not evidence.get("source_id"):
        return False, "direction_or_source:缺少来源 ID"
    return True, ""


def gate_atom_mapping_declared(evidence: dict) -> tuple[bool, str]:
    """原子映射必须显式声明(可用或 unavailable),不许含糊缺席。"""
    am = evidence.get("atom_mapping")
    if am is None or am == "":
        return False, "atom_mapping_undeclared"
    return True, ""


def gate_element_changes(
    substrate_smiles: str,
    product_smiles: str,
    *,
    allowed_new_elements: frozenset = ALLOWED_NEW_ELEMENTS,
    o_insert_cap: int = O_INSERT_CAP,
) -> tuple[bool, str, dict]:
    """按反应类型允许的元素变化(预测提案适用;环境降解规则)。

    规则(与 v4 gates.check_conservation 同语义):
    - 产物出现底物没有的重元素:仅允许显式白名单(外源 O),其余拒
      (element_change_not_justified:<El> —— 一步不凭空造原子);
    - O 允许 +≤o_insert_cap(掺氧上限),超出拒(oxygen_insert_cap);
    - 元素减少一律允许(碎片裂解释放)。
    返回 (ok, reason, delta) —— delta 随校验产物留痕作为例外依据,
    不把元素计数当作机理证明。
    """
    from ..services.atom_tool import element_delta

    delta = element_delta(substrate_smiles, product_smiles)
    for el, d in sorted(delta.items()):
        if d <= 0:
            continue
        if el not in allowed_new_elements:
            return (False,
                    f"element_change_not_justified:{el}(+{d},"
                    f"底物无此元素且不在环境外源白名单)", delta)
        if el == "O" and d > o_insert_cap:
            return (False,
                    f"oxygen_insert_cap:+{d}>{o_insert_cap}(一步掺氧上限)",
                    delta)
    return True, "", delta


def validate_event_products(
    *,
    evidence: dict,
    ancestry_cns: list[str],
    existing_sibling_cns: set[str] | None = None,
    substrate_smiles: str = "",
    check_elements: bool = False,
) -> list[ProductVerdict]:
    """对接受反应的全部有序产物逐一过门禁,保留原始顺序。

    - unparseable / 价态非法 → 拒;
    - 同一事件内重复产物(对称位点等)→ 首个保留、后续拒(sibling_dedup);
    - 与既有兄弟路径(同父路径的既有产物)同身份 → 拒(sibling_dedup);
    - 回到本路径祖先链任一分子(含当前底物)→ 拒(in_path_cycle);
    - check_elements(模型提案适用):按反应类型的元素变化显式规则,
      拒因与 delta 例外依据留痕;
    - 原子映射缺失不是拒因 —— 显式标 unavailable(真实资产无映射数据)。
    """
    verdicts: list[ProductVerdict] = []
    seen_in_event: set[str] = set()
    siblings = set(existing_sibling_cns or set())
    for pos, prod in enumerate(evidence.get("products", [])):
        smi = prod.get("product_smiles_full") or prod.get("product_smiles", "")
        reasons: list[str] = []
        exceptions: dict = {}
        ok, reason = gate_smiles(smi)
        if not ok:
            reasons.append(reason)
        cn = prod.get("product_identity") or ""
        if cn:
            if cn in seen_in_event:
                reasons.append("sibling_dedup:同一事件内重复产物")
            elif cn in siblings:
                reasons.append("sibling_dedup:与既有兄弟路径同分子")
            elif is_in_path_cycle(cn, ancestry_cns):
                reasons.append("in_path_cycle:产物回到本路径祖先分子")
        if check_elements and substrate_smiles:
            el_ok, el_reason, delta = gate_element_changes(substrate_smiles, smi)
            exceptions["element_delta"] = delta
            if not el_ok:
                reasons.append(el_reason)
        seen_in_event.add(cn)
        verdict = ProductVerdict(
            position=pos, product_smiles=smi, product_identity=cn,
            accepted=not reasons, reasons=reasons,
        )
        if exceptions:
            verdict.exceptions = exceptions
        verdicts.append(verdict)
    return verdicts


_DEPTH_DEPTH_RE = re.compile(r"^depth")


def gate_depth(depth: int, max_depth: int) -> tuple[bool, str]:
    if depth > MAX_DEPTH_HARD:
        return False, f"depth_hard_limit:{depth}>{MAX_DEPTH_HARD}"
    if depth >= max_depth:
        return False, f"depth_limit:{depth}>={max_depth}"
    return True, ""


def gate_budget(used_expansions: int, max_expansions: int) -> tuple[bool, str]:
    if used_expansions >= max_expansions:
        return False, f"budget_exhausted:{used_expansions}>={max_expansions}"
    return True, ""


# 供 workflow 使用的常量再导出(避免 workflow 直接依赖 models 内部名)
PATH_IN = PATH_STATUS_FRONTIER
PATH_REJECTED = PATH_STATUS_REJECTED
MAPPING_UNAVAILABLE = ATOM_MAPPING_UNAVAILABLE
