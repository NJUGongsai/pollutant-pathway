"""functional_group_retrieval.py — 官能团条件检索与两路合并服务（S3a/S3c）。

零 LLM、纯化学规则驱动。
依据公开化学官能团 SMARTS 表（assets/functional_groups/rules.json），
按底物实际具备的官能团筛选反应中心匹配的候选模板族，再在族内按相似度排序。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from rdkit import Chem, DataStructs, RDLogger

RDLogger.DisableLog("rdApp.*")

_DEFAULT_RULES_PATH = Path(__file__).resolve().parents[3] / "assets/functional_groups/rules.json"


@lru_cache(maxsize=1)
def load_functional_group_patterns(rules_path: str | Path | None = None) -> list[tuple[str, Any]]:
    path = Path(rules_path or _DEFAULT_RULES_PATH)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    patterns = []
    for item in data.get("rules", []):
        name = str(item["name"])
        smarts = str(item["smarts"])
        mol = Chem.MolFromSmarts(smarts)
        if mol is not None:
            patterns.append((name, mol))
    return patterns


def detect_functional_groups(mol_or_smiles: str | Any, rules_path: str | Path | None = None) -> set[str]:
    if isinstance(mol_or_smiles, str):
        mol = Chem.MolFromSmiles(mol_or_smiles)
    else:
        mol = mol_or_smiles
    if mol is None:
        return set()

    patterns = load_functional_group_patterns(rules_path)
    hits = set()
    for name, patt in patterns:
        if mol.HasSubstructMatch(patt):
            hits.add(name)
    return hits


def detect_center_functional_groups(mapped_lhs: str, center_atoms: list[int], rules_path: str | Path | None = None) -> set[str]:
    """判定 mapped_lhs 中中心原子所参与的官能团类别。"""
    if not mapped_lhs or not center_atoms:
        return set()
    try:
        mol = Chem.MolFromSmiles(mapped_lhs)
        if mol is None:
            return set()
        # 构建 map_num -> atom_idx 映射
        map_to_idx = {}
        for atom in mol.GetAtoms():
            m = atom.GetAtomMapNum()
            if m:
                map_to_idx[m] = atom.GetIdx()

        center_indices = {map_to_idx[c] for c in center_atoms if c in map_to_idx}
        if not center_indices:
            return set()

        patterns = load_functional_group_patterns(rules_path)
        matched_groups = set()
        for name, patt in patterns:
            for match in mol.GetSubstructMatches(patt):
                if center_indices.intersection(match):
                    matched_groups.add(name)
        return matched_groups
    except Exception:
        return set()


class FunctionalGroupAnalogResolver:
    """基于官能团条件的模板索引与检索器（S3a/S3c）。"""

    def __init__(self, analog_source_resolver, rules_path: str | Path | None = None):
        self.base_resolver = analog_source_resolver
        self.rules_path = rules_path
        self._fg_index: list[dict] | None = None

    def _get_fg_index(self) -> list[dict]:
        if self._fg_index is None:
            base_index = self.base_resolver._reactant_fp_index()
            fg_index = []
            for entry in base_index:
                row = entry["row"]
                lhs = str(row.get("mapped_lhs", ""))
                center = [int(x) for x in (row.get("center_atoms") or [])]
                fg_set = detect_center_functional_groups(lhs, center, self.rules_path)
                fg_index.append({
                    "entry": entry,
                    "fg_set": fg_set,
                })
            self._fg_index = fg_index
        return self._fg_index

    def templates_by_functional_group(
        self, substrate_smiles: str, *, threshold: float = 0.25, top_k: int = 24
    ) -> list[Any]:
        """S3a: 按底物具备的官能团筛选中心匹配模板，再按相似度排序。"""
        sub_fg = detect_functional_groups(substrate_smiles, self.rules_path)
        if not sub_fg:
            # 底物无明确官能团匹配时回退到基础相似度检索
            return self.base_resolver.templates_similar_to(substrate_smiles, threshold=threshold, top_k=top_k)

        index = self._get_fg_index()
        fp = self.base_resolver._reactant_fingerprint(substrate_smiles)
        if fp is None:
            return []

        scored = []
        for item in index:
            # 模板中心官能团必须与底物官能团有交集
            if not item["fg_set"].intersection(sub_fg):
                continue
            entry = item["entry"]
            sim = DataStructs.TanimotoSimilarity(fp, entry["fp"])
            if sim >= threshold:
                row = entry["row"]
                scored.append((sim, entry["line_no"], str(row.get("record_id", "")), entry))

        scored.sort(key=lambda t: (-t[0], t[1], t[2]))
        meta = self.base_resolver._asset_meta["analog_corpus_templates"]
        out = []
        from pathway_v43.services.analog_source import DonorRef, _lhs_rhs, _mapping_quality, _strip_map, CHANNEL_SIMILAR, SIMILARITY_VERSION
        for rank, (sim, _ln, _rid, entry) in enumerate(scored[:top_k], 1):
            row = entry["row"]
            lhs, rhs = _lhs_rhs(row)
            out.append(DonorRef(
                record_id=str(row.get("record_id", "")),
                index="analog_corpus_templates",
                asset_file=meta["asset_file"],
                asset_sha256=meta["asset_sha256"],
                line_no=entry["line_no"],
                mapping_quality=_mapping_quality(lhs, rhs, row.get("qc_flags") or {}),
                reactant_smiles=entry["reactant"],
                product_smiles=_strip_map(rhs),
                mapped_lhs=lhs,
                mapped_rhs=rhs,
                center_atoms=[int(x) for x in (row.get("center_atoms") or [])],
                find_channels=[CHANNEL_SIMILAR, "functional_group"],
                similarity=round(float(sim), 6),
                similarity_version=SIMILARITY_VERSION,
                similarity_rank=rank,
            ))
        return out

    def two_way_merge(
        self, substrate_smiles: str, *, threshold: float = 0.35, top_k: int = 24
    ) -> list[Any]:
        """S3c: 相似度 top-k 与官能团 top-k 两路合并去重，按综合相似度排序。"""
        sim_refs = self.base_resolver.templates_similar_to(substrate_smiles, threshold=threshold, top_k=top_k)
        fg_refs = self.templates_by_functional_group(substrate_smiles, threshold=threshold, top_k=top_k)

        seen_records = set()
        merged = []
        for r in sim_refs:
            if r.record_id not in seen_records:
                seen_records.add(r.record_id)
                merged.append(r)
        for r in fg_refs:
            if r.record_id not in seen_records:
                seen_records.add(r.record_id)
                merged.append(r)

        merged.sort(key=lambda r: (-float(getattr(r, "similarity", 0)), int(getattr(r, "line_no", 0))))
        return merged[:top_k]
