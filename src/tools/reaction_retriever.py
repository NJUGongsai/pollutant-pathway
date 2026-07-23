# src/tools/reaction_retriever.py
# C 路线：基于 Morgan 指纹的相似反应检索
# 数据源（学生 tar.gz 交付）：
#   #3a route_c/reference_reaction_index.csv.gz    — 4,051 query-excluded 参考反应
#   #3b route_c/reference_morgan_radius8.pkl       — 4,000 mol Morgan radius=8 指纹
#
# 与 M3-P0B1 证据对齐：Morgan radius=8、query-excluded、无泄漏。

import math
import gzip
import json
import logging
import pickle as pkl
import csv
from pathlib import Path
from typing import List, Optional, Any
from collections import Counter

from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs

from src.schemas.evidence import CandidateReaction
from config.settings import (
    REFERENCE_REACTION_INDEX_PATH,
    REFERENCE_MORGAN_RADIUS8_PATH,
    ENZYMECAGE_DRY_RUN,
)

logger = logging.getLogger(__name__)


# ─── 化学工具函数 ───────────────────────────────────────────────────────

def get_rdkit_mol(smi: str) -> Optional[Chem.Mol]:
    if not smi or not isinstance(smi, str):
        return None
    return Chem.MolFromSmiles(smi)


def neutralize_atoms(smi: str) -> str:
    """中性化分子电荷（与参考库同一预处理管线）"""
    mol = get_rdkit_mol(smi)
    if mol is None:
        return smi
    pattern = Chem.MolFromSmarts(
        "[+1!h0!$([*]~[-1,-2,-3,-4]),-1!$([*]~[+1,+2,+3,+4])]"
    )
    at_matches = mol.GetSubstructMatches(pattern)
    for match in at_matches:
        atom = mol.GetAtomWithIdx(match[0])
        chg = atom.GetFormalCharge()
        hcount = atom.GetTotalNumHs()
        atom.SetFormalCharge(0)
        atom.SetNumExplicitHs(hcount - chg)
        atom.UpdatePropertyCache()
    result = Chem.MolToSmiles(mol)
    return result if get_rdkit_mol(result) else smi


def get_morgan_fp(smi: str, radius: int = 8):
    """Morgan 指纹 (radius=8, connectivity invariants) —— 与参考库一致"""
    mol = get_rdkit_mol(neutralize_atoms(smi))
    if mol is None:
        return None
    Chem.SanitizeMol(mol)
    fp = AllChem.GetMorganFingerprint(
        mol, radius,
        invariants=AllChem.GetConnectivityInvariants(mol, includeRingMembership=False)
    )
    return fp


def bulk_tanimoto(target_fp, fp_list: list, ids: list) -> dict:
    sim_list = DataStructs.BulkTanimotoSimilarity(target_fp, fp_list)
    return dict(zip(ids, sim_list))


# ─── 反应相似度 (S1/S2 max) ─────────────────────────────────────────────

def calc_reaction_similarity(
    query_rxn_smiles: str,
    cand_rxn_smiles: str,
    mol_sim_dict: dict,
    cand_mol_to_id: dict,
) -> float:
    q_subs = Counter(query_rxn_smiles.split(">>")[0].split("."))
    q_prods = Counter(query_rxn_smiles.split(">>")[1].split("."))
    c_subs = Counter(cand_mol_to_id.get(s) for s in cand_rxn_smiles.split(">>")[0].split("."))
    c_prods = Counter(cand_mol_to_id.get(p) for p in cand_rxn_smiles.split(">>")[1].split("."))

    info = {"s1": q_subs, "p1": q_prods, "s2": c_subs, "p2": c_prods}
    pairs_cfg = [("s1", "s2"), ("s1", "p2"), ("p1", "s2"), ("p1", "p2")]
    ss = {}
    for pair_key in pairs_cfg:
        simm = {}
        for mol_x in info[pair_key[0]]:
            simm[mol_x] = 0.0
            if mol_x in mol_sim_dict:
                for mol_y in info[pair_key[1]]:
                    if mol_y and mol_y in mol_sim_dict[mol_x]:
                        simm[mol_x] = max(simm[mol_x], mol_sim_dict[mol_x][mol_y])
        scores = list(simm.values())
        ss[pair_key] = sum(scores) / len(scores) if scores else 0.0

    s1 = math.sqrt(ss[pairs_cfg[0]] ** 2 + ss[pairs_cfg[3]] ** 2) / math.sqrt(2)
    s2 = math.sqrt(ss[pairs_cfg[1]] ** 2 + ss[pairs_cfg[2]] ** 2) / math.sqrt(2)
    return max(s1, s2)


