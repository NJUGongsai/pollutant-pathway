# tests/test_t6r3_contract_decisions.py
"""T6-R3 六项裁定回归测试。

逐条覆盖六项裁定在源码中的落地 hard gate：
  裁定 1  enviPath lookup 暂不入图               → 图节点集合无 enviPath 节点
  裁定 2  MISS 后 predictor=BioTransformer ENVMICRO → predict_reactions 默认引擎 + fallback 语义
  裁定 3  source_tag/source_tool 强制非空        → CandidateReaction 必填字段 + 构造点取值
  裁定 4  统一公共 ID 合同 RT-{16hex}            → reaction_node 产出/保留锚定键
  裁定 5  选菌层 LLM 硬依赖 fail-closed          → organism_selection LLM 不可用即显式终止
  裁定 6  lowercase aromatic SMILES 入口直收      → RDKit 硬门 + 原文/规范化双字段

全部为单元级用例：不依赖网络、不依赖 LLM 凭证、不依赖学生数据产物。
"""

import hashlib
import importlib
import inspect
import re

import pytest
from pydantic import ValidationError

from src.state import EnzymeCrewState
from src.schemas.evidence import (
    CandidateReaction,
    OrganismCandidate,
    PredictedReaction,
    SubstrateInfo,
)
from src.schemas.bridge import MultistepBridgeResult, MultistepStep
from src.tools.substrate_parser import (
    detect_smiles_in_query,
    parse_substrate,
    validate_smiles,
)
from src.tools.reaction_predictor import _postprocess_products, predict_reactions
from src.tools.reaction_retriever import _mock_retrieve_dryrun
from src.graph import build_graph, compile_graph, route_after_reaction

# 注意：`import src.nodes.xxx as mod` 会因 src/nodes/__init__.py 里的
# `from .xxx import xxx`（模块与函数同名）导致 `mod` 绑定到函数而非模块，
# 进而 monkeypatch 目标错误（AttributeError）。改用 importlib 从 sys.modules
# 取真实模块对象，保证 monkeypatch 与访问节点函数都指向模块。
reaction_node_mod = importlib.import_module("src.nodes.reaction_node")
reaction_prediction_mod = importlib.import_module("src.nodes.reaction_prediction_node")
organism_selection_mod = importlib.import_module("src.nodes.organism_selection_node")
multi_step_bridge_mod = importlib.import_module("src.nodes.multi_step_bridge_node")


# ═══════════════════ 裁定 6：lowercase aromatic SMILES 入口直收 ═══════════════════

class TestDecision6AromaticSmilesGate:
    def test_lowercase_aromatic_smiles_validates(self):
        # 芳香碳小写开头的 canonical aromatic SMILES 可通过 RDKit 硬门
        assert validate_smiles("c1ccccc1") == "c1ccccc1"

    def test_detect_lowercase_aromatic_in_query(self):
        canonical, raw = detect_smiles_in_query("请降解 c1ccccc1（苯）的酶")
        assert canonical == "c1ccccc1"
        assert raw == "c1ccccc1"

    def test_detect_uppercase_aromatic_in_query(self):
        # 首字符放宽为大小写后，大写芳香形式同样直收；canonical 由 RDKit
        # 归一为小写芳香形式（C1=CC=CC=C1 → c1ccccc1），raw token 保留原文。
        canonical, raw = detect_smiles_in_query("降解 C1=CC=CC=C1 的酶")
        assert canonical == "c1ccccc1"
        assert raw == "C1=CC=CC=C1"

    def test_rdkit_hard_gate_rejects_plain_words(self):
        # 普通英文单词即使匹配正则，也会被 RDKit parse 硬门拒绝（不误收）
        canonical, raw = detect_smiles_in_query("benzene is an aromatic hydrocarbon")
        assert canonical is None
        assert raw is None

    def test_parse_substrate_keeps_raw_and_canonical_both(self):
        # 裁定 6 双字段：规范化 SMILES + 原文 token 均保留，来源可追踪
        info = parse_substrate("降解 c1ccccc1 的酶")
        assert info.source == "user_smiles"
        assert info.substrate_smiles == "c1ccccc1"
        assert info.raw_substrate_smiles == "c1ccccc1"


