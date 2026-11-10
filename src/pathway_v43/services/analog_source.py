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
from rdkit.Chem import rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

from ..adapters.asset_manifest import sha256_file  # noqa: E402
from ..domain.identity import cn_identity, stereo_blind  # noqa: E402
from .atom_tool import align_donor_mapping  # noqa: E402

CORPUS_V1_REL = "v3_reactions/corpus_env/corpus_v1.jsonl"
DONOR_INDEX_REL = "v3_reactions/corpus_env/donor_index.jsonl"


def _analog_corpus_rel(config) -> str:
    """Phase D D2:按配置显式选择 v1/v2 语料(白名单外的值在 config 层
    已拒;此处再 fail-closed 一次,防旁路构造)。"""
    from ..adapters.asset_manifest import analog_corpus_rel

    return analog_corpus_rel(getattr(config, "analog_corpus", "v1"))

# ---- Phase D D1:供体反应物相似度检索(reactant_similar 通道) ----
# 检索定义整体版本化:指纹/半径/位数/立体/规范化/阈值边界任何一项变化
# 都必须升版本并使跨版本缓存失效(索引键含本串)。
SIMILARITY_VERSION = "v43-rsim-1"
SIMILARITY_FP_KIND = "morgan"
SIMILARITY_FP_RADIUS = 2
SIMILARITY_FP_BITS = 2048
SIMILARITY_FP_CHIRALITY = False   # 立体盲(与 stereo_blind 身份口径一致)
SIMILARITY_METRIC = "tanimoto"
SIMILARITY_CMP = "ge"             # 阈值边界:相似度 >= threshold 才召回