# ─── 参考反应库（学生 route_c 双文件） ────────────────────────────────

class ReactionDatabase:
    """
    参考反应库：CSV 索引 + PKL 指纹分离结构。
    - CSV.gz 提供 reaction_smiles / rhea / ec 元数据
    - PKL 提供 mol_smiles → morgan_fp 映射
    对未确定 schema 字段采用宽松匹配，任何格式偏差报出明确错误。
    """

    # CSV 列名候选（按优先级匹配）
    _RXN_COL_CANDIDATES = ["CANO_RXN_SMILES", "reaction_smiles", "rxn_smiles"]
    # rhea 列支持 JSON 列表（学生 v1 index）与旧字符串格式
    _RHEA_COL_CANDIDATES = [
        "rhea_master_ids_json",
        "rhea_ids_json",
        "rhea_master_id",
        "rhea_id",
        "RHEA_ID",
    ]
    _EC_COL_CANDIDATES = ["ec", "EC", "ec_numbers"]

    def __init__(
        self,
        index_path: Optional[Path] = None,
        fp_path: Optional[Path] = None,
    ):
        self._index_path = index_path or REFERENCE_REACTION_INDEX_PATH
        self._fp_path = fp_path or REFERENCE_MORGAN_RADIUS8_PATH
        self._loaded = False
        self._rxn_smiles_list: List[str] = []
        self._rxn_rhea_map: dict = {}       # rxn_smiles → rhea_id
        self._rxn_ec_map: dict = {}          # rxn_smiles → list[EC]
        self._mol_fps: list = []
        self._mol_ids: list = []             # 与 _mol_fps 同序
        self._mol_to_id: dict = {}           # mol_smiles → mol_id (通常就是 smiles)

    # ---------- CSV.gz ----------

    def _pick_col(self, header: List[str], candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in header:
                return c
        return None

    def _load_index_csv(self):
        if not self._index_path.exists():
            raise FileNotFoundError(
                f"route-C 参考反应索引不存在: {self._index_path}\n"
                "请检查学生 tar.gz 是否解压到 M3_AGENT_DATA_ASSETS_ROOT 且包含 route_c/。"
            )

        with gzip.open(self._index_path, "rt", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            rxn_col = self._pick_col(header, self._RXN_COL_CANDIDATES)
            rhea_col = self._pick_col(header, self._RHEA_COL_CANDIDATES)
            ec_col = self._pick_col(header, self._EC_COL_CANDIDATES)
            if rxn_col is None:
                raise KeyError(
                    f"route-C 索引缺 reaction SMILES 列，header={header}"
                )

            for row in reader:
                rxn = row[rxn_col]
                if not rxn:
                    continue
                self._rxn_smiles_list.append(rxn)
                if rhea_col:
                    rhea_raw = row[rhea_col] or ""
                    if rhea_col.endswith("_json"):
                        # JSON list → 取首个作为代表 rhea_id（已排序或已 master）
                        try:
                            rhea_list = [str(x).strip() for x in json.loads(rhea_raw) if str(x).strip()]
                        except (json.JSONDecodeError, TypeError):
                            rhea_list = []
                        if rhea_list:
                            self._rxn_rhea_map[rxn] = rhea_list[0]
                    else:
                        self._rxn_rhea_map[rxn] = rhea_raw or None
                if ec_col:
                    ec_raw = row[ec_col] or ""
                    ec_list = [e.strip() for e in ec_raw.split(";") if e.strip()]
                    if ec_list:
                        self._rxn_ec_map[rxn] = ec_list

        logger.info(
            f"Loaded {len(self._rxn_smiles_list)} reference reactions "
            f"(rhea={len(self._rxn_rhea_map)}, ec={len(self._rxn_ec_map)})"
        )

    # ---------- PKL 指纹 ----------

    def _load_morgan_pkl(self):
        if not self._fp_path.exists():
            raise FileNotFoundError(
                f"route-C Morgan radius=8 指纹不存在: {self._fp_path}\n"
                "请检查学生 tar.gz 是否解压到 M3_AGENT_DATA_ASSETS_ROOT/route_c/。"
            )
        logger.info(f"Loading Morgan radius=8 fingerprints from {self._fp_path}...")
        with open(self._fp_path, "rb") as f:
            payload: Any = pkl.load(f)

        # 支持三类载荷：
        # 1) v1 schema (学生 2026-07-21 M3-P1 交付):
        #    {'format_version': 'enzymecage_m3_route_c_morgan_radius8_v1',
        #     'molecule_smiles_by_id': [...], 'neutralized_smiles_by_id': [...],
        #     'fingerprints_by_id': [UIntSparseIntVect,...], 'radius': 8, ...}
        # 2) dict[mol_smiles] = fp                                   → 直接用
        # 3) {"mol_ids": [...], "mol_fps": [...], "mol_to_id": {...}} → 兼容旧结构
        if (
            isinstance(payload, dict)
            and payload.get("format_version", "").startswith(
                "enzymecage_m3_route_c_morgan_radius8"
            )
            and "fingerprints_by_id" in payload
        ):
            # v1 schema：以 neutralized_smiles 为 mol_id（与下游 calc_reaction_similarity
            # 内部用 neutralize_atoms(query) 后匹配保持一致）
            neut_smiles = list(payload["neutralized_smiles_by_id"])
            fps = list(payload["fingerprints_by_id"])
            if len(neut_smiles) != len(fps):
                raise ValueError(
                    f"v1 schema mol/fp 长度不一致: mol={len(neut_smiles)} fp={len(fps)}"
                )
            self._mol_ids = neut_smiles
            self._mol_fps = fps
            # 同时建立原始 SMILES → neutralized SMILES 的反向映射，便于下游直接用
            raw_smiles = list(payload.get("molecule_smiles_by_id", neut_smiles))
            self._mol_to_id = {r: n for r, n in zip(raw_smiles, neut_smiles)}
            # neutralized 自映射也加入（下游可能直接传 neutralized SMILES）
            for n in neut_smiles:
                self._mol_to_id.setdefault(n, n)
            logger.info(
                f"[v1 schema] radius={payload.get('radius')} "
                f"fingerprint_type={payload.get('fingerprint_type')} "
                f"rdkit_version={payload.get('rdkit_version')}"
            )
        elif isinstance(payload, dict) and "mol_fps" in payload and "mol_ids" in payload:
            self._mol_ids = list(payload["mol_ids"])
            self._mol_fps = list(payload["mol_fps"])
            self._mol_to_id = dict(payload.get("mol_to_id", {})) or {
                mid: mid for mid in self._mol_ids
            }
        elif isinstance(payload, dict):
            # {mol_smiles: fp}
            self._mol_ids = list(payload.keys())
            self._mol_fps = [payload[k] for k in self._mol_ids]
            self._mol_to_id = {mid: mid for mid in self._mol_ids}
        else:
            raise ValueError(
                f"Morgan pkl 载荷类型未识别: {type(payload)}；"
                "期望 v1 schema 或 dict[mol_smiles]=fp 或 {'mol_ids','mol_fps','mol_to_id'}。"
            )

        logger.info(f"Loaded {len(self._mol_ids)} molecule fingerprints")

    # ---------- 对外 ----------

    def load(self):
        if self._loaded:
            return
        self._load_index_csv()
        self._load_morgan_pkl()
        self._loaded = True

    @property
    def rxn_count(self) -> int:
        return len(self._rxn_smiles_list)


# ─── 主入口 ────────────────────────────────────────────────────────────

def _mock_retrieve_dryrun(substrate_smiles: str, topk: int) -> List[CandidateReaction]:
    """DRY_RUN mock：不读参考库，直接造少量候选反应，供本地拓扑验证。

    与 enzymecage_client._mock_predict 对称：同一套 md5-based 确定性伪值。
    ec_numbers 注入已知非空，以便下游 pool builder 至少能走一次 EC 查询。
    """
    import hashlib
    logger.warning(
        "[DRY_RUN] reaction_retriever 返回 mock 候选反应，不构成任何相似性证据"
    )
    n = min(3, topk)
    seed = int(hashlib.md5(substrate_smiles.encode()).hexdigest()[:8], 16)
    fake_ecs = ["1.14.15.3", "1.14.14.1", "1.14.13.-"]  # 典型单加氧酶类 EC
    results: List[CandidateReaction] = []
    for i in range(n):
        _ = ((seed + i * 17) % 10000) / 10000.0  # 保留确定性种子（为未来扩展预留）
        results.append(CandidateReaction(
            reaction_smiles=f"{substrate_smiles}.O=O>>{substrate_smiles}O_mock{i}",
            similarity_score=round(0.9 - i * 0.1, 4),
            source="retrieved",
            rhea_id=f"MOCK:{10000 + i}",
            ec_numbers=[fake_ecs[i % len(fake_ecs)]],
        ))
    return results


def retrieve_similar_reactions(
    substrate_smiles: str,
    topk: int = 10,
    db: Optional[ReactionDatabase] = None,
) -> List[CandidateReaction]:
    """
    给定底物 SMILES，检索最相似的 Top-K 参考反应。
    与 M3-P0B1 一致：底物侧 Morgan radius=8 → 反应级 Tanimoto 排序。

    ENZYMECAGE_DRY_RUN=1 时走 mock（不读参考库，不构成相似性证据）。
    """
    if ENZYMECAGE_DRY_RUN:
        return _mock_retrieve_dryrun(substrate_smiles, topk)

    if db is None:
        db = ReactionDatabase()
    db.load()

    query_fp = get_morgan_fp(substrate_smiles)
    if query_fp is None:
        raise ValueError(f"无法计算底物指纹: {substrate_smiles}")

    sim_scores = bulk_tanimoto(query_fp, db._mol_fps, db._mol_ids)

    rxn_scores = []
    for rxn_smi in db._rxn_smiles_list:
        subs_side = rxn_smi.split(">>")[0].split(".")
        sub_ids = [db._mol_to_id.get(s) for s in subs_side if s in db._mol_to_id]
        if not sub_ids:
            rxn_scores.append(0.0)
            continue
        max_sims = [max((sim_scores.get(mid, 0.0) for mid in sub_ids), default=0.0)]
        rxn_scores.append(sum(max_sims) / len(max_sims))

    indexed = sorted(enumerate(rxn_scores), key=lambda x: x[1], reverse=True)[:topk]

    results: List[CandidateReaction] = []
    for idx, score in indexed:
        rxn_smi = db._rxn_smiles_list[idx]
        results.append(CandidateReaction(
            reaction_smiles=rxn_smi,
            similarity_score=round(score, 4),
            source="retrieved",
            rhea_id=db._rxn_rhea_map.get(rxn_smi),
            ec_numbers=db._rxn_ec_map.get(rxn_smi),
        ))

    logger.info(
        f"Retrieved {len(results)} similar reactions "
        f"(top score: {results[0].similarity_score if results else 0})"
    )
    return results
