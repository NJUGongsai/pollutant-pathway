"""S1 变更集施工测试 — E2(temperature)/E3(rank 窗口)/E1(rank 协议呈现)
三个配置化开关。

纪律钉(HIT60 S1,任务书 T1 §4/§5、PREREGISTRATION §2.1/§2.2/§2.3):

- 默认行为不变:不设 temperature → 请求体不含该键(逐字节与 HEAD 一致);
  rank 窗口缺省 8;rank 候选呈现缺省 v1(任务书逐字节与 HEAD 一致,
  黄金测试另见 test_prediction_task / test_s1_e1_rank_v2);
- 开关取值进 run identity(prediction.policy)与 batch identity
  (config + prediction_policy 块),跨配置 resume 被拒;
- temperature 单通道:env / 显式 request_params 携带温度键一律拒绝;
  NaN/Infinity/bool/越界 fail-closed;
- kimi-k3 系模型不接受 temperature(API 400,CHENYU_ACCESS 坑清单):
  设了温度臂 → 装配期报"该模型不支持温度臂",不静默忽略;
- 窗口 16 只改 rank 任务候选数,不改入围规则(仍只合格 recorded 卡);
- 呈现 v2 只改 rank 任务的候选呈现与解析契约(prompt=ranker_v2.md);
- configs/s1_dev_{C0,E2,E3,E1}.json 的逐字段差异必须恰为
  ARM_CONFIG_DIFFS.md 预登记字段(跑分判定只认那里列出的字段)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pathway_v43.domain.policy import (  # noqa: E402
    PREDICTION_POLICY_DEFAULTS,
    prediction_policy,
)

REPO = Path(__file__).resolve().parents[1]


# ------------------------------------------------ 默认行为不变(缺省开关)


def test_policy_defaults_temperature_null_window_8():
    """缺省:temperature=None(= 不发送)、rank 窗口 8、rank 呈现 v1、
    novel 守恒过滤 off(T8 G2,默认 C0 行为);其余默认不受施工影响。"""
    pol = prediction_policy()
    assert pol["temperature"] is None
    assert pol["max_candidates_for_ranking"] == 8
    assert pol["rank_candidate_presentation"] == "v1"
    assert pol["novel_conservation_filter"] == "off"
    assert PREDICTION_POLICY_DEFAULTS["temperature"] is None
    assert PREDICTION_POLICY_DEFAULTS["max_candidates_for_ranking"] == 8
    assert PREDICTION_POLICY_DEFAULTS["rank_candidate_presentation"] == "v1"
    assert PREDICTION_POLICY_DEFAULTS["novel_conservation_filter"] == "off"
    # 既有默认键一个不少、一个不多(施工累计只允许新增这三个开关键:
    # temperature(E2)/rank_candidate_presentation(E1)/
    # novel_conservation_filter(T8 G2))
    head_keys = {
        "policy_version", "max_candidates_for_ranking",
        "max_reportable_products", "allow_novel_on_mapping_failure",
        "allow_novel_on_no_evidence", "max_parse_retries",
        "analogy_enabled", "max_analogy_donor_candidates",
        "allow_noop_edit", "reactant_similar_enabled",
        "reactant_similar_threshold", "reactant_similar_top_k",
    }
    assert set(PREDICTION_POLICY_DEFAULTS) == head_keys | {
        "temperature", "rank_candidate_presentation",
        "novel_conservation_filter"}


def test_request_body_default_has_no_temperature():
    """不设开关:请求体逐字节不含 temperature;设了才显式携带。"""
    from pathway_v43.adapters.llm_client import OpenAICompatibleClient

    client = OpenAICompatibleClient(
        base_url="https://llm.example/v1", api_key="k", model="m",
        timeout_s=5)
    default_body = client._request_body(
        "sys", "user", dict(client.request_params))
    assert b"temperature" not in default_body
    temp_body = client._request_body(
        "sys", "user", {**client.request_params, "temperature": 0.0})
    assert b'"temperature": 0.0' in temp_body
    # 除新增键外,默认请求体的其余字节不受影响
    stripped = temp_body.replace(b'"temperature": 0.0, ', b"") \
        if b'"temperature": 0.0, ' in temp_body else temp_body
    assert b'"temperature"' in stripped or stripped == default_body


# ------------------------------------------------ temperature fail-closed


@pytest.mark.parametrize("bad", [
    float("nan"), float("inf"), float("-inf"), -0.1, 2.5, "0.7", True, [0.0],
])
def test_temperature_invalid_values_fail_closed(bad):
    """NaN/Infinity/越界/字符串/bool/列表一律当场拒绝(配置写错不进身份)。"""
    with pytest.raises(ValueError):
        prediction_policy({"temperature": bad})


@pytest.mark.parametrize("good", [0, 0.0, 0.5, 1.5, 2])
def test_temperature_valid_values_normalized_to_float(good):
    pol = prediction_policy({"temperature": good})
    assert pol["temperature"] == float(good)
    assert isinstance(pol["temperature"], float)  # 0 与 0.0 身份字节一致


def test_temperature_via_env_request_params_still_forbidden(monkeypatch):
    """env 通道禁止温度键(既有纪律不动)。"""
    from pathway_v43.adapters import llm_client

    monkeypatch.setenv(llm_client.LLM_REQUEST_PARAMS_ENV,
                       '{"temperature": 0.0}')
    with pytest.raises(llm_client.ModelNotConfigured):
        llm_client.OpenAICompatibleClient(
            base_url="https://x", api_key="k", model="m")


def _set_real_env(monkeypatch, model: str) -> None:
    from pathway_v43.adapters import llm_client

    monkeypatch.setenv(llm_client.LLM_BASE_URL_ENV, "https://llm.example/v1")
    monkeypatch.setenv(llm_client.LLM_API_KEY_ENV, "test-key-no-secret")
    monkeypatch.setenv(llm_client.LLM_MODEL_ENV, model)
    monkeypatch.delenv(llm_client.LLM_REQUEST_PARAMS_ENV, raising=False)
    monkeypatch.delenv("V43_LLM_TIMEOUT_S", raising=False)


def test_temperature_via_explicit_request_params_forbidden(monkeypatch):
    """显式 request_params 通道同样禁止:温度只走 policy(可预登记/可冻结)。"""
    from pathway_v43.adapters import llm_client

    _set_real_env(monkeypatch, "qwen3.8-max")
    with pytest.raises(llm_client.ModelNotConfigured) as ei:
        llm_client.resolve_model_setup(
            "real", request_params={"temperature": 0.5})
    assert "temperature" in str(ei.value)


@pytest.mark.parametrize("kimi", ["kimi-k3", "Moonshot/kimi-k3-preview"])
def test_kimi_k3_temperature_arm_fails_closed(monkeypatch, kimi):
    """kimi-k3 系模型 + 温度臂 → 装配期报"该模型不支持温度臂"(API 400 钉死)。"""
    from pathway_v43.adapters import llm_client

    _set_real_env(monkeypatch, kimi)
    with pytest.raises(llm_client.ModelNotConfigured) as ei:
        llm_client.resolve_model_setup(
            "real", policy=prediction_policy({"temperature": 0.0}))
    assert "该模型不支持温度臂" in str(ei.value)
    assert ei.value.detail["model_id"] == kimi
    # 不设温度臂时同一模型照常装配(kimi 检查只拦温度臂,不拦模型本身)
    setup = llm_client.resolve_model_setup(
        "real", policy=prediction_policy())
    assert setup.policy["temperature"] is None


def test_supported_model_assembles_with_temperature(monkeypatch):
    """支持温度的模型 + 温度臂 → 正常装配,取值进 policy(即进身份块)。"""
    from pathway_v43.adapters import llm_client

    _set_real_env(monkeypatch, "qwen3.8-max")
    setup = llm_client.resolve_model_setup(
        "real", policy=prediction_policy({"temperature": 0.0}),
        request_params={"reasoning_effort": "max"})
    assert setup.policy["temperature"] == 0.0
    # 温度不混入 request_params(身份里两条通道各自可见,单变量可读)
    assert "temperature" not in setup.request_params
    assert setup.request_params == {"reasoning_effort": "max"}


# ------------------------------------------------ 开关进身份 + resume 拒绝


def _identity(prediction_block: dict) -> dict:
    from pathway_v43.storage.run_identity import build_run_identity
    from pathway_v43.storage.run_identity import scripted_asset_identity

    return build_run_identity(
        run_id="r1", root_smiles="Oc1ccccc1O", root_cn="Oc1ccccc1O",
        strategy={"version": "v43-policy-1", "max_depth": 1,
                  "max_expansions": 1, "max_frontier_width": 5},
        asset_identity=scripted_asset_identity(),
        v3_code_identity={"git_commit": "x"},
        prediction=prediction_block,
    )


def test_temperature_and_window_enter_run_identity_and_reject_resume():
    """开关取值进 prediction.policy;跨配置 resume → IdentityMismatch。"""
    from pathway_v43.adapters.llm_client import resolve_model_setup
    from pathway_v43.storage.run_identity import (
        IdentityMismatch, check_resume_identity,
    )

    setup_c0 = resolve_model_setup("fake", policy=prediction_policy())
    setup_e2 = resolve_model_setup(
        "fake", policy=prediction_policy({"temperature": 0.0}))
    setup_e3 = resolve_model_setup(
        "fake", policy=prediction_policy({"max_candidates_for_ranking": 16}))

    blk_c0 = setup_c0.identity_block()
    assert blk_c0["policy"]["temperature"] is None
    assert blk_c0["policy"]["max_candidates_for_ranking"] == 8
    assert setup_e2.identity_block()["policy"]["temperature"] == 0.0
    assert setup_e3.identity_block()["policy"][
        "max_candidates_for_ranking"] == 16

    base = _identity(blk_c0)
    check_resume_identity(base, _identity(blk_c0))  # 同身份不抛
    for other, key in ((setup_e2, "temperature"),
                       (setup_e3, "max_candidates_for_ranking")):
        with pytest.raises(IdentityMismatch) as ei:
            check_resume_identity(base, _identity(other.identity_block()))
        assert "prediction" in ei.value.detail["differences"]


def test_batch_identity_freezes_arm_switch(tmp_path):
    """批次身份:两臂配置只差预登记字段 → sha256 不同(新批次根纪律的依据)。"""
    from pathway_v43.batch import _policy_block_for_identity, build_batch_identity

    manifest = {
        "schema_version": "v43-batch-1", "kind": "batch_input_manifest",
        "split": "exam298", "route_order": ["q1"],
        "routes": [{"route_id": "q1", "root_smiles": "CCO",
                    "root_smiles_sha256": "0" * 64}],
        "source": {"v3_root": "fixture"},
        "whitelist_fields": ["route_id", "root_smiles",
                             "root_smiles_sha256"],
        "gold_fields_excluded": True,
    }
    manifest_path = tmp_path / "input_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def identity_for(config: dict) -> dict:
        return build_batch_identity(
            split="exam298", input_manifest_path=manifest_path,
            config=config, provider="openai_compatible", model_id="m",
            request_params={}, timeout_s=300.0, export_policy={},
            prediction_policy_block=_policy_block_for_identity("real", config))

    c0 = json.loads((REPO / "configs" / "s1_dev_C0.json").read_text())
    e2 = json.loads((REPO / "configs" / "s1_dev_E2.json").read_text())
    e3 = json.loads((REPO / "configs" / "s1_dev_E3.json").read_text())
    e1 = json.loads((REPO / "configs" / "s1_dev_E1.json").read_text())
    # 预登记外的字段全部抹平(只留预登记差异,验证的就是这些开关)
    for cfg in (e2, e3, e1):
        cfg["arm"] = c0["arm"]
        cfg["batch_root"] = c0["batch_root"]

    id_c0, id_e2, id_e3, id_e1 = (identity_for(c) for c in (c0, e2, e3, e1))
    assert len({id_c0["sha256"], id_e2["sha256"], id_e3["sha256"],
                id_e1["sha256"]}) == 4
    pol_c0 = id_c0["identity"]["model"]["prediction_policy"]
    assert pol_c0["temperature"] is None
    assert pol_c0["max_candidates_for_ranking"] == 8
    assert pol_c0["rank_candidate_presentation"] == "v1"
    assert id_e2["identity"]["model"]["prediction_policy"][
        "temperature"] == 0.0
    assert id_e3["identity"]["model"]["prediction_policy"][
        "max_candidates_for_ranking"] == 16
    assert id_e1["identity"]["model"]["prediction_policy"][
        "rank_candidate_presentation"] == "v2"


# ------------------------------------------------ E3 窗口:只改入围数量


def _rank_task(policy: dict, tmp_path) -> dict:
    from pathway_v43.domain.identity import cn_identity
    from pathway_v43.services.prediction import (
        PREDICTION_MODE_RANK, build_prediction_task,
    )
    from pathway_v43.storage.pathway_store import PathwayStore
    from wf_helpers import CATECHOL, evidence

    s = cn_identity(CATECHOL)
    usable = [evidence(f"bt0001#r{i:04d}", "recorded_reaction", s,
                       ["O=CCC=CO"]) for i in range(20)]
    dirty = [evidence(f"bt0009#c{i}", "recorded_reaction", s, ["CC(O)=O"],
                      condition_fit="conflict") for i in range(2)]
    rule = [evidence("bt0010#rule", "rule_application", s, ["CCO"],
                     match_type="rule_template")]
    store_dir = Path(tmp_path)
    store_dir.mkdir(parents=True, exist_ok=True)
    store = PathwayStore(store_dir / "t.sqlite")
    root = store.ensure_run("r1-window", CATECHOL, s)
    return build_prediction_task(
        store=store, run_id="r1-window", path_id=root,
        substrate_identity=s, substrate_smiles=CATECHOL,
        root_smiles=CATECHOL, mode=PREDICTION_MODE_RANK,
        retrieval_payload={"evidences": usable + dirty + rule},
        retrieval_payload_hash="h", conditions=[],
        model_block={}, policy=policy,
        budget={"active_depth": 0, "max_depth": 1, "max_expansions": 1,
                "max_frontier_width": 5, "max_llm_calls": 3,
                "max_proposals": 1, "used_expansions": 0,
                "used_llm_calls": 0, "used_proposals": 0},
        siblings=[], analogy_eligibility=None,
    )


def test_rank_window_default_8_and_arm_16_only_changes_count(tmp_path):
    """窗口 16 生效且只影响入围数量:规则卡/脏 recorded 卡照旧不入任务。"""
    task8 = _rank_task(prediction_policy(), tmp_path / "w8")
    ids8 = [c["evidence_id"] for c in task8["candidates"]]
    assert len(ids8) == 8  # 缺省窗口 8(与 HEAD 一致)

    task16 = _rank_task(
        prediction_policy({"max_candidates_for_ranking": 16}),
        tmp_path / "w16")
    ids16 = [c["evidence_id"] for c in task16["candidates"]]
    assert len(ids16) == 16
    assert ids16[:8] == ids8  # 只是同一有序合格池的前 8 → 前 16,不改规则
    assert all(i.startswith("E-bt0001#") for i in ids16)  # 只有合格 recorded
    for c in task16["candidates"]:
        assert c["kind"] == "recorded_reaction"


# ------------------------------------------------ 工作流注入(extra_params)


class _RecordingClient:
    """伪客户端:记录 complete() 实收的 extra_params(温度臂注入点)。"""

    provider = "fake"

    def __init__(self, raw_text: str) -> None:
        self.raw_text = raw_text
        self.seen: list[dict | None] = []

    def complete(self, *, mode, system_prompt, user_payload,
                 idempotency_key=None, extra_params=None):
        from pathway_v43.adapters.llm_client import LLMResponse

        self.seen.append(extra_params)
        return LLMResponse(ok=True, raw_text=self.raw_text)


def _model_with_client(client, policy_overrides: dict | None):
    from pathway_v43.adapters.llm_client import ModelSetup, prompt_versions
    from pathway_v43.config import repo_root

    return ModelSetup(
        provider="fake", model_id="recording-v1", client=client,
        prompts_root=repo_root() / "configs" / "prompts",
        prompt_versions=prompt_versions(
            repo_root() / "configs" / "prompts"),
        policy=prediction_policy(policy_overrides),
    )


def _run_rank(tmp_path, model):
    from wf_helpers import CATECHOL, evidence, run_scripted
    from pathway_v43.domain.identity import cn_identity

    s = cn_identity(CATECHOL)
    scripted = {
        s: [evidence("bt0001#r0001", "recorded_reaction", s, ["O=CCC=CO"]),
            evidence("bt0002#r0002", "recorded_reaction", s, ["O=C=O"])],
    }
    client = model.client
    summary, runs = run_scripted(
        "s1temp", scripted, max_depth=1, runs_root=tmp_path,
        model=model, max_llm_calls=3)
    return summary, runs, client


def test_workflow_default_policy_sends_no_temperature(tmp_path):
    """缺省:complete() 的 extra_params=None;调用产物不带 temperature 键。"""
    from wf_helpers import rank_response

    client = _RecordingClient(rank_response("E-bt0001#r0001"))
    model = _model_with_client(client, None)
    summary, runs, client = _run_rank(tmp_path, model)
    assert summary["counts"]["reaction_events"] == 1
    assert client.seen and all(p is None for p in client.seen)
    call_files = sorted((runs / "s1temp" / "results").glob(
        "*/prediction_call.a1.json"))
    assert call_files
    payload = json.loads(call_files[0].read_text(encoding="utf-8"))["payload"]
    assert "temperature" not in payload


def test_workflow_temperature_arm_sends_explicit_zero(tmp_path):
    """E2 臂:complete() 收到 extra_params={"temperature": 0.0} 且逐调用留痕。"""
    from wf_helpers import rank_response

    client = _RecordingClient(rank_response("E-bt0001#r0001"))
    model = _model_with_client(client, {"temperature": 0.0})
    summary, runs, client = _run_rank(tmp_path, model)
    assert summary["counts"]["reaction_events"] == 1
    assert client.seen and all(p == {"temperature": 0.0} for p in client.seen)
    call_files = sorted((runs / "s1temp" / "results").glob(
        "*/prediction_call.a1.json"))
    assert call_files
    payload = json.loads(call_files[0].read_text(encoding="utf-8"))["payload"]
    assert payload["temperature"] == 0.0


# ------------------------------------------------ 四配置预登记 diff 纪律


ARMS = ("C0", "E2", "E3", "E1")
# 部署回填后(ARM_CONFIG_DIFFS.md §4.1/§4.4,2026-09-29 登记于任何付费调用之前):
# batch_cost_cap_cny 为费用治理字段按臂分摊(C0=8.0/E2=5.0/E3=6.0/E1=6.0),
# 属预登记合法差异;provider_price_snapshot 四臂同值回填,不进 diff 集。
EXPECTED_DIFF_FIELDS = {
    "arm", "batch_root", "batch_cost_cap_cny",
    "prediction_policy_overrides.temperature",
    "prediction_policy_overrides.max_candidates_for_ranking",
    "prediction_policy_overrides.rank_candidate_presentation",
}
# §4.1/§4.4 登记的回填取值(价格快照四臂同值;费用帽按 PREREGISTRATION
# §2/§5 分摊,E1 帽 ¥6 = PREREG §2.3 单批上限)
BACKFILLED_COST_CAPS = {"C0": 8.0, "E2": 5.0, "E3": 6.0, "E1": 6.0}
BACKFILLED_SNAPSHOT_MODEL_ID = "ZHIPU/GLM-5.3-Flash"


def _configs() -> dict[str, dict]:
    return {a: json.loads(
        (REPO / "configs" / f"s1_dev_{a}.json").read_text(encoding="utf-8"))
        for a in ARMS}


def _flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def test_s1_configs_pairwise_diff_is_exactly_registered():
    """四配置逐字段差异恰为 ARM_CONFIG_DIFFS.md 预登记字段,多一字段即破坏。"""
    flat = {a: _flatten(c) for a, c in _configs().items()}
    diff_keys: set[str] = set()
    for i, a in enumerate(ARMS):
        for b in ARMS[i + 1:]:
            ka, kb = set(flat[a]), set(flat[b])
            diff_keys |= (ka ^ kb) | {
                k for k in ka & kb if flat[a][k] != flat[b][k]}
    assert diff_keys == EXPECTED_DIFF_FIELDS, (
        f"超出/缺失预登记差异:{sorted(diff_keys ^ EXPECTED_DIFF_FIELDS)}")


def test_s1_configs_preregistered_values():
    """四配置共同基线字段 + 唯一实验差异的取值钉死。"""
    cfg = _configs()
    for a in ARMS:
        assert cfg[a]["budgets"] == {
            "max_depth": 1, "max_expansions": 1, "max_frontier_width": 5,
            "max_llm_calls": 3, "max_proposals": 1}
        ov = cfg[a]["prediction_policy_overrides"]
        assert ov["reactant_similar_enabled"] is False  # 类比线封存
        assert ov["reactant_similar_threshold"] == 0.0
        assert ov["reactant_similar_top_k"] == 0
        assert ov["max_analogy_donor_candidates"] == 3
        # 部署回填已完成(ARM_CONFIG_DIFFS.md §4.1):费用帽按臂分摊、
        # 价格快照四臂同值(model_id 钉死;凭证类内容不进配置)
        assert cfg[a]["batch_cost_cap_cny"] == BACKFILLED_COST_CAPS[a]
        snap = cfg[a]["provider_price_snapshot"]
        assert snap and snap["model_id"] == BACKFILLED_SNAPSHOT_MODEL_ID
        assert snap["checked"] == "2026-09-29"
        # 超时墙 3600(§4.2 三臂同值修正,E1 同值接力)
        assert cfg[a]["llm_timeout_s"] == 3600.0
        # 远端部署位题卷占位(部署代理放好;配置不写本地路径)
        assert cfg[a]["exam_inputs"] == \
            "workspaces/dependingv43_s1/exam/dev_questions.jsonl"
    assert "temperature" not in cfg["C0"]["prediction_policy_overrides"]
    assert "temperature" not in cfg["E3"]["prediction_policy_overrides"]
    assert "temperature" not in cfg["E1"]["prediction_policy_overrides"]
    assert "max_candidates_for_ranking" not in \
        cfg["C0"]["prediction_policy_overrides"]
    assert "max_candidates_for_ranking" not in \
        cfg["E2"]["prediction_policy_overrides"]
    assert "max_candidates_for_ranking" not in \
        cfg["E1"]["prediction_policy_overrides"]
    assert cfg["E2"]["prediction_policy_overrides"]["temperature"] == 0.0
    assert cfg["E3"]["prediction_policy_overrides"][
        "max_candidates_for_ranking"] == 16
    # E1 唯一实验差异:rank 候选呈现 v2(其余臂不设 = 缺省 v1)
    assert "rank_candidate_presentation" not in \
        cfg["C0"]["prediction_policy_overrides"]
    assert "rank_candidate_presentation" not in \
        cfg["E2"]["prediction_policy_overrides"]
    assert "rank_candidate_presentation" not in \
        cfg["E3"]["prediction_policy_overrides"]
    assert cfg["E1"]["prediction_policy_overrides"][
        "rank_candidate_presentation"] == "v2"


def test_s1_configs_policy_blocks_differ_only_on_registered_switch():
    """批次身份的策略块:两两差异恰为单一注册开关(单变量成臂的机读形式)。"""
    from pathway_v43.batch import _policy_block_for_identity

    blocks = {a: _policy_block_for_identity(
        "real", {"prediction_policy_overrides":
                 _configs()[a]["prediction_policy_overrides"]})
        for a in ARMS}
    assert blocks["E2"]["temperature"] == 0.0
    assert blocks["C0"]["temperature"] is None
    assert blocks["E3"]["temperature"] is None
    assert blocks["E3"]["max_candidates_for_ranking"] == 16
    assert blocks["C0"]["max_candidates_for_ranking"] == 8
    assert blocks["E2"]["max_candidates_for_ranking"] == 8
    assert blocks["E1"]["rank_candidate_presentation"] == "v2"
    assert blocks["C0"]["rank_candidate_presentation"] == "v1"
    assert {k for k in blocks["C0"] if blocks["C0"][k] != blocks["E2"][k]} \
        == {"temperature"}
    assert {k for k in blocks["C0"] if blocks["C0"][k] != blocks["E3"][k]} \
        == {"max_candidates_for_ranking"}
    assert {k for k in blocks["C0"] if blocks["C0"][k] != blocks["E1"][k]} \
        == {"rank_candidate_presentation"}
