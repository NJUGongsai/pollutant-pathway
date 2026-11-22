"""v44-Next v1.3 T2 步骤 1：枚举候选注入候选池（默认关闭）。

用途
----
把 T1-D 通用枚举器（18 条一步规则 + 非环单键断裂）的候选，按**步骤 0 离线
先验**排序后注入建池阶段的 Top-16 候选池。注入会改变提示词，因此这是
**付费验证专用**的开关；未开启时建池路径逐字节同 v1.2（零漂移）。

注入规则（写死、可审计）
------------------------
1. **候选来源**：``generic_enumerator.enumerate_for_pool_injection``——零 LLM、
   零外部数据，全部由 RDKit 从底物确定性生成。
2. **先验**：候选的规则集合（同一产物可能被多条规则生成）在 ``corpus_v1``
   历史记录里"解释"过的次数取**最大值**。语料统计与自排除口径见
   ``scripts/eval/v13_t2_step0_prior.py``。
3. **排序**：先验降序 → 与底物的 Morgan(r=2) Tanimoto 降序 → 规则名/SMILES
   字典序（完全确定性，无随机）。
4. **去重**：产物严格身份已在池内 ⇒ 跳过（不占名额）。
5. **编译**：逐个走 ``compile_s5_candidate_to_spec``（与 S5 入池同一编译 +
   RDKit 执行 + 11 项审计准入链路）；编译不过的跳过、不占名额；最多取 k 个。
6. **替换规则**：每成功注入 1 个，**删除池列表末位 1 条**（池尾 = 建池阶段
   排序末位，即最低先验/最弱相似条目），注入项追加到池尾；池上限
   ``max_pool`` 不变。池不足 2 条时不注入（没有可替换的尾部条目）。

调用方
------
``s5_hybrid_choice.build_s5_hybrid_pool_entries`` 在池装配完成后调用
:func:`inject_enumerated_candidates`；先验表由建池 CLI
（``s5b_cli build --enumerated-rule-priors``）从步骤 0 的
``rule_frequencies.json`` 读入并随批次冻结。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdkit import Chem, RDLogger

from . import generic_enumerator as enumerator

RDLogger.DisableLog("rdApp.*")

INJECTION_VERSION = "v13-enumerated-injection-1"
PLAN_KEY = "enumerated_injection"


def _strip_cx(smiles: str) -> str:
    """剥离 CXSMILES 扩展段（atom class 等注释不改变分子图）。"""
    return str(smiles or "").split("|", 1)[0].strip()


def load_rule_priors(path: str | Path) -> dict[str, int]:
    """读步骤 0 的 ``rule_frequencies.json`` → ``{规则名: 历史出现次数}``。"""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    frequencies = payload.get("frequencies") if isinstance(payload, dict) else None
    if not isinstance(frequencies, dict):
        raise ValueError("rule_frequencies.json 缺少 frequencies 字典")
    return {str(k): int(v) for k, v in frequencies.items()}


def priors_sha256(path: str | Path) -> str:
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank_injection_candidates(
    substrate_smiles: str,
    rule_priors: dict[str, int],
    *,
    exclude_strict: set[str] | None = None,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """按先验 + 相似度对枚举候选排序（不含编译）。"""
    from ..pollutant.chemstate import strict_identity_of

    sub = str(substrate_smiles or "").strip()
    sub_mol = Chem.MolFromSmiles(sub) if sub else None
    if sub_mol is None:
        return []
    excluded = set(exclude_strict or ())
    result = enumerator.enumerate_for_pool_injection(sub, enabled=True)
    mapping: dict[str, list[str]] = {}
    for rule, smiles_list in (result.by_rule or {}).items():
        for smiles in smiles_list:
            mapping.setdefault(str(smiles), []).append(str(rule))
    for smiles in result.candidates:
        mapping.setdefault(str(smiles), [])
    ranked: list[dict[str, Any]] = []
    for smiles, rules in mapping.items():
        plain = _strip_cx(smiles)
        if not plain:
            continue
        try:
            strict = strict_identity_of(plain)
        except Exception:  # noqa: BLE001
            continue
        if not strict or strict in excluded:
            continue
        candidate_mol = Chem.MolFromSmiles(plain)
        similarity = (enumerator.tanimoto(sub_mol, candidate_mol)
                      if candidate_mol is not None else 0.0)
        prior = max((int(rule_priors.get(rule, 0)) for rule in rules), default=0)
        ranked.append({
            "cand_smiles": plain,
            "cand_strict": strict,
            "rules": sorted(rules),
            "prior": prior,
            "similarity": round(float(similarity), 6),
        })
    ranked.sort(key=lambda row: (
        -int(row["prior"]), -float(row["similarity"]),
        ",".join(row["rules"]), str(row["cand_smiles"])))
    if limit and limit > 0:
        return ranked[: int(limit)]
    return ranked


def inject_enumerated_candidates(
    substrate_smiles: str,
    pool_specs: list[dict[str, Any]],
    *,
    k: int,
    rule_priors: dict[str, int],
    max_pool: int = 16,
    compile_candidate=None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """把最多 ``k`` 条枚举候选编译后注入池（替换池尾同等数量条目）。

    ``compile_candidate`` 缺省用 ``s5_hybrid_choice.compile_s5_candidate_to_spec``
    （与 S5 入池同一链路）；测试可注入桩函数。
    """
    from ..pollutant.chemstate import strict_identity_of

    report: dict[str, Any] = {
        "version": INJECTION_VERSION,
        "k": int(k),
        "n_candidates_ranked": 0,
        "n_compiled": 0,
        "injected": [],
        "replaced": [],
        "skipped_compile": 0,
    }
    if int(k) <= 0:
        return list(pool_specs), report
    pool = list(pool_specs or [])
    if len(pool) < 2:
        report["note"] = "池不足 2 条,无尾部条目可替换,不注入"
        return pool, report
    if compile_candidate is None:
        from .s5_hybrid_choice import compile_s5_candidate_to_spec

        def compile_candidate(cand, index):  # type: ignore[misc]
            return compile_s5_candidate_to_spec(
                str(substrate_smiles), cand, index=index,
                is_gated_supplement=False)

    exclude: set[str] = set()
    for spec in pool:
        product = str(spec.get("product_smiles") or "")
        if not product:
            continue
        try:
            exclude.add(strict_identity_of(_strip_cx(product)))
        except Exception:  # noqa: BLE001
            continue
    ranked = rank_injection_candidates(
        substrate_smiles, rule_priors, exclude_strict=exclude)
    report["n_candidates_ranked"] = len(ranked)

    injected: list[dict[str, Any]] = []
    attempted = 0
    for row in ranked:
        if len(injected) >= int(k):
            break
        if len(pool) - len(injected) < 2:
            break
        attempted += 1
        rules = list(row["rules"])
        cand = {
            "cand_smiles": row["cand_smiles"],
            "product_smiles": row["cand_smiles"],
            "env_rule_ids": rules,
            "prior_score": float(row["prior"]),
            "s5_prior_score": float(row["prior"]),
            "prior_tier": "ENUM_PRIOR",
            "s5_prior_tier": "ENUM_PRIOR",
            "source_families": ["enumerated"],
            "sources": ["enumerated"],
        }
        spec = compile_candidate(cand, attempted)
        if spec is None:
            report["skipped_compile"] += 1
            continue
        spec = dict(spec)
        spec["key"] = f"s5-{attempted:02d}-enum-{str(rules[0])[:40]}"
        spec["transformation_ref"] = f"enum-rule:{rules[0]}"
        spec["origin_group_key"] = f"enumerated:{row['cand_strict']}"
        spec["coefficient"] = int(spec.get("coefficient", 1) or 1)
        spec["selection_channels"] = ["enumerated"]
        spec["analog_rank"] = 200 + attempted
        spec["s5_prior_score"] = float(row["prior"])
        spec["s5_prior_tier"] = "ENUM_PRIOR"
        spec["source_families"] = ["enumerated"]
        spec["is_gated_supplement"] = False
        spec["enumerated_injection"] = {
            "version": INJECTION_VERSION,
            "rules": rules,
            "prior": int(row["prior"]),
            "similarity": float(row["similarity"]),
        }
        compile_meta = dict(spec.get("compile") or {})
        compile_meta.update({
            "source_kind": "s5_hybrid_rule",
            "injection_source": "v13_enumerated_rule",
            "primary_rule_id": rules[0],
            "s5_prior_score": float(row["prior"]),
            "s5_prior_tier": "ENUM_PRIOR",
            "source_families": ["enumerated"],
            "is_gated_supplement": False,
        })
        spec["compile"] = compile_meta
        injected.append(spec)

    if not injected:
        report["note"] = "无候选编译通过,池保持原样"
        return pool, report

    replaced = pool[-len(injected):]
    kept = pool[: len(pool) - len(injected)]
    new_pool = kept + injected
    report["n_compiled"] = len(injected)
    report["injected"] = [
        {
            "product_strict": str(spec.get("origin_group_key") or ""),
            "rules": (spec.get("enumerated_injection") or {}).get("rules"),
            "prior": (spec.get("enumerated_injection") or {}).get("prior"),
        }
        for spec in injected
    ]
    report["replaced"] = [
        {
            "key": str(spec.get("key") or ""),
            "transform": str(spec.get("transformation_ref") or ""),
            "s5_prior_score": spec.get("s5_prior_score"),
        }
        for spec in replaced
    ]
    report["pool_size_before"] = len(pool)
    report["pool_size_after"] = len(new_pool[: int(max_pool)])
    return new_pool[: int(max_pool)], report