"""Provenance — 复用既有标签,补细分而非升格(实施书 §5.4/§17.3.1)。

- 保留 kind、source_id、asset_sources、哈希、score_semantics,原样透传;
- 新增 source_origin 细分:curated_reaction | biotransformation_rule |
  analog_transfer | patent_template | model_proposal | unknown;
- evidence_basis 与 source_origin **分轴**保存(§17.3.1):
  experimentally_observed_exact 必须有可追溯观察记录、明确匹配范围和
  结构信息,不能仅凭 curated/kind/CN 标签推定 —— 映射函数不产出该值,
  只有显式带观察记录引用的构造路径可以使用;原始来源不充分时保持
  unknown/curated_record_only;
- recorded 表示库中记录,不自动表示本场景直接实测;
- 组合来源(如 envipath+retrieval)保存每个成分,不糊成单一"实测";
- 相同来源记录的重复引用只算一个支持组;原研究身份未知时独立支持数
  也未知(不把多个数据库 ID 当多次独立实验)。部分 study_map 映射
  下独立支持数是**已知下界**,以 count_basis 分轴披露(R3/P2:
  exact | known_lower_bound + unresolved 计数)。

既有标签产出处(P0-1 现状映射,均为本仓代码):
- kind 常量:domain/models.py:35-38(recorded_reaction / rule_application /
  analog_reaction / novel_proposal);
- recorded 卡:services/reaction_finder.py:240-266(kind=recorded、
  match_type=exact_donor_cn_match、source_id=btid#reac_id、asset_sources
  =library_full.jsonl);
- 规则/类比卡:services/reaction_finder.py:271-340(_kind_for_source
  :102-108;预测块来源含 eawag_lookup 也降格为 rule:273-275;组合来源
  每成分 asset_sources:299-302);
- 模型提案卡:services/prediction.py:854-931(novel/analogy、
  source_record.predicted_by_model=True、asset_sources=[])。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.models import (
    EVIDENCE_KIND_ANALOG,
    EVIDENCE_KIND_NOVEL,
    EVIDENCE_KIND_RECORDED,
    EVIDENCE_KIND_RULE,
    content_hash,
    stable_id,
)
from .profile import PPV1_PROVENANCE_SCHEMA_VERSION

SOURCE_ORIGIN_CURATED_REACTION = "curated_reaction"
SOURCE_ORIGIN_BIOTRANSFORMATION_RULE = "biotransformation_rule"
SOURCE_ORIGIN_ANALOG_TRANSFER = "analog_transfer"
SOURCE_ORIGIN_PATENT_TEMPLATE = "patent_template"
SOURCE_ORIGIN_MODEL_PROPOSAL = "model_proposal"
SOURCE_ORIGIN_UNKNOWN = "unknown"
SOURCE_ORIGINS = frozenset({
    SOURCE_ORIGIN_CURATED_REACTION, SOURCE_ORIGIN_BIOTRANSFORMATION_RULE,
    SOURCE_ORIGIN_ANALOG_TRANSFER, SOURCE_ORIGIN_PATENT_TEMPLATE,
    SOURCE_ORIGIN_MODEL_PROPOSAL, SOURCE_ORIGIN_UNKNOWN,
})

# 依据类型(分轴;不是强度次序,§17.3.5)
EVIDENCE_BASIS_EXPERIMENTALLY_OBSERVED = "experimentally_observed_exact"
EVIDENCE_BASIS_CURATED_RECORD_ONLY = "curated_record_only"
EVIDENCE_BASIS_RULE_DERIVED = "rule_derived"
EVIDENCE_BASIS_ANALOG_TRANSFERRED = "analog_transferred"
EVIDENCE_BASIS_MODEL_PROPOSED = "model_proposed"
EVIDENCE_BASIS_UNKNOWN = "unknown"
EVIDENCE_BASES = frozenset({
    EVIDENCE_BASIS_EXPERIMENTALLY_OBSERVED,
    EVIDENCE_BASIS_CURATED_RECORD_ONLY, EVIDENCE_BASIS_RULE_DERIVED,
    EVIDENCE_BASIS_ANALOG_TRANSFERRED, EVIDENCE_BASIS_MODEL_PROPOSED,
    EVIDENCE_BASIS_UNKNOWN,
})

# legacy match_type 取值(现状样例,透传保留;不据此升格)
_LEGACY_MATCH_MODEL_ANALOGY = "model_analogy_transfer"
_LEGACY_MATCH_MODEL_NOVEL = "model_constrained_proposal"
_LEGACY_MATCH_EXACT_DONOR = "exact_donor_cn_match"


@dataclass
class ProvenanceComponent:
    """组合来源的单个成分(每个成分各自的细分与资产引用)。"""

    source_origin: str
    evidence_basis: str
    asset_file: str = ""
    asset_sha256: str = ""
    source_id: str = ""
    role: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class ProvenanceInfo:
    """一条证据的来源细分(主成分 + 全部成分;原字段由调用方透传)。

    legacy_evidence_id(R3/P2):旧账本的证据 ID —— 导入映射到新
    record_id 后,旧 ID 保留在此字段供追溯(不悬空)。
    """

    source_origin: str
    evidence_basis: str
    components: list[ProvenanceComponent] = field(default_factory=list)
    legacy_kind: str = ""
    legacy_source_id: str = ""
    legacy_match_type: str = ""
    legacy_evidence_id: str = ""
    schema_version: str = PPV1_PROVENANCE_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "source_origin": self.source_origin,
            "evidence_basis": self.evidence_basis,
            "components": [c.to_dict() for c in self.components],
            "legacy_kind": self.legacy_kind,
            "legacy_source_id": self.legacy_source_id,
            "legacy_match_type": self.legacy_match_type,
            "legacy_evidence_id": self.legacy_evidence_id,
        }


def map_legacy_card(card: dict) -> ProvenanceInfo:
    """既有证据卡 → 来源细分(P0-1 映射 v2/F10 回修;不升格、不猜)。

    规则(与 reaction_finder.py 的产出逻辑一一对应;v2 修正):
    - kind=recorded_reaction → curated_reaction / curated_record_only
      (库中记录 ≠ 本场景直接实测;experimentally_observed_exact 不在
      此处产出 —— 需要显式观察记录);
    - kind=rule_application:**显式**来源标识才映射 —— uspto →
      patent_template;envipath/eawag 规则标识 → biotransformation_
      rule;来源与资产成分都无标识 ⇒ **unknown**(不默认生物转化规则;
      rule_derived 是推演性质,不代表生物来源已知,F10);
    - 组合来源逐成分映射:asset role envipath → biotransformation_
      rule、uspto → patent_template、**retrieval/语料 → analog_
      transfer**(语料检索邻居通道,不是生物转化规则,F10);
    - kind=analog_reaction 且 match_type 为模型类比提案或
      predicted_by_model → model_proposal(模型产物,与库中类比证据
      分开,F10);
    - kind=analog_reaction(检索邻居) → analog_transfer /
      analog_transferred;
    - kind=novel_proposal → model_proposal / model_proposed。
    """
    kind = str(card.get("kind", "") or "")
    source_id = str(card.get("source_id", "") or "")
    match_type = str(card.get("match_type", "") or "")
    asset_sources = card.get("asset_sources") or []
    source_record = card.get("source_record") or {}
    predicted_by_model = bool(source_record.get("predicted_by_model"))

    def _component_origin(asset: dict) -> str | None:
        token = str(asset.get("role", "")).lower()
        if "uspto" in token:
            return SOURCE_ORIGIN_PATENT_TEMPLATE
        if "envipath" in token or "eawag" in token:
            return SOURCE_ORIGIN_BIOTRANSFORMATION_RULE
        if "retrieval" in token or "corpus" in token:
            return SOURCE_ORIGIN_ANALOG_TRANSFER
        return None  # 成分无标识 ⇒ 该成分 unknown

    components: list[ProvenanceComponent] = []
    if kind == EVIDENCE_KIND_RECORDED:
        main_origin = SOURCE_ORIGIN_CURATED_REACTION
        main_basis = EVIDENCE_BASIS_CURATED_RECORD_ONLY
        for a in asset_sources or [{"role": "recorded"}]:
            components.append(ProvenanceComponent(
                source_origin=SOURCE_ORIGIN_CURATED_REACTION,
                evidence_basis=EVIDENCE_BASIS_CURATED_RECORD_ONLY,
                asset_file=str(a.get("asset_file", "")),
                asset_sha256=str(a.get("asset_sha256", "")),
                source_id=source_id, role=str(a.get("role", "recorded"))))
    elif kind == EVIDENCE_KIND_RULE:
        s = source_id.lower()
        has_uspto = "uspto" in s
        has_envipath = ("envipath" in s) or ("eawag" in s)
        component_origins = [c for c in (_component_origin(a)
                                         for a in asset_sources)
                             if c is not None]
        if has_uspto:
            main_origin = SOURCE_ORIGIN_PATENT_TEMPLATE
        elif has_envipath:
            main_origin = SOURCE_ORIGIN_BIOTRANSFORMATION_RULE
        elif component_origins:
            # 来源字符串无标识,但资产成分显式(组合来源主成分)
            main_origin = component_origins[0]
        else:
            main_origin = SOURCE_ORIGIN_UNKNOWN  # 无任何显式标识:不猜
        main_basis = EVIDENCE_BASIS_RULE_DERIVED
        for a in asset_sources or []:
            origin = _component_origin(a)
            components.append(ProvenanceComponent(
                source_origin=origin or SOURCE_ORIGIN_UNKNOWN,
                evidence_basis=EVIDENCE_BASIS_RULE_DERIVED,
                asset_file=str(a.get("asset_file", "")),
                asset_sha256=str(a.get("asset_sha256", "")),
                source_id=source_id, role=str(a.get("role", ""))))
    elif kind == EVIDENCE_KIND_ANALOG:
        if match_type == _LEGACY_MATCH_MODEL_ANALOGY or predicted_by_model:
            main_origin = SOURCE_ORIGIN_MODEL_PROPOSAL
            main_basis = EVIDENCE_BASIS_MODEL_PROPOSED
        else:
            main_origin = SOURCE_ORIGIN_ANALOG_TRANSFER
            main_basis = EVIDENCE_BASIS_ANALOG_TRANSFERRED
        for a in asset_sources or []:
            components.append(ProvenanceComponent(
                source_origin=main_origin, evidence_basis=main_basis,
                asset_file=str(a.get("asset_file", "")),
                asset_sha256=str(a.get("asset_sha256", "")),
                source_id=source_id, role=str(a.get("role", ""))))
    elif kind == EVIDENCE_KIND_NOVEL:
        main_origin = SOURCE_ORIGIN_MODEL_PROPOSAL
        main_basis = EVIDENCE_BASIS_MODEL_PROPOSED
        components.append(ProvenanceComponent(
            source_origin=SOURCE_ORIGIN_MODEL_PROPOSAL,
            evidence_basis=EVIDENCE_BASIS_MODEL_PROPOSED,
            source_id=source_id, role="model"))
    else:
        main_origin = SOURCE_ORIGIN_UNKNOWN
        main_basis = EVIDENCE_BASIS_UNKNOWN

    return ProvenanceInfo(
        source_origin=main_origin, evidence_basis=main_basis,
        components=components, legacy_kind=kind,
        legacy_source_id=source_id, legacy_match_type=match_type,
        legacy_evidence_id=str(card.get("evidence_id", "") or ""))


@dataclass
class SupportGroup:
    """支持组(§5.4:相同来源记录重复引用只算一组;v3/R3-P2)。

    independent_support_count 与 **count_basis 分轴**(P2:部分
    study_map 映射下该数是已知**下界**,不是精确独立研究数):
    - count_basis="exact":全部组的研究身份已知,计数精确;
    - count_basis="known_lower_bound":存在未知研究身份的组,
      independent_support_count = 已知不同研究身份数(**下界**),
      n_unresolved_study_identity = 未知组数 —— 不得把下界当精确值;
    - count_basis="unknown_study_identity":未提供 study_map,
      independent_support_count = None(不以布尔开关冒充研究身份)。
    """

    group_id: str
    record_refs: list[dict]
    count_basis: str                      # exact | known_lower_bound | unknown_study_identity
    independent_support_count: int | None   # None = 原研究身份未知
    origin_study_ref: str | None = None
    n_unresolved_study_identity: int | None = None
    schema_version: str = PPV1_PROVENANCE_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "group_id": self.group_id,
            "record_refs": [dict(r) for r in self.record_refs],
            "count_basis": self.count_basis,
            "independent_support_count": self.independent_support_count,
            "origin_study_ref": self.origin_study_ref,
            "n_unresolved_study_identity":
                self.n_unresolved_study_identity,
        }


COUNT_BASIS_EXACT = "exact"
COUNT_BASIS_KNOWN_LOWER_BOUND = "known_lower_bound"
COUNT_BASIS_UNKNOWN_STUDY_IDENTITY = "unknown_study_identity"


def build_support_groups(
    cards: list[dict],
    *,
    study_map: dict[str, str] | None = None,
) -> list[SupportGroup]:
    """证据卡 → 支持组列表(v3:记录去重与原研究独立性分开 + 分轴)。

    - 记录去重:相同 (kind, source_id) 的重复引用归一组(一组=一条
      库记录的引用集合);
    - 原研究独立性:study_map(库记录 key "kind:source_id" → 原研究
      身份)给出**实际可追溯**的原研究归并时,独立支持数 = 不同研究
      身份数,组携带 origin_study_ref;未提供 study_map(默认,本仓
      资产无原研究身份链)⇒ 独立支持数 = **None(未知)**;
    - P2:study_map 有未知映射时,计数标 **known_lower_bound**
      (已知下界,不冒称精确独立研究数),未知组数单独披露。
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for card in cards:
        key = (str(card.get("kind", "")), str(card.get("source_id", "")))
        groups.setdefault(key, []).append({
            "evidence_id": card.get("evidence_id", ""),
            "kind": card.get("kind", ""),
            "source_id": card.get("source_id", ""),
            "asset_file": card.get("asset_file", ""),
            "asset_sha256": card.get("asset_sha256", ""),
        })
    out: list[SupportGroup] = []
    study_of_group: dict[tuple[str, str], str | None] = {}
    for key in sorted(groups):
        kind, sid = key
        if study_map is not None:
            study_of_group[key] = study_map.get(f"{kind}:{sid}")
        else:
            study_of_group[key] = None
    n_independent = None
    n_unresolved = None
    basis = COUNT_BASIS_UNKNOWN_STUDY_IDENTITY
    if study_map is not None:
        known_studies = {s for s in study_of_group.values() if s}
        n_unresolved = len(
            [k for k, s in study_of_group.items() if not s])
        n_independent = len(known_studies)
        basis = (COUNT_BASIS_EXACT if n_unresolved == 0
                 else COUNT_BASIS_KNOWN_LOWER_BOUND)
    for (kind, sid), refs in sorted(groups.items()):
        out.append(SupportGroup(
            group_id=stable_id("sg", kind, sid, content_hash(refs)),
            record_refs=refs,
            count_basis=basis,
            independent_support_count=n_independent,
            origin_study_ref=study_of_group.get((kind, sid)),
            n_unresolved_study_identity=n_unresolved,
        ))
    return out
