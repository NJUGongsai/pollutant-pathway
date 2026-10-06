"""ChemicalState — 化学状态与 CN 身份分开(实施书 §5.1,S1;v3 回修)。

v3(ppv1-chemstate-3,2026-10-06 R3 回修)相对 v2 的变化:
- 身份键 = 规范化 canonical CXSMILES(RDKit canonical 写出器对增强
  立体做规范化:AND/OR 整组翻转同键、部分反转保持不同);公开表示
  smiles_isomeric 同源携带注解,往返闭合;plain 与 ABS 归一。

v4(ppv1-chemstate-4,2026-10-06 R4 回修)相对 v3 的变化(均为 Codex
R3 复审 R3-04 与 mimo R3 1.2/1.3 的落实):
- 身份键 = **化学 CX 事实子集**:生成前移除非化学 CX 元数据 ——
  坐标(conformer)、原子标签(atomLabel)、任意 atomProp(绘图/
  注释不改严格分子图身份);保留增强立体组、自由基层、基串内的
  同位素/电荷/立体;
- **混合并列 ABS 归一**:ABS 剥离改为令牌级语法解析(``a:1,&1:3``
  ≡ ``|&1:3|``、``^1:0,a:1`` ≡ ``|^1:0|``;v3 的段级正则对逗号并列
  形态永远匹配不上,同一立体事实分裂成两个 state_id,mimo A2b);
- 与 RDKit RegistrationHash 的一致性**限定**在整组翻转/部分反转/
  排列/kekulé/映射号子集;plain≡|a:…| 同键是本仓归一设计,与
  RegistrationHash 的 CANONICAL_SMILES 层(保留 |a:…|)存在
  **已登记分歧**;
- 无组且无自由基层注解的分子输出与普通 canonical isomeric SMILES
  逐字相同;**自由基分子带 |^n:…| 后缀是例外**(radical 保真轴
  为已登记缺口,身份层区分自由基)。

v2(ppv1-chemstate-2,2026-10-05 回修)的变化:
- 身份键在 canonical 重排后的分子图上生成,并显式序列化增强立体组
  (v1 普通 MolToSmiles 静默丢组造成三输入碰撞,F05);
- representation_fidelity 由单旗标改为**分轴声明**(stereo / isotope /
  formal_charge / protonation_basis),电荷轴直接决定电荷账可算性;
- 通用工厂拒绝 origin=legacy_cn_only(CN-only 只能走专用只读工厂);
- from_dict 校验 schema 版本,未知版本 fail-closed(F08)。

既有不变量(自 v1):state_id 按保留形式电荷、同位素和立体信息的确定性
分子图生成;原子映射号不属于分子身份;原始结构与解析后的图都保留;
形式电荷是结构事实不表示某 pH 质子化分布;CN 仅作旧评分/资产键适配
(cn_identity 的 basis: scoring_key —— contract clause,
implementation pending;未落地前不得在报告呈现该字段);CN-only 不
猜回立体信息;存档形恢复不冒称原实验全部结构细节已知。

解析失败 fail-closed(ChemicalStateError,kind=unparseable_smiles)。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rdkit import Chem, RDLogger

from ..domain.identity import cn_identity as _legacy_cn_identity
from ..domain.models import stable_id
from .profile import PPV1_CHEMSTATE_SCHEMA_VERSION

RDLogger.DisableLog("rdApp.*")

PPV1_CHEMSTATE_SUPPORTED_VERSIONS = (PPV1_CHEMSTATE_SCHEMA_VERSION,)

STRUCTURE_ORIGIN_RAW_INPUT = "raw_input"
STRUCTURE_ORIGIN_SOURCE_PRODUCT = "source_product"
STRUCTURE_ORIGIN_EXECUTED_PRODUCT = "executed_product"
STRUCTURE_ORIGIN_LEGACY_CN_ONLY = "legacy_cn_only"
STRUCTURE_ORIGINS = frozenset({
    STRUCTURE_ORIGIN_RAW_INPUT, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    STRUCTURE_ORIGIN_EXECUTED_PRODUCT, STRUCTURE_ORIGIN_LEGACY_CN_ONLY,
})
# 通用结构工厂接受的来源(legacy_cn_only 只能走专用只读工厂)
STRUCTURE_FACTORY_ORIGINS = frozenset({
    STRUCTURE_ORIGIN_RAW_INPUT, STRUCTURE_ORIGIN_SOURCE_PRODUCT,
    STRUCTURE_ORIGIN_EXECUTED_PRODUCT,
})

STEREO_SPECIFIED = "specified"
STEREO_PARTLY_UNSPECIFIED = "partly_unspecified"
STEREO_UNKNOWN = "unknown"
STEREO_NOT_APPLICABLE = "not_applicable"

ISOTOPE_SPECIFIED = "specified"
ISOTOPE_NOT_APPLICABLE = "not_applicable"
ISOTOPE_UNKNOWN = "unknown"  # CN-only:同位素状态不可知

# 表示保真分轴(mimo 1.2(2);每轴独立取值,不混单旗标)
FIDELITY_AXES = ("stereo", "isotope", "formal_charge", "protonation_basis")
FIDELITY_AS_WRITTEN = "as_written"
FIDELITY_ABSENT_IN_ARCHIVE = "absent_in_archive"
FIDELITY_UNKNOWN = "unknown"
FIDELITY_NEUTRALIZED_BY_CN = "neutralized_by_cn"

_FULL_PARSE_FIDELITY = {
    "stereo": FIDELITY_AS_WRITTEN,
    "isotope": FIDELITY_AS_WRITTEN,
    "formal_charge": FIDELITY_AS_WRITTEN,
    "protonation_basis": FIDELITY_AS_WRITTEN,
}
_ARCHIVE_RECOVERED_FIDELITY = {
    # 存档串不含立体/同位素细节 ⇒ 该两轴记 absent_in_archive(不代表
    # 原实验没有);电荷按存档串 as_written —— 中性串电荷为零可以是
    # 合法结构事实,不从中性猜"电荷丢失"(Codex §4 纠偏 mimo)
    "stereo": FIDELITY_ABSENT_IN_ARCHIVE,
    "isotope": FIDELITY_ABSENT_IN_ARCHIVE,
    "formal_charge": FIDELITY_AS_WRITTEN,
    "protonation_basis": FIDELITY_AS_WRITTEN,
}
_CN_ONLY_FIDELITY = {
    "stereo": FIDELITY_UNKNOWN,
    "isotope": FIDELITY_UNKNOWN,
    # CN 已中和:原始电荷不可猜回 ⇒ 电荷轴 unknown,电荷账不可算
    "formal_charge": FIDELITY_UNKNOWN,
    "protonation_basis": FIDELITY_NEUTRALIZED_BY_CN,
}

# 旧单旗标 → 分轴(读取 v1 字符串形状时的显式映射;仅用于诊断输出,
# 不用于恢复数据 —— 本 profile 无历史产物)
LEGACY_FIDELITY_LABELS = frozenset({
    "full_parse", "archive_recovered", "cn_only_projection"})


class ChemicalStateError(RuntimeError):
    """ChemicalState 构造失败(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _identity_key(mol: Chem.Mol) -> str:
    """分子身份键(v4):**化学 CX 事实子集**的规范化 canonical CXSMILES。

    - 原子映射号不属于分子身份(生成前去除);
    - **非化学 CX 元数据移除**:二维/三维坐标(conformer)、原子标签
      (atomLabel)、任意 atomProp —— 绘图与注释不改变严格分子图身份
      (R3-04:普通 CO / 原子标签 / 坐标 / atomProp note 五输入同键);
    - **保留化学事实**:增强立体组(AND/OR)、自由基层(^n:idx)、
      同位素/电荷/立体(基串);RDKit canonical 写出器对增强立体做
      规范化(AND/OR 整组翻转同键、部分反转保持不同);
    - ABS 组是冗余注解(与 isomeric SMILES 默认绝对构型同一事实)
      ⇒ **令牌级**剥离(支持混合并列形态:a:1,&1:3 / ^1:0,a:1 /
      a:2,5,&1:2,5;逗号既分隔注解头也分隔组内原子列表,故按"有
      前缀的注解头 token + 其后裸数字延续"语法解析,R3-04/mimo
      A2b);
    - Kekulé/芳香表示差异由 RDKit 感知归一;
    - 键值 = 公开表示(smiles_isomeric),同一事实源(往返重建同 id)。
    """
    m = Chem.Mol(mol)
    for atom in m.GetAtoms():
        if atom.GetAtomMapNum():
            atom.SetAtomMapNum(0)
        for prop in list(atom.GetPropNames()):
            atom.ClearProp(prop)
    m.RemoveAllConformers()
    for prop in list(m.GetPropNames()):
        m.ClearProp(prop)
    return _strip_abs_tokens(Chem.MolToCXSmiles(m))


def _strip_abs_tokens(cxsmiles: str) -> str:
    """从 canonical CXSMILES 的 |…| 扩展段剥离 ABS 组注解(令牌级)。

    语法依据(CXSMILES 写出器实测):注解段内不同组以逗号连接
    (如 ``a:1,&1:3``、``^1:0,a:1``),组内原子列表同样以逗号连接
    (如 ``&1:2,5``)。token 含 ``:`` 且前缀为注解头(``a``/``&N``/
    ``oN``/``^N``)时开新注解;裸数字 token 是上一注解的原子列表
    延续。ABS 组(``a:`` 前缀)与其后的延续数字一并剥除;其余
    (AND/OR 组、自由基层)原样保留。段间仍按空白分块。
    """
    m = re.search(r"\|([^|]*)\|\s*$", cxsmiles)
    if not m:
        return cxsmiles
    blocks = m.group(1).split(" ")
    kept_blocks = []
    for block in blocks:
        tokens = block.split(",")
        kept: list[str] = []
        skipping_abs = False
        for token in tokens:
            head, sep, _ = token.partition(":")
            has_annotation_head = bool(sep) and bool(head) and not \
                head.lstrip("!").isdigit() and head.lstrip("!") != ""
            if has_annotation_head:
                skipping_abs = head.rstrip("!") == "a"
                if not skipping_abs:
                    kept.append(token)
            else:
                if not skipping_abs:
                    kept.append(token)
        kept_blocks.append(",".join(kept))
    body = " ".join(b for b in kept_blocks if b).strip()
    if not body:
        return cxsmiles[:m.start()].strip()
    return cxsmiles[:m.start()].rstrip() + " |" + body + "|"


def normalized_structure_smiles(mol: Chem.Mol) -> str:
    """公开规范表示(= 身份键;供 smiles_isomeric 输出)。

    带增强立体组的结构携带 CX 注解(往返可重建同一 state_id);
    无组**且无自由基层注解**的分子输出与普通 canonical isomeric
    SMILES 逐字相同;自由基分子带 ``|^n:…|`` 后缀(radical 保真轴
    为已登记缺口,身份层区分自由基)。非化学元数据(坐标/标签/
    atomProp)不进入公开表示。
    """
    return _identity_key(mol)


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


def _validate_fidelity(fidelity: dict, origin: str) -> dict:
    out = {}
    for axis in FIDELITY_AXES:
        value = (fidelity or {}).get(axis)
        allowed = {FIDELITY_AS_WRITTEN, FIDELITY_ABSENT_IN_ARCHIVE,
                   FIDELITY_UNKNOWN, FIDELITY_NEUTRALIZED_BY_CN}
        if value not in allowed:
            raise ChemicalStateError(
                f"representation_fidelity 轴 {axis} 取值非法:{value!r}",
                {"axis": axis, "value": repr(value), "origin": origin})
        out[axis] = value
    return out


@dataclass
class ChemicalState:
    """化学状态(§5.1 全字段;JSON 可往返,幂等重建得同一 state_id)。

    representation_fidelity(v2 起为分轴 dict):结构语义各轴的保真度,
    其中 formal_charge 轴 == as_written 是电荷账可算的前提(F01/mimo)。
    structure_smiles_raw / structure_origin / source_refs 属**出现记录**
    (同一结构不同来路各自保留,见 store 的语义/出现拆分,F04),不参与
    state_id 或身份冲突判定。
    """

    state_id: str
    structure_smiles_raw: str        # 原始输入串(未规范化,含映射号如有)
    smiles_isomeric: str             # 规范化 canonical CXSMILES(=身份键;
                                     # 增强立体注解保留,往返重建同一 id)
    cn_identity: str                 # 旧口径 CN(评分/资产键;非结构事实)
    structure_origin: str
    original_structure_available: bool
    formal_charge: int | None        # None = 原始电荷不可知(CN-only)
    stereo_information_status: str
    isotope_information_status: str
    source_refs: list[dict] = field(default_factory=list)
    representation_fidelity: dict = field(
        default_factory=lambda: dict(_FULL_PARSE_FIDELITY))
    schema_version: str = PPV1_CHEMSTATE_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "ChemicalState":
        version = d.get("schema_version")
        if version not in PPV1_CHEMSTATE_SUPPORTED_VERSIONS:
            raise ChemicalStateError(
                f"ChemicalState schema 版本未知:{version!r}(支持 "
                f"{list(PPV1_CHEMSTATE_SUPPORTED_VERSIONS)};fail-closed,"
                "不静默按当前版本解析)",
                {"schema_version": version})
        fidelity = _validate_fidelity(
            d.get("representation_fidelity") or {},
            d.get("structure_origin", ""))
        payload = dict(d)
        payload["representation_fidelity"] = fidelity
        return cls(**payload)


def build_chemical_state(
    structure: str,
    origin: str,
    source_refs: list[dict] | None = None,
    *,
    fidelity: dict | None = None,
) -> ChemicalState:
    """结构 → ChemicalState(工厂;解析失败 fail-closed)。

    - origin 仅接受 raw_input / source_product / executed_product;
      legacy_cn_only 走 build_chemical_state_from_cn_only(专用只读
      工厂,不伪装原始结构可知,F05);
    - fidelity 缺省按 origin 取全轴 as_written;archive 场景调用方传
      _ARCHIVE_RECOVERED_FIDELITY 或逐轴覆盖(存档串的立体/同位素轴
      记 absent_in_archive;电荷轴 as_written —— 中性是合法结构事实)。
    """
    if not isinstance(structure, str) or not structure.strip():
        raise ChemicalStateError(
            "结构输入为空或非字符串", {"structure": repr(structure)[:200],
                                   "origin": origin})
    if origin not in STRUCTURE_FACTORY_ORIGINS:
        if origin == STRUCTURE_ORIGIN_LEGACY_CN_ONLY:
            raise ChemicalStateError(
                "origin=legacy_cn_only 不能用通用结构工厂(CN-only 状态"
                "须走 build_chemical_state_from_cn_only,原始结构不可知"
                "不得伪装为可知)",
                {"kind": "cn_only_requires_dedicated_factory",
                 "origin": origin})
        raise ChemicalStateError(
            f"未知 structure_origin:{origin!r}(允许 "
            f"{sorted(STRUCTURE_FACTORY_ORIGINS)})",
            {"kind": "invalid_structure_origin", "origin": origin})
    mol = Chem.MolFromSmiles(structure)
    if mol is None:
        raise ChemicalStateError(
            "SMILES 无法解析(结构失败,不猜结构)",
            {"kind": "unparseable_smiles", "structure": structure[:200],
             "origin": origin})
    base_fidelity = dict(_FULL_PARSE_FIDELITY)
    for k, v in (fidelity or {}).items():
        if k not in FIDELITY_AXES:
            raise ChemicalStateError(
                f"未知保真轴:{k!r}(允许 {list(FIDELITY_AXES)})",
                {"axis": k})
        base_fidelity[k] = v
    resolved_fidelity = _validate_fidelity(base_fidelity, origin)
    identity = _identity_key(mol)
    cn = _legacy_cn_identity(structure) or ""
    return ChemicalState(
        state_id=stable_id("cs", identity),
        structure_smiles_raw=structure,
        smiles_isomeric=identity,  # 规范化 CXSMILES(=身份键,往返闭合)
        cn_identity=cn,
        structure_origin=origin,
        original_structure_available=True,
        formal_charge=Chem.GetFormalCharge(mol),
        stereo_information_status=_stereo_status(mol),
        isotope_information_status=_isotope_status(mol),
        source_refs=[dict(r) for r in (source_refs or [])],
        representation_fidelity=resolved_fidelity,
    )


def archive_recovered_fidelity() -> dict:
    """存档形恢复的分轴模板(立体/同位素 absent_in_archive)。"""
    return dict(_ARCHIVE_RECOVERED_FIDELITY)


def build_chemical_state_from_cn_only(
    cn: str,
    source_refs: list[dict] | None = None,
) -> ChemicalState:
    """历史只剩 CN 的只读状态(§5.1):标 legacy_cn_only,不猜回结构。

    - structure_smiles_raw 记 CN 串本身(仅作追溯,不是原结构);
    - smiles_isomeric 空;formal_charge=None(CN 已中和,原始电荷
      不可猜回 ⇒ 电荷账不可算,F01/mimo C1);
    - 立体/同位素状态=unknown;fidelity 分轴见 _CN_ONLY_FIDELITY;
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
        representation_fidelity=dict(_CN_ONLY_FIDELITY),
    )


def strict_identity_of(structure: str) -> str:
    """与 state_id 同一事实源的严格身份键(供体诊断 strict 轴等复用)。

    解析失败抛 ChemicalStateError(与 build_chemical_state 同 fail-closed
    语义);不构造完整状态,只取身份键。
    """
    if not isinstance(structure, str) or not structure.strip():
        raise ChemicalStateError(
            "结构输入为空或非字符串", {"structure": repr(structure)[:200]})
    mol = Chem.MolFromSmiles(structure)
    if mol is None:
        raise ChemicalStateError(
            "SMILES 无法解析", {"kind": "unparseable_smiles",
                             "structure": structure[:200]})
    return _identity_key(mol)
