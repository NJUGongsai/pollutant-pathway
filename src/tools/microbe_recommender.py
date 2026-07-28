# src/tools/microbe_recommender.py
# M5: 微生物推荐工具（严格镜像学生 microbe_crew.tools.enzyme2organism_tool）
#
# 职责：把酶 UID 映射到 reviewed UniProt 宿主（主证据）+ 独立 KEGG multiplicity（交叉证据），
#       产出 EnzymeSourceProvenance（原始证据维度透传），供 OrganismAggregator 聚合。
#
# 纪律：
# - MT-D1：v1 仅纳入 UniProt reviewed (Swiss-Prot) 宿主；unreviewed(TrEMBL) 记为 SourceError 排除。
# - MT-D2：透传原始维度（reviewed 状态 / annotation score / protein existence / KEGG multiplicity），
#          不合成 organism_confidence float、不把 reviewed/unreviewed 映射成 0-1。
# - 不做 metaTraits 性状判定 / 污水适配打分（M4b，未立项）。habitat_match 一律留空并诚实标注。

import hashlib
import json
import logging
from typing import Dict, List, Optional, Tuple

import httpx

from src.schemas.evidence import (
    EnzymeSourceProvenance,
    KEGGSupplementEvidence,
    MicrobeCandidate,
    SourceError,
    UniProtReviewedHostEvidence,
)

logger = logging.getLogger(__name__)

UNIPROT_ENTRY_TYPE = "UniProtKB reviewed (Swiss-Prot)"
_HTTP_TIMEOUT = 20.0
_USER_AGENT = "EnzymeCAGE-Crew-Enzyme2Organism/1.0"
_HEADERS = {"User-Agent": _USER_AGENT, "Accept": "application/json, text/plain"}


def _uniprot_url(uid: str) -> str:
    return f"https://rest.uniprot.org/uniprotkb/{uid}.json"


def _kegg_url(uid: str) -> str:
    return f"https://rest.kegg.jp/conv/genes/uniprot:{uid}"


