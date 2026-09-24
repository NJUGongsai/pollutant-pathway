#!/usr/bin/env python
"""恢复测试驱动 — 在独立进程里 run / resume 一个 scripted 夹具工作流。

用法(由 tests/test_workflow_recovery.py / test_prediction_recovery.py 以
子进程调用):
    python tests/recovery_driver.py run  --runs-root R --run-id I --smiles S \
        --scripted fixture.json [--counter c.txt] [--crash-after NODE] \
        [--fake-script responses.json] [--model fake|off]
    python tests/recovery_driver.py resume --runs-root R --run-id I \
        --scripted fixture.json [--counter c.txt] [--crash-after NODE] \
        [--fake-script responses.json] [--model fake|off]

crash-after 使指定节点在副作用落盘后、下个 checkpoint 前 os._exit(70)
硬杀进程 —— 模拟真实的「检索/提交/预测调用落盘后中断」。
预测相关注入点:prepare_prediction(任务落盘后)/ call_model(调用记录
issued 落盘后、模型响应前)/ call_model_response(响应落盘后)/
prediction_recorded(prediction.json 落盘后)。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pathway_v43.adapters.llm_client import resolve_model_setup
from pathway_v43.config import resolve_config
from pathway_v43.services.reaction_finder import ScriptedReactionFinder
from pathway_v43.workflow import resume_run, start_run


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "resume"])
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--smiles", default="Oc1ccccc1O")
    ap.add_argument("--scripted", default=None,
                    help="JSON 文件:{substrate_identity: [evidence,...]}")
    ap.add_argument("--counter", default=None,
                    help="真实检索调用计数文件(跨进程累加)")
    ap.add_argument("--llm-counter", default=None,
                    help="fake 模型调用计数文件(跨进程累加)")
    ap.add_argument("--fake-script", default=None,
                    help="fake 模型剧本 JSON:{mode: [响应文本,...]}")
    ap.add_argument("--model", default="off", choices=["off", "fake", "real"])
    ap.add_argument("--crash-after", default=None)
    ap.add_argument("--migrate-from", default=None,
                    help="显式迁移:读取旧 run 身份输入开新 run(旧目录零改动)")
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument("--max-expansions", type=int, default=6)
    ap.add_argument("--max-frontier-width", type=int, default=2)
    a = ap.parse_args()

    try:
        scripted = {}
        if a.scripted:
            scripted = json.loads(Path(a.scripted).read_text(encoding="utf-8"))
        finder = ScriptedReactionFinder(scripted, counter_path=a.counter)
        fake_script = {}
        if a.fake_script:
            fake_script = json.loads(
                Path(a.fake_script).read_text(encoding="utf-8"))
        model = None
        if a.model != "off":
            model = resolve_model_setup(
                a.model, fake_script=fake_script,
                fake_counter_path=a.llm_counter,
            )  # fake 缺省响应按 mode 由剧本耗尽后兜底为空(显式失败)
        if a.mode == "run":
            summary = start_run(
                config=resolve_config(), runs_root=a.runs_root, run_id=a.run_id,
                smiles=a.smiles, max_depth=a.max_depth,
                max_expansions=a.max_expansions,
                max_frontier_width=a.max_frontier_width,
                finder=finder, scripted=True, model=model,
                crash_after=a.crash_after, migrate_from=a.migrate_from,
            )
        else:
            summary = resume_run(
                config=resolve_config(), runs_root=a.runs_root, run_id=a.run_id,
                finder=finder, model=model, crash_after=a.crash_after,
            )
    except Exception as exc:  # 结构化失败(与 CLI 同契约),无 traceback
        print(json.dumps({
            "ok": False,
            "error": {"type": type(exc).__name__, "message": str(exc),
                      "detail": getattr(exc, "detail", {})},
        }, ensure_ascii=False))
        return 2
    print("SUMMARY " + json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
