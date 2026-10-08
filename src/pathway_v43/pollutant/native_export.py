"""S4b 原生正式导出 —— 文件级 payload + manifest + 读取/过期/完整性
首消费(契约 ppv1-native-export-1 / native-export-policy-1 登记)。

S4b 范围(任务书 §7 S4b 第 1-4 项 + §4.4 G02):把 S4a 原生结果对象
落为**正式文件导出**(run 目录 ``native_export/<export_digest>/``):

- ``payload.json``:原生结果全量载荷(canonical_json 字节,含
  content_digest;共同产物/备选/不同来路/条件/依赖/audit/proof
  scope/deferred/未展开集合/预算/停止原因/endpoint 分账全字段 ——
  导出不截断、不按 CN 合并、不改写 unknown/partial/deferred);
- ``manifest.json``:导出身份与新鲜度锚(全部版本常量、固定导出
  策略、payload 字节 sha、**graph revision 等价身份** = 全部事实表
  内容 digest、权威引用(endpoint/stop 行 hash、原生结果 artifact、
  逐 artifact 内容 hash、冻结计划))。

确定性(G02):payload 与 manifest 均无时间戳、键序固定、列表稳定
排序;``export_digest = content_hash(manifest 核心)`` ⇒ 相同事实 +
相同版本 + 相同策略 ⇒ 相同目录、相同字节(同进程/跨进程一致);
事实变化 = 新 digest = 新目录,旧导出文件**保全不覆盖**(历史保留,
按 digest 可回溯)。

首消费(读取)按固定次序核验,fail-closed 结构化拒绝(kind):

1. 文件缺失 ⇒ ``export_missing``;
2. manifest 不可解析/缺 export_digest/与请求 digest 不符 ⇒
   ``export_manifest_corrupt``(integrity);
3. payload 字节 sha 与 manifest 不符 ⇒ ``export_payload_corrupt``
   (integrity;保全原文件,不覆盖不重算);
4. manifest schema 版本未知 ⇒ ``export_version_unknown``(fail-closed
   不猜迁移);
5. payload 内容 digest 复算不符 ⇒ ``export_digest_mismatch``;
6. 权威引用断裂(endpoint/stop 行、原生结果 artifact、被引用
   artifact、冻结计划;含内容 hash 不一致)⇒
   ``export_reference_mismatch``(endpoint 记录自身的 staleness 由
   read_run_endpoint 首消费先行 —— 输入漂移先以 endpoint 拒绝浮出);
7. 导出策略 hash 不符 ⇒ ``export_policy_stale``(stale 类;策略/版本
   变化后旧导出不得当当前结果);
8. graph facts digest 与当前持久权威不符 ⇒ ``export_stale``
   (stale 类;改变源图 ⇒ 旧结果过期,不能静默消费)。

防"洗白":过期/损坏导出**零写入、原文件保全**;自洽重写 payload +
manifest(重算内部 hash)逃不过第 6/8 条 —— 引用与事实 digest 从
独立权威(DB 行 + artifact store)重算,不信任 manifest 自声明。
不做密码学签名、不抗全库协同改写(沿 S3B-01/S4a 同一边界披露)。

边界:本模块不修改 legacy/export_v3.py(v3 有损投影见
v3_projection.py);不产生新化学判定(纯派生文件);payload 即
S4a 原生结果(不另造第二套字段);导出/读取共用本模块判据,
不在其他入口复制。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ..domain.models import canonical_json, content_hash
from .endpoint import read_run_endpoint
from .native_result import (
    NATIVE_RESULT_ARTIFACT,
    NATIVE_RESULT_TASK_KEY,
    artifact_reference_index,
    read_native_result,
)
from .profile import (
    PPV1_ENDPOINT_POLICY_VERSION,
    PPV1_ENDPOINT_SCHEMA_VERSION,
    PPV1_NATIVE_EXPORT_POLICY_VERSION,
    PPV1_NATIVE_EXPORT_VERSION,
    PPV1_NATIVE_RESULT_VERSION,
    PPV1_PROFILE_SCHEMA_VERSION,
    PPV1_RUNFLOW_SCHEMA_VERSION,
    PPV1_SEARCH_SCHEMA_VERSION,
    PPV1_STORE_SCHEMA_VERSION,
)
from .search import read_search_artifact

NATIVE_EXPORT_SUBDIR = "native_export"
NATIVE_EXPORT_PAYLOAD_FILE = "payload.json"
NATIVE_EXPORT_MANIFEST_FILE = "manifest.json"

# 冻结计划 artifact 引用(runflow 常量的单一来源;延迟导入避免
# 模块级循环:runflow → native_export → runflow 常量)
_FROZEN_PLAN_TASK_KEY = "run-plan"
_FROZEN_PLAN_ARTIFACT = "frozen_plan"


class NativeExportContractError(RuntimeError):
    """原生正式导出契约违反(结构化 fail-closed;零写入)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class NativeExportConflict(NativeExportContractError):
    """同 digest 目录已存在不同内容(不可变导出;保全原文件)。"""


