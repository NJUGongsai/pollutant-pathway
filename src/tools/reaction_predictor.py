# src/tools/reaction_predictor.py
# M5: 反应预测工具 (fallback 分支)
# 当相似反应检索失败时，生成候选反应
#
# 引擎现状（2026-08-03）：
# - biotransformer_envmicro: 已实装（BioTransformer 3.0 ENVMICRO）
#   ENVMICRO 是 EAWAG-BBD/PPS 规则系统：SMARTS 决定"底物哪里能反应"，
#   SMIRKS 决定"命中后结构如何变换"；不是深度学习生成、不是 Rhea/EC/UniProt 查询。
#   输出 CSV 中 Enzyme(s)=UNSPECIFIED_ENVIRONMENTAL_BACTERIAL_ENZYME，不可作为候选酶 UID。
# - template_matching / llm_generation: 占位，待引擎选型裁定后实装

import csv
import io
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from src.schemas.evidence import PredictedReaction

logger = logging.getLogger(__name__)

# BioTransformer 3.0 vendor CSV 字段名（不同小版本有差异，解析时多候选容错）
_PRODUCT_COL_CANDIDATES = ("Product_SMILES", "Product SMILES", "Products", "Product(s)", "Product")
_RXN_ID_COL_CANDIDATES = ("Reaction ID", "Reaction_ID", "ReactionID", "Reaction")
_ENZYME_COL_CANDIDATES = ("Enzyme(s)", "Enzyme", "Enzymes")


def _find_col(header: List[str], candidates) -> Optional[str]:
    for cand in candidates:
        if cand in header:
            return cand
    return None


def _biotransformer_jar() -> Optional[str]:
    """从环境变量 / 配置读取 BioTransformer jar 路径。"""
    return os.environ.get("BIOTRANSFORMER_JAR") or None


def run_biotransformer_envmicro(substrate_smiles: str, jar_path: str, timeout: int = 180) -> Optional[str]:
    """
    调用 BioTransformer 3.0 ENVMICRO 生成候选产物，返回 vendor CSV 文本。

    执行命令（与晨羽 HPC 返回包工具身份一致）：
        java -jar <jar> -k pred -b env -ismi <smiles> -ocsv <csv> -s 1

    返回 None 表示调用失败（jar 缺失 / 命令异常），由调用方决定 fail-closed。
    """
    if not substrate_smiles:
        logger.warning("[reaction_predictor] empty substrate_smiles")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        out_csv = str(Path(tmpdir) / "biotransformer_out.csv")
        cmd = [
            "java", "-jar", jar_path,
            "-k", "pred",
            "-b", "env",
            "-ismi", substrate_smiles,
            "-ocsv", out_csv,
            "-s", "1",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            logger.error("[reaction_predictor] java not found; cannot run BioTransformer")
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"[reaction_predictor] BioTransformer timeout after {timeout}s")
            return None

        if proc.returncode != 0:
            logger.error(
                f"[reaction_predictor] BioTransformer failed rc={proc.returncode}: {proc.stderr[-500:]}"
            )
            return None

        try:
            return Path(out_csv).read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.error("[reaction_predictor] BioTransformer output CSV missing")
            return None


def _parse_vendor_csv(csv_text: str) -> List[dict]:
    """解析 BioTransformer vendor CSV 为行字典（字段名容错）。"""
    rows = []
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
    except csv.Error:
        logger.error("[reaction_predictor] BioTransformer CSV unparseable")
        return rows

    header = reader.fieldnames or []
    product_col = _find_col(header, _PRODUCT_COL_CANDIDATES)
    rxn_id_col = _find_col(header, _RXN_ID_COL_CANDIDATES)
    enzyme_col = _find_col(header, _ENZYME_COL_CANDIDATES)
    if product_col is None:
        logger.warning(f"[reaction_predictor] no product column in header: {header}")
        return rows

    for line_no, row in enumerate(reader, start=2):
        product_smiles = (row.get(product_col) or "").strip()
        if not product_smiles:
            continue
        rows.append(
            {
                "product_smiles": product_smiles,
                "reaction_id": (row.get(rxn_id_col) or "").strip() if rxn_id_col else "",
                "enzyme": (row.get(enzyme_col) or "").strip() if enzyme_col else "",
                "csv_line": line_no,
            }
        )
    return rows


