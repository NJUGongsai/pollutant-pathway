"""ArtifactStore — 不可变 JSON 产物(task_id 幂等)。

- 写入先落临时文件,再以 ``os.link`` 原子占位:目标已存在时 link 失败,
  绝不覆盖 —— 同键同内容幂等返回,同键不同内容 ArtifactConflict;
  并发写同一键也只有一个进程能占位成功(check-then-replace 竞态已消除)。
- 读取时重算 payload 哈希并与信封核对,不符 → ArtifactIntegrityError
  (产物被篡改/损坏时 fail-closed,不静默返回脏数据)。
检索、裁决、校验三类产物都经此落盘;State 只保存 task_id/name 引用。
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from ..domain.models import canonical_json, content_hash, now_iso


class ArtifactConflict(RuntimeError):
    def __init__(self, path: Path, existing_hash: str, new_hash: str) -> None:
        super().__init__(
            f"产物冲突:{path} 已存在但内容不同(existing={existing_hash[:12]},"
            f" new={new_hash[:12]});不可覆盖不可变产物"
        )
        self.detail = {
            "path": str(path), "existing_hash": existing_hash,
            "new_hash": new_hash,
        }


class ArtifactIntegrityError(RuntimeError):
    def __init__(self, path: Path, stored_hash: str, actual_hash: str) -> None:
        super().__init__(
            f"产物完整性校验失败:{path} 的 payload 与记录哈希不符"
            f"(stored={stored_hash[:12]}, actual={actual_hash[:12]});"
            "产物可能被篡改或损坏"
        )
        self.detail = {
            "path": str(path), "stored_hash": stored_hash,
            "actual_hash": actual_hash,
        }


class ArtifactStore:
    def __init__(self, runs_dir: str | Path, run_id: str) -> None:
        self.run_id = run_id
        self.base = Path(runs_dir) / run_id / "results"

    def _path(self, task_id: str, name: str) -> Path:
        return self.base / task_id / f"{name}.json"

    def read(self, task_id: str, name: str) -> dict | None:
        """读产物并核验 payload 哈希;缺失返回 None,被篡改抛错。"""
        import json

        path = self._path(task_id, name)
        if not path.is_file():
            return None
        envelope = json.loads(path.read_text(encoding="utf-8"))
        actual = content_hash(envelope.get("payload", {}))
        stored = envelope.get("payload_hash")
        if stored != actual:
            raise ArtifactIntegrityError(path, stored or "?", actual)
        return envelope

    def write(self, task_id: str, name: str, payload: dict) -> dict:
        """写入产物;同键同内容幂等返回,同键不同内容抛冲突。返回信封。"""
        path = self._path(task_id, name)
        envelope = {
            "schema_version": "v43-artifact-1",
            "run_id": self.run_id,
            "task_id": task_id,
            "name": name,
            "created_at": now_iso(),
            "payload_hash": content_hash(payload),
            "payload": payload,
        }
        text = canonical_json(envelope)
        if path.exists():
            return self._compare_existing(path, envelope)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(
            f"{name}.{os.getpid()}.{time.monotonic_ns()}.tmp"
        )
        tmp.write_text(text + "\n", encoding="utf-8")
        try:
            os.link(tmp, path)  # 原子占位:已存在则失败,绝不覆盖
        except FileExistsError:
            return self._compare_existing(path, envelope, cleanup=tmp)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        tmp.unlink(missing_ok=True)
        envelope["created"] = True
        return envelope

    @staticmethod
    def _compare_existing(path: Path, envelope: dict,
                          cleanup: Path | None = None) -> dict:
        import json

        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        if cleanup is not None:
            cleanup.unlink(missing_ok=True)
        if existing.get("payload_hash") == envelope["payload_hash"]:
            envelope["created"] = False
            return envelope
        raise ArtifactConflict(
            path, existing.get("payload_hash", "?"), envelope["payload_hash"]
        )

    def count_retrievals(self) -> int:
        """已落盘检索产物数 = 真实发生的展开数(预算记账的持久事实源)。"""
        if not self.base.is_dir():
            return 0
        return sum(1 for p in self.base.glob("*/retrieval.json") if p.is_file())

    def count_llm_calls(self) -> int:
        """已登记的模型调用记录数(含悬空/失败 attempt —— 它们都真实耗额)。

        持久事实源:恢复重放不会重复计数,悬空请求(已发出未响应)同样
        计入 LLM 预算,不假装免费。
        """
        if not self.base.is_dir():
            return 0
        return sum(
            1 for p in self.base.glob("*/prediction_call.*.json")
            if p.is_file()
        )