def native_export_policy() -> dict:
    """固定导出策略(ppv1-native-export-policy-1;无用户可配项)。

    变更任一规则(序列化/命名/无时间戳/manifest 组成)须升
    PPV1_NATIVE_EXPORT_POLICY_VERSION —— 旧导出按 policy stale 拒。
    """
    return {
        "version": PPV1_NATIVE_EXPORT_POLICY_VERSION,
        "payload_serialization": "canonical_json_sortkeys_compact_newline",
        "manifest_serialization": "canonical_json_sortkeys_compact_newline",
        "directory_naming": "native_export/<export_digest[:24]>/",
        "export_digest_basis":
            "content_hash(manifest_core_without_export_digest)",
        "payload_timestamps": "forbidden",
        "manifest_timestamps": "forbidden",
        "overwrite": "forbidden_same_digest_different_bytes_refused",
        "stale_detection":
            "graph_facts_digests+authority_references+policy_hash",
    }


def export_policy_hash(policy: dict) -> str:
    return hashlib.sha256(
        canonical_json(policy).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- 事实 digest


def _table_digest(conn, sql: str, params: tuple = ()) -> str:
    """一张(组)事实行的内容 digest(全行、稳定排序;payload 保持
    原始 JSON 字符串形态 —— 与行内容一一对应,不重解释)。"""
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    return content_hash([
        [row.get(k) for k in sorted(row)] for row in rows])


def graph_facts_digests(ledger) -> dict:
    """**graph revision 等价身份**:PPV1 pollutant 存储没有整数
    graph_revision(那是 legacy PathwayStore 的概念);本仓的事实图
    修订身份 = 全部持久事实表的逐表内容 digest(全行,含派生投影表)。
    任何事实行新增/改写 ⇒ 对应 digest 变化 ⇒ 旧导出 stale。"""
    conn = ledger.conn
    run_id = ledger.run_id
    facts = {
        "states": _table_digest(conn, "SELECT * FROM states"),
        "state_appearances": _table_digest(
            conn, "SELECT state_id, appearance_hash, payload, created_at"
            " FROM state_appearances"),
        "hypotheses": _table_digest(conn, "SELECT * FROM hypotheses"),
        "events": _table_digest(conn, "SELECT * FROM events"),
        "report_projections": _table_digest(
            conn, "SELECT * FROM report_projections"),
        "expansion_plans": _table_digest(
            conn, "SELECT * FROM expansion_plans"),
        "event_appearance_links": _table_digest(
            conn, "SELECT * FROM event_appearance_links"),
        "provenance_records": _table_digest(
            conn, "SELECT * FROM provenance_records WHERE run_id = ?",
            (run_id,)),
        "search_actions": _table_digest(
            conn, "SELECT * FROM search_actions WHERE run_id = ?",
            (run_id,)),
        "search_attempts": _table_digest(
            conn, "SELECT * FROM search_attempts WHERE run_id = ?",
            (run_id,)),
        "budget_reservations": _table_digest(
            conn, "SELECT * FROM budget_reservations WHERE run_id = ?",
            (run_id,)),
        "model_requests": _table_digest(
            conn, "SELECT * FROM model_requests WHERE run_id = ?",
            (run_id,)),
        "search_commit_records": _table_digest(
            conn, "SELECT * FROM search_commit_records WHERE run_id = ?",
            (run_id,)),
        "stop_reason_records": _table_digest(
            conn, "SELECT run_id, payload, payload_hash FROM"
            " stop_reason_records WHERE run_id = ?", (run_id,)),
        "endpoint_records": _table_digest(
            conn, "SELECT run_id, payload, payload_hash FROM"
            " endpoint_records WHERE run_id = ?", (run_id,)),
    }
    facts["note"] = (
        "PPV1 graph revision 等价身份 = 持久事实表逐表内容 digest"
        "(legacy 整数 graph_revision 不适用;任何行变化 ⇒ 旧导出 stale)")
    return facts


def _artifact_references(ledger) -> dict:
    """导出消费的全部 artifact 的内容 hash 引用(单一来源:
    native_result.artifact_reference_index + 冻结计划 + 原生结果
    artifact 自身;读取侧逐条重读核对 —— 依赖对象内容变化 ⇒
    reference_mismatch 拒)。"""
    refs: dict[str, dict] = {}
    for entry in artifact_reference_index(ledger):
        envelope = read_search_artifact(
            ledger.artifact_store, entry["task_key"], entry["name"])
        if envelope is None:
            continue
        refs[f"{entry['task_key']}/{entry['name']}"] = {
            "payload_hash": str(envelope.get("payload_hash") or ""),
            "source_action_id": entry["source_action_id"],
        }
    frozen = read_search_artifact(
        ledger.artifact_store, _FROZEN_PLAN_TASK_KEY, _FROZEN_PLAN_ARTIFACT)
    if frozen is not None:
        refs[f"{_FROZEN_PLAN_TASK_KEY}/{_FROZEN_PLAN_ARTIFACT}"] = {
            "payload_hash": str(frozen.get("payload_hash") or ""),
            "source_action_id": "",
        }
    return dict(sorted(refs.items()))


def _authority_references(ledger, native_result: dict) -> dict:
    """DB 通道独立权威引用(endpoint/stop 行 hash;原生结果 artifact
    键与内容 digest)。"""
    conn = ledger.conn
    run_id = ledger.run_id
    stop_row = conn.execute(
        "SELECT payload_hash FROM stop_reason_records WHERE run_id = ?",
        (run_id,)).fetchone()
    endpoint_row = conn.execute(
        "SELECT payload_hash FROM endpoint_records WHERE run_id = ?",
        (run_id,)).fetchone()
    return {
        "stop_record_payload_hash":
            str(stop_row["payload_hash"]) if stop_row is not None else "",
        "endpoint_record_payload_hash":
            str(endpoint_row["payload_hash"])
            if endpoint_row is not None else "",
        "native_result_task_key": f"{NATIVE_RESULT_TASK_KEY}:"
                                  f"{str(native_result['content_digest'])[:24]}",
        "native_result_content_digest":
            str(native_result["content_digest"]),
    }


# ---------------------------------------------------------------- 写入


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(
        f"{path.name}.{os.getpid()}.{_atomic_write_seq():d}.tmp")
    tmp.write_bytes(data)
    try:
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


_SEQ = [0]


def _atomic_write_seq() -> int:
    _SEQ[0] += 1
    return _SEQ[0]


def _write_immutable(path: Path, data: bytes) -> bool:
    """不可变写入:目标已存在 ⇒ 字节相同幂等(created=False),不同 ⇒
    NativeExportConflict(保全原文件,绝不覆盖)。"""
    if path.exists():
        if path.read_bytes() == data:
            return False
        raise NativeExportConflict(
            f"导出文件已存在且内容不同(不可变导出;保全原文件不覆盖):"
            f"{path}",
            {"kind": "native_export_conflict", "path": str(path)})
    _atomic_write(path, data)
    return True


def export_native_result(ledger, native_result: dict,
                          run_dir: str | Path) -> dict:
    """原生正式导出落盘(payload + manifest;确定性,幂等)。

    - native_result 必须是 build_native_result 的产物(含
      content_digest;其 endpoint 记录须已通过首消费 —— 本函数再经
      read_run_endpoint 首消费门核验,过期记录不包装成正式结果);
    - 同事实/同版本/同策略 ⇒ 同 export_digest、同目录、同字节;
      事实变化 ⇒ 新 digest 新目录(旧文件保全);
    - 纯只读业务表(零 event/attempt/request/budget 写入)。
    """
    run_dir = Path(run_dir)
    # endpoint 记录首消费门(独立于调用方:过期/损坏记录不包装成正式
    # 结果 —— 与 runflow 派生侧同一判据来源,幂等只读)
    read_run_endpoint(ledger, ledger.run_id)
    policy = native_export_policy()
    payload_text = canonical_json(native_result) + "\n"
    payload_sha = hashlib.sha256(
        payload_text.encode("utf-8")).hexdigest()
    # manifest 核心(无 export_digest、无时间戳)
    core = {
        "schema_version": PPV1_NATIVE_EXPORT_VERSION,
        "run_id": ledger.run_id,
        "export_policy": policy,
        "export_policy_sha256": export_policy_hash(policy),
        "contract_versions": {
            "profile": PPV1_PROFILE_SCHEMA_VERSION,
            "store": PPV1_STORE_SCHEMA_VERSION,
            "search": PPV1_SEARCH_SCHEMA_VERSION,
            "runflow": PPV1_RUNFLOW_SCHEMA_VERSION,
            "endpoint": PPV1_ENDPOINT_SCHEMA_VERSION,
            "endpoint_policy": PPV1_ENDPOINT_POLICY_VERSION,
            "native_result": PPV1_NATIVE_RESULT_VERSION,
        },
        "content_digest": str(native_result["content_digest"]),
        "payload_sha256": payload_sha,
        "graph_facts": graph_facts_digests(ledger),
        "artifact_references": _artifact_references(ledger),
        "authority_references": _authority_references(
            ledger, native_result),
        "determinism_note": (
            "payload/manifest 无时间戳;canonical_json 键序 + 列表稳定"
            "排序;export_digest = content_hash(本 manifest 去掉"
            " export_digest 键);同事实+同版本+同策略 ⇒ 同字节"),
    }
    export_digest = content_hash(core)
    manifest = dict(core)
    manifest["export_digest"] = export_digest
    manifest_text = canonical_json(manifest) + "\n"
    out_dir = run_dir / NATIVE_EXPORT_SUBDIR / export_digest[:24]
    payload_path = out_dir / NATIVE_EXPORT_PAYLOAD_FILE
    manifest_path = out_dir / NATIVE_EXPORT_MANIFEST_FILE
    out_dir.mkdir(parents=True, exist_ok=True)
    payload_created = _write_immutable(payload_path,
                                       payload_text.encode("utf-8"))
    manifest_created = _write_immutable(manifest_path,
                                        manifest_text.encode("utf-8"))
    return {
        "export_digest": export_digest,
        "dir": str(out_dir),
        "payload_path": str(payload_path),
        "manifest_path": str(manifest_path),
        "payload_sha256": payload_sha,
        "content_digest": str(native_result["content_digest"]),
        "schema_version": PPV1_NATIVE_EXPORT_VERSION,
        "export_policy_version": PPV1_NATIVE_EXPORT_POLICY_VERSION,
        "created": {"payload": payload_created, "manifest": manifest_created},
        "note": ("S4b 正式文件导出:全量事实 + manifest 新鲜度锚"
                 "(graph facts digest/权威引用/策略 hash);确定性幂等,"
                 "旧导出按 digest 保全;读取走 read_native_export 首消费"),
    }


def list_native_exports(run_dir: str | Path) -> list[str]:
    """既有导出 digest 列表(目录名;稳定排序;不含验证)。"""
    root = Path(run_dir) / NATIVE_EXPORT_SUBDIR
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())


