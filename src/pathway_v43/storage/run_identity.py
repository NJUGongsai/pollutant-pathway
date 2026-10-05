"""run_identity — 一次运行的完整身份(代码/资产/策略),resume 的核对门槛。

resume 必须核对本文件与当前代码、资产、策略身份:任一变更都拒绝静默
继续旧 run(任务书 §2)。代码身份取 src/pathway_v43 的逐文件 SHA256 与
聚合哈希(按 profile 分集:legacy 排除 pollutant/ 新包);依赖版本
(langgraph 等)一并记录。v2(v43-identity-2)新增 profile 块:legacy_v43
(缺省,口径不变)与 pollutant_pathway_v1(显式启用的新模式)。
"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

from ..domain.models import DOMAIN_SCHEMA_VERSION, STRATEGY_VERSION, now_iso

IDENTITY_SCHEMA_VERSION = "v43-identity-2"
# v2:新增 profile 块(污染物路径实施书 §3.1 新旧模式分开);v1 保存的
# identity 无该字段,读取端按 legacy_v43 兼容。本文件自身随 v2 变更,
# 升级后旧 run 的一次性 resume 拒绝(code_identity 变化)是设计行为。

PROFILE_LEGACY_V43 = "legacy_v43"
PROFILE_POLLUTANT_PATHWAY_V1 = "pollutant_pathway_v1"
KNOWN_PROFILES = frozenset({PROFILE_LEGACY_V43, PROFILE_POLLUTANT_PATHWAY_V1})
# 新 profile 专属代码根:legacy 的 code_identity 排除该目录(加新文件
# 不再废掉 legacy 的同版本恢复);pollutant profile 哈希全树(它依赖
# legacy 模块)。前缀按包内相对路径(pathway_v43/pollutant/...)匹配。
PROFILE_EXCLUSIVE_PACKAGE_PREFIX = "pathway_v43/pollutant/"

# v35 资产集的环境 lookup 库(v3 identity block "library" 实际指向的文件;
# 旧 P4.2 的 eawag/donor_product.jsonl 已被 library/library_full.jsonl 取代)
RECORDING_SOURCE_FILE = "v3_reactions/library/library_full.jsonl"


def retrieval_asset_identity(config) -> dict:
    """检索资产身份(统一形状,start/resume/证据卡共用)。

    真实模式走本仓总清单校验(不装载引擎);scripted 模式用于合成夹具。
    """
    from ..adapters.asset_manifest import verify_repo_manifest

    from ..adapters.asset_manifest import analog_corpus_rel

    manifest = verify_repo_manifest(config.assets_root)
    corpus_rel = analog_corpus_rel(
        getattr(config, "analog_corpus", "v1"))
    return {
        "mode": "repo_assets",
        "assets_root": manifest["assets_root"],
        "manifest_sha256": manifest["manifest_sha256"],
        "n_manifest_files": manifest["n_files"],
        "source_file": RECORDING_SOURCE_FILE,
        "source_file_sha256": manifest["files"].get(RECORDING_SOURCE_FILE),
        # Phase D D2:所选类比语料版本 + SHA 进入 run 身份
        # (v1/v2 臂身份不同;资产变化拒绝旧 run resume)
        "analog_corpus": getattr(config, "analog_corpus", "v1"),
        "analog_corpus_file": corpus_rel,
        "analog_corpus_sha256": manifest["files"].get(corpus_rel),
    }


def scripted_asset_identity() -> dict:
    return {
        "mode": "scripted_fixture",
        "manifest_sha256": "scripted-fixture",
        "source_file": "fixtures://scripted",
        "source_file_sha256": "scripted-fixture",
    }


def code_identity(profile: str = PROFILE_LEGACY_V43) -> dict:
    """本包代码身份:src/pathway_v43/**/*.py 的逐文件 SHA256 + 聚合哈希。

    按 profile 分集(§3.1 新旧分开):legacy_v43 只绑定 legacy 执行路径
    文件,排除 pollutant/ 新包(此后新 profile 代码变更不再改变 legacy
    身份);pollutant_pathway_v1 哈希全树(新 profile 复用 legacy 模块)。
    profile 未知一律拒绝(不猜测默认)。
    """
    if profile not in KNOWN_PROFILES:
        raise ValueError(
            f"未知 profile:{profile!r}(允许 {sorted(KNOWN_PROFILES)})")
    root = Path(__file__).resolve().parents[1]
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root.parent).as_posix()
        if (profile == PROFILE_LEGACY_V43
                and rel.startswith(PROFILE_EXCLUSIVE_PACKAGE_PREFIX)):
            continue
        files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    aggregate = hashlib.sha256(
        "\n".join(f"{k}:{v}" for k, v in sorted(files.items())).encode()
    ).hexdigest()
    return {"profile": profile, "files": files, "aggregate_sha256": aggregate}


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
    profile: str = PROFILE_LEGACY_V43,
    profile_policy: dict | None = None,
) -> dict:
    """完整 run 身份(任务书 §4:锁定模型、提示词、MoleCode 实现、资产与策略)。

    prediction: 预测身份块(ModelSetup.identity_block();off 时由本函数
    构造与 workflow.runner._prediction_block 一致的默认块,保证 resume
    重建身份可比)。
    molecode:AtomTool vendor 身份(实现被改 → resume 拒绝)。
    profile:新旧模式分开(§3.1):legacy_v43 为缺省(行为与既有口径一致);
    pollutant_pathway_v1 时 profile 块取自 pollutant.profile(延迟 import,
    legacy 路径不依赖新包),code_identity 按分集规则计算。profile_policy
    为新模式的显式开关块(input_preview_policy 等;legacy 时必须为 None)。
    """
    from ..domain.policy import PREDICTION_POLICY_VERSION
    from ..services.atom_tool import verify_vendor_integrity

    # 裁决 schema/策略版本进入身份:排序或门禁规则变更 = 不同身份,
    # 旧 run resume 被拒(任务书 Phase B §3.5)
    from ..services.report_adjudication import (
        REPORT_ADJUDICATION_POLICY_VERSION,
        REPORT_ADJUDICATION_SCHEMA_V2,
    )

    if profile not in KNOWN_PROFILES:
        raise ValueError(
            f"未知 profile:{profile!r}(允许 {sorted(KNOWN_PROFILES)})")
    if profile == PROFILE_LEGACY_V43 and profile_policy is not None:
        raise ValueError("legacy_v43 不接受 profile_policy(无新模式开关)")
    if profile == PROFILE_POLLUTANT_PATHWAY_V1:
        from ..pollutant.profile import build_profile_identity_block

        profile_block = build_profile_identity_block(**(
            profile_policy or {}))
    else:
        profile_block = {"name": PROFILE_LEGACY_V43}

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
        "profile": profile_block,
        "strategy": {"version": STRATEGY_VERSION, **strategy},
        "asset_identity": asset_identity,
        "v3_engine_code": v3_code_identity,
        "prediction": prediction or {
            "enabled": False, "provider": "off", "model_id": "",
            "prompt_versions": {},
            "policy_version": PREDICTION_POLICY_VERSION, "policy": {},
        },
        "adjudication": {
            "schema_version": REPORT_ADJUDICATION_SCHEMA_V2,
            "policy_version": REPORT_ADJUDICATION_POLICY_VERSION,
        },
        "molecode": molecode_block,
        "code_identity": code_identity(profile),
        "dependency_versions": dependency_versions(),
    }


def identity_fingerprint(identity: dict) -> str:
    """参与 resume 核对的字段指纹(排除 created_at 等时间性字段)。"""
    keys = ("domain_schema_version", "inputs", "profile", "strategy",
            "asset_identity", "v3_engine_code", "prediction", "adjudication",
            "molecode", "code_identity", "dependency_versions")
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
    for key in ("domain_schema_version", "inputs", "profile", "strategy",
                "asset_identity", "v3_engine_code", "prediction",
                "adjudication", "molecode", "code_identity",
                "dependency_versions"):
        # v43-identity-1 旧身份无 profile 块:按 legacy_v43 兼容读取
        # (缺字段不单独拒;code_identity 差异仍会如实拒绝)
        saved_val = saved.get(key)
        current_val = current.get(key)
        if key == "profile" and saved_val is None:
            saved_val = {"name": PROFILE_LEGACY_V43}
        if saved_val != current_val:
            diffs[key] = {"saved_fingerprint": _fp(saved_val),
                          "current_fingerprint": _fp(current_val)}
    if diffs:
        raise IdentityMismatch(diffs)


def _fp(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:12]
