"""PPV1 S5b 池层逐候选谱系诊断(T1a,s5b-pool-policy-6)—— 正/负控
(公共链;零网络、零金标、合成夹具与真实 298 题面零重叠)。

- 正控:每候选一行(pool_diagnostics.candidates)四态全覆盖 ——
  compiled(三通道)/compile_rejected(拒因短码)/merged_into(指向
  幸存 key)/pool_truncated(截断前排序位);
- 闭合:compile_failure_histogram 逐 reason 行数闭合、
  merged_source_keys 逐 key 闭合、截断计数 = n_unique_net_reactions
  − n_pool_returned 闭合;
- 不变量:run_inputs 字节等价(plan.pools 冻结内容零变化;诊断不进
  run_inputs)、判分/worker 对新 manifest 白名单消费正常、版本
  s5b-pool-policy-5 → s5b-pool-policy-6;
- 负控:既有聚合字段键集与语义零变化(candidates 纯追加);行
  schema 七键精确(null 位次按 outcome 严格)。
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.pollutant.recorded_source import (  # noqa: E402
    reset_corpus_cache,
    reset_library_cache,
)
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    S5B_POOL_POLICY_VERSION,
    build_question_batch,
    default_pool_provider,
)
from pathway_v43.pollutant.s5b_scoring import (  # noqa: E402
    score_s5b_batch,
)
from pathway_v43.pollutant.s5b_worker import (  # noqa: E402
    manifest_provider_kind,
)

# ---------------------------------------------------------------- 夹具

_SUB = "CCO"  # 乙醇(合成小分子,与真实 298 金标零重叠)


def _rhea_row(rid, mid, direction, donor_a, comps, product_b, pcomps):
    """合成 corpus_v1 行(cosub_d2 同款;与真实语料零重叠)。"""
    return {
        "atom_mapping": None, "direction": direction,
        "donor_A_smiles": donor_a, "donor_components": comps,
        "ec": None, "mapping_status": "absent", "master_id": mid,
        "parse_note": "rxn-parsed", "product_B_smiles": product_b,
        "product_components": pcomps, "provenance_sha256": "f" * 64,
        "reaction_smiles": f"{donor_a}>>{product_b}",
        "record_id": rid, "source_id": rid, "source_type": "rhea",
    }


def _eawag_row(reac_id: str, product: str) -> dict:
    """合成 EAWAG 库行(w23456 W2 同款;donor=乙醇)。"""
    return {"btid": "btX", "donor_id": "CCO", "donor_smiles": "CCO",
            "package": "SYNTH", "product_sb": product,
            "product_smiles": product, "reac_id": reac_id}


class _LineageEngine:
    """EAWAG library + corpus_v1 双身份桩(identity_block + expand_raw;
    w23456 _FakeEngine 与 cosub_d2 _CorpusEngine 合体)。"""

    def __init__(self, tmp: Path, lib_rows: list[dict],
                 corpus_rows: list[dict]):
        self._tmpdir = Path(tempfile.mkdtemp(
            prefix="t1a-lineage-", dir=str(tmp)))
        lib = self._tmpdir / "library_full.jsonl"
        lib.write_text(
            "\n".join(json.dumps(r) for r in lib_rows) + "\n",
            encoding="utf-8")
        corpus = self._tmpdir / "corpus_v1.jsonl"
        corpus.write_text(
            "\n".join(json.dumps(r) for r in corpus_rows) + "\n",
            encoding="utf-8")
        self.identity_block = {
            "library_path": str(lib),
            "library_sha256": hashlib.sha256(
                lib.read_bytes()).hexdigest(),
            "corpus_v1_path": str(corpus),
            "corpus_v1_sha256": hashlib.sha256(
                corpus.read_bytes()).hexdigest(),
        }

    def expand_raw(self, smiles: str, case_id: str = "c") -> dict:
        rows: list[dict] = []
        seen: set[str] = set()
        for line in Path(
                self.identity_block["library_path"]).read_text(
                encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record["donor_smiles"] != smiles:
                continue
            rid = f"{record['btid']}#{record['reac_id']}"
            if rid in seen:
                continue
            seen.add(rid)
            rows.append({
                "product_smiles": record["product_smiles"],
                "product_smiles_full": record["product_smiles"],
                "source": "eawag_lookup", "layer": "lookup",
                "eawag_reactions": [rid], "donor_exact_match": True,
                "n_evidence": 1, "tanimoto": 1.0,
                "ion_filtered": False, "cofactor_filtered": False,
                "filtered": False,
            })
        return {"lookup": rows, "pred_edges": [], "merged_edges": rows,
                "n_pred_candidates": 0, "n_lookup": len(rows),
                "budget_cut": False, "pool_capped": False,
                "canonical_smiles": smiles}


class _Ref:
    """类比模板检索行桩(w23456 W4 同款)。"""

    def __init__(self, rid, lhs, rhs, cen, sim):
        self.record_id = rid
        self.mapped_lhs = lhs
        self.mapped_rhs = rhs
        self.center_atoms = cen
        self.similarity = sim


def _patch_analog(monkeypatch, refs: list[_Ref]) -> None:
    """注入模板检索桩(builder 内 deferred import,patch 模块属性)。"""
    import pathway_v43.services.analog_source as analog_source

    class _Resolver:
        def __init__(self, config):
            pass

        def templates_similar_to(self, substrate, *, threshold, top_k):
            return list(refs)[:top_k]

    original = analog_source.AnalogSourceResolver

    class _Patched(_Resolver, original):  # type: ignore[misc]
        def __init__(self, config):
            _Resolver.__init__(self, config)

    monkeypatch.setattr(
        analog_source, "AnalogSourceResolver", _Patched)


# 三通道满配夹具:EAWAG(CC=O / CC(=O)O / 苯环必拒)+ corpus(乙酸
# 整串,与 EAWAG CC(=O)O 同净反应 ⇒ 跨通道合并)+ analog(加氧 unique
# / charge 必拒 / 含 N 模板 pregate 必拒)
def _full_lib_rows() -> list[dict]:
    return [_eawag_row("r0001", "CC=O"),
            _eawag_row("r0002", "CC(=O)O"),
            _eawag_row("r0003", "c1ccccc1")]


def _full_corpus_rows() -> list[dict]:
    return [_rhea_row("rhea:91001", "91000", "LR", "CCO", ["CCO"],
                      "CC(=O)O", ["CC(=O)O"])]


def _full_refs() -> list[_Ref]:
    return [
        _Ref("oxi", "[CH3:1][CH2:2][OH:3]",
             "[CH3:1][CH2:2][O:3][OH:4]", [3], 0.9),
        _Ref("bad1", "[CH3:1][CH2:2][OH:3]",
             "[CH3:1][CH2:2][O-:3]", [2, 3], 0.8),
        _Ref("noal", "[CH3:1][NH2:2]", "[CH3:1][NH3:2]", [2], 0.7),
    ]


def _full_provider(tmp_path, monkeypatch, *, max_pool: int = 8):
    engine = _LineageEngine(
        tmp_path, _full_lib_rows(), _full_corpus_rows())
    _patch_analog(monkeypatch, _full_refs())
    return default_pool_provider(
        object(), engine=engine, max_pool=max_pool,
        min_unique_targets=1)


@pytest.fixture(autouse=True)
def _clean_caches():
    reset_library_cache()
    reset_corpus_cache()
    yield
    reset_library_cache()
    reset_corpus_cache()


# ================================================================ 正控


def test_compiled_rows_all_channels(tmp_path, monkeypatch) -> None:
    """正控:编译成功候选 —— 三通道各出 outcome=compiled 行,
    channel/record_key/pool_rank/signature_head 在位,null 位次正确。"""
    provider = _full_provider(tmp_path, monkeypatch)
    specs = provider(_SUB)
    rows = provider.last_diagnostics["candidates"]
    by_outcome: dict[str, list[dict]] = {}
    for row in rows:
        by_outcome.setdefault(row["outcome"], []).append(row)
    compiled = by_outcome["compiled"]
    # 3 独特净反应(EAWAG×2 + analog;corpus 同净反应被并)全入池
    # (max_pool=8 不截断)
    assert len(compiled) == len(specs) == 3
    # recorded 行:EAWAG 候选 record_id 定位;池序首位
    rec = next(r for r in compiled if r["channel"] == "recorded")
    assert rec["record_key"] == "btX#r0001"
    assert rec["pool_rank"] == 1
    assert isinstance(rec["signature_head"], list) and rec["signature_head"]
    assert all(isinstance(t, str) and t for t in rec["signature_head"])
    assert rec["reason"] is None and rec["merged_into"] is None
    # 幸存 spec key 规则(rec-<record_id>)与行可互定位
    assert specs[0]["key"] == f"rec-{rec['record_key']}"
    # corpus 行:整串候选严格身份 == 底物 ⇒ 编译成功入池(池序第二;
    # 与 EAWAG CC(=O)O 同净反应者被并,见 merged 用例 —— 此处唯一
    # compiled corpus 行定位键为行级 record_key)
    # analog 行:tpl key 定位;签名头来自净反应签名(加氧产物)
    ana = next(r for r in compiled if r["channel"] == "analog")
    assert ana["record_key"] == "tpl-oxi"
    assert ana["pool_rank"] == 3
    assert ana["signature_head"] == ["CCOO"]
    assert ana["reason"] is None and ana["merged_into"] is None


def test_compile_rejected_rows_close_with_histogram(
        tmp_path, monkeypatch) -> None:
    """正控:编译失败候选 —— outcome=compile_rejected + reason 短码;
    与聚合计数闭合(histogram 每 reason 计数 = 同 reason 行数)。"""
    provider = _full_provider(tmp_path, monkeypatch)
    provider(_SUB)
    diag = provider.last_diagnostics
    rows = diag["candidates"]
    rejects = [r for r in rows if r["outcome"] == "compile_rejected"]
    assert len(rejects) == 3
    per_reason = Counter(r["reason"] for r in rejects)
    hist = diag["compile_failure_histogram"]
    # 闭合:直方图逐 reason 计数 == 同 reason 行数(双向)
    assert dict(per_reason) == dict(hist)
    assert sum(hist.values()) == len(rejects)
    # 拒因短码逐项在位(三通道 × 三拒因面)
    keys = {(r["channel"], r["reason"]) for r in rejects}
    assert ("recorded", "no_structure_correspondence") in keys
    # T-E/E1a(s5b-pool-policy-9):bad1 模板 rhs 的 [O-:3] 阴离子经
    # 记录侧形式归一(Uncharger 逐组分;实跑短路)被中和 ⇒ 变换消失
    # ⇒ 拒因由 charge_edit_unsupported 迁移为 transform_no_change
    # (仍拒、仍不入池;归一事件 applied 随行披露 —— 理由迁移,结局
    # 不变;map 号在归一输出中逐原子保留)。
    assert ("analog", "transform_no_change") in keys
    bad1 = next(r for r in rejects if r["record_key"] == "tpl-bad1")
    assert bad1["record_side_form_norm"] == "applied"
    trace = bad1["record_side_form_norm_trace"]
    assert trace["status"] == "applied"
    assert trace["source_ref"]["channel"] == "analog"
    assert trace["source_ref"]["record_key"] == "tpl-bad1"
    assert trace["changes"] and trace["atom_correspondence"]
    # T-G C2(R2',2026-10-19):F1 拒候选的拒因口径——旧 pregate 恒记
    # no_alignment(不编译);R2' 起 F5 不过面维持 no_alignment、
    # F5 defer(坏模板/空中心/截断)转编译层如实出因。本夹具的
    # 「含 N 模板」rhs 不可解析 ⇒ 真实拒因 rhs_unparseable(理由
    # 迁移、结局不变:仍拒、仍不入池)。
    assert ("analog", "rhs_unparseable") in keys
    for row in rejects:
        assert row["merged_into"] is None
        assert row["pool_rank"] is None
        assert row["signature_head"] is None


def test_merged_into_rows_close_with_merged_source_keys(
        tmp_path, monkeypatch) -> None:
    """正控:被合并候选 —— outcome=merged_into + 指向幸存 key;与
    幸存者 merged_source_keys 闭合(跨通道同净反应亦并)。"""
    provider = _full_provider(tmp_path, monkeypatch)
    specs = provider(_SUB)
    diag = provider.last_diagnostics
    rows = diag["candidates"]
    merged = [r for r in rows if r["outcome"] == "merged_into"]
    # corpus 整串 CC(=O)O 与 EAWAG r0002 同净反应 ⇒ 并入幸存者
    assert len(merged) == 1
    row = merged[0]
    assert row["channel"] == "corpus"
    assert row["merged_into"] == "rec-btX#r0002"
    assert row["pool_rank"] is None and row["reason"] is None
    assert row["signature_head"] is None  # 行 schema:仅 compiled 非空
    # 闭合:幸存者 merged_source_keys 逐 key 与 merged 行可互定位
    # (被并 key 本就不在幸存池中 —— 合并语义本身)
    survivor = next(s for s in specs if s["key"] == "rec-btX#r0002")
    msk = survivor["compile"]["merged_source_keys"]
    assert msk == [f"rec-{row['record_key']}"]
    assert row["merged_into"] in [s["key"] for s in specs]
    # 池槽不被被并候选重复占据
    assert diag["n_unique_net_reactions"] == 3


def test_pool_truncated_rows_close_with_counts(
        tmp_path, monkeypatch) -> None:
    """正控:池宽截断候选 —— outcome=pool_truncated + 截断前排序位
    (1 基)> max_pool;计数 = n_unique_net_reactions − n_pool_returned。"""
    provider = _full_provider(tmp_path, monkeypatch, max_pool=2)
    specs = provider(_SUB)
    diag = provider.last_diagnostics
    assert len(specs) == diag["n_pool_returned"] == 2
    rows = diag["candidates"]
    trunc = [r for r in rows if r["outcome"] == "pool_truncated"]
    assert len(trunc) == (diag["n_unique_net_reactions"]
                          - diag["n_pool_returned"]) == 1
    row = trunc[0]
    assert row["channel"] == "analog" and row["record_key"] == "tpl-oxi"
    assert row["pool_rank"] == 3 > 2
    assert row["reason"] is None and row["merged_into"] is None
    assert row["signature_head"] is None  # 行 schema:仅 compiled 非空
    # 幸存者位次 1..max_pool 连续
    ranks = sorted(r["pool_rank"] for r in rows
                   if r["outcome"] == "compiled")
    assert ranks == [1, 2]


# ================================================================ 不变量


def test_manifest_compatible_with_worker_and_scoring(
        tmp_path, monkeypatch) -> None:
    """不变量:判分/worker 对新 manifest 白名单消费正常 —— 未知追加
    字段(candidates)不拒;批条目含 candidates 行且判分聚合可产出。"""
    provider = _full_provider(tmp_path, monkeypatch)
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps({
        "qid": "T1A-Q001", "substrate_smiles": _SUB,
        "products_smiles": ["CC=O"]}) + "\n", encoding="utf-8")
    manifest = build_question_batch(
        questions, tmp_path / "batch", batch_tag="t1a-compat",
        pool_provider=provider, provider_kind="scripted",
        synthetic_review=True)
    entry = manifest["entries"][0]
    rows = entry["pool_diagnostics"]["candidates"]
    assert rows and all("outcome" in r for r in rows)
    # worker 面:manifest_provider_kind 白名单取字段正常
    assert manifest_provider_kind(
        tmp_path / "batch" / "batch_manifest.json") == "scripted"
    # 判分面:score_s5b_batch 装载新 manifest(合成 scope;失败题留
    # 分母路径)——不因 candidates 追加字段拒
    agg = score_s5b_batch(
        tmp_path / "batch", runs_root=tmp_path / "runs",
        data_scope="synthetic_rule_level")
    assert agg["denominator"] == 1


def test_run_inputs_byte_equivalent_and_free_of_diagnostics(
        tmp_path, monkeypatch) -> None:
    """不变量:同输入 build 两次 —— run_inputs/plan.pools 冻结内容
    逐字节一致;诊断行只进 batch_manifest,不进 run_inputs。"""
    questions = tmp_path / "questions.jsonl"
    questions.write_text(json.dumps({
        "qid": "T1A-Q001", "substrate_smiles": _SUB,
        "products_smiles": ["CC=O"]}) + "\n", encoding="utf-8")
    manifests = []
    input_bytes = []
    for i in range(2):
        provider = _full_provider(tmp_path, monkeypatch)
        manifest = build_question_batch(
            questions, tmp_path / f"batch{i}", batch_tag="t1a-byte",
            pool_provider=provider, provider_kind="scripted",
            synthetic_review=True)
        manifests.append(manifest)
        input_bytes.append(
            (tmp_path / f"batch{i}" / "run_inputs" /
             "T1A-Q001.json").read_bytes())
    assert input_bytes[0] == input_bytes[1]
    assert b"pool_diagnostics" not in input_bytes[0]
    assert b"candidates" not in input_bytes[0]
    run_input = json.loads(input_bytes[0].decode("utf-8"))
    provider = _full_provider(tmp_path, monkeypatch)
    pools_fresh = {_SUB: provider(_SUB)}
    # 冻结内容 = provider 产出 spec 序列(结构等价,与两次 build 一致)
    assert run_input["plan"]["pools"] == json.loads(json.dumps(
        {k: [{kk: vv for kk, vv in s.items()} for s in v]
         for k, v in pools_fresh.items()}))


def test_pool_policy_version_bumped() -> None:
    """不变量:版本承载 —— 池诊断从聚合升为逐候选 ⇒ 语义化升版
    s5b-pool-policy-5 → s5b-pool-policy-6;C 线(2026-10-14)池成员
    变化(analog 共底物伴生供给)⇒ s5b-pool-policy-7。"""
    # T-G C2(2026-10-19):重刀 R2' 路由/准入解耦接线 + s5b-compiler-4 中心锚定对齐(池成员变化)⇒ 8
    # T-E/E1a(2026-10-19):记录侧形式归一(池成员/诊断面变化;路由
    # 算法未改但路由结果可变)⇒ 9
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-9"
    assert S5B_POOL_POLICY_VERSION != "s5b-pool-policy-5"


# ================================================================ 负控


_ROW_SCHEMA_KEYS = {"channel", "record_key", "outcome", "reason",
                    "merged_into", "pool_rank", "signature_head",
                    # T-G C2(R2',s5b-pool-policy-8)追加路由/准入五键
                    # (行 schema v2;非 analog 通道行为 None)
                    "route", "execution_input_source",
                    "execution_input_sha256", "f5",
                    "light_gap_coverable_by_bag",
                    # T-E/E1a(s5b-pool-policy-9):逐候选归一三值 +
                    # 原子级 trace(全形态行;审计字段单独验收)
                    "record_side_form_norm", "record_side_form_norm_trace"}

# 既有无条件聚合键(s5b-pool-policy-5 时代已在;candidates 之外零新增)
_PREEXISTING_AGGREGATE_KEYS = {
    "pool_policy_version", "n_recorded_strict_exact",
    "n_recorded_cn_candidate", "n_corpus_strict_exact",
    "n_corpus_cn_candidate", "n_cosubstrate_declared_specs",
    "cosubstrate_pool_labels", "n_analog_compiled",
    "n_unique_net_reactions", "n_pool_returned",
    "compile_failure_histogram", "candidates"}


def test_aggregate_fields_unchanged_and_row_schema(
        tmp_path, monkeypatch) -> None:
    """负控:既有 pool_diagnostics 聚合键与语义零变化(candidates 纯
    追加);行 schema 七键精确,null 位次按 outcome 严格;聚合与行
    四态计数全闭合。"""
    provider = _full_provider(tmp_path, monkeypatch, max_pool=2)
    specs = provider(_SUB)
    diag = provider.last_diagnostics
    # 聚合键集:既有键全在;新增键只有 candidates(条件键如实,不裁剪)
    # s5b-pool-policy-7(C 线,2026-10-14)追加 analog_cosub_supply_*
    # 计数(向后兼容追加;既有键与语义零变化)
    assert _PREEXISTING_AGGREGATE_KEYS <= set(diag)
    assert set(diag) - _PREEXISTING_AGGREGATE_KEYS <= {
        "recorded_diagnostics", "corpus_diagnostics",
        "analog_threshold", "analog_threshold_dropped",
        "analog_pregate_skipped",
        "analog_cosub_supply_version",
        "analog_cosub_supply_rescued",
        "analog_cosub_supply_compile_attempted",
        "analog_cosub_supply_wildcard_blocked",
        # T-G C2(2026-10-19):R2' 路由真源版本 + F5 中心准入计数
        # (向后兼容追加;既有键与语义零变化)
        "analog_route_truth_version",
        "analog_center_admission_checked",
        "analog_center_admission_skipped",
        "analog_center_admission_deferred",
        # T-E/E1a(2026-10-19,s5b-pool-policy-9):记录侧形式归一
        # 批级机读绑定(版本+指纹+路由绑定注记+覆盖限制披露)
        "record_side_form_norm_version",
        "record_side_form_norm_param_sha256",
        "record_side_form_norm_route_binding_note",
        "record_side_form_norm_coverage_limitation",
        # P3-IDENT(D1.2 二轮复审登记,T-H 前置 2026-10-20):批级
        # 活编译器版本键(向后兼容追加;既有键与语义零变化)
        "compiler_version"}
    assert diag["pool_policy_version"] == S5B_POOL_POLICY_VERSION
    assert diag["compiler_version"] == "s5b-compiler-6"
    rows = diag["candidates"]
    assert rows
    for row in rows:
        # 行 schema:十二键精确,无多余键(T-G C2 起 v2 五键追加)
        assert set(row) == _ROW_SCHEMA_KEYS
        assert row["outcome"] in ("compiled", "compile_rejected",
                                  "merged_into", "pool_truncated")
        # null 位次按 outcome 严格(schema §3.1)
        if row["outcome"] == "compiled":
            assert row["reason"] is None
            assert row["merged_into"] is None
            assert isinstance(row["pool_rank"], int)
            assert isinstance(row["signature_head"], list)
        elif row["outcome"] == "compile_rejected":
            assert isinstance(row["reason"], str) and row["reason"]
            assert row["merged_into"] is None
            assert row["pool_rank"] is None
            assert row["signature_head"] is None
        elif row["outcome"] == "merged_into":
            assert row["reason"] is None
            assert isinstance(row["merged_into"], str)
            assert row["pool_rank"] is None
            assert row["signature_head"] is None
        else:  # pool_truncated
            assert row["reason"] is None
            assert row["merged_into"] is None
            assert isinstance(row["pool_rank"], int)
            assert row["pool_rank"] > 2
            assert row["signature_head"] is None
    # 聚合语义与行四态逐项闭合(诊断升级不自坏)
    compiled = [r for r in rows if r["outcome"] == "compiled"]
    truncated = [r for r in rows if r["outcome"] == "pool_truncated"]
    rejected = [r for r in rows if r["outcome"] == "compile_rejected"]
    merged = [r for r in rows if r["outcome"] == "merged_into"]
    assert diag["n_pool_returned"] == len(compiled) == len(specs)
    assert diag["n_unique_net_reactions"] == len(compiled) + len(truncated)
    assert Counter(r["reason"] for r in rejected) == Counter(
        diag["compile_failure_histogram"])
    msk_all = [k for s in specs
               for k in (s.get("compile") or {}).get(
                   "merged_source_keys") or []]
    assert len(msk_all) == len(merged)
    assert sorted(msk_all) == sorted(
        ("rec-" + r["record_key"]) if r["channel"] in
        ("recorded", "corpus") else r["record_key"] for r in merged)
    # 行序 = 候选产出序(recorded → corpus → analog;通道内检索序)
    channels = [r["channel"] for r in rows]
    assert channels == sorted(
        channels, key=lambda c: {"recorded": 0, "corpus": 1,
                                 "analog": 2}[c])
