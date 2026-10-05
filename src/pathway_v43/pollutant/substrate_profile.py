"""SubstrateProfile — 底物档案(实施书 §7.1,S2)。

- **独立于 candidates**(C2 修复:底物档案不依赖候选列表),所有模型
  路由都能读到;
- 承载 ChemicalState 的完整结构(isomeric SMILES、形式电荷、立体/
  同位素状态)+ 元素组成与分子式 + 上下文条件引用;
- 新路径检索/模型输入使用完整结构;CN 仅作旧评分/资产键适配字段
  (cn_identity),不冒充严格结构一致;
- 只读构造(纯函数),不接触模型、frontier 或策略状态。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from rdkit import Chem
from rdkit import RDLogger

from .chemstate import ChemicalState
from .path_context import PathContext
from .profile import PPV1_SUBSTRATE_PROFILE_SCHEMA_VERSION

RDLogger.DisableLog("rdApp.*")

FEATURE_POLICY_VERSION = "ppv1-substrate-features-1"
FEATURE_POLICY_KEYS = frozenset({"include_element_counts",
                                  "include_molecular_formula",
                                  "include_condition_refs"})
FEATURE_POLICY_DEFAULTS = {
    "include_element_counts": True,
    "include_molecular_formula": True,
    "include_condition_refs": True,
}


class SubstrateProfileError(RuntimeError):
    """底物档案构造失败(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


@dataclass
class SubstrateProfile:
    """底物档案(§7.1;含完整结构与特征,不含候选信息)。"""

    schema_version: str
    state_ref: str
    structure_smiles: str          # isomeric canonical(完整结构)
    cn_identity: str               # 旧口径键(兼容适配;非结构事实)
    formal_charge: int | None
    stereo_information_status: str
    isotope_information_status: str
    structure_origin: str
    original_structure_available: bool
    representation_fidelity: str
    element_counts: dict[str, int] = field(default_factory=dict)
    molecular_formula: str = ""
    source_refs: list[dict] = field(default_factory=list)
    condition_keys_known: list[str] = field(default_factory=list)
    context_ref: str = ""
    feature_policy_version: str = FEATURE_POLICY_VERSION
    feature_policy: dict = field(default_factory=lambda: dict(
        FEATURE_POLICY_DEFAULTS))

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def build_substrate_profile(
    state: ChemicalState,
    context: PathContext | None = None,
    feature_policy: dict | None = None,
) -> SubstrateProfile:
    """§7.1 固定接口:状态 + 上下文 → 底物档案(纯函数)。

    CN-only 状态(结构未知)也可建档:元素组成/分子式留空并如实标注,
    不从 CN 猜结构。feature_policy 只裁剪特征输出,不影响状态事实。
    """
    policy = dict(FEATURE_POLICY_DEFAULTS)
    for k, v in (feature_policy or {}).items():
        if k not in FEATURE_POLICY_KEYS:
            raise SubstrateProfileError(
                f"未知特征策略键:{k!r}(允许 {sorted(FEATURE_POLICY_KEYS)})",
                {"key": k})
        policy[k] = v
    element_counts: dict[str, int] = {}
    formula = ""
    if state.smiles_isomeric:
        mol = Chem.MolFromSmiles(state.smiles_isomeric)
        if mol is None:
            raise SubstrateProfileError(
                "底物状态的结构无法解析(档案构造失败)",
                {"state_ref": state.state_id})
        counts = Counter(
            atom.GetSymbol() for atom in mol.GetAtoms())
        element_counts = dict(sorted(counts.items()))
        try:
            from rdkit.Chem.rdMolDescriptors import CalcMolFormula

            formula = CalcMolFormula(mol)
        except Exception:
            formula = ""
    condition_keys = []
    context_ref = ""
    if context is not None and policy["include_condition_refs"]:
        condition_keys = sorted(
            f.key for f in context.condition_facts
            if f.status != "unknown")
        context_ref = context.context_id
    return SubstrateProfile(
        schema_version=PPV1_SUBSTRATE_PROFILE_SCHEMA_VERSION,
        state_ref=state.state_id,
        structure_smiles=state.smiles_isomeric,
        cn_identity=state.cn_identity,
        formal_charge=state.formal_charge,
        stereo_information_status=state.stereo_information_status,
        isotope_information_status=state.isotope_information_status,
        structure_origin=state.structure_origin,
        original_structure_available=state.original_structure_available,
        representation_fidelity=state.representation_fidelity,
        element_counts=element_counts if policy[
            "include_element_counts"] else {},
        molecular_formula=formula if policy[
            "include_molecular_formula"] else "",
        source_refs=[dict(r) for r in state.source_refs],
        condition_keys_known=condition_keys,
        context_ref=context_ref,
        feature_policy=policy,
    )
