# -*- coding: utf-8 -*-
"""化学名 → SMILES 确定性解析服务（PubChem 主、ChEBI 兜底）

设计原则（2026-07-22 引入）：
- LLM 不能可靠生成 SMILES —— 实测 5 次跑 (S)-6-hydroxynicotine 只有 2 次正确异构体，
  1 次骨架错、1 次位置异构体错、1 次输出无效 SMILES。SMILES 是精确串，
  `c1ccc(O)nc1` 与 `c1ccncc1O` 长得几乎一样但完全不同分子。
- 因此把"名字 → SMILES"这步交给权威化学库（PubChem CID lookup），
  LLM 只承担"从自然语言中提取化学名"这一较松的任务。

对外接口：
    resolve_name_to_smiles(name: str) -> ChemLookupResult | None

失败语义：任何一个后端返回 200 但无匹配，或全部后端超时/异常，都返回 None。
调用方按 None 决定是否升级到"要求用户提供 SMILES/InChI"或"raise 无法识别"。
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import httpx
from rdkit import Chem

logger = logging.getLogger(__name__)


@dataclass
class ChemLookupResult:
    """名字 → 结构解析结果。SMILES 经 rdkit canonical，InChIKey 用于跨库匹配。"""
    smiles: str                # canonical SMILES（rdkit MolToSmiles）
    inchi_key: str             # rdkit MolToInchiKey，可用于反查数据库
    name: str                  # 传入的化学名（原样透传，便于 provenance）
    source: str                # "pubchem" | "chebi"
    raw_smiles: str            # 后端返回的原始 SMILES（未 canonical，保留追溯）
    backend_cid: Optional[str] = None  # PubChem CID / ChEBI ID


# ─────────────────────── 后端配置 ───────────────────────

_PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_CHEBI_BASE = "https://www.ebi.ac.uk/ols/api"      # 备用；PubChem 覆盖 >95% 常见化合物
_HTTP_TIMEOUT = 15.0
_HTTP_RETRY_MAX = 3
_HTTP_RETRY_BACKOFF = 1.5   # 1.5s → 3s → 6s


def _http_get_with_retry(url: str, tag: str) -> Optional[httpx.Response]:
    """带指数退避的 GET；连接超时/网络抖动情况下重试 3 次。"""
    for attempt in range(_HTTP_RETRY_MAX):
        try:
            r = httpx.get(url, timeout=_HTTP_TIMEOUT, follow_redirects=True)
            return r
        except httpx.HTTPError as e:
            if attempt == _HTTP_RETRY_MAX - 1:
                logger.warning(f"[{tag}] GET failed after {_HTTP_RETRY_MAX} attempts: {e}")
                return None
            wait = _HTTP_RETRY_BACKOFF * (2 ** attempt)
            logger.debug(f"[{tag}] GET retry {attempt+1}/{_HTTP_RETRY_MAX} after {wait}s: {e}")
            time.sleep(wait)
    return None


def _canonicalize(smiles: str) -> Optional[tuple[str, str]]:
    """rdkit canonical SMILES + InChIKey；失败返回 None。"""
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    canon = Chem.MolToSmiles(m)
    ikey = Chem.MolToInchiKey(m)
    return canon, ikey


# ─────────────────────── PubChem ───────────────────────

def _pubchem_lookup(name: str) -> Optional[ChemLookupResult]:
    """PubChem PUG-REST /compound/name/{name}/property/SMILES,InChIKey/JSON

    优先取 IsomericSMILES（含立体）；若无则回退 SMILES。
    2026 PUG-REST 已把 CanonicalSMILES / IsomericSMILES 合并为 `SMILES` 字段。
    """
    url = f"{_PUBCHEM_BASE}/compound/name/{quote(name)}/property/SMILES,InChIKey/JSON"
    r = _http_get_with_retry(url, tag=f"pubchem[{name}]")
    if r is None or r.status_code != 200:
        return None
    try:
        props = r.json()["PropertyTable"]["Properties"]
        if not props:
            return None
        p = props[0]
    except (KeyError, ValueError, TypeError):
        return None

    raw = p.get("SMILES") or p.get("IsomericSMILES") or p.get("CanonicalSMILES")
    if not raw:
        return None
    canonized = _canonicalize(raw)
    if canonized is None:
        logger.warning(f"[pubchem] returned invalid SMILES for {name!r}: {raw!r}")
        return None
    canon, ikey = canonized
    cid = str(p.get("CID")) if p.get("CID") is not None else None
    return ChemLookupResult(
        smiles=canon,
        inchi_key=ikey,
        name=name,
        source="pubchem",
        raw_smiles=raw,
        backend_cid=cid,
    )


# ─────────────────────── ChEBI (兜底) ───────────────────────
# 说明：ChEBI 无直接 name→SMILES REST endpoint；这里保留占位，
# 若 PubChem miss 则尝试通过 EBI OLS 搜 chebi 术语再翻结构文件。
# 现阶段（M3-P1）不实现，直接返回 None；未来 miss 率高再补。

def _chebi_lookup(name: str) -> Optional[ChemLookupResult]:
    logger.debug(f"[chebi] fallback stub for {name!r}; currently not implemented")
    return None


# ─────────────────────── 对外接口 ───────────────────────

def resolve_name_to_smiles(name: str) -> Optional[ChemLookupResult]:
    """化学名 → 权威 SMILES/InChIKey。

    后端顺序：PubChem → ChEBI（stub）。任何一步命中即返回。
    传入 name 应尽量归一（去多余引号/前后空白），但保留大小写和括号
    （PubChem 对 "(S)-6-hydroxynicotine" 直接命中）。
    """
    name = (name or "").strip().strip('"').strip("'")
    if not name:
        return None

    for backend in (_pubchem_lookup, _chebi_lookup):
        result = backend(name)
        if result is not None:
            logger.info(
                f"[chem_resolver] hit {result.source} for {name!r}: "
                f"CID={result.backend_cid} ikey={result.inchi_key}"
            )
            return result

    logger.info(f"[chem_resolver] miss all backends for {name!r}")
    return None
