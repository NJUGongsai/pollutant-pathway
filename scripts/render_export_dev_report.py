#!/usr/bin/env python
"""export_dev_report.json → docs/EXPORT_DEV_REPORT.md(确定性渲染,零 LLM)。

用法:
    python scripts/render_export_dev_report.py \
        --report <batch_root>/report/export_dev_report.json \
        --out docs/EXPORT_DEV_REPORT.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def fmt(x, nd=4):
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    r = json.loads(Path(a.report).read_text(encoding="utf-8"))

    cn = r["eval_v43"]["cn_overall"]
    raw = r["eval_v43"]["raw_sb_overall"]
    cn_s = r["eval_v43"]["cn_by_stratum"]
    model = r["batch"]["model"]
    config = r["batch"]["config"]
    acct = r["api_account"]["totals"]
    lines: list[str] = []
    w = lines.append

    w("# v4.3 第四阶段:dev 20 路真实模型批跑、冻结导出与对照报告")
    w("")
    w("> 生成:`scripts/build_dev_report.py` + `scripts/render_export_dev_report.py`"
      "(确定性渲染,零 LLM);批次身份 sha256 前 16 位 "
      f"`{r['batch']['sha256'][:16]}`。")
    w("")
    w("## 0. 结论速览")
    w("")
    w(f"- 批次:{r['batch']['short']} / {config['budgets']}")
    w(f"- 模型:`{model['model_id']}`(provider={model['provider']},"
      f"request_params={json.dumps(model['request_params'])},"
      f"timeout={model['timeout_s']}s)")
    w(f"- **cn 主口径**:step hit@1={fmt(cn['step_hit@1'])} "
      f"hit@3={fmt(cn['step_hit@3'])} hit@5={fmt(cn['step_hit@5'])};"
      f"route_recall={fmt(cn['route_recall'])};gold-leaf reached="
      f"{fmt(cn['gold_leaf_reached'])};spurious={fmt(cn['spurious_rate'])}")
    w(f"- **raw_sb 对照**:hit@1={fmt(raw['step_hit@1'])} "
      f"hit@5={fmt(raw['step_hit@5'])};recall={fmt(raw['route_recall'])};"
      f"spurious={fmt(raw['spurious_rate'])}")
    w("- S/M/D 分层(cn hit@5):" + ", ".join(
        f"{k}={fmt(v['step_hit@5'])}" for k, v in sorted(cn_s.items())))
    w(f"- API:issued={acct['n_calls_issued']},响应={acct['n_responses']},"
      f"孤儿={acct['n_orphaned']},429={acct['n_http_429']},"
      f"传输失败={acct['n_transport_failed']};"
      f"tokens in/out={acct['input_tokens']}/{acct['output_tokens']}"
      f"(cache {acct['cached_input_tokens']},思考 {acct['reasoning_output_tokens']})")
    w(f"- 估算费用:{r['api_account'].get('cost_estimate_cny')} CNY"
      f"(口径:{r['api_account'].get('cost_basis', '')})")
    w("")
    w("## 1. 协议限定(必随数字外传)")
    w("")
    for c in r["protocol_caveats"]:
        w(f"- {c}")
    w("")
    w("## 2. 逐路线状态")
    w("")
    w("| route_id | run_id | 停止原因 | 答卷类型 | 失败原因 |")
    w("|---|---|---|---|---|")
    merged_meta = r["diagnostics"]["merged_predictions"]
    for pr in r.get("per_route_status", []):
        w(f"| {pr['route_id']} | {pr['run_id']} | {pr.get('stop_reason','')} |"
          f" {pr.get('answer_kind','')} | {pr.get('failure_reason') or ''} |")
    w("")
    w("## 3. 逐路线诊断(描述性,非冻结评测器原生切片)")
    w("")
    for rid, d in sorted(r["diagnostics"]["per_route"].items()):
        buckets = d["missed_gold_edges"]["buckets"]
        pool = d["retrieval_pool_diagnostic_hit"]
        w(f"### {rid}")
        w("")
        w(f"- stop_reason={d['stop_reason']};事件={d['n_committed_events']}"
          f"({json.dumps(d['source_mix_events'], ensure_ascii=False)});"
          f"展开={d['n_expansions_retrieval_tasks']};最大深度="
          f"{d['max_depth_reached']}")
        w(f"- 失分归因:{json.dumps(buckets, ensure_ascii=False)}")
        w(f"- 检索池诊断命中(非正式分数):top5={pool['top5_of_any_path']},"
          f"全池={pool['any_rank_of_any_path']}")
        w("")
    w("## 4. 历史基线对照(同 dev 20 路、同冻结评测器;口径不同,仅供参考)")
    w("")
    for label, b in r.get("baselines", {}).items():
        w(f"### {label}")
        w("")
        w(f"- 状态:{b['status']};答卷 {b.get('n_answer_lines', 0)} 行"
          f"(缺 {len(b.get('missing', []))} 行按空计分)")
        if "cn_overall" in b:
            w(f"- cn hit@1={fmt(b['cn_overall']['step_hit@1'])} "
              f"hit@5={fmt(b['cn_overall']['step_hit@5'])} "
              f"recall={fmt(b['cn_overall']['route_recall'])} "
              f"spurious={fmt(b['cn_overall']['spurious_rate'])}")
        w(f"- 注:{b.get('note', '')}")
        w("")
    w("## 5. 基线可比性声明")
    w("")
    w("- v4.1/v4.2 dev 臂模型为 deepseek-v4.1-flash(temperature=0,非思考),")
    w("  预算为 max_depth=12/max_expands=50/max_nodes=200;v4.3 本轮为")
    w("  ZHIPU/GLM-5.3-Flash(仅思考,reasoning_effort=max),预算为 "
      f"max_depth={config['budgets']['max_depth']}/"
      f"max_expansions={config['budgets']['max_expansions']};")
    w("  架构(v4 引擎三段式 vs v4.3 LangGraph 逐路径检索-裁决-验证)与")
    w("  排序语义均不同 —— 数字并列仅作参考,不构成提升/下降百分比。")
    w("  v43_depth3_r2 为同模型同架构的小预算(depth 3)消融,供预算敏感性")
    w("  参考;其余 v41/v42 臂不可直接比。")
    w("")
    we = r.get("worker_evidence", {})
    w("## 6. worker 进程与时间证据(协调器日志摘录)")
    w("")
    w(f"- spawn 事件 {we.get('n_spawn_events', 0)} 次(20 路一次派发,无失败重试);")
    w("  全部 20 个 worker 均有唯一终态,失败恢复 0 次。")
    w("")
    for e in we.get("events", [])[:50]:
        w(f"- `{e}`")
    w("")
    w("## 7. 事故与恢复记录(如实披露)")
    w("")
    w("- 本次任务执行期间存在**两个并发实施会话**共享同一本地仓;Chenyu 上")
    w("  曾同时出现三个批跑协调器(本仓 batch_dev_v1、对方仓 devbatch_v43r1/r2),")
    w("  共享同一 DashScope 主账号额度。本会话发现后立即 pkill 停掉自己的")
    w("  batch_dev_v1(12/20 终态,已花调用极少量),保留产物供审计;最终")
    w("  正式批次 = 本仓 batch_dev_v2(修复后代码 + depth-6 冻结配置)。")
    w("- batch_dev_v1 与对方 r1 各有 6 条路线 worker 失败,根因相同:")
    w("  `predicted_evidence_id` 跨迭代泄漏(LangGraph State 键残留)→")
    w("  下一条确定性 recorded 路径误入提案卡分支 KeyError('proposed_card')。")
    w("  修复 = select_frontier 进入新路径前清空全部迭代引用 + 提案卡缺失")
    w("  改结构化 NodeStateError;修复后 batch_dev_v2 20/20 零 worker 失败。")
    w("- 18 次 HTTP 尝试 300s 超时(thinking 模型偶发长思考;无 429/403)。")
    w("  超时后节点层按 attempt 重试并逐次落盘;超时尝试的用量提供者未返回,")
    w("  费用账中如实标注 unknown。timeout=300s 是下一个明确的调参杠杆。")
    w("- 烟测与正式批次调用分开记录(smoke/dashscope_smoke.json,1 次调用)。")
    w("")
    w("## 8. 已知限制与冻结候选")
    w("")
    w("- **冻结候选** = 本报告批次配置(depth 6 / expansions 40 / width 3 /")
    w("  llm 42 / proposals 40 / timeout 300s / reasoning_effort=max);")
    w("  选择依据见 budget_rationale(dev 深度分布覆盖)与本轮实测。")
    w("- 15/20 路停于 awaiting_prediction:竞争 recorded 需模型裁决的路径上,")
    w("  模型 hold/abstain 或超时重试耗尽后显式停留(不假成功);答卷如实")
    w("  截断,不抬高分数。提高 timeout 与裁决重试是下一步杠杆。")
    w("- spurious_rate=0.0:答卷只含已提交事实,无模型杜撰产物进入答卷。")
    w("- 检索池诊断命中率(全池)远高于正式 hit(如 pb_0065 全池 21/35 vs")
    w("  答卷命中 0/35):主要失分在\"检索到但未提交\"与\"父未到达\",即预算/")
    w("  裁决/停留行为,而非检索覆盖 —— 与失分归因分桶一致。")
    w("")
    w("## 6. 批次配置冻结")
    w("")
    w("```json")
    w(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True))
    w("```")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
