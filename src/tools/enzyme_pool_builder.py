# src/tools/enzyme_pool_builder.py
# B-primary / C-fallback 酶 pool 构造
#
# 数据源（学生 tar.gz 交付）：
#   #2 rhea140/rhea2ec.tsv                              — Rhea → EC
#   #5 route_b/ec_to_uid_query_excluded.csv.gz           — 公平 EC → UID（451 query 全局排除）
#   #4 d4/uid_asset_availability.csv.gz                  — 107,705 D4 完整资产 UID
#   #3 route_c/reference_reaction_index.csv.gz           — route-C 参考反应（含 UID 列时用于 C 路线）
#
# M3D2 硬约束（老师裁定）：
#   - B-primary / C-fallback；B 非空用 B，B 空才用 C
#   - 不做 B+C 并集
#   - 每路 pool > 100 fail closed
#   - B、C 独立 provenance 都保留（即使只用了一路）

import csv
import gzip
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Literal, Set

from src.schemas.evidence import CandidateReaction
from config.settings import (
    EC_TO_UID_QUERY_EXCLUDED_PATH,
    RHEA2EC_TSV,
    D4_UID_AVAILABILITY_PATH,
    REFERENCE_REACTION_INDEX_PATH,
    MAX_POOL_SIZE,
    ENZYMECAGE_DRY_RUN,
)

logger = logging.getLogger(__name__)


# ─── 通用 helpers ───────────────────────────────────────────────────────

def _open_maybe_gz(path: Path, mode: str = "rt"):
    """按后缀自动 gz 直读"""
    if str(path).endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8")
    return open(path, mode, encoding="utf-8")