def _postprocess_products(
    parent_smiles: str,
    rows: List[dict],
    top_k: int = 10,
) -> List[PredictedReaction]:
    """
    adapter 后处理：RDKit 规范化 / 去重 / 按 vendor CSV 行序保留 rank / Top-10 截断。

    BioTransformer 的 rank 不是概率：raw_score=null、score_semantics=absent，
    因此 confidence 统一置 0.0，语义在 provenance 中说明。
    """
    from rdkit import Chem

    seen_products = set()
    results: List[PredictedReaction] = []

    for row in rows:
        mol = Chem.MolFromSmiles(row["product_smiles"])
        if mol is None:
            continue
        canonical_smiles = Chem.MolToSmiles(mol)
        if canonical_smiles in seen_products:
            continue
        seen_products.add(canonical_smiles)

        # parent>>product 半反应表示（BioTransformer 只预测产物，不预测完整反应）
        reaction_smiles = f"{parent_smiles}>>{canonical_smiles}"
        provenance = (
            "biotransformer_envmicro: rule-based (EAWAG-BBD/PPS lineage), "
            "rank from vendor CSV order, raw_score=null; "
            f"reaction_id={row['reaction_id'] or 'NA'}; "
            f"enzyme_field={row['enzyme'] or 'NA'} (NOT usable as enzyme UID)"
        )
        results.append(
            PredictedReaction(
                reaction_smiles=reaction_smiles,
                prediction_method="biotransformer_envmicro",
                confidence=0.0,
                provenance=provenance,
            )
        )
        if len(results) >= top_k:
            break

    return results


def predict_reactions(
    substrate_smiles: str,
    method: str = "biotransformer_envmicro",
    top_k: int = 5,
) -> List[PredictedReaction]:
    """
    基于底物 SMILES 预测可能的降解反应。

    可选方法:
    - "biotransformer_envmicro": BioTransformer 3.0 ENVMICRO 规则引擎（已实装）
    - "template_matching": 已知降解路径模板匹配（占位，待引擎选型裁定）
    - "llm_generation": LLM 生成 + RDKit 验证（占位）

    Args:
        substrate_smiles: 底物 SMILES
        method: 预测方法
        top_k: 返回最大候选反应数

    Returns:
        PredictedReaction 列表（无候选或调用失败时返回空列表，由上层 fail-closed）
    """
    if method != "biotransformer_envmicro":
        logger.warning(f"[reaction_predictor] method '{method}' not implemented yet")
        return []

    jar_path = _biotransformer_jar()
    if jar_path is None:
        logger.warning(
            "[reaction_predictor] BIOTRANSFORMER_JAR not set; "
            "BioTransformer ENVMICRO unavailable, returning empty candidates"
        )
        return []

    csv_text = run_biotransformer_envmicro(substrate_smiles, jar_path)
    if csv_text is None:
        return []

    rows = _parse_vendor_csv(csv_text)
    if not rows:
        logger.warning("[reaction_predictor] BioTransformer produced no product rows")
        return []

    return _postprocess_products(substrate_smiles, rows, top_k=top_k)


def validate_reaction_smiles(reaction_smiles: str) -> bool:
    """
    验证反应 SMILES 的化学合理性。

    检查:
    - 格式正确 (A>>B)
    - 底物/产物均可解析
    - 原子数守恒 (可选)
    """
    try:
        from rdkit import Chem
        parts = reaction_smiles.split(">>")
        if len(parts) != 2:
            return False
        for side in parts:
            mols = side.split(".")
            for smi in mols:
                if Chem.MolFromSmiles(smi) is None:
                    return False
        return True
    except Exception:
        return False
