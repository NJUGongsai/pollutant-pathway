"""R1-d 费用账测试(任务书 §5;无网络、无凭证、零 LLM)。

覆盖:全 usage、部分缺失、全部缺失、超时后成功重试(旧 attempt 失败
新 attempt 成功)、孤儿调用;known 小计 vs 保守预留 vs 最终总账的
字段区别 —— 不得把 ¥小计写成总费用。
"""

from __future__ import annotations

import json
from pathlib import Path

from pathway_v43.batch import api_account

PRICE = {
    "model_id": "test-model", "input_cny_per_m": 0.8,
    "output_cny_per_m": 2.8, "cache_read_cny_per_m": 0.23,
    "source": "fixture", "checked": "2026-09-28",
}


def _env(payload: dict) -> str:
    from pathway_v43.domain.models import content_hash

    return json.dumps({
        "schema_version": "v43-artifact-1", "run_id": "r",
        "task_id": "t", "name": "n", "payload_hash": content_hash(payload),
        "payload": payload,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_call(results: Path, task: str, attempt: int) -> None:
    (results / task).mkdir(parents=True, exist_ok=True)
    (results / task / f"prediction_call.a{attempt}.json").write_text(
        _env({"status": "issued", "attempt": attempt}), encoding="utf-8")


def _write_response(results: Path, task: str, attempt: int, *,
                    status="completed", usage=None, error_kind=None) -> None:
    (results / task).mkdir(parents=True, exist_ok=True)
    _write_call(results, task, attempt)
    payload = {"status": status, "attempt": attempt, "transport": {
        "elapsed_s": 1.0, "usage": usage,
        "http_attempts": [{"status": 200}],
    }}
    if error_kind:
        payload["transport"]["error_kind"] = error_kind
    (results / task / f"prediction_response.a{attempt}.json").write_text(
        _env(payload), encoding="utf-8")


def _write_task(results: Path, task: str, text_chars: int = 800) -> None:
    (results / task).mkdir(parents=True, exist_ok=True)
    (results / task / "prediction_task.json").write_text(
        _env({"task": "x" * text_chars}), encoding="utf-8")


def _run(tmp_path: Path) -> Path:
    results = tmp_path / "runA" / "results"
    results.mkdir(parents=True)
    return results


USAGE_OK = {"prompt_tokens": 1000, "completion_tokens": 500,
            "total_tokens": 1500}


def test_all_usage_present_gives_cost(tmp_path):
    results = _run(tmp_path)
    _write_task(results, "T1")
    _write_response(results, "T1", 1, usage=USAGE_OK)
    acc = api_account(tmp_path, ["runA"], PRICE)
    assert acc["totals"]["n_usage_missing"] == 0
    assert acc["cost_estimate_cny"] == round(
        1000 / 1e6 * 0.8 + 500 / 1e6 * 2.8, 4)
    assert "conservative_reservation" not in acc
    # 逐调用明细存在且 usage_present
    assert len(acc["calls"]) == 1 and acc["calls"][0]["usage_present"]
    assert acc["calls"][0]["known_tokens"]["input_tokens"] == 1000


def test_partial_usage_keeps_total_unknown(tmp_path):
    results = _run(tmp_path)
    _write_task(results, "T1")
    _write_response(results, "T1", 1, usage=USAGE_OK)
    _write_task(results, "T2")
    _write_response(results, "T2", 1, usage=None,
                    status="transport_failed", error_kind="timeout")
    acc = api_account(tmp_path, ["runA"], PRICE)
    # 部分缺失:总费用 unknown,known 小计单列,不冒充实测
    assert acc["cost_estimate_cny"] == "unknown"
    assert "cost_estimate_known_usage_cny" in acc
    assert acc["totals"]["n_usage_missing"] == 1
    # 保守预留:输入可证明上界,输出不可证明
    res = acc["conservative_reservation"]
    assert res["input_tokens_upper"] > 0
    assert res["output_bound"] == "unprovable_no_request_output_cap"
    assert res["output_cost_upper_cny"] is None
    assert res["input_cost_upper_cny"] > 0
    # known 小计 ≠ 总费用字段
    assert acc["cost_estimate_known_usage_cny"] != "unknown"
    assert acc["cost_estimate_cny"] != acc["cost_estimate_known_usage_cny"]


def test_all_usage_missing_total_unknown(tmp_path):
    results = _run(tmp_path)
    _write_task(results, "T1")
    _write_response(results, "T1", 1, usage=None,
                    status="transport_failed", error_kind="timeout")
    acc = api_account(tmp_path, ["runA"], PRICE)
    assert acc["cost_estimate_cny"] == "unknown"
    assert "cost_estimate_known_usage_cny" not in acc
    assert "conservative_reservation" in acc
    assert acc["totals"]["n_usage_missing"] == 1


def test_timeout_then_successful_retry(tmp_path):
    """超时后成功重试:a1 无 usage(留残差),a2 有 usage 计入小计。"""
    results = _run(tmp_path)
    _write_task(results, "T1")
    _write_response(results, "T1", 1, usage=None,
                    status="transport_failed", error_kind="timeout")
    _write_response(results, "T1", 2, usage=USAGE_OK)
    acc = api_account(tmp_path, ["runA"], PRICE)
    t = acc["totals"]
    assert t["n_usage_records"] == 1 and t["n_usage_missing"] == 1
    assert t["input_tokens"] == 1000
    assert acc["cost_estimate_cny"] == "unknown"  # 仍有 1 条缺失
    assert "cost_estimate_known_usage_cny" in acc
    assert acc["conservative_reservation"]["input_tokens_upper"] > 0
    # 逐调用两条,各标 attempt 与 usage_present
    at = {(c["attempt"], c["usage_present"]) for c in acc["calls"]}
    assert (1, False) in at and (2, True) in at


def test_orphan_call_counted_not_estimated(tmp_path):
    """孤儿调用:真实耗额计数,无请求文本不入输入预留。"""
    results = _run(tmp_path)
    _write_call(results, "T1", 1)
    (results / "T1" / "prediction_orphan.a1.json").write_text(
        _env({"orphan": "request_issued_no_response"}), encoding="utf-8")
    acc = api_account(tmp_path, ["runA"], PRICE)
    assert acc["totals"]["n_orphaned"] == 1
    assert acc["totals"]["n_calls_issued"] == 1
    assert acc["cost_estimate_cny"] == "unknown"
    res = acc["conservative_reservation"]
    assert res["orphan_calls_not_reserved"] == 1
    assert res["input_tokens_upper"] == 0  # 无可证明请求文本


def test_price_snapshot_recorded_verbatim(tmp_path):
    results = _run(tmp_path)
    _write_response(results, "T1", 1, usage=USAGE_OK)
    acc = api_account(tmp_path, ["runA"], PRICE)
    assert acc["price_snapshot"] == PRICE
    assert acc["price_snapshot"]["checked"] == "2026-09-28"