def _pick_col(header: List[str], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in header:
            return c
    return None


# ─── D4 UID 白名单（#4） ─────────────────────────────────────────────

class D4UIDWhitelist:
    """
    107,705 完整资产 UID 白名单：用于过滤 B/C pool 中未被 D4 覆盖的 UID。
    与 M3D2E 一致：M3 v1 只在 D4 冻结资产域内构造 pool。
    """

    _UID_COL_CANDIDATES = ["UniprotID", "uniprot_id", "uid", "UID"]

    def __init__(self, path: Optional[Path] = None):
        self._path = path or D4_UID_AVAILABILITY_PATH
        self._uid_set: Set[str] = set()
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        if not self._path.exists():
            raise FileNotFoundError(
                f"D4 UID 资产可用性表不存在: {self._path}\n"
                "请检查学生 tar.gz 是否解压且包含 d4/。"
            )
        logger.info(f"Loading D4 UID whitelist from {self._path}...")
        with _open_maybe_gz(self._path) as f:
            reader = csv.DictReader(f)
            uid_col = _pick_col(reader.fieldnames or [], self._UID_COL_CANDIDATES)
            if uid_col is None:
                raise KeyError(
                    f"D4 UID 表缺 UID 列，header={reader.fieldnames}"
                )
            for row in reader:
                uid = (row.get(uid_col) or "").strip()
                if uid:
                    self._uid_set.add(uid)
        self._loaded = True
        logger.info(f"Loaded {len(self._uid_set)} D4 complete-asset UIDs")

    def filter(self, uids: List[str]) -> List[str]:
        self.load()
        return [u for u in uids if u in self._uid_set]

    def __contains__(self, uid: str) -> bool:
        self.load()
        return uid in self._uid_set


# ─── B 路线：EC → UID（学生 #5 公平表） ─────────────────────────────

class ECUIDMapper:
    """
    公平 query-excluded EC → UID 映射（route-B pool 来源）。
    与 B1 证据一致：451 个 P0 query 反应的正例 UID 已在此表中全局排除。
    """

    _EC_COL_CANDIDATES = ["ec", "EC", "ec_number"]
    _UID_COL_CANDIDATES = ["uid", "UID", "uniprot_id", "UniprotID"]

    def __init__(self, mapping_path: Optional[Path] = None):
        self._path = mapping_path or EC_TO_UID_QUERY_EXCLUDED_PATH
        self._ec_to_uids: dict[str, List[str]] = {}
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        if not self._path.exists():
            raise FileNotFoundError(
                f"EC→UID 公平映射表不存在: {self._path}\n"
                "请检查学生 tar.gz 是否解压且包含 route_b/。"
            )
        logger.info(f"Loading fair EC→UID from {self._path}...")
        with _open_maybe_gz(self._path) as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            ec_col = _pick_col(header, self._EC_COL_CANDIDATES)
            uid_col = _pick_col(header, self._UID_COL_CANDIDATES)
            if ec_col is None or uid_col is None:
                raise KeyError(
                    f"EC→UID 表缺列 (ec={ec_col}, uid={uid_col}), header={header}"
                )
            for row in reader:
                ec = (row.get(ec_col) or "").strip()
                uid = (row.get(uid_col) or "").strip()
                if ec and uid:
                    self._ec_to_uids.setdefault(ec, []).append(uid)
        self._loaded = True
        logger.info(f"Loaded {len(self._ec_to_uids)} EC entries (fair)")

    def query(self, ec_numbers: List[str]) -> List[str]:
        self.load()
        uids: Set[str] = set()
        for ec in ec_numbers:
            uids.update(self._ec_to_uids.get(ec, []))
        return list(uids)


# ─── Rhea → EC（#2 rhea2ec.tsv，格式未变） ──────────────────────────

class RheaECIndex:
    """Rhea master → EC 映射（rhea2ec.tsv 官方格式）"""

    def __init__(self, rhea2ec_path: Optional[Path] = None):
        self._path = rhea2ec_path or RHEA2EC_TSV
        self._rhea_to_ec: dict[str, List[str]] = {}
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        if not self._path.exists():
            raise FileNotFoundError(
                f"rhea2ec.tsv 不存在: {self._path}\n"
                "请检查学生 tar.gz 是否解压且包含 rhea140/。"
            )
        logger.info(f"Loading Rhea→EC from {self._path}...")
        with open(self._path, "r") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader, None)  # header
            for row in reader:
                if len(row) >= 4:
                    # rhea2ec.tsv 官方列：MASTER_ID  DIRECTION  MASTER_ID  ID(EC)
                    rhea_master = row[0].strip()
                    ec = row[3].strip()
                    if rhea_master and ec:
                        self._rhea_to_ec.setdefault(rhea_master, []).append(ec)
        self._loaded = True
        logger.info(f"Loaded {len(self._rhea_to_ec)} Rhea→EC mappings")

    def get_ec(self, rhea_id: str) -> List[str]:
        self.load()
        # 兼容传入 "RHEA:11532" 或 "11532"
        key = rhea_id.split(":")[-1].strip()
        return self._rhea_to_ec.get(key, [])


# ─── C 路线：反应 → UID（学生 #3 route-C 索引中若有 UID 列） ─────