# 找回通道(Phase D 任务书 §2:三通道合并,全部留痕)
CHANNEL_PRODUCT = "product_producing"
CHANNEL_SIMILAR = "reactant_similar"
CHANNEL_TRACE = "corpus_trace"

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
    # Phase D D1:找回通道与相似度留痕(find_channels 可多值 = 多通道召回同一供体)
    find_channels: list = field(default_factory=list)
    similarity: float | None = None       # reactant_similar 通道分数
    similarity_version: str = ""
    similarity_rank: int | None = None    # 通道内召回位次(1-based)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _reactant_fingerprint(smiles: str):
    """供体反应物/底物的检索指纹(Morgan r2 b2048 立体盲;失败返回 None)。"""
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return None
    try:
        return rdMolDescriptors.GetMorganFingerprintAsBitVect(
            mol, SIMILARITY_FP_RADIUS,
            nBits=SIMILARITY_FP_BITS,
            useChirality=SIMILARITY_FP_CHIRALITY,
        )
    except Exception:
        return None


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
        # Phase D D2:显式 v1/v2 装载选择;所选文件必须在清单内且哈希
        # 一致(verify 已核),缺失/不在清单 → 失败,绝不静默回退另一版
        corpus_rel = _analog_corpus_rel(config)
        if corpus_rel not in self.manifest["files"]:
            raise AnalogSourceError(
                f"所选类比语料不在清单内:{corpus_rel}"
                f"(analog_corpus={getattr(config, 'analog_corpus', 'v1')})",
                {"selected": corpus_rel})
        self.analog_corpus_version = getattr(config, "analog_corpus", "v1")
        self.paths = {
            "analog_corpus_templates": self.assets_root / corpus_rel,
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
                ("analog_corpus_templates", corpus_rel),
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

    def _reactant_fp_index(self) -> list[dict]:
        """供体反应物指纹索引(Phase D D1):[{row, line_no, fp, reactant}]。

        索引键含资产 SHA **与算法版本串**:任一变化都重建,跨版本缓存
        不串用。反应物不可解析的行如实跳过(检索层不猜;该行仍可被
        record_id / 产物通道找回)。"""
        key = self._index_key("analog_corpus_templates") \
            + ("reactant_fp", SIMILARITY_VERSION)
        cached = AnalogSourceResolver._INDEX_CACHE.get(key)
        if cached is None:
            cached = []
            with open(self.paths["analog_corpus_templates"],
                      encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    lhs, _rhs = _lhs_rhs(row)
                    reactant = _strip_map(lhs)
                    if not reactant:
                        continue
                    fp = _reactant_fingerprint(reactant)
                    if fp is None:
                        continue
                    cached.append({"row": row, "line_no": line_no,
                                   "fp": fp, "reactant": reactant})
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
            find_channels=[CHANNEL_PRODUCT],
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
                find_channels=[CHANNEL_PRODUCT],
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
                find_channels=[CHANNEL_TRACE],
            ))
        return out

    def templates_similar_to(self, substrate_smiles: str, *,
                             threshold: float, top_k: int) -> list[DonorRef]:
        """按供体**反应物**与当前底物的结构相似度召回模板(Phase D D1)。

        语义边界(任务书 §2):相似度只决定**召回次序**,绝不替代
        ``assess_donor`` 的化学适用性判定;无映射模板不会被本通道召回
        (索引只含带 mapped_lhs 的行,但召回后仍按 Phase C 全门禁评估)。

        - 相似度 = Tanimoto(Morgan r2 b2048 立体盲);
        - 阈值边界 **>=**(SIMILARITY_CMP),恰在阈值上的召回;
        - 底物不可解析 → 返回 [](检索层不猜,调用方按无召回处理);
        - 排序 (-similarity, line_no, record_id) 确定性 tie-break,
          与引擎异构 score 无关;取前 ``top_k``;
        - 同一底物与自身完全相同的模板(相似度 1.0)也会召回 —— 是否
          属"精确查找领域"由 assess_donor 的 donor_same_as_substrate 判。
        """
        fp = _reactant_fingerprint(substrate_smiles)
        if fp is None or top_k <= 0 or threshold > 1.0:
            return []
        from rdkit import DataStructs

        index = self._reactant_fp_index()
        scored: list[tuple[float, int, str, dict]] = []
        for entry in index:
            sim = DataStructs.TanimotoSimilarity(fp, entry["fp"])
            if sim >= threshold:
                row = entry["row"]
                scored.append((sim, entry["line_no"],
                               str(row.get("record_id", "")), entry))
        scored.sort(key=lambda t: (-t[0], t[1], t[2]))
        meta = self._asset_meta["analog_corpus_templates"]
        out: list[DonorRef] = []
        for rank, (sim, _ln, _rid, entry) in enumerate(scored[:top_k], 1):
            row = entry["row"]
            lhs, rhs = _lhs_rhs(row)
            out.append(DonorRef(
                record_id=str(row.get("record_id", "")),
                index="analog_corpus_templates",
                asset_file=meta["asset_file"],
                asset_sha256=meta["asset_sha256"],
                line_no=entry["line_no"],
                mapping_quality=_mapping_quality(
                    lhs, rhs, row.get("qc_flags") or {}),
                reactant_smiles=entry["reactant"],
                product_smiles=_strip_map(rhs),
                mapped_lhs=lhs, mapped_rhs=rhs,
                center_atoms=[int(x) for x in (row.get("center_atoms") or [])],
                find_channels=[CHANNEL_SIMILAR],
                similarity=round(float(sim), 6),
                similarity_version=SIMILARITY_VERSION,
                similarity_rank=rank,
            ))
        return out

    # ------------------------------------------------------------ S3a/S3c/S2-uspto 扩展检索(默认关闭,开启时调用)

    @staticmethod
    def _load_fg_patterns() -> list[tuple[str, Any]]:
        key = ("_fg_patterns_v1",)
        cached = AnalogSourceResolver._INDEX_CACHE.get(key)
        if cached is None:
            rules_path = Path(__file__).resolve().parent / "fg_smarts_rules_v1.json"
            patterns: list[tuple[str, Any]] = []
            if rules_path.is_file():
                data = json.loads(rules_path.read_text(encoding="utf-8"))
                for item in data.get("rules") or []:
                    name = str(item.get("name", ""))
                    smarts = str(item.get("smarts", ""))
                    patt = Chem.MolFromSmarts(smarts) if smarts else None
                    if name and patt is not None:
                        patterns.append((name, patt))
            AnalogSourceResolver._INDEX_CACHE[key] = patterns
            cached = patterns
        return cached

    @classmethod
    def _detect_mol_fgs(cls, mol) -> set[str]:
        if mol is None:
            return set()
        hits: set[str] = set()
        for name, patt in cls._load_fg_patterns():
            try:
                if mol.HasSubstructMatch(patt):
                    hits.add(name)
            except Exception:
                continue
        return hits

    @classmethod
    def _detect_center_fgs(cls, lhs_smiles: str, center_maps: list[int], env_maps: list[int]) -> list[str]:
        if not lhs_smiles:
            return []
        mol = Chem.MolFromSmiles(lhs_smiles)
        if mol is None:
            return []
        target_maps = {int(x) for x in (center_maps or [])} | {int(x) for x in (env_maps or [])}
        center_idx = {a.GetIdx() for a in mol.GetAtoms() if a.GetAtomMapNum() in target_maps}
        if not center_idx:
            center_idx = {a.GetIdx() for a in mol.GetAtoms() if a.GetAtomMapNum() > 0}
        # Expand 1 hop so functional groups attached to center atoms are included
        expanded = set(center_idx)
        for b in mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            if i in center_idx or j in center_idx:
                expanded.add(i)
                expanded.add(j)
        hits: list[str] = []
        for name, patt in cls._load_fg_patterns():
            try:
                for m in mol.GetSubstructMatches(patt):
                    if expanded.intersection(m):
                        hits.append(name)
                        break
            except Exception:
                continue
        return sorted(set(hits))

    def _fg_reactant_index(self) -> list[dict]:
        key = self._index_key("analog_corpus_templates") + ("fg_reactant_v1", SIMILARITY_VERSION)
        cached = AnalogSourceResolver._INDEX_CACHE.get(key)
        if cached is not None:
            return cached

        fp_index = self._reactant_fp_index()
        sha_short = self._asset_meta["analog_corpus_templates"]["asset_sha256"][:12]
        import os
        cache_dir = Path("/tmp/v43_pool_coverage_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        disk_file = cache_dir / f"fg_map_{sha_short}.json"
        fg_by_line: dict[str, list[str]] = {}
        if disk_file.is_file():
            try:
                fg_by_line = json.loads(disk_file.read_text(encoding="utf-8"))
            except Exception:
                fg_by_line = {}

        if not fg_by_line:
            for entry in fp_index:
                row = entry["row"]
                lhs, _rhs = _lhs_rhs(row)
                c_atoms = [int(x) for x in (row.get("center_atoms") or [])]
                e_atoms = [int(x) for x in (row.get("env_shell") or [])]
                fg_by_line[str(entry["line_no"])] = self._detect_center_fgs(lhs, c_atoms, e_atoms)
            try:
                tmp_f = cache_dir / f"fg_map_{sha_short}.{os.getpid()}.tmp"
                tmp_f.write_text(json.dumps(fg_by_line, ensure_ascii=False), encoding="utf-8")
                tmp_f.replace(disk_file)
            except Exception:
                pass

        out_idx: list[dict] = []
        for entry in fp_index:
            fgs = set(fg_by_line.get(str(entry["line_no"])) or [])
            if fgs:
                out_idx.append({"entry": entry, "fg_set": fgs})
        AnalogSourceResolver._INDEX_CACHE[key] = out_idx
        return out_idx

    def templates_by_functional_group(
        self,
        substrate_smiles: str,
        *,
        top_k: int = 24,
        center_shell: int = 2,
    ) -> list[DonorRef]:
        """S3a: 按底物官能团筛选反应中心匹配的模板族，结合中心锚定探针与相似度排序。"""
        sub_mol = Chem.MolFromSmiles(substrate_smiles) if substrate_smiles else None
        fp = _reactant_fingerprint(substrate_smiles)
        if sub_mol is None or fp is None or top_k <= 0:
            return []
        sub_fgs = self._detect_mol_fgs(sub_mol)
        if not sub_fgs:
            return self.templates_similar_to(substrate_smiles, threshold=0.25, top_k=top_k)

        from rdkit import DataStructs
        from ..pollutant.s5b_compiler import center_anchor_probe

        fg_index = self._fg_reactant_index()
        pre_scored: list[tuple[int, float, int, str, dict]] = []
        for item in fg_index:
            overlap = len(item["fg_set"] & sub_fgs)
            if overlap <= 0:
                continue
            entry = item["entry"]
            sim = DataStructs.TanimotoSimilarity(fp, entry["fp"])
            row = entry["row"]
            pre_scored.append((
                overlap,
                float(sim),
                int(entry["line_no"]),
                str(row.get("record_id", "")),
                entry,
            ))

        # Sort by (-fg_overlap, -tanimoto_sim, line_no, record_id) and probe top 96 for center compatibility
        pre_scored.sort(key=lambda t: (-t[0], -t[1], t[2], t[3]))
        probe_limit = min(len(pre_scored), max(96, top_k * 3))
        final_scored: list[tuple[int, int, float, int, str, dict]] = []
        for idx, (overlap, sim, ln, rid, entry) in enumerate(pre_scored):
            probe_ok = 0
            if idx < probe_limit:
                row = entry["row"]
                lhs, rhs = _lhs_rhs(row)
                probe = center_anchor_probe(
                    lhs, rhs, substrate_smiles, center_shell=center_shell
                )
                if probe.get("status") != "absent":
                    probe_ok = 1
            final_scored.append((probe_ok, overlap, sim, ln, rid, entry))

        final_scored.sort(key=lambda t: (-t[0], -t[1], -t[2], t[3], t[4]))
        meta = self._asset_meta["analog_corpus_templates"]
        out: list[DonorRef] = []
        for rank, (_pok, _ov, sim, _ln, _rid, entry) in enumerate(final_scored[:top_k], 1):
            row = entry["row"]
            lhs, rhs = _lhs_rhs(row)
            out.append(DonorRef(
                record_id=str(row.get("record_id", "")),
                index="analog_corpus_templates",
                asset_file=meta["asset_file"],
                asset_sha256=meta["asset_sha256"],
                line_no=entry["line_no"],
                mapping_quality=_mapping_quality(
                    lhs, rhs, row.get("qc_flags") or {}),
                reactant_smiles=entry["reactant"],
                product_smiles=_strip_map(rhs),
                mapped_lhs=lhs, mapped_rhs=rhs,
                center_atoms=[int(x) for x in (row.get("center_atoms") or [])],
                find_channels=[CHANNEL_SIMILAR, "functional_group"],
                similarity=round(float(sim), 6),
                similarity_version=SIMILARITY_VERSION,
                similarity_rank=rank,
            ))
        return out

    def templates_merged_sim_and_fg(
        self,
        substrate_smiles: str,
        *,
        threshold: float = 0.45,
        top_k: int = 24,
        center_shell: int = 2,
    ) -> list[DonorRef]:
        """S3c: 相似度检索 top-k ∪ 官能团检索 top-k，去重后按统一 RRF 分数排序。"""
        sim_refs = self.templates_similar_to(
            substrate_smiles, threshold=threshold, top_k=top_k
        )
        fg_refs = self.templates_by_functional_group(
            substrate_smiles, top_k=top_k, center_shell=center_shell
        )
        by_rid: dict[str, DonorRef] = {}
        rrf_score: dict[str, float] = {}
        for rank_s, r in enumerate(sim_refs, 1):
            rid = str(r.record_id)
            by_rid[rid] = r
            rrf_score[rid] = rrf_score.get(rid, 0.0) + 1.0 / (10.0 + rank_s)
        for rank_f, r in enumerate(fg_refs, 1):
            rid = str(r.record_id)
            if rid not in by_rid:
                by_rid[rid] = r
            else:
                chans = list(by_rid[rid].find_channels or [])
                if "functional_group" not in chans:
                    chans.append("functional_group")
                by_rid[rid].find_channels = chans
            rrf_score[rid] = rrf_score.get(rid, 0.0) + 1.0 / (10.0 + rank_f)

        merged = list(by_rid.values())
        merged.sort(
            key=lambda r: (
                -round(rrf_score.get(str(r.record_id), 0.0) + 0.01 * float(r.similarity or 0.0), 8),
                -float(r.similarity or 0.0),
                int(r.line_no or 0),
                str(r.record_id),
            )
        )
        for rank, r in enumerate(merged[:top_k], 1):
            r.similarity_rank = rank
        return merged[:top_k]

    def _uspto_uni_rows(self) -> tuple[str, list[dict]]:
        key = ("_uspto_uni_freq5_v1", str(self.assets_root))
        cached = AnalogSourceResolver._INDEX_CACHE.get(key)
        if cached is not None:
            return cached

        uspto_rel = "analog/uspto_relaxed_index_v1.jsonl"
        uspto_path = self.assets_root / uspto_rel
        uspto_sha = str(self.manifest["files"].get(uspto_rel) or sha256_file(uspto_path))

        import os
        from collections import Counter
        cache_dir = Path("/tmp/v43_pool_coverage_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        disk_file = cache_dir / f"uspto_uni_freq5_{uspto_sha[:12]}.json"
        raw_rows: list[dict] = []
        if disk_file.is_file():
            try:
                raw_rows = json.loads(disk_file.read_text(encoding="utf-8"))
            except Exception:
                raw_rows = []

        if not raw_rows and uspto_path.is_file():
            with open(uspto_path, encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    o = json.loads(line)
                    freq = int(o.get("freq", 0))
                    if freq < 5:
                        continue
                    tpl = str(o.get("template_id", ""))
                    lhs, _, rhs = tpl.partition(">>")
                    if not lhs or not rhs or "." in lhs:
                        continue
                    r1 = str(o.get("r1", ""))
                    if not r1:
                        continue
                    raw_rows.append({
                        "line_no": line_no,
                        "template_id": tpl,
                        "lhs": lhs,
                        "rhs": rhs,
                        "freq": freq,
                        "r1": r1,
                        "r2": str(o.get("r2", "")),
                        "center_atoms": [int(x) for x in (o.get("center_atoms") or [])],
                        "sig_pairs": sorted(Counter(str(x) for x in (o.get("center_signature") or [])).items()),
                    })
            raw_rows.sort(key=lambda r: (-int(r["freq"]), str(r["template_id"])))
            try:
                tmp_f = cache_dir / f"uspto_uni_freq5_{uspto_sha[:12]}.{os.getpid()}.tmp"
                tmp_f.write_text(json.dumps(raw_rows, ensure_ascii=False), encoding="utf-8")
                tmp_f.replace(disk_file)
            except Exception:
                pass

        res = (uspto_sha, raw_rows)
        AnalogSourceResolver._INDEX_CACHE[key] = res
        return res

    @staticmethod
    def _instantiate_uspto_on_substrate(row: dict, sub_mol) -> tuple[str, str, list[int]] | None:
        lhs_mol = Chem.MolFromSmiles(str(row["lhs"]), sanitize=False)
        rhs_mol = Chem.MolFromSmiles(str(row["rhs"]), sanitize=False)
        if lhs_mol is None or rhs_mol is None:
            return None
        rq = row.get("_rq")
        if rq is None:
            rq = Chem.MolFromSmarts(str(row.get("r1") or "")) or Chem.MolFromSmarts(str(row.get("r2") or ""))
            row["_rq"] = rq
        if rq is None or rq.GetNumAtoms() != lhs_mol.GetNumAtoms():
            return None
        try:
            matches = sub_mol.GetSubstructMatches(rq, uniquify=True, maxMatches=8)
        except Exception:
            return None
        if not matches:
            return None
        match = matches[0]

        lhs_map2idx = {a.GetAtomMapNum(): a.GetIdx() for a in lhs_mol.GetAtoms() if a.GetAtomMapNum() > 0}
        rhs_map2idx = {a.GetAtomMapNum(): a.GetIdx() for a in rhs_mol.GetAtoms() if a.GetAtomMapNum() > 0}
        if not lhs_map2idx or not rhs_map2idx:
            return None

        sub_copy = Chem.Mol(sub_mol)
        try:
            Chem.Kekulize(sub_copy, clearAromaticFlags=True)
        except Exception:
            pass
        used_maps = set(lhs_map2idx.keys()) | set(rhs_map2idx.keys())
        next_map = max(used_maps, default=0) + 10
        sub_idx_to_map: dict[int, int] = {}
        for l_map, l_idx in lhs_map2idx.items():
            if l_idx >= len(match):
                return None
            s_idx = int(match[l_idx])
            if s_idx in sub_idx_to_map:
                return None
            sub_idx_to_map[s_idx] = int(l_map)
        for atom in sub_copy.GetAtoms():
            s_idx = atom.GetIdx()
            if s_idx not in sub_idx_to_map:
                while next_map in used_maps:
                    next_map += 1
                sub_idx_to_map[s_idx] = next_map
                used_maps.add(next_map)
            atom.SetAtomMapNum(sub_idx_to_map[s_idx])
        mapped_lhs = Chem.MolToSmiles(sub_copy)

        rw = Chem.RWMol(sub_copy)
        map_to_rw_idx = {a.GetAtomMapNum(): a.GetIdx() for a in rw.GetAtoms() if a.GetAtomMapNum() > 0}

        for r_map, r_idx in rhs_map2idx.items():
            if r_map not in map_to_rw_idx:
                r_atom = rhs_mol.GetAtomWithIdx(r_idx)
                if r_atom.GetAtomicNum() <= 0:
                    return None
                na = Chem.Atom(r_atom.GetAtomicNum())
                na.SetAtomMapNum(int(r_map))
                na.SetFormalCharge(r_atom.GetFormalCharge())
                new_rw_idx = rw.AddAtom(na)
                map_to_rw_idx[int(r_map)] = new_rw_idx

        c_maps = set(lhs_map2idx.keys())
        r_maps = set(rhs_map2idx.keys())

        for m_keep in (c_maps & r_maps):
            for m_leave in (c_maps - r_maps):
                u, v = map_to_rw_idx[m_keep], map_to_rw_idx[m_leave]
                if rw.GetBondBetweenAtoms(u, v) is not None:
                    rw.RemoveBond(u, v)

        r_list = sorted(r_maps)
        for i_idx in range(len(r_list)):
            for j_idx in range(i_idx + 1, len(r_list)):
                m1, m2 = r_list[i_idx], r_list[j_idx]
                rb = rhs_mol.GetBondBetweenAtoms(rhs_map2idx[m1], rhs_map2idx[m2])
                u, v = map_to_rw_idx[m1], map_to_rw_idx[m2]
                cur_b = rw.GetBondBetweenAtoms(u, v)
                if rb is None:
                    if (m1 in c_maps and m2 in c_maps) and cur_b is not None:
                        rw.RemoveBond(u, v)
                else:
                    btype = rb.GetBondType()
                    if btype == Chem.BondType.AROMATIC:
                        btype = cur_b.GetBondType() if cur_b is not None else Chem.BondType.SINGLE
                    if cur_b is None:
                        rw.AddBond(u, v, btype)
                    elif cur_b.GetBondType() != btype:
                        cur_b.SetBondType(btype)

        out_mol = rw.GetMol()
        for a in out_mol.GetAtoms():
            a.SetNoImplicit(False)
            a.SetNumExplicitHs(0)
        try:
            Chem.SanitizeMol(out_mol)
        except Exception:
            return None
        mapped_rhs = Chem.MolToSmiles(out_mol)
        if _strip_map(mapped_lhs) == _strip_map(mapped_rhs):
            return None
        center_out = sorted(c_maps & r_maps) or sorted(c_maps)
        return mapped_lhs, mapped_rhs, center_out

    def uspto_templates_for_substrate(
        self, substrate_smiles: str, *, top_k: int = 24
    ) -> list[DonorRef]:
        """S2-uspto: 从 uspto_relaxed_index_v1 (freq>=5) 匹配并在底物上实例化无通配符模板。"""
        from collections import Counter

        sub_mol = Chem.MolFromSmiles(substrate_smiles) if substrate_smiles else None
        if sub_mol is None or top_k <= 0:
            return []
        elem_counts = Counter(a.GetSymbol() for a in sub_mol.GetAtoms())
        uspto_sha, uni_rows = self._uspto_uni_rows()
        out: list[DonorRef] = []
        seen_rhs: set[str] = set()
        for row in uni_rows:
            if any(elem_counts.get(el, 0) < int(cnt) for el, cnt in row["sig_pairs"]):
                continue
            inst = self._instantiate_uspto_on_substrate(row, sub_mol)
            if inst is None:
                continue
            ml, mr, c_atoms = inst
            prod_smi = _strip_map(mr)
            if not prod_smi or prod_smi in seen_rhs:
                continue
            seen_rhs.add(prod_smi)
            ln = int(row["line_no"])
            out.append(DonorRef(
                record_id=f"uspto:L{ln}",
                index="uspto_relaxed_index_v1",
                asset_file="analog/uspto_relaxed_index_v1.jsonl",
                asset_sha256=uspto_sha,
                line_no=ln,
                mapping_quality=QUALITY_BIJECTION,
                reactant_smiles=_strip_map(ml),
                product_smiles=prod_smi,
                mapped_lhs=ml,
                mapped_rhs=mr,
                center_atoms=c_atoms,
                find_channels=["uspto_relaxed"],
                similarity=round(min(1.0, float(row["freq"]) / 100.0), 6),
                similarity_version=SIMILARITY_VERSION,
                similarity_rank=len(out) + 1,
            ))
            if len(out) >= top_k:
                break
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


def similar_donor_refs(resolver: AnalogSourceResolver | None,
                        substrate_smiles: str, *,
                        threshold: float, top_k: int) -> list[dict]:
    """当前底物的相似供体引用(Phase D D1 reactant_similar 通道)。

    resolver 缺席 / 通道参数关闭(threshold<=0 或 top_k<=0) → [](不猜)。
    返回按相似度降序的 ref dict 列表(含通道、分数、版本与召回位次);
    供体资格仍由 build_eligibility/assess_donor 判定,本函数只召回。
    """
    if resolver is None or threshold <= 0 or top_k <= 0:
        return []
    return [r.to_dict() for r in resolver.templates_similar_to(
        substrate_smiles, threshold=threshold, top_k=top_k)]