# ═══════════════════ 裁定 4：统一公共 ID 合同 RT-{16hex} ═══════════════════

def _state_for_reaction(smiles: str, task_id: str | None = None) -> EnzymeCrewState:
    return EnzymeCrewState(
        user_query=f"降解 {smiles} 的酶",
        substrate_info=SubstrateInfo(
            substrate_smiles=smiles, source="user_smiles", provenance="test"
        ),
        reaction_task_id=task_id,
    )


class TestDecision4ReactionTaskIdContract:
    def test_reaction_task_id_conforms_to_rt_format(self, monkeypatch):
        def fake_retrieve(substrate_smiles, topk, db):
            return [
                CandidateReaction(
                    reaction_smiles=f"{substrate_smiles}>>O",
                    similarity_score=0.9,
                    source="retrieved",
                    source_tag="similarity_retrieval_route_c",
                    source_tool="reaction_retriever",
                )
            ]

        monkeypatch.setattr(reaction_node_mod, "_get_db", lambda: object())
        monkeypatch.setattr(reaction_node_mod, "retrieve_similar_reactions", fake_retrieve)

        out = reaction_node_mod.reaction_node(_state_for_reaction("c1ccccc1"))
        tid = out["reaction_task_id"]
        # 单步场景：底物确定性 md5 前缀 → RT-{16hex}
        assert re.fullmatch(r"RT-[0-9a-f]{16}", tid)
        expected = "RT-" + hashlib.md5(b"c1ccccc1").hexdigest()[:16]
        assert tid == expected

    def test_preserves_preassigned_reaction_task_id(self, monkeypatch):
        def fake_retrieve(substrate_smiles, topk, db):
            return [
                CandidateReaction(
                    reaction_smiles=f"{substrate_smiles}>>O",
                    similarity_score=0.5,
                    source="retrieved",
                    source_tag="similarity_retrieval_route_c",
                    source_tool="reaction_retriever",
                )
            ]

        monkeypatch.setattr(reaction_node_mod, "_get_db", lambda: object())
        monkeypatch.setattr(reaction_node_mod, "retrieve_similar_reactions", fake_retrieve)

        # 多步桥接已写入的锚定键必须保留，不被单步逻辑覆盖
        preset = "RT-aaaaaaaaaaaaaaaa"
        out = reaction_node_mod.reaction_node(_state_for_reaction("c1ccccc1", preset))
        assert out["reaction_task_id"] == preset


# ═══════════════════ 裁定 3：source_tag/source_tool 强制非空 ═══════════════════

class TestDecision3SourceProvenanceRequired:
    def test_candidate_reaction_requires_source_fields(self):
        # source_tag / source_tool 为必填字段：缺省构造直接校验失败（强制非空）
        with pytest.raises(ValidationError):
            CandidateReaction(reaction_smiles="A>>B", similarity_score=0.5)

    def test_source_tag_value_in_allowlist(self):
        # 合法取值集合锁定（禁止缺省/默认 enviPath 归因）
        allowlist = {
            "similarity_retrieval_route_c",
            "biotransformer_envmicro",
            "depending_v32",
            "mock_dry_run",
            "unknown",
        }
        rxn = CandidateReaction(
            reaction_smiles="A>>B",
            similarity_score=0.5,
            source="retrieved",
            source_tag="similarity_retrieval_route_c",
            source_tool="reaction_retriever",
        )
        assert rxn.source_tag in allowlist
        assert rxn.source_tool == "reaction_retriever"

    def test_dryrun_retrieve_candidates_carry_provenance(self):
        cands = _mock_retrieve_dryrun("CCO", topk=3)
        assert cands
        for c in cands:
            assert c.source == "retrieved"
            assert c.source_tag == "mock_dry_run"
            assert c.source_tool == "reaction_retriever"
            assert c.source_tag and c.source_tool  # 非空


# ═══════════════════ 裁定 2：MISS 后 predictor = BioTransformer ENVMICRO ═══════════════════

