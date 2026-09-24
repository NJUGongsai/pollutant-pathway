"""pathway_v43 CLI — checkenv/probe(资产接线)+ run/resume/inspect(v4.3 主干)。

    python -m pathway_v43 checkenv [--v3-code-root X] [--assets-root A] [--out PATH] [--analog-rows]
    python -m pathway_v43 probe --smiles "Oc1ccccc1O" [--v3-code-root X] [--assets-root A]
                                [--top-k 10] [--case-id C] [--out PATH]
    python -m pathway_v43 run --smiles SMILES --run-id ID [--max-depth 3]
                              [--max-expansions 10] [--max-frontier-width 3]
                              [--runs-root PATH] [--out PATH]
    python -m pathway_v43 resume --run-id ID [--runs-root PATH] [--out PATH]
    python -m pathway_v43 inspect --run-id ID [--runs-root PATH] [--out PATH]

checkenv 从任意工作目录启动都必须定位并校验同一批 v4.3 资产;失败以结构化
JSON 报告并返回非零;输出不含任何凭证。probe 额外加载真实引擎并输出候选
摘要与 asset_identity(--out 写文件,缺省 stdout)。run/resume/inspect 的
成功输出也是结构化 JSON;inspect 不加载引擎。运行产物在 <runs-root>/<run-id>/
(checkpoint.sqlite、pathway.sqlite、results/、run_identity.json、report/)。
环境变量 PATHWAY_V43_CRASH_AFTER 仅供恢复测试注入硬杀点(取值:节点名)。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path


def _emit(payload: dict, out: str | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if out and out != "-":
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(f"written: {path}", file=sys.stderr)
    else:
        print(text)


def _versions() -> dict:
    import platform

    info = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import rdkit

        info["rdkit"] = rdkit.__version__
    except Exception:
        info["rdkit"] = None
    try:
        import lightgbm

        info["lightgbm"] = lightgbm.__version__
    except Exception:
        info["lightgbm"] = None
    return info


def cmd_checkenv(args: argparse.Namespace) -> int:
    from pathway_v43.config import resolve_config
    from pathway_v43.adapters.asset_manifest import (
        analog_index_shas,
        extension_file_shas,
        verify_repo_manifest,
    )

    config = resolve_config(args.v3_code_root, args.assets_root)
    report: dict = {"command": "checkenv", "config": config.to_dict()}

    # ---- 1. 本仓总清单(21 文件逐一哈希 + MANIFEST.json 三方核对) ----
    manifest = verify_repo_manifest(config.assets_root)
    report["repo_manifest"] = {
        "ok": True,
        "manifest_sha256": manifest["manifest_sha256"],
        "n_files": manifest["n_files"],
        "total_bytes": manifest["total_bytes"],
    }

    # ---- 2. v3 代码根可用性(只查存在性,不导入引擎) ----
    if not config.v3_depending_dir.is_dir():
        raise FileNotFoundError(f"v3 引擎目录缺失:{config.v3_depending_dir}")
    if not (config.v3_depending_dir / "dp_paths.py").is_file():
        raise FileNotFoundError(f"dp_paths.py 缺失:{config.v3_depending_dir}")
    report["v3_code_root"] = {"ok": True, "depending_dir": str(config.v3_depending_dir)}

    # ---- 3. 原版 env_asset_root.resolve_and_verify(显式传本仓运行根) ----
    if str(config.v3_depending_dir) not in sys.path:
        sys.path.insert(0, str(config.v3_depending_dir))
    import env_asset_root as EAR

    identity = EAR.resolve_and_verify(str(config.v3_run_root))
    from pathway_v43.adapters.v3_engine import _require_under

    # 物理边界 = 配置的 assets_root:v3_reactions 若是 symlink 指向旧仓,
    # identity 返回的路径 resolve 后会落在边界外 → 结构化失败
    physical_boundary = str(config.assets_root.resolve())
    for key, value in sorted(identity.items()):
        if key.endswith("_path"):
            _require_under(physical_boundary, value, f"v3 核心资产 {key}")
    report["v3_run_root"] = {
        "ok": True,
        "root": str(config.v3_run_root.resolve()),
        "asset_mode": identity.get("asset_mode"),
        "core_files": {
            k[: -len("_path")]: str(Path(v).resolve())
            for k, v in sorted(identity.items())
            if k.endswith("_path")
        },
    }

    # ---- 4. 扩展资产与两份类比索引:总清单哈希 ----
    report["extension_files"] = extension_file_shas(manifest)
    report["analog_index_files"] = analog_index_shas(manifest)

    # ---- 5. (可选)完整装载两份类比索引并报告行数 ----
    if args.analog_rows:
        from pathway_v43.adapters.analog_index import AnalogAssets

        report["analog"] = AnalogAssets(
            config.assets_root, manifest_identity=manifest
        ).status()

    report["ok"] = True
    report["versions"] = _versions()
    _emit(report, args.out)
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    from pathway_v43.config import resolve_config
    from pathway_v43.adapters.v3_engine import get_engine

    config = resolve_config(args.v3_code_root, args.assets_root)
    engine = get_engine(config)
    candidates = engine.predict(args.smiles, args.case_id, top_k=args.top_k)
    merged = engine.expand_merged(args.smiles, args.case_id)
    payload = {
        "command": "probe",
        "config": config.to_dict(),
        "input": {
            "smiles": args.smiles,
            "case_id": args.case_id,
            "canonical_smiles": merged.get("canonical_smiles"),
        },
        "summary": {
            "n_candidates": len(candidates),
            "n_pred_candidates": merged.get("n_pred_candidates"),
            "n_lookup": merged.get("n_lookup"),
            "lookup_hit": merged.get("lookup_hit"),
            "budget_cut": merged.get("budget_cut"),
        },
        "candidates": candidates,
        "asset_identity": engine.asset_identity(),
        "engine_load_stats": engine.load_stats,
        "versions": _versions(),
        "ok": True,
    }
    _emit(payload, args.out)
    return 0


def _runs_root(args) -> Path:
    from pathway_v43.config import repo_root

    raw = getattr(args, "runs_root", None)
    if raw:
        return Path(raw).expanduser().resolve()
    return repo_root() / "runs"


def _load_fake_script(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _model_setup(provider: str, fake_script: str | None):
    """装配模型;real 提供者缺凭证 → 结构化错误(不冒充可用)。"""
    from pathway_v43.adapters.llm_client import resolve_model_setup

    return resolve_model_setup(
        provider, fake_script=_load_fake_script(fake_script),
    )


def cmd_run(args) -> int:
    from pathway_v43.config import resolve_config
    from pathway_v43.adapters.v3_engine import get_engine
    from pathway_v43.services.reaction_finder import EngineReactionFinder
    from pathway_v43.workflow import start_run

    if args.migrate_from and not args.smiles:
        # 显式迁移:输入取自旧 run 身份(只读),CLI 不必重复给 --smiles
        from pathway_v43.storage.run_identity import load_run_identity

        old = load_run_identity(_runs_root(args), args.migrate_from)
        if old is None:
            raise FileNotFoundError(
                f"迁移来源 run 不存在:{args.migrate_from}")
        args.smiles = old["inputs"]["root_smiles"]
    if not args.smiles:
        raise ValueError("必须提供 --smiles(或 --migrate-from)")

    config = resolve_config(args.v3_code_root, args.assets_root)
    model = None if args.model == "off" else _model_setup(
        args.model, args.fake_script)
    # 模型启用时同时启用类比供体找回(任务书 §1:证据可用性优先)
    engine = get_engine(config)
    analog_resolver = None
    if model is not None:
        from pathway_v43.services.analog_source import AnalogSourceResolver

        analog_resolver = AnalogSourceResolver(config)
    finder = EngineReactionFinder(engine, config,
                                  analog_resolver=analog_resolver)
    summary = start_run(
        config=config, runs_root=_runs_root(args), run_id=args.run_id,
        smiles=args.smiles, max_depth=args.max_depth,
        max_expansions=args.max_expansions,
        max_frontier_width=args.max_frontier_width,
        finder=finder, scripted=False, model=model,
        crash_after=os.environ.get("PATHWAY_V43_CRASH_AFTER") or None,
        migrate_from=args.migrate_from,
        max_llm_calls=args.max_llm_calls, max_proposals=args.max_proposals,
    )
    payload = {"command": "run", "ok": True, **summary}
    _emit(payload, args.out)
    return 0


def cmd_resume(args) -> int:
    from pathway_v43.config import resolve_config
    from pathway_v43.workflow import resume_run

    config = resolve_config(args.v3_code_root, args.assets_root)
    model = None
    if args.model and args.model != "off":
        model = _model_setup(args.model, args.fake_script)
    summary = resume_run(
        config=config, runs_root=_runs_root(args), run_id=args.run_id,
        model=model,
        crash_after=os.environ.get("PATHWAY_V43_CRASH_AFTER") or None,
    )
    payload = {"command": "resume", "ok": True, **summary}
    _emit(payload, args.out)
    return 0


def cmd_inspect(args) -> int:
    from pathway_v43.output.report import inspect_payload
    from pathway_v43.config import repo_root

    payload = {"command": "inspect",
               **inspect_payload(_runs_root(args), args.run_id)}
    _emit(payload, args.out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pathway_v43",
        description="v4.3 CLI(资产接线:checkenv/probe;主干:run/resume/inspect)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--v3-code-root", default=None,
                        help="v3 只读代码根(默认 ../dependingv3 或 $V3_CODE_ROOT)")
    common.add_argument("--assets-root", default=None,
                        help="v4.3 资产根(默认本仓 assets/ 或 $V43_ASSET_ROOT)")
    common.add_argument("--out", default=None,
                        help="JSON 输出文件(缺省 stdout)")
    common.add_argument("--runs-root", default=None,
                        help="运行产物根目录(默认 <repo>/runs)")

    p_check = sub.add_parser("checkenv", parents=[common],
                             help="校验本仓清单、v3 运行根与类比索引(fail-closed)")
    p_check.add_argument("--analog-rows", action="store_true",
                         help="额外完整装载两份类比索引并报告行数(慢)")

    p_probe = sub.add_parser("probe", parents=[common],
                             help="加载引擎并对单分子冒烟,输出候选与 asset_identity")
    p_probe.add_argument("--smiles", required=True)
    p_probe.add_argument("--top-k", type=int, default=10)
    p_probe.add_argument("--case-id", default="probe")

    p_run = sub.add_parser("run", parents=[common],
                           help="从底物出发运行 v4.3 主干(off=确定性;fake/real=预测接线)")
    p_run.add_argument("--smiles", required=False, default="")
    p_run.add_argument("--run-id", required=True)
    p_run.add_argument("--max-depth", type=int, default=3)
    p_run.add_argument("--max-expansions", type=int, default=10)
    p_run.add_argument("--max-frontier-width", type=int, default=3)
    p_run.add_argument("--model", default="off",
                       choices=["off", "fake", "real"],
                       help="模型模式:off(默认,确定性主干)/ fake(剧本假模型)/ "
                            "real(OpenAI 兼容提供者,凭证只读环境变量)")
    p_run.add_argument("--fake-script", default=None,
                       help="fake 模型剧本 JSON:{mode: [响应文本,...]}")
    p_run.add_argument("--max-llm-calls", type=int, default=0,
                       help="LLM 调用预算(0=随 max-expansions 派生)")
    p_run.add_argument("--max-proposals", type=int, default=0,
                       help="新提案提交预算(0=随 max-expansions 派生)")
    p_run.add_argument("--migrate-from", default=None,
                       help="显式迁移:读取旧 run 身份的输入/策略开新 run"
                            "(旧 run 目录零改动;直接 resume 旧 run 仍被身份门槛拒绝)")

    p_resume = sub.add_parser("resume", parents=[common],
                              help="从 LangGraph 检查点恢复既有 run")
    p_resume.add_argument("--run-id", required=True)
    p_resume.add_argument("--model", default="off",
                          choices=["off", "fake", "real"])
    p_resume.add_argument("--fake-script", default=None)

    p_inspect = sub.add_parser("inspect", parents=[common],
                               help="查看 run 状态/停止原因/路径与证据摘要")
    p_inspect.add_argument("--run-id", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "checkenv":
            return cmd_checkenv(args)
        if args.command == "probe":
            return cmd_probe(args)
        if args.command == "run":
            return cmd_run(args)
        if args.command == "resume":
            return cmd_resume(args)
        if args.command == "inspect":
            return cmd_inspect(args)
        parser.error(f"未知子命令:{args.command}")
    except Exception as exc:  # 结构化 fail-closed 退出;不含凭证
        payload = {
            "ok": False,
            "command": getattr(args, "command", "?"),
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "detail": getattr(exc, "detail", {}),
            },
        }
        if os.environ.get("PATHWAY_V43_DEBUG"):
            payload["error"]["traceback"] = traceback.format_exc()
        _emit(payload, getattr(args, "out", None))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
