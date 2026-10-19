"""PPV1 S5b T-E/E1a —— 记录侧形式归一测试族(record-side-formnorm-1 /
s5b-pool-policy-9;零网络、零金标、合成夹具与真实 298 题面零重叠)。

依据:FROZEN_V3 §5(C-1/C-5)+ 设计稿 v2 §1.1/§1.3/§4 + Codex 二轮
复审 §4.1/§4.2/§4.3(最终口径)。断言族:

- 算子:实跑短路(非 canonical no-op 原串直通)/ 幂等双遍(成功域
  字节固定点 + failed 域重现)/ 失败直通(all-or-nothing 全回原始)/
  组分序与重复份数 / **map 号保留逐行断言** / 实测三默认参数存在性 /
  H 分列(显式/隐式/邻接 H 原子含同位素,D 不当普通 H);
- 注入点:recorded(compile 入口)/ corpus(分类前统一消费视体,贯穿
  分类→编译→装配→NC-10 两处声明)/ analog(for-ref 起点视体,raw ref
  不得传编译;record_equation 保 raw);
- 披露:三值标量(全形态行)/ trace schema 逐字段(source_ref/
  changes/atom_correspondence/H 分列)/ matching_scope /
  intersection / risk_status 四值含 unknown 禁伪填 / applied 五键
  条件性 / 未 applied spec 零字节 / trace_ref 回指诊断行;
- 嵌套:首次 applied→二遍 no-op 不覆盖(局部 not_applicable 不移除
  证明域)/ 父事务 failed→子集 compile 不得重新授权。
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rdkit import Chem  # noqa: E402
from rdkit.Chem.MolStandardize import rdMolStandardize  # noqa: E402

from pathway_v43.domain.identity import cn_identity  # noqa: E402

from pathway_v43.pollutant.recorded_source import (  # noqa: E402
    RECORD_SIDE_FORMNORM_PARAM_SHA256,
    RECORD_SIDE_FORMNORM_VERSION,
    RECORDED_SOURCE_VERSION,
    compile_recorded_reaction,
    find_recorded_exact,
    normalize_record_side_smiles,
    normalize_record_side_transaction,
    record_side_form_norm_trace_ref,
    reset_corpus_cache,
    reset_library_cache,
)
from pathway_v43.pollutant.s5b_builder import (  # noqa: E402
    S5B_POOL_POLICY_VERSION,
    default_pool_provider,
)

_SPEC_KEYS = {"record_side_form_norm", "record_side_form_norm_version",
              "record_side_form_norm_param_sha256",
              "record_side_form_norm_trace_ref", "verification_domain"}

_SUB = "CCO"  # 乙醇(合成小分子)


def _eawag_row(reac_id: str, donor: str, product: str) -> dict:
    return {"btid": "btX", "donor_id": donor, "donor_smiles": donor,
            "package": "SYNTH", "product_sb": product,
            "product_smiles": product, "reac_id": reac_id}


def _rhea_row(rid, mid, direction, donor_a, comps, product_b, pcomps,
              rxn=None):
    return {
        "atom_mapping": None, "direction": direction,
        "donor_A_smiles": donor_a, "donor_components": comps,
        "ec": None, "mapping_status": "absent", "master_id": mid,
        "parse_note": "rxn-parsed", "product_B_smiles": product_b,
        "product_components": pcomps, "provenance_sha256": "f" * 64,
        "reaction_smiles": rxn or f"{donor_a}>>{product_b}",
        "record_id": rid, "source_id": rid, "source_type": "rhea",
    }


class _Engine:
    """EAWAG library + corpus_v1 双身份桩(合成;零真实资产)。"""

    def __init__(self, tmp: Path, lib_rows: list[dict],
                 corpus_rows: list[dict]):
        self._tmpdir = Path(tempfile.mkdtemp(prefix="te-fn-", dir=str(tmp)))
        lib = self._tmpdir / "library_full.jsonl"
        lib.write_text("\n".join(json.dumps(r) for r in lib_rows) + "\n",
                       encoding="utf-8")
        corpus = self._tmpdir / "corpus_v1.jsonl"
        corpus.write_text("\n".join(json.dumps(r) for r in corpus_rows)
                          + "\n", encoding="utf-8")
        self.identity_block = {
            "library_path": str(lib),
            "library_sha256": hashlib.sha256(lib.read_bytes()).hexdigest(),
            "corpus_v1_path": str(corpus),
            "corpus_v1_sha256": hashlib.sha256(
                corpus.read_bytes()).hexdigest(),
        }

    def expand_raw(self, smiles: str, case_id: str = "c") -> dict:
        rows = []
        seen = set()
        for line in Path(
                self.identity_block["library_path"]).read_text(
                encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record["donor_smiles"] != smiles and \
                    cn_identity(record["donor_smiles"]) != \
                    cn_identity(smiles):
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
                "filtered": False})
        return {"lookup": rows, "pred_edges": [], "merged_edges": rows,
                "n_pred_candidates": 0, "n_lookup": len(rows),
                "budget_cut": False, "pool_capped": False,
                "canonical_smiles": smiles}


class _Ref:
    def __init__(self, rid, lhs, rhs, cen, sim, asset_sha256="a" * 64):
        self.record_id = rid
        self.mapped_lhs = lhs
        self.mapped_rhs = rhs
        self.center_atoms = cen
        self.similarity = sim
        self.asset_sha256 = asset_sha256


def _patch_analog(monkeypatch, refs: list[_Ref]) -> None:
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

    monkeypatch.setattr(analog_source, "AnalogSourceResolver", _Patched)


@pytest.fixture(autouse=True)
def _clean_caches():
    reset_library_cache()
    reset_corpus_cache()
    yield
    reset_library_cache()
    reset_corpus_cache()


# ================================================================ 算子


def test_operator_short_circuit_verbatim() -> None:
    """短路:实跑算子后状态未变 ⇒ not_applicable 且原串逐字节直通
    (非 canonical 输入不得被重序列化)。"""
    for smi in ("C(C)O", "OCC", "CC(=O)O", "c1ccccc1"):
        r = normalize_record_side_smiles(smi)
        assert r["status"] == "not_applicable"
        assert r["normalized"] == smi
        assert r["changes"] == [] and r["atom_correspondence"] == []


def test_operator_applied_and_atom_detail() -> None:
    """applied:q/H 分列(总 H 口径 GetTotalNumHs(includeNeighbors=True);
    显式/隐式/邻接 H 原子含同位素)—— D 不当普通 H。"""
    r = normalize_record_side_smiles("[2H][N-]C")
    assert r["status"] == "applied"
    assert r["normalized"] == "[2H]NC"
    ch = r["changes"][0]
    assert ch["source_atom_index"] == 1
    assert ch["charge_before"] == -1 and ch["charge_after"] == 0
    assert ch["hydrogen_detail"]["definition"] == (
        "GetTotalNumHs(includeNeighbors=True)")
    nb_before = ch["hydrogen_detail"]["neighbor_h_before"]
    assert {"idx": 0, "isotope": 2} in nb_before
    # 参数指纹入批(常量已登记 + 64 hex)
    assert RECORD_SIDE_FORMNORM_VERSION == "record-side-formnorm-1"
    assert len(RECORD_SIDE_FORMNORM_PARAM_SHA256) == 64
    assert RECORDED_SOURCE_VERSION == "s5b-recorded-source-4"
    assert S5B_POOL_POLICY_VERSION == "s5b-pool-policy-9"


def test_operator_measured_default_params_exist() -> None:
    """实测三默认参数存在性(canonicalOrder/force/protonationOnly)+
    实例不可自省单列 + neutralize 关键字被拒(不得出现在代码)。"""
    doc = inspect.getdoc(rdMolStandardize.Uncharger) or ""
    sig = str(getattr(rdMolStandardize.Uncharger, "__init__", ""))
    text = doc + sig + str(getattr(
        rdMolStandardize.Uncharger.__init__, "__doc__", ""))
    for name in ("canonicalOrder", "force", "protonationOnly"):
        assert name in text
    u = rdMolStandardize.Uncharger()
    for attr in ("canonicalOrder", "force", "protonationOnly"):
        assert not hasattr(u, attr)
    with pytest.raises(Exception):
        rdMolStandardize.Uncharger(neutralize=True)  # type: ignore[call-arg]
    from pathway_v43.pollutant.recorded_source import (
        _RECORD_SIDE_FORMNORM_PARAM_SPEC,
    )
    defaults = _RECORD_SIDE_FORMNORM_PARAM_SPEC[
        "constructor_defaults_from_signature"]
    assert defaults == {"canonicalOrder": True, "force": False,
                        "protonationOnly": False}
    assert _RECORD_SIDE_FORMNORM_PARAM_SPEC[
        "instance_introspection"] == "unavailable"


def test_operator_idempotent_double_pass_and_failed_domain() -> None:
    """幂等:成功域双遍字节固定点;failed 域确定性重现且原串不变。"""
    applied = normalize_record_side_smiles("[O-]C(=O)C")
    assert applied["status"] == "applied"
    second = normalize_record_side_smiles(applied["normalized"])
    assert second["status"] == "not_applicable"
    assert second["normalized"] == applied["normalized"]
    bad = normalize_record_side_smiles("C1CC1[XXX")
    assert bad["status"] == "failed"
    assert bad["normalized"] == "C1CC1[XXX"
    assert normalize_record_side_smiles(bad["normalized"])["status"] == (
        "failed")
    # 内盐永久电荷:applied 允许保留电荷;二遍 no-op
    inner = normalize_record_side_smiles(
        "[O-]C(=O)C.C[N+](C)(C)CC([O-])=O")
    assert inner["status"] == "applied"
    assert "+" in inner["normalized"] or "-" in inner["normalized"]
    assert normalize_record_side_smiles(
        inner["normalized"])["status"] == "not_applicable"


def test_transaction_all_or_nothing_and_order_fidelity() -> None:
    """事务 all-or-nothing:任一分量失败 ⇒ 全部回原始;组分序与重复
    份数保输入序(不跨组分排序)。"""
    tx = normalize_record_side_transaction([
        {"side": "lhs", "field": "donor_smiles", "entry_index": 0,
         "smiles": "[O-]C(=O)C"},
        {"side": "rhs", "field": "products", "entry_index": 0,
         "smiles": "C1CC1[XXX"}])
    assert tx["status"] == "failed"
    assert tx["reason"] == "component_unparseable"
    assert tx["values"] == ["[O-]C(=O)C", "C1CC1[XXX"]
    assert tx["changes"] == [] and tx["atom_correspondence"] == []
    for f in tx["fields"]:
        assert f["status"] == "failed"
    tx2 = normalize_record_side_transaction([
        {"side": "lhs", "field": "donor_smiles", "entry_index": 0,
         "smiles": "[O-]C(=O)C.O.[O-]C(=O)C"}])
    assert tx2["status"] == "applied"
    out = tx2["values"][0]
    comps = out.split(".")
    assert len(comps) == 3
    assert comps[0] == comps[2]      # 重复份数保留
    assert comps[1] == "O"           # 中间组分原位保留


def test_component_map_numbers_preserved_rowwise() -> None:
    """map 号保留逐行断言(前置 1 丢号缺陷不得回归):归一前后
    每原子 map 号集合逐行相等(含单组分模板串)。"""
    for smi in ("[CH3:1][CH2:2][O-:3]",
                "[CH3:1][C:2]([O-:3])=[O:4]",
                "[CH3:1][CH2:2][OH:3].[O-:6]C=O"):
        r = normalize_record_side_smiles(smi)
        before = {a.GetAtomMapNum() for a in Chem.MolFromSmiles(smi).GetAtoms()
                  if a.GetAtomMapNum()}
        after = {a.GetAtomMapNum()
                 for a in Chem.MolFromSmiles(r["normalized"]).GetAtoms()
                 if a.GetAtomMapNum()}
        assert before == after, smi
        assert r["status"] in ("applied", "not_applicable")


# ================================================================ 注入点


def test_recorded_compile_entry_normalizes_and_stamps(tmp_path) -> None:
    """recorded:compile 入口注入 —— applied ⇒ spec 条件追加审计五键
    (标量,不嵌套)+ 证明域;未 applied ⇒ 五键缺席、原字节不变。"""
    # applied:供体是阴离子,底物=酸式
    out = compile_recorded_reaction(
        substrate_smiles="CCO",
        donor_smiles="CC[O-]",
        products=["CC=O"], record_id="btX#r1")
    assert out.get("status") == "compiled"
    spec = out["spec"]
    comp = spec["compile"]
    assert _SPEC_KEYS <= set(comp)
    assert comp["record_side_form_norm"] == "applied"
    assert comp["record_side_form_norm_version"] == (
        RECORD_SIDE_FORMNORM_VERSION)
    assert comp["record_side_form_norm_param_sha256"] == (
        RECORD_SIDE_FORMNORM_PARAM_SHA256)
    assert comp["verification_domain"] == "normalized_record_side"
    assert comp["record_products"] == ["CC=O"]
    fn = out["formnorm"]
    assert fn["status"] == "applied"
    assert comp["record_side_form_norm_trace_ref"] == (
        record_side_form_norm_trace_ref(fn["trace"]))
    # 未 applied:全中性 canonical strings ⇒ 五键缺席
    out2 = compile_recorded_reaction(
        substrate_smiles="CCO",
        donor_smiles="CCO",
        products=["CC=O"], record_id="btX#r2")
    assert out2.get("status") == "compiled"
    assert not (_SPEC_KEYS & set(out2["spec"]["compile"]))
    assert out2["formnorm"]["status"] == "not_applicable"


def test_find_recorded_exact_candidate_trace(tmp_path) -> None:
    """recorded 候选行:三值 + trace(source_ref 含 channel/
    asset_sha256/record_key/matched_side_or_component)。"""
    engine = _Engine(tmp_path, [
        _eawag_row("r0001", "CC[O-]", "CC=O"),
        _eawag_row("r0002", "CCO", "CC=O")], [])
    res = find_recorded_exact(
        substrate_smiles="CCO", engine=engine, max_reactions=8)
    by_rid = {c["record_id"]: c for c in res["candidates"]}
    charged = by_rid["btX#r0001"]
    neutral = by_rid["btX#r0002"]
    assert charged["record_side_form_norm"] == "applied"
    assert neutral["record_side_form_norm"] == "not_applicable"
    tr = charged["record_side_form_norm_trace"]
    assert tr["source_ref"]["channel"] == "recorded"
    assert tr["source_ref"]["asset_sha256"] == (
        engine.identity_block["library_sha256"])
    assert tr["source_ref"]["record_key"] == "btX#r0001"
    assert tr["source_ref"]["matched_side_or_component"][
        "matched_side"] == "CC[O-]"
    assert tr["changes"] and tr["atom_correspondence"]
    # 未 applied 行 trace 保留(全形态)且 risk not_applicable
    tr2 = neutral["record_side_form_norm_trace"]
    assert tr2["status"] == "not_applicable"
    assert tr2["risk_status"] == "not_applicable"
    # 批级机读绑定
    diag = res["diagnostics"]
    assert diag["record_side_form_norm_version"] == (
        RECORD_SIDE_FORMNORM_VERSION)
    assert diag["recorded_source_version"] == RECORDED_SOURCE_VERSION


def test_corpus_view_preclassify_and_same_domain(tmp_path) -> None:
    """corpus:分类前统一消费视体;实际装配(record_products/co_substrates)
    同域;matched_component 保 raw + applied 消费态披露;NC-10 两处
    声明同域(view);嵌套 compile 局部 not_applicable 不覆盖首 applied。"""
    # 底物=乙醛酸受体;记录:供体阴离子(可中和),产物中性
    engine = _Engine(tmp_path, [], [
        _rhea_row("rhea:91001", "91000", "LR",
                  "CC[O-]", ["CC[O-]"], "CC=O", ["CC=O"])])
    res = find_recorded_exact.__globals__["find_corpus_recorded_exact"](
        substrate_smiles="CCO", engine=engine, max_reactions=8)
    cands = res["candidates"]
    assert cands
    cand = cands[0]
    assert cand["record_side_form_norm"] == "applied"
    spec = cand["compile"]
    assert spec is not None
    # 五键(applied;由 corpus 首事务盖章,嵌套 compile no-op 不覆盖)
    assert _SPEC_KEYS <= set(spec["compile"])
    assert spec["compile"]["verification_domain"] == (
        "normalized_record_side")
    # 装配同域:record_products = 视体(中性串)
    assert spec["compile"]["record_products"] == ["CC=O"]
    # matched_component 保 raw + 消费态披露(来源例外)
    assert spec["corpus"]["matched_component"] == "CC[O-]"
    assert spec["corpus"]["matched_component_consumption_view"] == (
        "CCO")
    assert "NOT a post-normalization strict identity claim" in \
        spec["corpus"]["matched_component_disclosure"]
    # trace 回指:spec trace_ref == 诊断行 trace 哈希
    tr = cand["record_side_form_norm_trace"]
    assert spec["compile"]["record_side_form_norm_trace_ref"] == (
        record_side_form_norm_trace_ref(tr))
    assert tr["source_ref"]["channel"] == "corpus"
    assert tr["source_ref"]["asset_sha256"] == (
        engine.identity_block["corpus_v1_sha256"])


def test_corpus_failed_parent_reverts_and_no_grant(tmp_path) -> None:
    """父事务 failed(成分不可解析)⇒ 整视体回原始;子集 compile 不得
    重新归一授益(failed 行五键缺席)。"""
    engine = _Engine(tmp_path, [], [
        _rhea_row("rhea:91002", "91002", "LR",
                  "CC[O-]", ["CC[O-]"], "CC=O",
                  ["CC=O", "C1CC1[XXX"],
                  rxn="CC[O-]>>CC=O.C1CC1[XXX")])
    find_corpus = find_recorded_exact.__globals__[
        "find_corpus_recorded_exact"]
    res = find_corpus(substrate_smiles="CCO", engine=engine,
                      max_reactions=8)
    cands = res["candidates"]
    assert cands
    for cand in cands:
        assert cand["record_side_form_norm"] == "failed"
        tr = cand["record_side_form_norm_trace"]
        assert tr["status"] == "failed"
        assert tr["failure_reason"] == "component_unparseable"
        assert tr["risk_status"] == "not_applicable"
        spec = cand.get("compile")
        if spec is not None:
            assert not (_SPEC_KEYS & set(spec["compile"]))


def test_analog_view_all_consumers_and_raw_exceptions(
        tmp_path, monkeypatch) -> None:
    """analog:for-ref 起点视体 —— 编译消费视体(归一后映射保留,
    raw ref 不再传编译);五键条件追加;未 applied 行零变更。"""
    # 带电 rhs:[O-:4] 中和后 = 过氧氢(与 [OH:4] 等价);raw rhs 直接
    # 编译会 charge_edit_unsupported ⇒ 编译成功本身证明消费了视体。
    refs = [
        _Ref("chg", "[CH3:1][CH2:2][OH:3]",
             "[CH3:1][CH2:2][O:3][O-:4]", [3], 0.9),
        _Ref("oxi", "[CH3:1][CH2:2][OH:3]", "[CH3:1][CH2:2][O:3][OH:4]",
             [3], 0.8),
    ]
    _patch_analog(monkeypatch, refs)
    provider = default_pool_provider(
        object(), max_pool=8, min_unique_targets=1)
    specs = provider(_SUB)
    assert specs
    by_key = {s["key"]: s for s in specs}
    diag = provider.last_diagnostics
    rows = {r["record_key"]: r for r in diag["candidates"]}
    assert rows["tpl-chg"]["record_side_form_norm"] == "applied"
    assert rows["tpl-oxi"]["record_side_form_norm"] == "not_applicable"
    chg_spec = by_key.get("tpl-chg")
    assert chg_spec is not None, "带电 ref 应经视体编译成功入池"
    assert _SPEC_KEYS <= set(chg_spec["compile"])
    tr = rows["tpl-chg"]["record_side_form_norm_trace"]
    assert tr["source_ref"]["channel"] == "analog"
    assert tr["source_ref"]["record_key"] == "tpl-chg"
    assert tr["source_ref"]["asset_sha256"] == "a" * 64
    assert tr["source_fields"]["record_equation"].startswith(
        "raw_source_fidelity")
    assert chg_spec["compile"]["record_side_form_norm_trace_ref"] == (
        record_side_form_norm_trace_ref(tr))
    # 未 applied 行 trace 零变更
    tr2 = rows["tpl-oxi"]["record_side_form_norm_trace"]
    assert tr2["changes"] == []
    assert tr2["risk_status"] == "not_applicable"


def test_analog_supply_path_raw_vs_view_mechanics(monkeypatch) -> None:
    """机械断言(raw 例外):伴生供给路径上 compile 收到**视体**串、
    analog_record_equation 收到 **raw** 串(来源例外 Q3)。"""
    import pathway_v43.pollutant.s5b_builder as builder_mod
    import pathway_v43.pollutant.s5b_compiler as compiler_mod

    raw_lhs = ("[CH3:1][C:2](=[O:3])[O:4][CH2:5][CH3:6]"
               ".[O-:7][H:8]")
    raw_rhs = ("[CH3:1][C:2](=[O:3])[O:4][H:8]"
               ".[CH3:6][CH2:5][O:7][H:9]")
    ref = _Ref("sup1", raw_lhs, raw_rhs, [2, 4, 7], 0.9)
    _patch_analog(monkeypatch, [ref])
    compile_args: list[dict] = []
    equation_args: list[tuple] = []
    orig_compile = compiler_mod.compile_donor_template
    orig_eq = builder_mod.analog_record_equation

    def _spy_compile(**kwargs):
        compile_args.append(dict(kwargs))
        return orig_compile(**kwargs)

    def _spy_eq(lhs, rhs):
        equation_args.append((str(lhs), str(rhs)))
        return orig_eq(lhs, rhs)

    monkeypatch.setattr(compiler_mod, "compile_donor_template",
                        _spy_compile)
    monkeypatch.setattr(builder_mod, "analog_record_equation", _spy_eq)
    provider = default_pool_provider(
        object(), max_pool=8, min_unique_targets=1)
    provider("CC(C)C(=O)OCC")  # 合成酯底物(供给夹具同款)
    assert compile_args, "应发生编译尝试"
    joined = json.dumps(compile_args)
    assert "[O-:7]" not in joined and "[O-" not in joined, (
        "raw ref(阴离子袋)不得传编译")
    diag = provider.last_diagnostics
    sup_rows = [r for r in diag["candidates"]
                if r["record_key"] == "tpl-sup1"]
    assert sup_rows
    if equation_args:  # 供给成功路径才发射 record_equation
        assert any("[O-" in lhs or "[O-" in rhs
                   for lhs, rhs in equation_args), (
            "record_equation 必须保 raw 来源例外")


def test_risk_status_unknown_not_fake_absent(tmp_path) -> None:
    """risk_status 禁伪填:applied 但编译未走到对齐 ⇒ unknown + 机读
    原因(不得 absent);可核交集非空 ⇒ present。"""
    # 记录侧预编译拒(通配行)→ 不建候选;改用:如 donor 与产物对不上
    # (no_structure_correspondence)⇒ applied + risk unknown
    out = compile_recorded_reaction(
        substrate_smiles="CCO",
        donor_smiles="CC[O-]",
        products=["CCCC"], record_id="btX#r9")
    assert out.get("status") != "compiled"
    fn = out["formnorm"]
    assert fn["status"] == "applied"
    assert fn["risk"] is None  # 未建映射材料 ⇒ trace unknown
    tr = fn["trace"]
    assert tr["risk_status"] == "unknown"
    assert "risk_reason" in tr and tr["risk_reason"]
    assert tr["human_review_required"] is True


# ================================================================ 披露 schema


def test_trace_schema_fields_complete(tmp_path, monkeypatch) -> None:
    """trace schema 逐字段:source_ref / changes(side/entry_index/
    fragment_index/source_atom_index/original_map/q/H)/atom_correspondence
    (normalized_atom_index/generated_map)/matching_scope/intersection/
    risk_status 四值域。"""
    engine = _Engine(tmp_path, [
        _eawag_row("r0001", "CC[O-]", "CC=O")], [])
    res = find_recorded_exact(substrate_smiles="CCO", engine=engine,
                              max_reactions=8)
    tr = res["candidates"][0]["record_side_form_norm_trace"]
    assert set(tr["source_ref"]) == {
        "channel", "asset_sha256", "record_key",
        "matched_side_or_component"}
    for ch in tr["changes"]:
        assert {"side", "field", "entry_index", "fragment_index",
                "source_atom_index", "original_map", "charge_before",
                "charge_after", "hydrogen_before", "hydrogen_after",
                "hydrogen_detail"} <= set(ch)
    for cp in tr["atom_correspondence"]:
        assert {"side", "field", "entry_index", "fragment_index",
                "source_atom_index", "original_map",
                "normalized_atom_index", "generated_map"} <= set(cp)
    assert tr["matching_scope"] in ("center_l1_l2", None)
    assert tr["risk_status"] in ("present", "absent", "unknown",
                                 "not_applicable")
    assert tr["version"] == RECORD_SIDE_FORMNORM_VERSION
    assert tr["param_sha256"] == RECORD_SIDE_FORMNORM_PARAM_SHA256


def test_spec_five_keys_conditionality_and_bytes(tmp_path) -> None:
    """未 applied spec 零字节:相同输入路径下,中性串编译产出与
    五键无关的 compile 键集合(record_products 保原值);applied 才
    追加(跨候选一致性:同一中性输入两次编译逐字节相等)。"""
    args = dict(substrate_smiles="CCO", donor_smiles="CCO",
                products=["CC=O"], record_id="btX#r2")
    a = compile_recorded_reaction(**args)["spec"]
    b = compile_recorded_reaction(**args)["spec"]
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert not (_SPEC_KEYS & set(a["compile"]))
    # 诊断面(未 applied)仍带 trace(全形态行;不进 run_inputs)
    fn = compile_recorded_reaction(**args)["formnorm"]
    assert fn["status"] == "not_applicable"

def test_corpus_nc10_event_invariant_same_domain(tmp_path) -> None:
    """NC-10 两处声明同域(事件级,带电共底物):B 阴离子经视体归一后,
    co_substrates/declared_copy_components/record_products 全部落在消费
    视体域 ⇒ 首消费(production.prepare_hypothesis)事件级不变量通过;
    同时证明 raw 域错配本会被拒(拷贝身份 strict 核对,NC-4)。"""
    engine = _Engine(tmp_path, [], [
        _rhea_row("rhea:91010", "91010", "LR", "CCO.CC(=O)[O-]",
                  ["CCO", "CC(=O)[O-]"], "CC=O.CC(=O)O",
                  ["CC=O", "CC(=O)O"])])
    find_corpus = find_recorded_exact.__globals__[
        "find_corpus_recorded_exact"]
    res = find_corpus(substrate_smiles="CCO", engine=engine)
    comp = [c for c in res["candidates"]
            if c["donor_match_kind"] == "component"]
    assert comp
    cand = comp[0]
    assert cand["record_side_form_norm"] == "applied"
    spec = cand["compile"]
    assert spec is not None
    # 消费视体域:共底物/拷贝/记录产物声明全为中和后串
    assert [x["smiles"] for x in spec["corpus"]["co_substrates"]] == [
        "CC(=O)O"]
    assert [e["smiles"] for e in spec["declared_copy_components"]] == [
        "CC(=O)O"]
    assert spec["cosubstrate_event_contract"]["record_products"] == [
        "CC=O", "CC(=O)O"]
    # matched_component 保 raw(来源例外)+ 消费态披露
    assert spec["corpus"]["matched_component"] == "CCO"
    # 事件级:首消费不变量通过(同域)
    from pathway_v43.pollutant.production import (
        build_product_state,
        prepare_hypothesis,
    )

    substrate_state = build_product_state(
        "CCO", source_refs=[{"record": "te-nc10"}])
    prepared = prepare_hypothesis(
        spec, parent_path_id="pp-te-nc10",
        substrate_state=substrate_state)
    assert prepared["cosubstrate_disclosure"] is not None
    assert prepared["cosubstrate_disclosure"]["declaration_sources"] == [
        "cosubstrate_event_contract", "corpus"]