def _request_bytes(url: str) -> bytes:
    resp = httpx.get(url, headers=_HEADERS, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()
    return bytes(resp.content)


def _request_error(source: str, url: str, exc: Exception) -> SourceError:
    return SourceError(
        source_database=source,
        source_url=url,
        error_type=type(exc).__name__,
        message=str(exc),
    )


def query_uniprot_reviewed(
    uid: str,
) -> Tuple[Optional[UniProtReviewedHostEvidence], Optional[SourceError]]:
    """查询 reviewed UniProt 宿主证据；unreviewed / 校验失败返回 (None, SourceError)。"""
    url = _uniprot_url(uid)
    body = _request_bytes(url)
    digest = hashlib.sha256(body).hexdigest()
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, SourceError(
            source_database="UniProtKB", source_url=url,
            error_type="malformed_response", message=f"invalid UTF-8 JSON: {exc}",
        )

    if not isinstance(payload, dict):
        return None, SourceError(
            source_database="UniProtKB", source_url=url,
            error_type="malformed_response", message="top-level UniProt response is not an object",
        )
    if payload.get("primaryAccession") != uid:
        return None, SourceError(
            source_database="UniProtKB", source_url=url,
            error_type="primary_accession_mismatch",
            message="primaryAccession does not exactly match the requested UID",
        )
    if payload.get("entryType") != UNIPROT_ENTRY_TYPE:
        return None, SourceError(
            source_database="UniProtKB", source_url=url,
            error_type="unreviewed_or_unsupported_entry",
            message="entryType is not UniProtKB reviewed (Swiss-Prot)",
        )

    organism = payload.get("organism")
    if not isinstance(organism, dict):
        organism = {}
    name = organism.get("scientificName")
    taxon_id = organism.get("taxonId")
    if not isinstance(name, str) or not name.strip():
        return None, SourceError(
            source_database="UniProtKB", source_url=url,
            error_type="missing_reviewed_host",
            message="reviewed record lacks a scientific organism name",
        )
    if isinstance(taxon_id, bool) or not isinstance(taxon_id, int) or taxon_id <= 0:
        return None, SourceError(
            source_database="UniProtKB", source_url=url,
            error_type="missing_reviewed_host",
            message="reviewed record lacks a positive integer NCBI taxon ID",
        )

    try:
        evidence = UniProtReviewedHostEvidence(
            source_url=url,
            response_sha256=digest,
            primary_accession=payload["primaryAccession"],
            entry_type=payload["entryType"],
            reviewed=True,
            scientific_organism_name=name,
            ncbi_taxon_id=taxon_id,
            lineage=organism.get("lineage", []),
            annotation_score=payload["annotationScore"],
            protein_existence=payload["proteinExistence"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        return None, SourceError(
            source_database="UniProtKB", source_url=url,
            error_type="malformed_response",
            message=f"reviewed evidence fields are malformed: {exc}",
        )
    return evidence, None


def query_kegg(uid: str) -> KEGGSupplementEvidence:
    """查询 KEGG 基因映射并保留 multiplicity 原样（解析异常时向上抛出，由调用方转 SourceError）。"""
    url = _kegg_url(uid)
    body = _request_bytes(url)
    digest = hashlib.sha256(body).hexdigest()
    text = body.decode("utf-8")
    expected_left = f"up:{uid}"
    gene_ids: List[str] = []
    seen: set = set()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        fields = raw_line.split("\t")
        if len(fields) != 2 or fields[0] != expected_left or not fields[1] or ":" not in fields[1]:
            raise ValueError(f"invalid KEGG conversion row {line_number}")
        gene_id = fields[1]
        if gene_id not in seen:
            seen.add(gene_id)
            gene_ids.append(gene_id)
    multiplicity = len(gene_ids)
    state = "missing" if multiplicity == 0 else "single" if multiplicity == 1 else "multiple"
    return KEGGSupplementEvidence(
        source_url=url, response_sha256=digest,
        gene_ids=gene_ids, multiplicity=multiplicity, state=state,
    )


def _map_one(uid: str) -> EnzymeSourceProvenance:
    errors: List[SourceError] = []
    uniprot: Optional[UniProtReviewedHostEvidence] = None
    kegg: Optional[KEGGSupplementEvidence] = None
    try:
        uniprot, exclusion = query_uniprot_reviewed(uid)
        if exclusion is not None:
            errors.append(exclusion)
    except httpx.HTTPError as exc:
        errors.append(_request_error("UniProtKB", _uniprot_url(uid), exc))
    try:
        kegg = query_kegg(uid)
    except (httpx.HTTPError, ValueError, UnicodeDecodeError) as exc:
        errors.append(_request_error("KEGG", _kegg_url(uid), exc))
    return EnzymeSourceProvenance(
        enzyme_uid=uid, uniprot_reviewed=uniprot, kegg=kegg, source_errors=errors,
    )


def map_enzyme_hosts(enzyme_uids: List[str]) -> Dict[str, EnzymeSourceProvenance]:
    """给定酶 UID 列表，映射到 reviewed UniProt 宿主 + KEGG multiplicity（首见去重顺序）。

    Returns:
        {enzyme_uid: EnzymeSourceProvenance}。网络不可用时各源记 SourceError，不编造。
    """
    provenance: Dict[str, EnzymeSourceProvenance] = {}
    for uid in enzyme_uids:
        if uid in provenance:
            continue
        provenance[uid] = _map_one(uid)
    reviewed = sum(1 for p in provenance.values() if p.uniprot_reviewed is not None)
    logger.info(
        f"[microbe_recommender] 映射 {len(provenance)} 个酶 UID → reviewed 宿主 {reviewed} 个"
    )
    return provenance


def microbe_candidates_from_provenance(
    provenance: Dict[str, EnzymeSourceProvenance],
    order: List[str],
    environment: str = "wastewater",
) -> List[MicrobeCandidate]:
    """从 provenance 派生 MicrobeCandidate（仅 reviewed 宿主），供展示/证据链使用。

    MT-D1：仅 reviewed 宿主成为候选；unreviewed / 失败者不进候选（其排除留痕在 provenance）。
    """
    candidates: List[MicrobeCandidate] = []
    for uid in order:
        prov = provenance.get(uid)
        if prov is None or prov.uniprot_reviewed is None:
            continue
        up = prov.uniprot_reviewed
        kegg_note = ""
        if prov.kegg is not None:
            kegg_note = f"；KEGG multiplicity={prov.kegg.multiplicity}({prov.kegg.state})"
        candidates.append(
            MicrobeCandidate(
                organism_name=up.scientific_organism_name,
                tax_id=up.ncbi_taxon_id,
                enzyme_uid=uid,
                habitat_match=None,  # M4b 未立项，不做污水适配评估
                growth_conditions=None,
                source_db="UniProt",
                evidence_level="reviewed",
                rationale=(
                    f"UniProt reviewed 宿主（annotation_score={up.annotation_score}, "
                    f"protein_existence={up.protein_existence}{kegg_note}）；"
                    f"目标环境 {environment} 未做性状适配评估，待 M4b metaTraits 集成"
                ),
            )
        )
    return candidates


def recommend_microbes(
    enzyme_uids: List[str],
    environment: str = "wastewater",
    top_k: int = 5,
) -> List[MicrobeCandidate]:
    """便捷入口：映射 + 派生 MicrobeCandidate（reviewed-only）。

    保留此函数以兼容既有调用；内部走 map_enzyme_hosts 单次网络查询。
    """
    uids = enzyme_uids[:top_k] if top_k else enzyme_uids
    provenance = map_enzyme_hosts(uids)
    candidates = microbe_candidates_from_provenance(provenance, uids, environment)
    if not candidates:
        logger.warning(
            "[microbe_recommender] 未获得任何 reviewed organism 映射（网络不可用或全部 unreviewed），返回空列表"
        )
    return candidates
