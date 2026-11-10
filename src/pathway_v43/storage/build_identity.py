"""build_identity — 受控批 build 身份 / 输入字节绑定(T-E/E1a §1.5)。

依据:FROZEN_V3 §5.3(工程前置)与设计稿 v2 §3.6 + Codex 二轮复审
§4.1(最终口径,逐字照落):

- 批根**唯一权威旁块 ``build_identity.json``**(manifest 只放引用/摘要,
  不再另存同内容权威块);
- 载荷 = build 代码聚合身份(code_identity,单一实现源复用)+ 池/source/
  formnorm 版本与指纹 + route/compiler/RDKit + 源资产身份 + 逐
  qid/run_id 输入原始字节 sha256;
- ``build_identity_fingerprint`` = sha256(canonical_json(payload)),
  **只排除**顶层自身哈希键与展示项 ``created_at``/``display_note``
  (排除清单随 schema 登记;代码/资产/版本/参数/RDKit/逐输入 sha 等
  实际身份事实不得排除);
- **首消费核对**:worker 在**创建 run 之前、driver 开始与任何付费调用
  之前**核对(输入原字节 sha + 旁块身份 vs 当前运行时逐字段);
- **run 来源持久化**:核对通过后把 ``{build_identity_fingerprint,
  run_input_sha256, qid, run_id}`` 唯一、不可覆盖地持久化到批侧
  ledger(``build_origin/<qid>.json``,写时 O_EXCL);case 只作摘要,
  不作唯一权威;来源落盘失败 ⇒ 不得继续调用;
- **恢复**:先读并核既存原来源,再与当前已验旁块/输入逐项同值;
  缺/坏/不符 ⇒ 拒并保全原记录(不覆盖、不用当前新摘要补造旧出处);
- **结构化拒因**:``build_identity_invalid``(detail 区分 missing/
  corrupt/version/content_mismatch)、``run_input_bytes_mismatch``、
  ``run_build_origin_mismatch``(detail 区分缺/坏/错);拒绝时失败题
  留分母、零发送;首启核对失败不建 run;恢复失败不改既存 run;
- 范围:**不改** ``run_identity.json`` 机制、**不改** native-export
  schema、不强改通用无批 scripted start(旧批无旁块 ⇒ 显式 legacy
  模式披露,不冒充受控批)。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

BUILD_IDENTITY_FILE = "build_identity.json"
BUILD_IDENTITY_SCHEMA_VERSION = "s5b-build-identity-1"
BUILD_ORIGIN_DIR = "build_origin"
BUILD_ORIGIN_SCHEMA_VERSION = "s5b-build-origin-1"

# 指纹排除清单(仅顶层 3 项;随 schema 登记)
FINGERPRINT_EXCLUSIONS = (
    "build_identity_fingerprint",   # 顶层自身哈希键
    "created_at",                   # 展示项
    "display_note",                 # 展示项
)


class BuildIdentityError(RuntimeError):
    """结构化拒(失败题留分母、零发送;不创建/不修改 run)。"""

    def __init__(self, failure_kind: str, detail: dict | None = None):
        super().__init__(f"{failure_kind}:{detail or {}}")
        self.failure_kind = str(failure_kind)
        self.detail = {"failure_kind": str(failure_kind),
                       **dict(detail or {})}


def _canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def build_identity_fingerprint(payload: dict) -> str:
    """sha256(canonical_json(payload)) 排除清单仅 3 项(顶层)。"""
    slim = {k: v for k, v in dict(payload or {}).items()
            if k not in FINGERPRINT_EXCLUSIONS}
    return hashlib.sha256(_canonical(slim).encode("utf-8")).hexdigest()


def current_build_identity_facts(*, config=None) -> dict:
    """当前运行时身份事实(单一实现源复用;可注入 config 供调用方)."""
    import rdkit

    from .run_identity import (
        PROFILE_POLLUTANT_PATHWAY_V1,
        code_identity,
        retrieval_asset_identity,
    )

    from ..pollutant.recorded_source import (
        CORPUS_RETRIEVAL_VERSION,
        RECORDED_SOURCE_VERSION,
        RECORD_SIDE_FORMNORM_PARAM_SHA256,
        RECORD_SIDE_FORMNORM_VERSION,
    )
    from ..pollutant.s5b_builder import (
        S5B_ANALOG_ROUTE_VERSION,
        S5B_POOL_POLICY_VERSION,
    )
    from ..pollutant.s5b_compiler import S5B_COMPILER_VERSION

    if config is None:
        from ..config import resolve_config

        config = resolve_config()
    return {
        "code_identity_aggregate_sha256":
            code_identity(PROFILE_POLLUTANT_PATHWAY_V1)["aggregate_sha256"],
        "pool_policy_version": S5B_POOL_POLICY_VERSION,
        "recorded_source_version": RECORDED_SOURCE_VERSION,
        "corpus_retrieval_version": CORPUS_RETRIEVAL_VERSION,
        "formnorm_version": RECORD_SIDE_FORMNORM_VERSION,
        "formnorm_param_sha256": RECORD_SIDE_FORMNORM_PARAM_SHA256,
        "route_version": S5B_ANALOG_ROUTE_VERSION,
        "route_version_note": (
            "route ALGORITHM unchanged (F1-F4 branch formulas); routing "
            "RESULTS may change because the input domain changed "
            "(record-side form normalization)"),
        "compiler_version": S5B_COMPILER_VERSION,
        "rdkit_version": str(rdkit.__version__),
        "asset_identity": retrieval_asset_identity(config),
    }


def assemble_build_identity_payload(*, facts: dict,
                                    run_inputs: list[dict],
                                    created_at: str | None = None,
                                    display_note: str | None = None) -> dict:
    """按复审 §4.1 字段集装配载荷(逐 qid/run_id 输入原始字节 sha)。"""
    payload = {
        "schema": {
            "schema_version": BUILD_IDENTITY_SCHEMA_VERSION,
            "file": BUILD_IDENTITY_FILE,
            "fingerprint_definition": (
                "sha256(canonical_json(payload)) with ONLY the "
                "top-level own hash key plus display-only keys excluded"),
            "fingerprint_exclusions": list(FINGERPRINT_EXCLUSIONS),
        },
        **{k: facts[k] for k in sorted(facts)},
        "run_inputs": [dict(e) for e in run_inputs],
    }
    if created_at is not None:
        payload["created_at"] = str(created_at)
    payload["display_note"] = str(display_note or (
        "唯一权威 build 身份旁块(manifest 仅放引用/摘要);身份事实不得"
        "排除;逐 qid 输入原始字节 sha256 供首消费核对"))
    payload["build_identity_fingerprint"] = build_identity_fingerprint(
        payload)
    return payload


def write_build_identity(batch_root: str | Path, payload: dict) -> Path:
    """原子落盘(批根;tmp + os.replace)。"""
    path = Path(batch_root) / BUILD_IDENTITY_FILE
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def write_batch_build_identity(batch_root: str | Path, *,
                               run_input_paths: dict[str, tuple[str, str]],
                               config=None,
                               created_at: str | None = None) -> dict:
    """受控批构建侧入口:算逐 qid 输入 sha256 并写唯一权威旁块。

    ``run_input_paths`` = ``{qid: (run_id, path)}``;读**原始字节**
    计 sha256(含 substrate_sha256 = 题面底物串 sha,核对同域)。
    """
    run_inputs: list[dict] = []
    for qid in sorted(run_input_paths):
        run_id, path = run_input_paths[qid]
        raw = Path(path).read_bytes()
        try:
            substrate = str(json.loads(raw.decode("utf-8")).get(
                "substrate_smiles") or "")
        except (ValueError, UnicodeDecodeError):
            substrate = ""
        run_inputs.append({
            "qid": str(qid),
            "run_id": str(run_id),
            "run_input_sha256": hashlib.sha256(raw).hexdigest(),
            "substrate_sha256": hashlib.sha256(
                substrate.encode("utf-8")).hexdigest(),
        })
    facts = current_build_identity_facts(config=config)
    payload = assemble_build_identity_payload(
        facts=facts, run_inputs=run_inputs, created_at=created_at)
    write_build_identity(batch_root, payload)
    return payload


# ---------------------------------------------------------------- 首消费核对


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def manifest_declares_build_identity(batch_root: str | Path) -> bool:
    manifest = _load_json(Path(batch_root) / "batch_manifest.json")
    if not isinstance(manifest, dict):
        return False
    ref = manifest.get("build_identity_ref")
    return bool(ref) if ref is not None else False


def load_build_identity(batch_root: str | Path) -> dict:
    """读旁块(缺/坏/版本不明 ⇒ 结构化拒 build_identity_invalid)。"""
    path = Path(batch_root) / BUILD_IDENTITY_FILE
    if not path.is_file():
        raise BuildIdentityError("build_identity_invalid", {
            "kind": "missing",
            "expected_file": BUILD_IDENTITY_FILE})
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise BuildIdentityError("build_identity_invalid", {
            "kind": "corrupt",
            "detail": "unreadable_or_not_object",
            "expected_file": BUILD_IDENTITY_FILE})
    schema = payload.get("schema") or {}
    version = str(schema.get("schema_version") or "") \
        if isinstance(schema, dict) else ""
    if version != BUILD_IDENTITY_SCHEMA_VERSION:
        raise BuildIdentityError("build_identity_invalid", {
            "kind": "version",
            "expected_schema_version": BUILD_IDENTITY_SCHEMA_VERSION,
            "actual_schema_version": version})
    stored_fp = str(payload.get("build_identity_fingerprint") or "")
    if stored_fp != build_identity_fingerprint(payload):
        raise BuildIdentityError("build_identity_invalid", {
            "kind": "corrupt",
            "detail": "fingerprint_recompute_mismatch"})
    return payload


def _content_diff(payload: dict, facts: dict) -> list[str]:
    diffs: list[str] = []
    for key in sorted(facts):
        if key == "asset_identity":
            continue
        if payload.get(key) != facts[key]:
            diffs.append(key)
    if payload.get("asset_identity") != facts.get("asset_identity"):
        diffs.append("asset_identity")
    return diffs


def verify_batch_build_identity(
        *, batch_root: str | Path, qid: str, run_id: str,
        run_input_bytes: bytes, current_facts: dict | None = None) -> dict:
    """首消费核对(创建 run/任何付费调用之前)。

    返回 ``{"mode": "verified"|"legacy_absent_disclosed",
    "build_identity_fingerprint", "run_input_sha256"}``。
    旧批(无旁块且 manifest 未声明引用)⇒ legacy 模式显式披露(不冒充
    受控批;设计 §3.6 范围预算"旁块只加不拦旧批只读")。受控批
    (旁块在位或 manifest 声明引用)⇒ 缺/坏/版本不明/内容不符/输入
    字节不符全部结构化拒。
    """
    root = Path(batch_root)
    declared = manifest_declares_build_identity(root)
    block_exists = (root / BUILD_IDENTITY_FILE).is_file()
    if not declared and not block_exists:
        return {"mode": "legacy_absent_disclosed",
                "build_identity_fingerprint": "",
                "run_input_sha256": hashlib.sha256(
                    run_input_bytes).hexdigest(),
                "claim": ("legacy batch without build_identity block: "
                          "no build-origin proof claimed; not a "
                          "controlled batch")}
    payload = load_build_identity(root)
    facts = current_facts if current_facts is not None \
        else current_build_identity_facts()
    diffs = _content_diff(payload, facts)
    if diffs:
        raise BuildIdentityError("build_identity_invalid", {
            "kind": "content_mismatch",
            "fields": diffs[:12],
            "n_diff_fields": len(diffs)})
    entry = None
    for e in payload.get("run_inputs") or []:
        if isinstance(e, dict) and str(e.get("qid")) == str(qid):
            entry = e
            break
    if entry is None:
        raise BuildIdentityError("run_input_bytes_mismatch", {
            "kind": "missing_entry", "qid": str(qid)})
    if str(entry.get("run_id")) != str(run_id):
        raise BuildIdentityError("run_input_bytes_mismatch", {
            "kind": "run_id_mismatch",
            "qid": str(qid),
            "block_run_id": str(entry.get("run_id")),
            "input_run_id": str(run_id)})
    actual = hashlib.sha256(run_input_bytes).hexdigest()
    if str(entry.get("run_input_sha256")) != actual:
        raise BuildIdentityError("run_input_bytes_mismatch", {
            "kind": "sha256_mismatch",
            "qid": str(qid),
            "block_sha256": str(entry.get("run_input_sha256"))[:16],
            "actual_sha256": actual[:16]})
    try:
        substrate = str(json.loads(
            run_input_bytes.decode("utf-8")).get("substrate_smiles") or "")
    except (ValueError, UnicodeDecodeError):
        substrate = ""
    sub_actual = hashlib.sha256(substrate.encode("utf-8")).hexdigest()
    if str(entry.get("substrate_sha256")) != sub_actual:
        raise BuildIdentityError("run_input_bytes_mismatch", {
            "kind": "substrate_sha256_mismatch", "qid": str(qid)})
    return {"mode": "verified",
            "build_identity_fingerprint": str(
                payload.get("build_identity_fingerprint") or ""),
            "run_input_sha256": actual}


# ---------------------------------------------------------------- run 来源


def _origin_path(batch_root: str | Path, qid: str) -> Path:
    return Path(batch_root) / BUILD_ORIGIN_DIR / f"{qid}.json"


def _origin_core(*, qid: str, run_id: str, verified: dict) -> dict:
    return {
        "schema": BUILD_ORIGIN_SCHEMA_VERSION,
        "qid": str(qid),
        "run_id": str(run_id),
        "build_identity_fingerprint": str(
            verified.get("build_identity_fingerprint") or ""),
        "run_input_sha256": str(verified.get("run_input_sha256") or ""),
    }


def _origin_equal(saved: dict, expected: dict) -> bool:
    return all(saved.get(k) == expected.get(k) for k in (
        "qid", "run_id", "build_identity_fingerprint",
        "run_input_sha256"))


def prepare_build_origin(*, batch_root: str | Path, qid: str, run_id: str,
                         verified: dict, resume: bool) -> dict:
    """唯一、不可覆盖的 run 来源持久化 + 恢复同核(复审 §4.1)。

    - legacy 模式(无旁块)⇒ 不写来源(显式披露;不受控批不冒充);
    - 既存来源:先读并核 ⇒ 坏/不符 ⇒ ``run_build_origin_mismatch``
      拒并**保全原记录**(不覆盖、不用当前新摘要补造旧出处);
    - 无来源:恢复路径(run 已存在)⇒ 缺 = 拒(detail missing);
      首启路径 ⇒ O_EXCL 写;写失败 ⇒ 拒(write_failed;不得继续调用)。
    """
    if str(verified.get("mode")) != "verified":
        return {"mode": "legacy_absent_disclosed"}
    expected = _origin_core(qid=qid, run_id=run_id, verified=verified)
    path = _origin_path(batch_root, qid)
    if path.is_file():
        saved = _load_json(path)
        if not isinstance(saved, dict):
            raise BuildIdentityError("run_build_origin_mismatch", {
                "kind": "corrupt", "qid": str(qid),
                "expected_file": str(path.name)})
        if not _origin_equal(saved, expected):
            raise BuildIdentityError("run_build_origin_mismatch", {
                "kind": "mismatch", "qid": str(qid),
                "saved_fingerprint8": str(saved.get(
                    "build_identity_fingerprint") or "")[:8],
                "expected_fingerprint8": str(expected.get(
                    "build_identity_fingerprint") or "")[:8]})
        return {"mode": "verified_existing", **expected}
    if resume:
        raise BuildIdentityError("run_build_origin_mismatch", {
            "kind": "missing", "qid": str(qid),
            "note": ("既有 run 缺来源记录(run 经由未绑定路径创建?)"
                     "——拒并保全原记录,不覆盖、不补造")})
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # 目录不可建(路径被占等)⇒ 落盘失败拒
        raise BuildIdentityError("run_build_origin_mismatch", {
            "kind": "write_failed", "qid": str(qid),
            "detail": f"{type(exc).__name__}"}) from exc
    try:
        # 唯一不可覆盖:O_EXCL 创建(已存在 ⇒ FileExistsError,不覆盖)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(
                    expected, ensure_ascii=False, sort_keys=True,
                    indent=1) + "\n")
        except OSError:
            raise
    except FileExistsError:
        saved = _load_json(path)
        if not isinstance(saved, dict) or not _origin_equal(saved, expected):
            raise BuildIdentityError("run_build_origin_mismatch", {
                "kind": "mismatch", "qid": str(qid),
                "note": "concurrent_existing_record_differs"}) from None
        return {"mode": "verified_existing", **expected}
    except OSError as exc:
        raise BuildIdentityError("run_build_origin_mismatch", {
            "kind": "write_failed", "qid": str(qid),
            "detail": f"{type(exc).__name__}"}) from exc
    return {"mode": "persisted_new", **expected}