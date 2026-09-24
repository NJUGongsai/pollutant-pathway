"""run_identity — 一次运行的完整身份(代码/资产/策略),resume 的核对门槛。

resume 必须核对本文件与当前代码、资产、策略身份:任一变更都拒绝静默
继续旧 run(任务书 §2)。本仓不是 git 仓,代码身份取 src/pathway_v43
全部 .py 的逐文件 SHA256 与聚合哈希;依赖版本(langgraph 等)一并记录。
"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

from ..domain.models import DOMAIN_SCHEMA_VERSION, STRATEGY_VERSION, now_iso

IDENTITY_SCHEMA_VERSION = "v43-identity-1"

# v35 资产集的环境 lookup 库(v3 identity block "library" 实际指向的文件;
# 旧 P4.2 的 eawag/donor_product.jsonl 已被 library/library_full.jsonl 取代)
RECORDING_SOURCE_FILE = "v3_reactions/library/library_full.jsonl"


def retrieval_asset_identity(config) -> dict:
    """检索资产身份(统一形状,start/resume/证据卡共用)。

    真实模式走本仓总清单校验(不装载引擎);scripted 模式用于合成夹具。
    """
    from ..adapters.asset_manifest import verify_repo_manifest

    manifest = verify_repo_manifest(config.assets_root)
    return {
        "mode": "repo_assets",
        "assets_root": manifest["assets_root"],
        "manifest_sha256": manifest["manifest_sha256"],
        "n_manifest_files": manifest["n_files"],
        "source_file": RECORDING_SOURCE_FILE,
        "source_file_sha256": manifest["files"].get(RECORDING_SOURCE_FILE),
    }


def scripted_asset_identity() -> dict:
    return {
        "mode": "scripted_fixture",
        "manifest_sha256": "scripted-fixture",
        "source_file": "fixtures://scripted",
        "source_file_sha256": "scripted-fixture",
    }


def code_identity() -> dict:
    """本包代码身份:src/pathway_v43/**/*.py 的逐文件 SHA256 + 聚合哈希。"""
    root = Path(__file__).resolve().parents[1]
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root.parent).as_posix()
        files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    aggregate = hashlib.sha256(
        "\n".join(f"{k}:{v}" for k, v in sorted(files.items())).encode()
    ).hexdigest()
    return {"files": files, "aggregate_sha256": aggregate}


def dependency_versions() -> dict:
    info = {"python": platform.python_version()}
    for mod_name in ("rdkit", "lightgbm", "langgraph", "langgraph.checkpoint",
                     "langgraph.checkpoint.sqlite"):
        try:
            mod = __import__(mod_name, fromlist=["__version__"])
            info[mod_name] = getattr(mod, "__version__", None)
        except Exception:
            info[mod_name] = None
    return info


def build_run_identity(
    *,
    run_id: str,
    root_smiles: str,
    root_cn: str,
    strategy: dict,
    asset_identity: dict,
    v3_code_identity: dict,
    prediction: dict | None = None,
) -> dict:
    """完整 run 身份(任务书 §4:锁定模型、提示词、MoleCode 实现、资产与策略)。

    prediction: 预测身份块(ModelSetup.identity_block();off 时由本函数
    构造与 workflow.runner._prediction_block 一致的默认块,保证 resume
    重建身份可比)。
    molecode:AtomTool vendor 身份(实现被改 → resume 拒绝)。
    """
    from ..domain.policy import PREDICTION_POLICY_VERSION
    from ..services.atom_tool import verify_vendor_integrity

    try:
        molecode_block = verify_vendor_integrity()
    except Exception as exc:  # vendor 缺失/被改:身份如实记录失败原因
        molecode_block = {"integrity": "failed", "reason": str(exc)[:200]}
    return {
        "schema_version": IDENTITY_SCHEMA_VERSION,
        "domain_schema_version": DOMAIN_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": now_iso(),
        "inputs": {"root_smiles": root_smiles, "root_identity": root_cn},
        "strategy": {"version": STRATEGY_VERSION, **strategy},
        "asset_identity": asset_identity,
        "v3_engine_code": v3_code_identity,
        "prediction": prediction or {
            "enabled": False, "provider": "off", "model_id": "",
            "prompt_versions": {},
            "policy_version": PREDICTION_POLICY_VERSION, "policy": {},
        },
        "molecode": molecode_block,
        "code_identity": code_identity(),
        "dependency_versions": dependency_versions(),
    }


def identity_fingerprint(identity: dict) -> str:
    """参与 resume 核对的字段指纹(排除 created_at 等时间性字段)。"""
    keys = ("domain_schema_version", "inputs", "strategy", "asset_identity",
            "v3_engine_code", "prediction", "molecode", "code_identity",
            "dependency_versions")
    slim = {k: identity.get(k) for k in keys}
    return hashlib.sha256(
        json.dumps(slim, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def write_run_identity(runs_dir: str | Path, identity: dict) -> Path:
    path = Path(runs_dir) / identity["run_id"] / "run_identity.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return path


def load_run_identity(runs_dir: str | Path, run_id: str) -> dict | None:
    path = Path(runs_dir) / run_id / "run_identity.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class IdentityMismatch(RuntimeError):
    def __init__(self, differences: dict) -> None:
        super().__init__(
            "resume 拒绝:run 身份与当前代码/资产/策略不一致,"
            f"差异字段:{sorted(differences)};不得静默继续旧 run"
        )
        self.detail = {"differences": differences}


def check_resume_identity(saved: dict, current: dict) -> None:
    diffs: dict = {}
    for key in ("domain_schema_version", "inputs", "strategy",
                "asset_identity", "v3_engine_code", "prediction",
                "molecode", "code_identity", "dependency_versions"):
        if saved.get(key) != current.get(key):
            diffs[key] = {"saved_fingerprint": _fp(saved.get(key)),
                          "current_fingerprint": _fp(current.get(key))}
    if diffs:
        raise IdentityMismatch(diffs)


def _fp(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:12]
