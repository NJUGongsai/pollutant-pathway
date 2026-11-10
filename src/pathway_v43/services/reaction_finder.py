"""ReactionFinder — 统一检索入口与基于本仓资产/冻结引擎的真实实现。

证据分级(任务书 §1.2,ARCHITECTURE §5):
- recorded_reaction:仅授予 eawag lookup 的**同一规范底物精确键命中**
  (donor_exact_match,方向=donor→product,可追溯 btid#reac_id);
- rule_application:envipath/uspto 规则模板命中 —— 是预测,不是实测;
- analog_reaction:语料检索邻居迁移;
- Tanimoto 高分、source 字符串含 envipath 等都不自动升格为已记录反应;
- 同一反应 ID 的多个产物聚合为**一张**证据卡(有序产物表);不同反应 ID
  是竞争反应,各自成卡;
- 原子映射在本资产集中不存在 → 显式 unavailable;条件数据缺失 → unknown;
- 保留引擎原始顺序(retrieval_rank 为 merged 池 1 起始位次)与原始分数语义,
  不跨来源比较成分数概率。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..domain.identity import cn_identity
from ..domain.models import (
    ATOM_MAPPING_UNAVAILABLE,
    CONDITION_UNKNOWN,
    EVIDENCE_KIND_ANALOG,
    EVIDENCE_KIND_RECORDED,
    EVIDENCE_KIND_RULE,
    content_hash,
    now_iso,
    stable_id,
)

RETRIEVAL_SCHEMA_VERSION = "v43-retrieval-2"  # v2:+donor_refs/mapping_status/mapping_reason(§1 兼容读取)
# 读取端接受的全部历史版本(runs/ 既有产物含 v43-retrieval-1 与 -2;
# 命名风格与 PREDICTION_TASK_SCHEMA_VERSION 等既有版本常量一致)
SUPPORTED_RETRIEVAL_SCHEMA_VERSIONS = ("v43-retrieval-1", "v43-retrieval-2")


class RetrievalSchemaError(RuntimeError):
    """检索产物 schema 版本未知(fail-closed:拒绝解析,不静默猜测字段义)。

    fable5 §5.1[缺失]/§7-2:检索实现变更字段结构时,下游必须能区分旧新
    格式;未知版本一律显式报错,不允许按旧结构静默解析。
    """

    def __init__(self, detail: dict | None = None):
        detail = detail or {}
        super().__init__(
            "检索产物 schema 版本未知:"
            f"{detail.get('schema_version')!r}(支持:"
            f"{list(SUPPORTED_RETRIEVAL_SCHEMA_VERSIONS)};"
            f"origin={detail.get('origin', '')})— fail-closed 拒绝解析")
        self.detail = detail


def validate_retrieval_payload(payload: dict, *,
                               origin: str = "retrieval") -> dict:
    """校验检索产物 envelope 的 schema 版本(消费端统一入口)。

    - 已知版本(v43-retrieval-1/2)→ 原样返回(只校验,不改写产物);
    - **缺失字段 → legacy 容忍**:早期产物与手工测试夹具无版本字段,按
      既有结构继续解析(旧 run 产物读取路径必须可用);
    - 未知版本 → ``RetrievalSchemaError``(明确异常,不静默解析)。
    """
    if not isinstance(payload, dict):
        raise RetrievalSchemaError({
            "schema_version": None, "origin": origin,
            "reason": "payload_not_dict"})
    version = payload.get("schema_version")
    if version is None:
        return payload  # legacy:无版本字段,按既有格式读取
    if version not in SUPPORTED_RETRIEVAL_SCHEMA_VERSIONS:
        raise RetrievalSchemaError({
            "schema_version": version, "origin": origin,
            "supported": list(SUPPORTED_RETRIEVAL_SCHEMA_VERSIONS)})
    return payload

# 类比来源适配(任务书 §1):注入 AnalogSourceResolver 后,检索卡按产物
# 身份做供体找回(映射模板/corpus_v1 溯源)并如实标注 mapping_status;
# 缺省不注入(单测快路径),此时卡标 unavailable:not_attempted。


@dataclass
class ReactionContext:
    """检索输入(任务书 §1.2:身份、run/path、按序祖先、条件)。"""

    run_id: str
    path_id: str
    substrate_smiles: str
    substrate_identity: str
    ancestry: list[dict] = field(default_factory=list)  # 根→当前的路径链记录
    conditions: dict | None = None                      # 环境条件(可空)


class ReactionFinder(Protocol):
    def find(self, ctx: ReactionContext) -> dict: ...


# ---------------------------------------------------------------- 真实实现


def _kind_for_source(source: str) -> str:
    s = (source or "").lower()
    if "eawag_lookup" in s:
        return EVIDENCE_KIND_RECORDED
    if "envipath" in s or "uspto" in s:
        return EVIDENCE_KIND_RULE
    return EVIDENCE_KIND_ANALOG


def _card_content_hash(card: dict) -> str:
    volatile = {"created_at", "_content_hash"}
    slim = {k: v for k, v in card.items() if k not in volatile}
    return content_hash(slim)


class EngineReactionFinder:
    """基于 V43Engine.expand_raw 的真实检索(只读,资产身份由引擎守卫)。

    ``analog_resolver`` 可选注入(真实工作流接线;任务书 §1):为预测块
    卡片执行供体找回与 mapping_status 标注。"""
    def __init__(self, engine, config, analog_resolver=None) -> None:
        self.engine = engine
        self.config = config
        self.analog_resolver = analog_resolver
        self._source_assets = self._build_source_assets()

    def _build_source_assets(self) -> dict[str, dict]:
        """证据类别 → 实际读取的资产文件(rel path + SHA256)。

        逐卡溯源的依据:recorded=引擎实际环境 lookup 库(identity block
        "library" = library/library_full.jsonl);envipath 规则=ENVIPATH_RULES;
        uspto 模板=TEMPLATES;语料检索=corpus_v1。路径取引擎装载后的实际值
        (相对资产根),哈希就地计算。
        """
        import os

        from ..adapters.asset_manifest import sha256_file

        root = str(self.config.assets_root)
        X = self.engine._X  # noqa: SLF001 — 服务层读取引擎装载事实
        entries = {
            "recorded": self.engine.identity_block["library_path"],
            "envipath": X.ENVIPATH_RULES,
            "uspto": X.TEMPLATES,
            "retrieval": self.engine.identity_block["corpus_v1_path"],
        }
        out: dict[str, dict] = {}
        for key, path in entries.items():
            out[key] = {
                "asset_file": os.path.relpath(str(path), root),
                "asset_sha256": sha256_file(path),
            }
        return out

    def _asset_refs(self) -> dict:
        # 与 run_identity.retrieval_asset_identity 同形状(清单校验口径);
        # 走引擎 identity_block 取 sha,避免每次检索重哈希 149MB 资产。
        from ..storage.run_identity import RECORDING_SOURCE_FILE

        assets = self.engine.asset_identity()["retrieval_assets"]
        library = assets.get("core_files", {}).get("library", {})
        return {
            "mode": "repo_assets",
            "assets_root": assets.get("assets_root"),
            "manifest_sha256": assets.get("manifest_sha256"),
            "n_manifest_files": assets.get("n_manifest_files"),
            "source_file": RECORDING_SOURCE_FILE,
            "source_file_sha256": library.get("sha256"),
        }

    @staticmethod
    def _pred_source_keys(source: str) -> list[str]:
        """预测边全部参与来源 → 资产映射键(按主来源优先排序)。

        组合来源(如 "envipath+retrieval")的每个成分都可能参与评分
        (p_envipath / p_retrieval),溯源必须逐个列出;主来源排首位。
        """
        s = (source or "").lower()
        keys: list[str] = []
        for token in [t for t in s.split("+") if t]:
            if "envipath" in token:
                key = "envipath"
            elif "uspto" in token:
                key = "uspto"
            else:
                key = "retrieval"
            if key not in keys:
                keys.append(key)
        return keys or ["retrieval"]

    def find(self, ctx: ReactionContext) -> dict:
        raw = self.engine.expand_raw(ctx.substrate_smiles, case_id=ctx.path_id)
        if "error" in raw:
            raise ValueError(
                f"引擎展开失败:{raw['error']}({ctx.substrate_smiles!r})"
            )
        merged = raw["merged_edges"]
        # 引擎原始顺序:merged 池 1..N;被合并去重的预测边(与 lookup 产物
        # 同分子)不进池,追加编号并如实挂牌,不冒充池内排名
        rank_of: dict[int, int] = {id(e): i + 1 for i, e in enumerate(merged)}
        extra_rank = len(merged)
        extra_pred: list[dict] = []
        for edge in raw["pred_edges"]:
            if id(edge) not in rank_of:
                extra_rank += 1
                rank_of[id(edge)] = extra_rank
                extra_pred.append(edge)

        cards: list[dict] = []
        # ---- lookup 块:按反应 ID 聚合(同一反应多产物 = 一张卡) ----
        by_reaction: dict[str, list[dict]] = {}
        for row in raw["lookup"]:
            for rid in row.get("eawag_reactions", []):
                by_reaction.setdefault(rid, []).append(row)
        for rid, rows in by_reaction.items():
            rows.sort(key=lambda r: rank_of[id(r)])
            products = []
            for pos, row in enumerate(rows):
                full = row.get("product_smiles_full") or row["product_smiles"]
                products.append({
                    "position": pos,
                    "product_smiles": row["product_smiles"],
                    "product_smiles_full": full,
                    "product_identity": cn_identity(full) or full,
                    "score": row.get("tanimoto", 0.0),
                    "score_semantics": "eawag_lookup_tanimoto",
                    "ion_filtered": row.get("ion_filtered", False),
                    "cofactor_filtered": row.get("cofactor_filtered", False),
                })
            rank = min(rank_of[id(r)] for r in rows)
            card = self._base_card(ctx, rank)
            card.update({
                "evidence_id": stable_id(
                    "E", ctx.run_id, ctx.path_id, "recorded", rid,
                    ctx.substrate_identity,
                    "\x00".join(p["product_identity"] for p in products),
                ),
                "source_id": rid,
                "kind": EVIDENCE_KIND_RECORDED,
                "match_type": "exact_donor_cn_match",
                "products": products,
                "score": max(p["score"] for p in products),
                "score_semantics": "eawag_lookup_tanimoto",
                "asset_file": self._source_assets["recorded"]["asset_file"],
                "asset_sha256": self._source_assets["recorded"]["asset_sha256"],
                "asset_sources": [dict(
                    {"role": "recorded"},
                    **self._source_assets["recorded"],
                )],
                "source_record": {
                    # 库名以实际读取文件为准(与 asset_file 同源,勿写死旧库名)
                    "library_file": self._source_assets["recorded"]["asset_file"],
                    "library_sha256": self._source_assets["recorded"]["asset_sha256"],
                    "btid": rid.split("#", 1)[0],
                    "reac_id": rid.split("#", 1)[1] if "#" in rid else rid,
                    "donor_exact_match": True,
                    "n_evidence": rows[0].get("n_evidence"),
                    "rows": [
                        {k: r.get(k) for k in (
                            "product_smiles", "tanimoto", "ion_filtered",
                            "cofactor_filtered", "filtered")}
                        for r in rows
                    ],
                },
            })
            card["_content_hash"] = _card_content_hash(card)
            cards.append(card)

        # ---- 预测块:规则模板 / 语料检索邻居 ----
        for edge in raw["pred_edges"]:
            kind = _kind_for_source(edge.get("source", ""))
            if kind == EVIDENCE_KIND_RECORDED:
                # 预测块来源即使字面含 lookup 也不是已记录反应(降格为规则)
                kind = EVIDENCE_KIND_RULE
            full = edge["product_smiles"]
            # 分数出处如实记录:优先透传引擎原始 score_semantics;缺席时
            # 声明数字实际取自哪个字段(edge_score / tanimoto),不统一糊成
            # 一个字符串
            score_field = (
                "edge_score" if edge.get("edge_score") is not None
                else "tanimoto"
            )
            score = float(edge.get(score_field) or 0.0)
            score_semantics = edge.get("score_semantics") or (
                f"engine_pred_edge_score:{score_field}"
            )
            products = [{
                "position": 0,
                "product_smiles": full,
                "product_smiles_full": full,
                "product_identity": cn_identity(full) or full,
                "score": score,
                "score_semantics": score_semantics,
            }]
            rank = rank_of[id(edge)]
            source_keys = self._pred_source_keys(edge.get("source", ""))
            primary = self._source_assets[source_keys[0]]
            asset_sources = [
                dict({"role": key}, **self._source_assets[key])
                for key in source_keys
            ]
            match_type = (
                "rule_template_application" if kind == EVIDENCE_KIND_RULE
                else "retrieval_neighbor_transfer"
            )
            mapping_fields = self._mapping_fields(card_ctx=ctx, product_identity=products[0]["product_identity"])
            card = self._base_card(ctx, rank)
            card.update({
                "evidence_id": stable_id(
                    "E", ctx.run_id, ctx.path_id, kind, edge.get("source", ""),
                    str(rank), products[0]["product_identity"],
                ),
                "source_id": edge.get("source", "") or "engine_pred",
                "kind": kind,
                "match_type": match_type,
                "products": products,
                "score": score,
                "score_semantics": score_semantics,
                "asset_file": primary["asset_file"],
                "asset_sha256": primary["asset_sha256"],
                # 组合来源逐成分溯源:p_envipath 与 p_retrieval 等都参与评分,
                # 每个成分的语料/规则文件与哈希都必须在卡上
                "asset_sources": asset_sources,
                # 类比来源适配字段(v43-retrieval-2):映射找回状态与供体引用
                **mapping_fields,
                "source_record": {
                    "engine_edge": {
                        k: edge.get(k) for k in (
                            "layer", "source", "v34_regime", "p_uspto",
                            "p_envipath", "p_retrieval", "tanimoto",
                            "edge_score", "score_semantics",
                            "ion_filtered", "wildcard_filtered",
                        )
                    },
                    "deduped_from_merged_pool": id(edge) in {id(e) for e in extra_pred},
                },
            })
            card["_content_hash"] = _card_content_hash(card)
            cards.append(card)

        cards.sort(key=lambda c: c["retrieval_rank"])
        return {
            "schema_version": RETRIEVAL_SCHEMA_VERSION,
            "created_at": now_iso(),
            "query": {
                "run_id": ctx.run_id,
                "path_id": ctx.path_id,
                "substrate_smiles": ctx.substrate_smiles,
                "substrate_identity": ctx.substrate_identity,
                "ancestry": ctx.ancestry,
            },
            "conditions": ctx.conditions,
            "evidences": cards,
            "retrieval_assets": self._asset_refs(),
            "engine_meta": {
                "case_id": ctx.path_id,
                "n_pred_candidates": raw["n_pred_candidates"],
                "n_lookup": raw["n_lookup"],
                "budget_cut": raw["budget_cut"],
                "pool_capped": raw["pool_capped"],
                "canonical_smiles": raw["canonical_smiles"],
            },
        }

    def _mapping_fields(self, card_ctx: ReactionContext,
                        product_identity: str) -> dict:
        """预测块卡片的 mapping 字段组(任务书 §1)。

        - 注入 resolver:按产物身份执行供体找回(resolved/ambiguous/
          unavailable + 原因),resolved 时带对齐后的映射模板;
        - 未注入:如实标注 unavailable:not_attempted(不编造映射)。
        recorded 卡不参与(已记录反应走确定性通路,无需映射)。
        """
        if self.analog_resolver is None:
            return {"donor_refs": [],
                    "mapping_status": "unavailable",
                    "mapping_reason": "not_attempted:no_resolver"}
        from .analog_source import build_card_mapping_fields

        return build_card_mapping_fields(
            self.analog_resolver, product_identity,
            card_ctx.substrate_identity,
        )

    @staticmethod
    def _base_card(ctx: ReactionContext, rank: int) -> dict:
        return {
            "evidence_id": "",
            "source_id": "",
            "kind": "",
            "query_identity": ctx.substrate_identity,
            "match_type": "",
            "reactant_smiles": ctx.substrate_smiles,
            "reactant_identity": ctx.substrate_identity,
            "products": [],
            # 本资产集无原生原子映射数据:显式 unavailable,不生成假映射
            # (v2 卡的找回状态由 _mapping_fields 就地覆盖)
            "atom_mapping": ATOM_MAPPING_UNAVAILABLE,
            "donor_refs": [],
            "mapping_status": "unavailable",
            "mapping_reason": "asset_has_no_native_mapping",
            # 本资产集无条件数据:不猜测环境相容,一律 unknown
            "condition_fit": CONDITION_UNKNOWN,
            "retrieval_rank": rank,
            "score": 0.0,
            "score_semantics": "",
            "source_record": {},
            "asset_file": "",
            "asset_sha256": "",
            "asset_sources": [],
            "run_id": ctx.run_id,
            "path_id": ctx.path_id,
            "created_at": now_iso(),
        }


class ScriptedReactionFinder:
    """测试夹具:按底物身份返回预设证据;可选跨进程调用计数(崩溃恢复用)。"""

    def __init__(
        self,
        scripted: dict[str, list[dict]] | None = None,
        counter_path: str | None = None,
        default_empty: bool = True,
    ) -> None:
        self.scripted = scripted or {}
        self.counter_path = counter_path
        self.default_empty = default_empty

    def find(self, ctx: ReactionContext) -> dict:
        if self.counter_path is not None:
            from pathlib import Path

            p = Path(self.counter_path)
            n = int(p.read_text()) if p.exists() else 0
            p.write_text(str(n + 1))
        cards = []
        for i, ev in enumerate(self.scripted.get(ctx.substrate_identity, []), 1):
            card = dict(ev)
            card.setdefault("evidence_id", stable_id("E", "scripted", str(i)))
            card.setdefault("query_identity", ctx.substrate_identity)
            card.setdefault("reactant_identity", ctx.substrate_identity)
            card.setdefault("retrieval_rank", i)
            card.setdefault("atom_mapping", ATOM_MAPPING_UNAVAILABLE)
            # v2 字段:scripted 卡可自带 donor_refs/mapping_status(透传),
            # 缺省 unavailable(不编造)
            card.setdefault("donor_refs", [])
            card.setdefault("mapping_status", "unavailable")
            card.setdefault("mapping_reason", "not_declared_by_fixture")
            card.setdefault("condition_fit", CONDITION_UNKNOWN)
            card.setdefault("run_id", ctx.run_id)
            card.setdefault("path_id", ctx.path_id)
            card.setdefault("created_at", now_iso())
            card["_content_hash"] = _card_content_hash(card)
            cards.append(card)
        if not cards and not self.default_empty:
            raise KeyError(f"脚本检索无预设证据:{ctx.substrate_identity}")
        return {
            "schema_version": RETRIEVAL_SCHEMA_VERSION,
            "created_at": now_iso(),
            "query": {
                "run_id": ctx.run_id,
                "path_id": ctx.path_id,
                "substrate_smiles": ctx.substrate_smiles,
                "substrate_identity": ctx.substrate_identity,
                "ancestry": ctx.ancestry,
            },
            "conditions": ctx.conditions,
            "evidences": cards,
            "retrieval_assets": {"manifest_sha256": "scripted-fixture"},
            "engine_meta": {"case_id": ctx.path_id},
        }
