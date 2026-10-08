"""v4 类比最终索引装载器 — 只读消费 assets/analog/ 两份索引。

装载口径逐字镜像 v4 ``pathway_agent/analog.py`` 的 UsptoIndex / CorpusIndex
(同 schema、同跳过规则、同 SHA 计算),因此行数与 v4 完全一致;本任务不改
检索排名算法、不改索引内容。与 v4 的差异是 fail-closed 收紧:

- 两份索引的 SHA256 必须先通过本仓总清单校验(不以文件存在代替完整性);
- 启用类比桥(require_complete=True)时缺任一索引即 AnalogAssetError;
  v4 旧版缺一份仍 available 的行为不再允许。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pathway_v43.adapters.asset_manifest import (
    ANALOG_INDEX_FILES,
    AssetManifestError,
    sha256_file,
    verify_repo_manifest,
)

USPTO_INDEX_NAME = "uspto_relaxed_index_v1.jsonl"
CORPUS_INDEX_NAME = "corpus_templates_v1.jsonl"
USPTO_REL = f"analog/{USPTO_INDEX_NAME}"
CORPUS_REL = f"analog/{CORPUS_INDEX_NAME}"

RELAX_LEVELS = (1, 2, 3)


class AnalogAssetError(RuntimeError):
    """类比索引缺失/校验失败(fail-closed)。detail 携带结构化信息。"""

    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


def _require_rel(assets_root: Path, rel: str) -> Path:
    """类比索引路径双重约束,返回实际读取路径。

    1) 词法:条目相对、无 ..(清单层面;完整性由哈希保证);
    2) 物理:resolve 后必须仍位于本仓 assets 根内 —— symlink 指向仓外文件的
       部署形态对类比索引是路径逃逸,fail-closed(任务书对类比索引实际读取
       路径的要求;v3 引擎装载路径同样做物理检查)。
    """
    root = assets_root.resolve()
    rel_path = Path(rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise AnalogAssetError(
            f"类比索引路径逃逸(词法):{rel}", {"assets_root": str(root), "rel": rel}
        )
    path = root / rel_path
    physical = path.resolve()
    if physical != root and root not in physical.parents:
        raise AnalogAssetError(
            f"类比索引路径逃逸(物理):{path} 解析到 {physical},"
            f"不在本仓 assets 根 {root} 内",
            {"assets_root": str(root), "rel": rel, "physical": str(physical)},
        )
    return path


class UsptoRow:
    """USPTO 放宽索引行(镜像 v4 analog._UsptoRow 的装载期字段;mol 惰性)。"""

    __slots__ = (
        "template_id", "lhs", "rhs", "freq", "sig_pairs", "r_forms",
        "center_maps", "env_maps",
    )

    def __init__(self, row: dict[str, Any]) -> None:
        from collections import Counter

        self.template_id = str(row["template_id"])
        lhs, _, rhs = self.template_id.partition(">>")
        self.lhs, self.rhs = lhs, rhs
        self.freq = int(row.get("freq", 0))
        sig = [str(x) for x in (row.get("center_signature") or [])]
        self.sig_pairs = tuple(sorted(Counter(sig).items()))
        self.center_maps = [int(x) for x in (row.get("center_atoms") or [])]
        self.env_maps = [int(x) for x in (row.get("env_shell") or [])]
        self.r_forms = {lv: str(row.get(f"r{lv}", "")) for lv in RELAX_LEVELS}

    def r_form(self, level: int) -> str:
        return self.r_forms.get(level, "")


class CorpusRow:
    """corpus_templates 索引行(镜像 v4 analog.CorpusRow 的装载期字段)。"""

    __slots__ = (
        "template_id", "record_id", "source", "mapped_lhs", "mapped_rhs",
        "center_maps", "env_maps", "confidence", "provenance_sha256",
    )

    def __init__(self, row: dict[str, Any]) -> None:
        self.template_id = str(row["template_id"])
        self.record_id = str(row.get("record_id") or self.template_id)
        self.source = str(row.get("source", "corpus_mapped"))
        self.mapped_lhs = str(row.get("mapped_lhs", ""))
        self.mapped_rhs = str(row.get("mapped_rhs", ""))
        self.center_maps = [int(x) for x in (row.get("center_atoms") or [])]
        self.env_maps = [int(x) for x in (row.get("env_shell") or [])]
        self.confidence = row.get("confidence")
        self.provenance_sha256 = row.get("provenance_sha256")


class UsptoRelaxedIndex:
    """uspto_relaxed_index_v1.jsonl 只读装载(镜像 v4 UsptoIndex:跳 r1 空行)。"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.sha256 = sha256_file(self.path)
        rows: list[UsptoRow] = []
        n_bad = 0
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                o = json.loads(line)
                if not str(o.get("r1", "")):
                    n_bad += 1
                    continue
                rows.append(UsptoRow(o))
        self.rows = rows
        self.n_bad_forms = n_bad


