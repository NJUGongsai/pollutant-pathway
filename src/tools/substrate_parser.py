# -*- coding: utf-8 -*-
# 底物解析工具：从用户自然语言查询中提取 SMILES
#
# 三级降级（2026-07-22 重构）：
#   1. 直接检测 SMILES（regex + rdkit 验证）
#   2. 直接检测 InChI（rdkit 转换）
#   3. LLM 提取化学名 + PubChem 官方查表（chem_name_resolver）
#      — LLM 只负责名字归一，SMILES 交给权威库。实测 LLM 直接生成 SMILES
#      正确率仅 2/5（细节见 chem_name_resolver.py 头部注释）。

import re
import json
import logging
from typing import Optional

from rdkit import Chem

from src.schemas.evidence import SubstrateInfo
from src.utils.llm import call_dashscope
from src.tools.chem_name_resolver import resolve_name_to_smiles

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个化学信息提取助手。任务：从用户描述中提取底物化合物的名字，
以便后续去 PubChem 查官方 SMILES。

重要规则：
1. 你必须只输出化合物名字（尽量使用英文或国际通用名，包含手性前缀、号位后缀），
   不要自己生成 SMILES。
2. 若用户提供的是中文名，尽量给出与之对应的英文名（因为 PubChem 对英文名命中率高）；
   同时保留 chem_name_zh 用于追溯。
3. 若用户提供了 SMILES——不需提取名字（但 substrate_parser 会先一步的 regex 处理，
   这时你不会被调用）。
输出格式（严格 JSON，不追加任何其他文字）：
{"chem_name": "(S)-6-hydroxynicotine", "chem_name_zh": "(S)-6-羟基尼古丁", "confidence": "high|medium|low"}

不能识别时返回：
{"chem_name": null, "chem_name_zh": null, "confidence": "low", "error": "无法识别底物"}
"""


def validate_smiles(smiles: str) -> Optional[str]:
    """验证并标准化 SMILES，返回 canonical SMILES 或 None"""
    if not smiles or not isinstance(smiles, str):
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def detect_smiles_in_query(query: str) -> tuple[Optional[str], Optional[str]]:
    """尝试从查询中直接检测 SMILES 字符串，返回 (canonical_smiles, raw_token)。

    候选 token 若原样 rdkit 无法解析，会尝试逐层剥去尾部标点
    （右括号 / 逗号 / 句号 / 分号）再验，以容忍 '降解己烷(CCCCCC)的酶'
    这种中文括号包裹场景。

    T6-R3 裁定 6：首字符放宽为大小写，接受 canonical lowercase aromatic
    SMILES（如 c1ccccc1，芳香碳小写开头）；RDKit parse 作为硬门拒绝误匹配。
    """
    # 匹配 SMILES token：首字符允许大小写（芳香碳 c/n/o/s/p 小写），
    # 后续为原子/键/括号/数字等；RDKit parse 硬门负责拒绝普通英文单词/标点。
    smiles_pattern = r'[a-zA-Z][a-zA-Z0-9@+\-\[\]()=#/\\.]{4,}'
    trailing_strip = ")],;.:），。；："
    candidates = re.findall(smiles_pattern, query)
    for cand in candidates:
        # 直接尝试
        validated = validate_smiles(cand)
        if validated:
            return validated, cand
        # 剥尾标点重试（最多剥 4 层）
        trimmed = cand
        for _ in range(4):
            if trimmed and trimmed[-1] in trailing_strip:
                trimmed = trimmed[:-1]
                validated = validate_smiles(trimmed)
                if validated:
                    return validated, trimmed
            else:
                break
    return None, None


def detect_inchi_in_query(query: str) -> Optional[str]:
    """尝试从查询中检测 InChI 并转换为 SMILES"""
    inchi_pattern = r'InChI=\S+'
    matches = re.findall(inchi_pattern, query)
    for inchi in matches:
        mol = Chem.MolFromInchi(inchi)
        if mol:
            return Chem.MolToSmiles(mol)
    return None


def parse_substrate(user_query: str) -> SubstrateInfo:
    """
    解析用户查询，提取底物 SMILES。
    
    优先级：
    1. 直接检测 SMILES（无需 LLM）
    2. 直接检测 InChI（无需 LLM）
    3. 调用 LLM 解析自然语言
    """
    # Step 1: 尝试直接检测 SMILES
    direct_smiles, raw_smiles = detect_smiles_in_query(user_query)
    if direct_smiles:
        logger.info(f"Direct SMILES detected: {direct_smiles} (raw={raw_smiles})")
        return SubstrateInfo(
            substrate_smiles=direct_smiles,
            substrate_name=None,
            source="user_smiles",
            raw_substrate_smiles=raw_smiles,
            provenance=f"regex_extracted_from_query(raw={raw_smiles})",
        )

    # Step 2: 尝试检测 InChI
    inchi_smiles = detect_inchi_in_query(user_query)
    if inchi_smiles:
        logger.info(f"InChI converted to SMILES: {inchi_smiles}")
        return SubstrateInfo(
            substrate_smiles=inchi_smiles,
            substrate_name=None,
            source="user_inchi",
            provenance=f"inchi_converted"
        )

    # Step 3: LLM 提取化学名字 → PubChem 官方查表
    logger.info("Calling LLM for chemical name extraction...")
    llm_response = call_dashscope(
        prompt=f"用户输入: {user_query}",
        system_prompt=SYSTEM_PROMPT,
        node_name="substrate_node",
    )

    # 解析 LLM JSON 响应
    try:
        # 清理可能的 markdown 代码块
        cleaned = re.sub(r'```json?\s*', '', llm_response)
        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(f"LLM 返回格式错误，无法解析为 JSON: {llm_response[:200]}")

    if parsed.get("error") or not parsed.get("chem_name"):
        raise ValueError(
            f"无法从用户输入中提取化学名: {parsed.get('error', 'unknown')}"
        )

    chem_name_en = parsed["chem_name"]
    chem_name_zh = parsed.get("chem_name_zh")

    # 依次尝试：英文名 → 中文名，任一命中即可
    for candidate_name in [chem_name_en, chem_name_zh]:
        if not candidate_name:
            continue
        lookup = resolve_name_to_smiles(candidate_name)
        if lookup is not None:
            return SubstrateInfo(
                substrate_smiles=lookup.smiles,
                substrate_name=chem_name_en or chem_name_zh,
                source="pubchem_lookup",
                provenance=(
                    f"llm_name_extracted={candidate_name!r} → "
                    f"{lookup.source}(cid={lookup.backend_cid}, ikey={lookup.inchi_key})"
                ),
            )

    # 所有名字候选都 miss：permission-denied式报错，避免静默搞错底物
    raise ValueError(
        f"化学名提取为 {chem_name_en!r}（zh={chem_name_zh!r}），但 PubChem 未命中。"
        f"请提供 SMILES 或 InChI 以确保结构准确。"
    )