# ---------------------------------------------------------------- 读取(首消费)


def read_native_export(ledger, run_dir: str | Path, export_digest: str,
                        *, policy: dict | None = None) -> dict:
    """原生正式导出读取(首消费:integrity → 版本门 → digest → 权威
    引用 → 策略 → staleness;fail-closed,零写入,原文件保全)。

    policy:当前导出策略(缺省 = native_export_policy();测试/未来版本
    可显式传入新策略 ⇒ 旧导出按 export_policy_stale 拒)。
    endpoint 记录的首消费(read_run_endpoint)先行 —— 输入事实漂移时
    先以 endpoint 拒绝浮出,导出侧不再吞掉。
    """
    run_dir = Path(run_dir)
    out_dir = run_dir / NATIVE_EXPORT_SUBDIR / str(export_digest)[:24]
    payload_path = out_dir / NATIVE_EXPORT_PAYLOAD_FILE
    manifest_path = out_dir / NATIVE_EXPORT_MANIFEST_FILE
    if not payload_path.is_file() or not manifest_path.is_file():
        raise NativeExportContractError(
            f"原生导出文件缺失:{out_dir}(不猜默认;按 digest 显式消费)",
            {"kind": "export_missing", "dir": str(out_dir),
             "export_digest": str(export_digest)})
    # ---- 2. manifest 可解析 + digest 绑定 ----
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise NativeExportContractError(
            f"导出 manifest 不可解析:{manifest_path}(保全原文件)",
            {"kind": "export_manifest_corrupt",
             "path": str(manifest_path),
             "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    if str(manifest.get("export_digest") or "") != str(export_digest):
        raise NativeExportContractError(
            "导出 manifest 的 export_digest 与请求不符(路径/内容身份"
            "断裂;保全原文件)",
            {"kind": "export_manifest_corrupt",
             "requested": str(export_digest),
             "manifest": str(manifest.get("export_digest") or "")})
    # ---- 3. payload 字节完整性 ----
    payload_bytes = payload_path.read_bytes()
    payload_sha = hashlib.sha256(payload_bytes).hexdigest()
    if payload_sha != str(manifest.get("payload_sha256")):
        raise NativeExportContractError(
            f"导出 payload 字节与 manifest sha256 不符(完整性失败;"
            f"保全原文件,不覆盖):{payload_path}",
            {"kind": "export_payload_corrupt",
             "path": str(payload_path),
             "recorded": str(manifest.get("payload_sha256"))[:12],
             "actual": payload_sha[:12]})
    # ---- 4. 版本门 ----
    if str(manifest.get("schema_version") or "") != PPV1_NATIVE_EXPORT_VERSION:
        raise NativeExportContractError(
            f"导出 schema 版本未知:{manifest.get('schema_version')!r}"
            f"(当前 {PPV1_NATIVE_EXPORT_VERSION};fail-closed 不猜迁移)",
            {"kind": "export_version_unknown",
             "schema_version": str(manifest.get("schema_version") or "")})
    # ---- 5. payload 内容 digest 复算 ----
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise NativeExportContractError(
            f"导出 payload 不可反序列化:{payload_path}(保全原文件)",
            {"kind": "export_payload_corrupt",
             "path": str(payload_path),
             "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    if content_hash({k: v for k, v in payload.items()
                     if k != "content_digest"}) \
            != str(payload.get("content_digest")):
        raise NativeExportContractError(
            f"导出 payload 内容 digest 复算不一致:{payload_path}"
            "(自洽性失败;保全原文件,不以重算新 ID 洗白)",
            {"kind": "export_digest_mismatch",
             "path": str(payload_path)})
    if str(payload.get("content_digest")) != \
            str(manifest.get("content_digest")):
        raise NativeExportContractError(
            "导出 payload 与 manifest 的 content_digest 不一致"
            "(内部引用断裂;保全原文件)",
            {"kind": "export_digest_mismatch",
             "payload": str(payload.get("content_digest")),
             "manifest": str(manifest.get("content_digest"))})
    # ---- 6. 权威引用(endpoint 首消费先行 + DB 行 + artifacts) ----
    read_run_endpoint(ledger, ledger.run_id)
    refs = manifest.get("authority_references") or {}
    conn = ledger.conn
    stop_row = conn.execute(
        "SELECT payload_hash FROM stop_reason_records WHERE run_id = ?",
        (ledger.run_id,)).fetchone()
    endpoint_row = conn.execute(
        "SELECT payload_hash FROM endpoint_records WHERE run_id = ?",
        (ledger.run_id,)).fetchone()
    if (stop_row is None
            or str(stop_row["payload_hash"])
            != str(refs.get("stop_record_payload_hash"))
            or endpoint_row is None
            or str(endpoint_row["payload_hash"])
            != str(refs.get("endpoint_record_payload_hash"))):
        raise NativeExportContractError(
            "导出与 DB 权威记录(endpoint/stop 行)引用不一致"
            "(四分账独立持久化;断裂 ⇒ 结构化拒,不猜补)",
            {"kind": "export_reference_mismatch",
             "stop_record_payload_hash":
                 str(refs.get("stop_record_payload_hash")),
             "endpoint_record_payload_hash":
                 str(refs.get("endpoint_record_payload_hash"))})
    native_task_key = str(refs.get("native_result_task_key"))
    try:
        native_back = read_native_result(
            ledger.artifact_store, native_task_key)
    except Exception as exc:  # noqa: BLE001 —— 引用失败如实上抛(拒)
        raise NativeExportContractError(
            f"导出引用的原生结果 artifact 不可用:{native_task_key}"
            "(引用断裂/损坏 ⇒ 拒;保全原文件)",
            {"kind": "export_reference_mismatch",
             "native_result_task_key": native_task_key,
             "error": f"{type(exc).__name__}: {exc}"[:200]}) from exc
    if str(native_back.get("content_digest")) != \
            str(manifest.get("content_digest")):
        raise NativeExportContractError(
            "导出 manifest 与原生结果 artifact 的 content_digest 不一致"
            "(权威源分叉;拒)",
            {"kind": "export_reference_mismatch",
             "manifest": str(manifest.get("content_digest")),
             "artifact": str(native_back.get("content_digest"))})
    artifact_refs = manifest.get("artifact_references") or {}
    for key, recorded in sorted(artifact_refs.items()):
        task_key, _, name = key.partition("/")
        envelope = read_search_artifact(
            ledger.artifact_store, task_key, name)
        if envelope is None or str(envelope.get("payload_hash") or "") \
                != str((recorded or {}).get("payload_hash")):
            raise NativeExportContractError(
                f"导出引用的 artifact 内容变化或缺失:{key}"
                "(依赖对象内容变化 ⇒ 旧导出拒;保全原文件)",
                {"kind": "export_reference_mismatch",
                 "artifact": key,
                 "recorded_payload_hash":
                     str((recorded or {}).get("payload_hash"))[:12],
                 "current_payload_hash": (
                     str(envelope.get("payload_hash") or "")[:12]
                     if envelope is not None else "<missing>")})
    # ---- 7. 导出策略 ----
    current_policy = policy if policy is not None else native_export_policy()
    current_policy_sha = export_policy_hash(current_policy)
    if str(manifest.get("export_policy_sha256")) != current_policy_sha:
        raise NativeExportContractError(
            "导出过期:导出策略/版本变化(旧导出不得当作当前结果;"
            "重新导出走公共 start/resume 或 export_native_result)",
            {"kind": "export_policy_stale",
             "recorded": str(manifest.get("export_policy_sha256"))[:12],
             "current": current_policy_sha[:12]})
    # ---- 8. graph facts staleness(独立权威重算,不信 manifest) ----
    current_facts = graph_facts_digests(ledger)
    recorded_facts = manifest.get("graph_facts") or {}
    changed = sorted(
        key for key, value in current_facts.items()
        if key != "note"
        and str(recorded_facts.get(key)) != str(value))
    if changed:
        raise NativeExportContractError(
            f"导出已过期:源图事实与当前持久权威不一致:{changed}"
            "(旧导出不能静默当作当前结果 —— 拒绝消费;重新导出走公共"
            " start/resume 或 export_native_result)",
            {"kind": "export_stale", "changed_facts": changed,
             "recorded": {k: recorded_facts.get(k) for k in changed},
             "current": {k: current_facts[k] for k in changed}})
    return {"manifest": manifest, "payload": payload,
            "payload_sha256": payload_sha}