class RxnUIDIndex:
    """
    从 route_c/reference_reaction_index.csv.gz 抽取 reaction_smiles → [UID]。
    若索引 CSV 不含 UID 列，则 C 路线降级为"通过 EC 走 ECUIDMapper"。
    """

    _RXN_COL_CANDIDATES = ["CANO_RXN_SMILES", "reaction_smiles", "rxn_smiles"]
    # 支持两种格式：
    #   - 直接字符串：'uid1;uid2'（旧格式）
    #   - JSON 列表：'["uid1","uid2"]'（学生 v1 route_c index，列名以 _json 结尾）
    _UID_COL_CANDIDATES = ["d4_valid_uids_json", "UniprotID", "uid", "uniprot_id", "known_uids"]
    _EC_COL_CANDIDATES = ["ec", "EC", "ec_numbers"]

    def __init__(self, path: Optional[Path] = None):
        self._path = path or REFERENCE_REACTION_INDEX_PATH
        self._rxn_to_uids: dict[str, List[str]] = {}
        self._rxn_to_ecs: dict[str, List[str]] = {}
        self._has_uid_col = False
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        if not self._path.exists():
            raise FileNotFoundError(
                f"route-C 参考反应索引不存在: {self._path}"
            )
        with _open_maybe_gz(self._path) as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            rxn_col = _pick_col(header, self._RXN_COL_CANDIDATES)
            uid_col = _pick_col(header, self._UID_COL_CANDIDATES)
            ec_col = _pick_col(header, self._EC_COL_CANDIDATES)
            self._has_uid_col = uid_col is not None
            if rxn_col is None:
                raise KeyError(
                    f"route-C 索引缺 reaction SMILES 列, header={header}"
                )
            for row in reader:
                rxn = row[rxn_col]
                if not rxn:
                    continue
                if uid_col:
                    uid_raw = row.get(uid_col) or ""
                    if uid_col.endswith("_json"):
                        # JSON list 编码（学生 v1 schema）
                        try:
                            uids = [str(u).strip() for u in json.loads(uid_raw) if str(u).strip()]
                        except (json.JSONDecodeError, TypeError):
                            uids = []
                    else:
                        # 兼容分号分隔（旧格式）
                        uids = [u.strip() for u in uid_raw.split(";") if u.strip()]
                    if uids:
                        self._rxn_to_uids.setdefault(rxn, []).extend(uids)
                if ec_col:
                    ec_raw = row.get(ec_col) or ""
                    ecs = [e.strip() for e in ec_raw.split(";") if e.strip()]
                    if ecs:
                        self._rxn_to_ecs.setdefault(rxn, []).extend(ecs)
        self._loaded = True
        logger.info(
            f"Loaded route-C index: has_uid_col={self._has_uid_col}, "
            f"rxn_to_uids={len(self._rxn_to_uids)}, rxn_to_ecs={len(self._rxn_to_ecs)}"
        )

    def uids_for(self, rxn_smiles: str) -> List[str]:
        self.load()
        return list(self._rxn_to_uids.get(rxn_smiles, []))

    def ecs_for(self, rxn_smiles: str) -> List[str]:
        self.load()
        return list(self._rxn_to_ecs.get(rxn_smiles, []))


# ─── B / C pool 构造 ────────────────────────────────────────────────

def build_pool_route_b(
    candidate_reactions: List[CandidateReaction],
    ec_uid_mapper: Optional[ECUIDMapper] = None,
    rhea_ec_index: Optional[RheaECIndex] = None,
    d4_whitelist: Optional[D4UIDWhitelist] = None,
) -> List[str]:
    """B 路线：候选反应 → EC → UID（受 D4 白名单过滤）"""
    ec_uid_mapper = ec_uid_mapper or ECUIDMapper()
    rhea_ec_index = rhea_ec_index or RheaECIndex()

    all_ec: Set[str] = set()
    for rxn in candidate_reactions:
        if rxn.ec_numbers:
            all_ec.update(rxn.ec_numbers)
        elif rxn.rhea_id:
            all_ec.update(rhea_ec_index.get_ec(rxn.rhea_id))

    if not all_ec:
        logger.warning("B route: 无 EC 命中")
        return []

    uids = ec_uid_mapper.query(list(all_ec))
    if d4_whitelist is not None:
        before = len(uids)
        uids = d4_whitelist.filter(uids)
        logger.info(f"B route: {before} → {len(uids)} UIDs after D4 whitelist")
    logger.info(f"B route: {len(all_ec)} ECs → {len(uids)} UIDs")
    return uids


def build_pool_route_c(
    candidate_reactions: List[CandidateReaction],
    rxn_uid_index: Optional[RxnUIDIndex] = None,
    ec_uid_mapper: Optional[ECUIDMapper] = None,
    d4_whitelist: Optional[D4UIDWhitelist] = None,
) -> List[str]:
    """
    C 路线：候选相似反应 → UID。
    - 若 route-C 索引含 UID 列，直接使用 reaction→UID
    - 否则降级：候选反应的 EC → ECUIDMapper
    """
    rxn_uid_index = rxn_uid_index or RxnUIDIndex()
    rxn_uid_index.load()

    uids: Set[str] = set()

    if rxn_uid_index._has_uid_col:
        for rxn in candidate_reactions:
            uids.update(rxn_uid_index.uids_for(rxn.reaction_smiles))
        route_note = "direct reaction→UID"
    else:
        # 降级路径：候选反应的 EC → ECUIDMapper
        ec_uid_mapper = ec_uid_mapper or ECUIDMapper()
        all_ec: Set[str] = set()
        for rxn in candidate_reactions:
            all_ec.update(rxn_uid_index.ecs_for(rxn.reaction_smiles))
            if rxn.ec_numbers:
                all_ec.update(rxn.ec_numbers)
        uids.update(ec_uid_mapper.query(list(all_ec)))
        route_note = f"fallback via {len(all_ec)} ECs"

    result = list(uids)
    if d4_whitelist is not None:
        before = len(result)
        result = d4_whitelist.filter(result)
        logger.info(f"C route: {before} → {len(result)} UIDs after D4 whitelist")
    logger.info(f"C route ({route_note}): {len(result)} UIDs")
    return result