class TestDecision2EnvMicroPredictor:
    def test_predict_reactions_defaults_to_envmicro(self):
        sig = inspect.signature(predict_reactions)
        assert sig.parameters["method"].default == "biotransformer_envmicro"

    def test_predict_reactions_other_methods_not_implemented(self):
        # template_matching / llm_generation 仍是占位，返回空（不伪造候选）
        assert predict_reactions("CCO", method="template_matching") == []

    def test_predict_reactions_without_jar_fails_closed(self, monkeypatch):
        monkeypatch.delenv("BIOTRANSFORMER_JAR", raising=False)
        assert predict_reactions("CCO", method="biotransformer_envmicro") == []

    def test_postprocess_products_envmicro_semantics(self):
        rows = [
            {"product_smiles": "CCO", "reaction_id": "r1", "enzyme": "UNSPECIFIED", "csv_line": 2},
            {"product_smiles": "CCO", "reaction_id": "r2", "enzyme": "UNSPECIFIED", "csv_line": 3},  # 去重
            {"product_smiles": "bad_smiles!", "reaction_id": "r3", "enzyme": "x", "csv_line": 4},  # 硬门拒绝
        ]
        results = _postprocess_products("CC", rows)
        assert len(results) == 1
        r = results[0]
        assert r.prediction_method == "biotransformer_envmicro"
        assert r.confidence == 0.0  # 规则引擎无概率，明确置 0
        assert r.reaction_smiles == "CC>>CCO"  # parent>>product 半反应
        assert "biotransformer_envmicro" in r.provenance

    def test_reaction_prediction_node_falls_back_to_envmicro(self, monkeypatch):
        def fake_predict(smiles, method="biotransformer_envmicro", top_k=5):
            assert method == "biotransformer_envmicro"
            return [
                PredictedReaction(
                    reaction_smiles="CC>>CCO",
                    prediction_method="biotransformer_envmicro",
                    confidence=0.0,
                    provenance="test",
                )
            ]

        monkeypatch.setattr(reaction_prediction_mod, "predict_reactions", fake_predict)

        state = EnzymeCrewState(
            user_query="q",
            substrate_info=SubstrateInfo(
                substrate_smiles="CC", source="user_smiles", provenance="t"
            ),
        )
        out = reaction_prediction_mod.reaction_prediction_node(state)
        assert out["reaction_source"] == "predicted"
        assert len(out["predicted_reactions"]) == 1
        assert out["predicted_reactions"][0].prediction_method == "biotransformer_envmicro"


# ═══════════════════ 裁定 5：选菌层 LLM 硬依赖 fail-closed ═══════════════════

def _org_candidate(uid: int, rank: int) -> OrganismCandidate:
    return OrganismCandidate(
        organism_uid=str(uid),
        ncbi_taxon_id=uid,
        organism_name=f"Organism{uid}",
        supporting_enzyme_count=1,
        default_order_rank=rank,
    )


