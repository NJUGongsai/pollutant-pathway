"""类比来源适配 — 供体反应找回、映射质量判定与当前分子对齐(任务书 §1)。

建立**可复核**的类比证据来源:从本仓已校验资产中以稳定 ID 找回来源
反应物、产物、原子映射和反应中心,并记录所用文件、SHA256、行号与映射
质量。两类找回(全部确定性、不凭来源字符串或候选产物编造映射):

1. **映射模板找回**(analogy_edit 的前提):``assets/analog/
   corpus_templates_v1.jsonl`` 逐行带 ``mapped_lhs/mapped_rhs``(原子映射
   供体反应)、``center_atoms``、``qc_flags``。按 ``record_id`` 精确解析;
   另建"产物身份 → 模板行"反向索引,支持把检索候选产物找回为唯一条
   映射模板。
2. **供体记录溯源**(``assets/v3_reactions/corpus_env/corpus_v1.jsonl`` +
   ``donor_index.jsonl``):检索引擎的事实源。多数行 ``mapping_status=
   absent``(无原子映射)——只用于溯源"哪些记录能产出该产物",如实标注
   ``unmapped``,不冒充映射。

无法找回、映射质量不合格或无法对齐当前分子的卡 → ``mapping_status=
unavailable`` + 结构化 ``mapping_reason``(拒因留痕)。对齐用 RDKit
子结构匹配(全供体优先,失败退反应中心),确定性取首个匹配。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

from ..adapters.asset_manifest import sha256_file  # noqa: E402
from ..domain.identity import cn_identity, stereo_blind  # noqa: E402
from .atom_tool import align_donor_mapping  # noqa: E402

ANALOG_CORPUS_REL = "analog/corpus_templates_v1.jsonl"
CORPUS_V1_REL = "v3_reactions/corpus_env/corpus_v1.jsonl"
DONOR_INDEX_REL = "v3_reactions/corpus_env/donor_index.jsonl"

# mapping_status(检索卡字段;缺省 unavailable,兼容 v1 读取)
MAPPING_RESOLVED = "resolved"        # 唯一映射模板 + 已对齐当前分子
MAPPING_AMBIGUOUS = "ambiguous"      # 多条候选贡献,无法归因到单一供体
MAPPING_UNAVAILABLE = "unavailable"  # 找不回/无映射/无法对齐(原因在 reason)

# mapping_quality(供体记录的映射质量,来自解析与 qc_flags,不猜测)
QUALITY_BIJECTION = "mapped_bijection"      # 双侧可解析 + 元素守恒 + 双射
QUALITY_UNVERIFIED = "mapped_unverified"    # 有映射但 qc 旗标不齐
QUALITY_UNPARSEABLE = "mapped_unparseable"  # 映射 SMILES 解析失败
QUALITY_UNMAPPED = "unmapped"               # 记录无原子映射(如 corpus_v1)

ALIGN_FULL = "full_donor_substructure"
ALIGN_CENTER = "reaction_center_substructure"


@dataclass
class DonorRef:
    """一个可追溯的供体反应引用(检索卡 donor_refs / 任务书 donor 块)。"""

    record_id: str
    index: str                    # analog_corpus_templates | corpus_v1
    asset_file: str               # 相对资产根
    asset_sha256: str
    line_no: int
    mapping_quality: str
    reactant_smiles: str          # 供体反应物(去映射 canonical)
    product_smiles: str           # 供体产物(去映射 canonical)
    mapped_lhs: str = ""
    mapped_rhs: str = ""
    center_atoms: list = field(default_factory=list)
    alignment: dict | None = None  # {strategy, n_aligned, alignment:{donor_idx: current_idx}}

    def to_dict(self) -> dict:
        return dict(self.__dict__)


class AnalogSourceError(RuntimeError):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _lhs_rhs(row: dict) -> tuple[str, str]:
    tpl = str(row.get("template_id", ""))
    if ">" in tpl and "mapped_lhs" not in row:
        lhs, _, rhs = tpl.partition(">>")
        return lhs, rhs
    return str(row.get("mapped_lhs", "")), str(row.get("mapped_rhs", ""))


def _mapped_mol(smiles: str):
    return Chem.MolFromSmiles(smiles) if smiles else None


def _strip_map(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return ""
    for a in mol.GetAtoms():
        a.SetAtomMapNum(0)
    return Chem.MolToSmiles(mol)


def _mapping_quality(lhs: str, rhs: str, qc: dict) -> str:
    lm, rm = _mapped_mol(lhs), _mapped_mol(rhs)
    if lm is None or rm is None:
        return QUALITY_UNPARSEABLE
    l_maps = {a.GetAtomMapNum() for a in lm.GetAtoms() if a.GetAtomMapNum()}
    r_maps = {a.GetAtomMapNum() for a in rm.GetAtoms() if a.GetAtomMapNum()}
    if not l_maps or not r_maps:
        return QUALITY_UNPARSEABLE
    if qc.get("element_balance") and qc.get("bijection"):
        return QUALITY_BIJECTION
    return QUALITY_UNVERIFIED


class AnalogSourceResolver:
    """按稳定 ID 找回供体反应;惰性反向索引按文件 SHA 缓存于类级。"""

    def __init__(self, config) -> None:
        from ..adapters.asset_manifest import verify_repo_manifest

        self.assets_root = Path(config.assets_root).resolve()
        self.manifest = verify_repo_manifest(self.assets_root)  # fail-closed
        self.paths = {
            "analog_corpus_templates": self.assets_root / ANALOG_CORPUS_REL,
            "corpus_v1": self.assets_root / CORPUS_V1_REL,
        }
        for name, path in self.paths.items():
            if not path.is_file():
                raise AnalogSourceError(
                    f"类比来源文件缺失:{path}", {"index": name}
                )
        self._asset_meta = {
            name: {"asset_file": rel, "asset_sha256": self.manifest["files"][rel]}
            for name, rel in (
                ("analog_corpus_templates", ANALOG_CORPUS_REL),
                ("corpus_v1", CORPUS_V1_REL),
            )
        }

    # ------------------------------------------------------------ 索引

    def _index_key(self, name: str) -> tuple:
        return (name, self._asset_meta[name]["asset_sha256"])

    _INDEX_CACHE: dict = {}

    def _template_by_record(self) -> dict[str, dict]:
        key = self._index_key("analog_corpus_templates")
        cached = AnalogSourceResolver._INDEX_CACHE.get(key)
        if cached is None:
            cached = {}
            with open(self.paths["analog_corpus_templates"], encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    cached[str(row.get("record_id", ""))] = {
                        "row": row, "line_no": line_no,
                    }
            AnalogSourceResolver._INDEX_CACHE[key] = cached
        return cached

    def _templates_by_rhs(self) -> dict[str, list[dict]]:
        """产物身份(stereo-blind canonical)→ 模板行列表。"""
        key = self._index_key("analog_corpus_templates") + ("rhs",)
        cached = AnalogSourceResolver._INDEX_CACHE.get(key)
        if cached is None:
            cached: dict[str, list[dict]] = {}
            with open(self.paths["analog_corpus_templates"], encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    lhs, rhs = _lhs_rhs(row)
                    rid = _strip_map(rhs)
                    if not rid:
                        continue
                    ident = stereo_blind(rid)
                    if ident:
                        cached.setdefault(ident, []).append(
                            {"row": row, "line_no": line_no}
                        )
            AnalogSourceResolver._INDEX_CACHE[key] = cached
        return cached

    def _corpus_v1_by_product(self) -> dict[str, list[dict]]:
        """产物身份 → corpus_v1 记录行(溯源用;多数无映射,如实标注)。"""
        key = self._index_key("corpus_v1") + ("product",)
        cached = AnalogSourceResolver._INDEX_CACHE.get(key)
        if cached is None:
            cached: dict[str, list[dict]] = {}
            with open(self.paths["corpus_v1"], encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    for comp in row.get("product_components") or []:
                        ident = stereo_blind(str(comp))
                        if ident:
                            cached.setdefault(ident, []).append(
                                {"row": row, "line_no": line_no}
                            )
            AnalogSourceResolver._INDEX_CACHE[key] = cached
        return cached

    # ------------------------------------------------------------ 找回

    def resolve_template(self, record_id: str) -> DonorRef | None:
        """按 record_id 从 analog corpus 精确解析映射模板(稳定 ID 找回)。"""
        hit = self._template_by_record().get(str(record_id))
        if hit is None:
            return None
        row = hit["row"]
        lhs, rhs = _lhs_rhs(row)
        meta = self._asset_meta["analog_corpus_templates"]
        return DonorRef(
            record_id=str(row.get("record_id", record_id)),
            index="analog_corpus_templates",
            asset_file=meta["asset_file"],
            asset_sha256=meta["asset_sha256"],
            line_no=hit["line_no"],
            mapping_quality=_mapping_quality(lhs, rhs, row.get("qc_flags") or {}),
            reactant_smiles=_strip_map(lhs),
            product_smiles=_strip_map(rhs),
            mapped_lhs=lhs, mapped_rhs=rhs,
            center_atoms=[int(x) for x in (row.get("center_atoms") or [])],
        )

    def templates_producing(self, product_identity: str) -> list[DonorRef]:
        """能产出该产物身份的映射模板(候选供体;多于一条即歧义)。"""
        hits = self._templates_by_rhs().get(product_identity, [])
        out = []
        for hit in hits:
            row = hit["row"]
            lhs, rhs = _lhs_rhs(row)
            meta = self._asset_meta["analog_corpus_templates"]
            out.append(DonorRef(
                record_id=str(row.get("record_id", "")),
                index="analog_corpus_templates",
                asset_file=meta["asset_file"],
                asset_sha256=meta["asset_sha256"],
                line_no=hit["line_no"],
                mapping_quality=_mapping_quality(
                    lhs, rhs, row.get("qc_flags") or {}),
                reactant_smiles=_strip_map(lhs),
                product_smiles=_strip_map(rhs),
                mapped_lhs=lhs, mapped_rhs=rhs,
                center_atoms=[int(x) for x in (row.get("center_atoms") or [])],
            ))
        return out

    def records_producing(self, product_identity: str) -> list[DonorRef]:
        """corpus_v1 溯源:能产出该产物的记录(多数 unmapped,如实标注)。"""
        hits = self._corpus_v1_by_product().get(product_identity, [])
        out = []
        meta = self._asset_meta["corpus_v1"]
        for hit in hits:
            row = hit["row"]
            out.append(DonorRef(
                record_id=str(row.get("record_id", "")),
                index="corpus_v1",
                asset_file=meta["asset_file"],
                asset_sha256=meta["asset_sha256"],
                line_no=hit["line_no"],
                mapping_quality=QUALITY_UNMAPPED,
                reactant_smiles=str(row.get("donor_A_smiles", "") or ""),
                product_smiles="",
                mapped_lhs="", mapped_rhs="",
                center_atoms=[],
            ))
        return out

    # ------------------------------------------------------------ 对齐

    def align(self, ref: DonorRef, current_smiles: str) -> DonorRef:
        """把供体模板的反应物对齐到当前分子(全供体 → 反应中心两级)。

        对齐用**带映射**的 lhs(中心原子按 AtomMapNum 找);返回的
        alignment 字典键为原始供体原子 idx。"""
        current = Chem.MolFromSmiles(current_smiles)
        donor = Chem.MolFromSmiles(ref.mapped_lhs or ref.reactant_smiles)
        if current is None or donor is None:
            ref.alignment = None
            return ref
        if cn_identity(ref.reactant_smiles) == cn_identity(current_smiles):
            # 供体与当前分子相同:这是精确查找的领域,不算类比
            ref.alignment = None
            return ref
        match, _ = align_donor_mapping(donor, current)
        strategy = ALIGN_FULL
        if match is None:
            match, _ = align_donor_mapping(
                donor, current, center_map_nums=ref.center_atoms or None,
                center_only=True,
            )
            strategy = ALIGN_CENTER
        if match is None:
            ref.alignment = None
            return ref
        ref.alignment = {
            "strategy": strategy,
            "n_aligned": len(match),
            "alignment": {str(d): c for d, c in match.items()},
        }
        return ref


def build_card_mapping_fields(
    resolver: AnalogSourceResolver | None,
    product_identity: str,
    substrate_smiles: str,
) -> dict:
    """检索卡 mapping 字段组(任务书 §1:卡上明确标 mapping_unavailable)。

    找回次序:唯一映射模板(对齐当前分子)→ resolved;多条模板 →
    ambiguous;无模板但 corpus_v1 有贡献记录 → unavailable(留溯源 refs
    与原因 no_mapped_template / donor_not_aligned);什么都没有 →
    unavailable:no_donor_record。resolver 缺席 → unavailable:not_attempted。
    """
    if resolver is None:
        return {"donor_refs": [], "mapping_status": MAPPING_UNAVAILABLE,
                "mapping_reason": "not_attempted:no_resolver"}
    refs = resolver.templates_producing(product_identity)
    refs = [r for r in refs if r.mapping_quality != QUALITY_UNPARSEABLE]
    if len(refs) == 1:
        aligned = resolver.align(refs[0], substrate_smiles)
        if aligned.alignment is not None:
            return {"donor_refs": [aligned.to_dict()],
                    "mapping_status": MAPPING_RESOLVED,
                    "mapping_reason": "unique_mapped_template_aligned"}
        trace = resolver.records_producing(product_identity)
        return {"donor_refs": [aligned.to_dict()] + [t.to_dict() for t in trace],
                "mapping_status": MAPPING_UNAVAILABLE,
                "mapping_reason": "donor_not_aligned"}
    if len(refs) > 1:
        return {"donor_refs": [r.to_dict() for r in refs],
                "mapping_status": MAPPING_AMBIGUOUS,
                "mapping_reason": f"ambiguous:{len(refs)}_templates_produce_product"}
    trace = resolver.records_producing(product_identity)
    if trace:
        return {"donor_refs": [t.to_dict() for t in trace],
                "mapping_status": MAPPING_UNAVAILABLE,
                "mapping_reason": "no_mapped_template:traceability_only"}
    return {"donor_refs": [], "mapping_status": MAPPING_UNAVAILABLE,
            "mapping_reason": "no_donor_record"}
