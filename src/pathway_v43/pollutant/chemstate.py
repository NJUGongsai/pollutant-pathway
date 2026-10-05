"""ChemicalState — 化学状态与 CN 身份分开(实施书 §5.1,S1)。

- state_id 按保留形式电荷、同位素和立体信息的确定性分子图生成;原子
  映射号不属于分子身份(生成前去除);
- 原始结构与解析后的图都保留;形式电荷是结构事实,不表示已知某 pH
  下的质子化分布;
- 新路径检索/模型输入使用事件产物的完整结构,CN 仅作旧评分/资产键
  适配(domain.identity.cn_identity 的冻结口径,不在此改);
- 历史只剩 CN 时标 legacy_cn_only,不猜回立体信息;有存档
  product_smiles_full 时可恢复存档形(representation_fidelity=
  archive_recovered),但不冒称原实验全部结构细节已知;
- 状态、PathContext、PathInstance 分开:同分子不同来路不共享并覆盖
  上下文(本模块只管分子状态本身)。

解析失败 fail-closed(ChemicalStateError,kind=unparseable_smiles):
不猜结构、不静默跳过(下游 audit 将其映射为 parse_check=violated)。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdkit import Chem, RDLogger

from ..domain.identity import cn_identity as _legacy_cn_identity
from ..domain.models import stable_id
from .profile import PPV1_CHEMSTATE_SCHEMA_VERSION

RDLogger.DisableLog("rdApp.*")

STRUCTURE_ORIGIN_RAW_INPUT = "raw_input"
STRUCTURE_ORIGIN_SOURCE_PRODUCT = "source_product"
STRUCTURE_ORIGIN_EXECUTED_PRODUCT = "executed_product"
STRUCTURE_ORIGIN_LEGACY_CN_ONLY = "legacy_cn_only"
STRUCTURE_ORIGINS = frozenset({
    STRUCTURE_ORIGIN_RAW_INPUT, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    STRUCTURE_ORIGIN_EXECUTED_PRODUCT, STRUCTURE_ORIGIN_LEGACY_CN_ONLY,
})

STEREO_SPECIFIED = "specified"
STEREO_PARTLY_UNSPECIFIED = "partly_unspecified"
STEREO_UNKNOWN = "unknown"
STEREO_NOT_APPLICABLE = "not_applicable"

ISOTOPE_SPECIFIED = "specified"
ISOTOPE_NOT_APPLICABLE = "not_applicable"
ISOTOPE_UNKNOWN = "unknown"  # CN-only:同位素状态不可知(与立体 unknown 同语义)

# 表示保真级别(§5.1 原始结构可用性的细化,不是新的结构事实)
REPRESENTATION_FULL_PARSE = "full_parse"
REPRESENTATION_ARCHIVE_RECOVERED = "archive_recovered"
REPRESENTATION_CN_ONLY_PROJECTION = "cn_only_projection"


class ChemicalStateError(RuntimeError):
    """ChemicalState 构造失败(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _identity_smiles(mol: Chem.Mol) -> str:
    """分子身份串:去原子映射号后的 canonical isomeric SMILES。

    保留形式电荷、同位素与立体信息;映射号是标注,不是分子身份。
    """
    for atom in mol.GetAtoms():
        if atom.GetAtomMapNum():
            atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(mol)


def _stereo_status(mol: Chem.Mol) -> str:
    """立体信息状态:结构中表示层面的如实标注,不冒称原始实验事实。"""
    try:
        infos = list(Chem.FindPotentialStereo(mol))
    except Exception:
        return STEREO_UNKNOWN
    if not infos:
        return STEREO_NOT_APPLICABLE
    n_specified = sum(
        1 for si in infos if str(si.specified) == "Specified")
    if n_specified == len(infos):
        return STEREO_SPECIFIED
    if n_specified == 0:
        return STEREO_UNKNOWN
    return STEREO_PARTLY_UNSPECIFIED


def _isotope_status(mol: Chem.Mol) -> str:
    for atom in mol.GetAtoms():
        if atom.GetIsotope():
            return ISOTOPE_SPECIFIED
    return ISOTOPE_NOT_APPLICABLE


@dataclass
class ChemicalState:
    """化学状态(§5.1 全字段;JSON 可往返,幂等重建得同一 state_id)。"""

    state_id: str
    structure_smiles_raw: str        # 原始输入串(未规范化,含映射号如有)
    smiles_isomeric: str             # 解析后的 canonical isomeric(无映射号)
    cn_identity: str                 # 旧口径 CN(评分/资产键适配;非结构事实)
    structure_origin: str
    original_structure_available: bool
    formal_charge: int | None        # None = 结构未知(CN-only),不猜
    stereo_information_status: str
    isotope_information_status: str
    source_refs: list[dict] = field(default_factory=list)
    representation_fidelity: str = REPRESENTATION_FULL_PARSE
    schema_version: str = PPV1_CHEMSTATE_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "ChemicalState":
        return cls(**d)


def build_chemical_state(
    structure: str,
    origin: str,
    source_refs: list[dict] | None = None,
    *,
    representation_fidelity: str = REPRESENTATION_FULL_PARSE,
) -> ChemicalState:
    """结构 → ChemicalState(工厂;解析失败 fail-closed)。

    representation_fidelity=archive_recovered:结构来自存档串(如历史
    product_smiles_full),按存档表示如实计算各状态字段,但存档串不含
    立体/同位素细节不代表原实验没有 —— 调用方在 source_refs 保留原始
    引用,本字段防冒称"原实验全部结构细节已知"。
    """
    if not isinstance(structure, str) or not structure.strip():
        raise ChemicalStateError(
            "结构输入为空或非字符串", {"structure": repr(structure)[:200],
                                   "origin": origin})
    if origin not in STRUCTURE_ORIGINS:
        raise ChemicalStateError(
            f"未知 structure_origin:{origin!r}(允许 {sorted(STRUCTURE_ORIGINS)})",
            {"origin": origin})
    mol = Chem.MolFromSmiles(structure)
    if mol is None:
        raise ChemicalStateError(
            "SMILES 无法解析(结构失败,不猜结构)",
            {"kind": "unparseable_smiles", "structure": structure[:200],
             "origin": origin})
    identity_smiles = _identity_smiles(mol)
    cn = _legacy_cn_identity(structure) or ""
    return ChemicalState(
        state_id=stable_id("cs", identity_smiles),
        structure_smiles_raw=structure,
        smiles_isomeric=identity_smiles,
        cn_identity=cn,
        structure_origin=origin,
        original_structure_available=True,
        formal_charge=Chem.GetFormalCharge(mol),
        stereo_information_status=_stereo_status(mol),
        isotope_information_status=_isotope_status(mol),
        source_refs=[dict(r) for r in (source_refs or [])],
        representation_fidelity=representation_fidelity,
    )


def build_chemical_state_from_cn_only(
    cn: str,
    source_refs: list[dict] | None = None,
) -> ChemicalState:
    """历史只剩 CN 的只读状态(§5.1):标 legacy_cn_only,不猜回结构。

    - structure_smiles_raw 记 CN 串本身(仅作追溯,不是原结构);
    - smiles_isomerial 不可得 → 空;formal_charge=None(不可知);
    - 立体/同位素状态=unknown(不伪造已知手性);
    - state_id 与结构状态空间隔离(前缀 cn-only,幂等)。
    """
    if not isinstance(cn, str) or not cn.strip():
        raise ChemicalStateError(
            "CN 输入为空或非字符串", {"cn": repr(cn)[:200]})
    return ChemicalState(
        state_id=stable_id("cs", "cn-only", cn),
        structure_smiles_raw=cn,
        smiles_isomeric="",
        cn_identity=cn,
        structure_origin=STRUCTURE_ORIGIN_LEGACY_CN_ONLY,
        original_structure_available=False,
        formal_charge=None,
        stereo_information_status=STEREO_UNKNOWN,
        isotope_information_status=ISOTOPE_UNKNOWN,
        source_refs=[dict(r) for r in (source_refs or [])],
        representation_fidelity=REPRESENTATION_CN_ONLY_PROJECTION,
    )