class TestDecision5OrganismSelectionHardDependency:
    def test_llm_unavailable_fails_closed_not_degrade(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("LLM API error: 401")

        monkeypatch.setattr(organism_selection_mod, "call_dashscope", boom)

        state = EnzymeCrewState(
            user_query="q",
            organism_candidates=[_org_candidate(1, 1), _org_candidate(2, 2)],
        )
        out = organism_selection_mod.organism_selection_node(state)

        # 硬依赖：LLM 不可用即显式 fail_closed，绝不按聚合分直通透传（"无面试录取"）
        assert out["fail_closed"] is True
        assert "fail_closed" in (out.get("error") or "")
        assert "organism_recommendations" not in out

    def test_no_candidates_skips_gracefully(self):
        # 无候选菌（上游未产出 reviewed 宿主）不是 LLM 失败，优雅跳过
        state = EnzymeCrewState(user_query="q", organism_candidates=[])
        out = organism_selection_mod.organism_selection_node(state)
        assert out.get("fail_closed") is not True
        assert "organism_recommendations" not in out
        assert any("无候选菌" in flag for flag in out["uncertainty_flags"])


# ═══════════════════ 裁定 1 + 图编译冒烟 ═══════════════════

class TestDecision1NoEnviPathInGraph:
    def test_graph_nodeset_has_no_envipath_node(self):
        # 裁定 1：enviPath lookup 暂不入图，图节点集合不包含任何 enviPath 节点
        g = build_graph()
        node_names = set(dict(g.nodes).keys())

        expected = {
            "orchestrator", "substrate", "reaction", "reaction_prediction",
            "enzyme_pool", "enzymecage", "reranking", "microbe",
            "organism_selection", "trait", "synthesis", "bridge",
        }
        assert node_names == expected
        joined = " ".join(sorted(node_names)).lower()
        assert "envipath" not in joined

    def test_graph_compiles(self):
        compiled = compile_graph()
        assert compiled is not None
        assert getattr(compiled, "nodes", None)


# ═══════════════════ 缺口①：source_tag/source_tool 拒绝空串/纯空白 ═══════════════════

class TestGap1SourceRejectsBlank:
    def test_source_tag_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            CandidateReaction(
                reaction_smiles="A>>B", similarity_score=0.5,
                source_tag="", source_tool="reaction_retriever",
            )

    def test_source_tag_rejects_whitespace(self):
        with pytest.raises(ValidationError):
            CandidateReaction(
                reaction_smiles="A>>B", similarity_score=0.5,
                source_tag="   ", source_tool="reaction_retriever",
            )

    def test_source_tool_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            CandidateReaction(
                reaction_smiles="A>>B", similarity_score=0.5,
                source_tag="similarity_retrieval_route_c", source_tool="",
            )

    def test_source_tool_rejects_whitespace(self):
        with pytest.raises(ValidationError):
            CandidateReaction(
                reaction_smiles="A>>B", similarity_score=0.5,
                source_tag="similarity_retrieval_route_c", source_tool="\t \n",
            )


# ═══════════════════ 缺口②：Route C 真实 MISS 可走 fallback，不误 fail_closed ═══════════════════

class TestGap2MissDoesNotFailClosed:
    def test_reaction_node_miss_does_not_fail_closed(self, monkeypatch):
        # Route C 真实 MISS（检索无命中）不是失败：不置 fail_closed/error，留路由决定追问
        monkeypatch.setattr(reaction_node_mod, "_get_db", lambda: object())
        monkeypatch.setattr(
            reaction_node_mod, "retrieve_similar_reactions", lambda *a, **k: []
        )
        out = reaction_node_mod.reaction_node(_state_for_reaction("c1ccccc1"))
        assert out.get("fail_closed") is not True
        assert "error" not in out
        assert out["candidate_reactions"] == []
        actions = [e.action for e in out["evidence_chain"]]
        assert "retrieval_miss" in actions

    def test_route_m5_miss_to_predict(self):
        state = EnzymeCrewState(
            user_query="q", pipeline_mode="m5", candidate_reactions=[], fail_closed=False
        )
        assert route_after_reaction(state) == "predict"

    def test_route_fail_closed_to_end(self):
        state = EnzymeCrewState(user_query="q", pipeline_mode="m5", fail_closed=True)
        assert route_after_reaction(state) == "end"


# ═══════════════════ 缺口③：空/空白酶 UID 不得误标 MATCHED ═══════════════════

def _make_step(task_id: str) -> MultistepStep:
    return MultistepStep(
        route_id="r1",
        reaction_task_id=task_id,
        source_node_id=f"{task_id}:n0",
        target_node_id=f"{task_id}:n1",
        depth=1,
        substrate_smiles="A",
        product_smiles="B",
        reaction_smiles="A>>B",
        reaction_source="retrieved",
        source_tool="unknown",
    )


class TestGap3BlankUidNotMatched:
    def test_all_blank_uids_to_unmatched(self):
        br = MultistepBridgeResult(route_id="r1", steps=[_make_step("RT-1")])
        multi_step_bridge_mod.apply_step_enzyme_matches(br, {"RT-1": ["", "   ", "\t"]})
        step = br.steps[0]
        assert step.enzyme_match_status == "UNMATCHED_ENZYME"
        assert step.matched_enzyme_uids == []

    def test_mixed_uids_keep_only_valid(self):
        br = MultistepBridgeResult(route_id="r1", steps=[_make_step("RT-1")])
        multi_step_bridge_mod.apply_step_enzyme_matches(br, {"RT-1": [" ", "uid-1", ""]})
        step = br.steps[0]
        assert step.enzyme_match_status == "MATCHED"
        assert step.matched_enzyme_uids == ["uid-1"]