def _mock_build_pool_dryrun(
    candidate_reactions: List[CandidateReaction],
) -> Tuple[List[str], Literal["B", "C"], List[str], List[str]]:
    """DRY_RUN mock：不读任何数据文件，直接造 B pool + 空 C pool。

    与 enzymecage_client / reaction_retriever 的 mock 分支对称，仅验 pipeline 拓扑 & evidence 结构。
    采用 B 路线以便覆盖 M3-Q2 裁定的 B-primary 主分支。
    """
    import hashlib
    logger.warning(
        "[DRY_RUN] enzyme_pool_builder 返回 mock B pool，不构成任何真实 pool provenance"
    )
    # 向 EC 注入方式衍生 “伪 UID”，具备确定性
    ecs: Set[str] = set()
    for rxn in candidate_reactions:
        if rxn.ec_numbers:
            ecs.update(rxn.ec_numbers)
    if not ecs:
        ecs = {"1.14.15.3"}  # fallback：候选反应未携 EC 时也保证非空
    pool_b: List[str] = []
    for ec in sorted(ecs):
        for i in range(5):
            uid = f"MOCK_UID_{hashlib.md5(f'{ec}#{i}'.encode()).hexdigest()[:8].upper()}"
            pool_b.append(uid)
    pool_b = list(dict.fromkeys(pool_b))  # 去重保序
    return pool_b, "B", pool_b, []


def build_enzyme_pool(
    candidate_reactions: List[CandidateReaction],
    ec_uid_mapper: Optional[ECUIDMapper] = None,
    rhea_ec_index: Optional[RheaECIndex] = None,
    rxn_uid_index: Optional[RxnUIDIndex] = None,
    d4_whitelist: Optional[D4UIDWhitelist] = None,
) -> Tuple[List[str], Literal["B", "C"], List[str], List[str]]:
    """
    构造酶 pool，遵循 M3D2 硬约束：
      - B-primary / C-fallback，不做并集
      - 每路 pool > 100 fail closed
      - B、C 独立 provenance 均返回

    Returns:
        (final_pool, route_used, pool_b, pool_c)
    Raises:
        ValueError: pool > MAX_POOL_SIZE，或两路均空
    """
    if ENZYMECAGE_DRY_RUN:
        return _mock_build_pool_dryrun(candidate_reactions)

    d4_whitelist = d4_whitelist or D4UIDWhitelist()

    pool_b = build_pool_route_b(candidate_reactions, ec_uid_mapper, rhea_ec_index, d4_whitelist)
    pool_c = build_pool_route_c(candidate_reactions, rxn_uid_index, ec_uid_mapper, d4_whitelist)

    if pool_b:
        if len(pool_b) > MAX_POOL_SIZE:
            raise ValueError(
                f"B route pool size ({len(pool_b)}) > MAX_POOL_SIZE ({MAX_POOL_SIZE}). Fail closed."
            )
        logger.info(f"Route decision: B-primary (|B|={len(pool_b)}, |C|={len(pool_c)} for provenance)")
        return pool_b, "B", pool_b, pool_c

    logger.info(f"Route decision: B empty → C-fallback (|C|={len(pool_c)})")

    if not pool_c:
        raise ValueError("B and C both empty. Fail closed.")

    if len(pool_c) > MAX_POOL_SIZE:
        raise ValueError(
            f"C route pool size ({len(pool_c)}) > MAX_POOL_SIZE ({MAX_POOL_SIZE}). Fail closed."
        )

    return pool_c, "C", pool_b, pool_c