class CorpusTemplatesIndex:
    """corpus_templates_v1.jsonl 只读装载 + record_id 反查(镜像 v4 CorpusIndex)。"""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.sha256 = sha256_file(self.path)
        self.rows: list[CorpusRow] = []
        self.by_record: dict[str, list[CorpusRow]] = {}
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = CorpusRow(json.loads(line))
                self.rows.append(row)
                self.by_record.setdefault(row.record_id, []).append(row)


class AnalogAssets:
    """两份类比最终索引的捆绑装载与身份报告。

    require_complete=True(默认,即“启用类比桥”):缺任一索引或哈希不符 →
    AnalogAssetError(fail-closed)。require_complete=False 时缺索引如实落
    None,供 checkenv 只报告不拒绝。
    """

    def __init__(
        self,
        assets_root: str | Path,
        *,
        require_complete: bool = True,
        manifest_identity: dict | None = None,
    ) -> None:
        self.assets_root = Path(assets_root).resolve()
        self._require_complete = bool(require_complete)
        self.manifest_identity = manifest_identity or verify_repo_manifest(
            self.assets_root
        )
        for rel in ANALOG_INDEX_FILES:
            if rel not in self.manifest_identity["files"]:
                raise AnalogAssetError(
                    f"类比索引不在本仓清单中:{rel}"
                    f"(assets_root={self.assets_root})",
                    {"rel": rel},
                )
        self.uspto = self._load(USPTO_REL, UsptoRelaxedIndex)
        self.corpus = self._load(CORPUS_REL, CorpusTemplatesIndex)
        if require_complete and (self.uspto is None or self.corpus is None):
            missing = [
                rel
                for rel, idx in ((USPTO_REL, self.uspto), (CORPUS_REL, self.corpus))
                if idx is None
            ]
            raise AnalogAssetError(
                f"启用类比桥要求两份最终索引齐备,缺失:{missing}"
                f"(v4 旧版“缺一份仍可用”的行为在 v4.3 不允许)",
                {"missing": missing},
            )

    def _load(self, rel: str, cls):
        expected = str(self.manifest_identity["files"][rel]).lower()
        path = _require_rel(self.assets_root, rel)
        if not path.is_file():
            return None
        idx = cls(path)
        if idx.sha256 != expected:
            raise AnalogAssetError(
                f"类比索引哈希与本仓清单不符:{path}\n"
                f"  manifest={expected}\n  actual  ={idx.sha256}",
                {"rel": rel, "manifest_sha256": expected, "actual_sha256": idx.sha256},
            )
        return idx

    @property
    def available(self) -> bool:
        return self.uspto is not None and self.corpus is not None

    def status(self) -> dict:
        """可用性 / 行数 / SHA 报告(checkenv、run_identity 素材)。"""

        def _block(rel: str, idx) -> dict:
            path = _require_rel(self.assets_root, rel)
            return {
                "path": str(path),
                "available": idx is not None,
                "rows": (len(idx.rows) if idx is not None else 0),
                "sha256": (idx.sha256 if idx is not None else None),
            }

        out = {
            "enabled": self.available,
            "available": self.available,
            "require_complete": self._require_complete,
            "uspto_index": _block(USPTO_REL, self.uspto),
            "corpus_index": _block(CORPUS_REL, self.corpus),
        }
        if self.uspto is not None:
            out["uspto_index"]["n_bad_forms"] = self.uspto.n_bad_forms
        return out
