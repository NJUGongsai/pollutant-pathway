"""本仓 assets/ 完整性清单校验(fail-closed,无回退)。

验收只认 assets/MANIFEST.sha256(21 条 "<sha256>  <relpath>")与
assets/MANIFEST.json(逐项 path/bytes/sha256)。两者的交叉一致性与磁盘上
的真实字节都核对;缺失、篡改、路径逃逸都以 AssetManifestError 失败并点名
文件。不以“文件存在”代替完整性,不回退旧 dependingv3/assets。
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

MANIFEST_SHA_NAME = "MANIFEST.sha256"
MANIFEST_JSON_NAME = "MANIFEST.json"

# 扩展引擎资产:v3 env_asset_root 只校验核心运行文件,模板/规则由本仓总清单兜底。
EXTENSION_FILES = (
    "v3_reactions/templates/uspto_templates.json",
    "v3_reactions/envipath/templates.tsv.gz",
    "v3_reactions/envipath/templates_implicitH.jsonl",
    "v3_reactions/eawag/rules_new_clean.jsonl",
    "v3_reactions/eawag/donor_product.jsonl",
)

# v4 类比最终索引(启用类比桥时都必须在清单内且哈希一致)。
# Phase D D2:corpus_templates_v2(重映射版)同列版本化必需 —— 本仓带
# v2 资产起,清单与磁盘必须覆盖全部三份;装载选择仍显式(v1/v2),
# 选 v2 时文件缺失/哈希不符 fail-closed,不静默回退 v1。
ANALOG_INDEX_FILES = (
    "analog/uspto_relaxed_index_v1.jsonl",
    "analog/corpus_templates_v1.jsonl",
    "analog/corpus_templates_v2.jsonl",
)


def analog_corpus_rel(version: str) -> str:
    """类比模板语料的清单相对路径(v1/v2 显式白名单)。"""
    if version == "v2":
        return "analog/corpus_templates_v2.jsonl"
    if version == "v1":
        return "analog/corpus_templates_v1.jsonl"
    raise AssetManifestError(
        f"未知类比语料版本:{version!r}(允许 v1/v2)", {"version": version})


class AssetManifestError(RuntimeError):
    """清单缺失/不一致/哈希不符/路径逃逸。detail 携带结构化信息。"""

    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_sha_manifest(path: Path) -> dict[str, str]:
    """解析 "<sha256>  <relpath>" 清单;拒绝空哈希、绝对路径与 .. 逃逸。"""
    out: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                raise AssetManifestError(
                    f"manifest 行无法解析:{path}:{lineno}",
                    {"manifest": str(path), "lineno": lineno},
                )
            digest, rel = parts[0], parts[1].strip().lstrip("*")
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
                raise AssetManifestError(
                    f"manifest 行哈希格式非法:{path}:{lineno} ({digest!r})",
                    {"manifest": str(path), "lineno": lineno},
                )
            if rel.startswith("/") or ".." in Path(rel).parts or not rel:
                raise AssetManifestError(
                    f"manifest 条目路径逃逸:{rel}(manifest={path})",
                    {"manifest": str(path), "relpath": rel, "lineno": lineno},
                )
            if rel in out:
                raise AssetManifestError(
                    f"manifest 条目重复:{rel}(manifest={path})",
                    {"manifest": str(path), "relpath": rel},
                )
            out[rel] = digest.lower()
    if not out:
        raise AssetManifestError(f"manifest 为空:{path}", {"manifest": str(path)})
    return out


def _require_lexical_under(root: Path, rel: str) -> None:
    """清单条目词法上必须落在 assets 根内(相对路径、无 ..)。

    这是第一层(词法)检查;verify_repo_manifest 随后对每个条目再做
    resolve 后的物理边界检查(配置的 assets_root 为边界,symlink 逃逸拒绝)。
    """
    joined = Path(os.path.normpath(str(root / rel)))
    try:
        joined.relative_to(root)
    except ValueError:
        raise AssetManifestError(
            f"manifest 条目路径逃逸:{rel}(assets_root={root})",
            {"assets_root": str(root), "relpath": rel},
        )


def verify_repo_manifest(assets_root: str | Path) -> dict:
    """校验本仓全部清单条目:磁盘哈希 + MANIFEST.json 三方一致 + 物理路径边界。

    物理边界 = 配置的 assets_root 自身 resolve 后的位置:清单内每个条目
    resolve 后都必须落在该边界内。因此把 ``v3_reactions``(或任何资产)用
    symlink 指向旧仓/其它位置的部署会被拒绝——即使字节与清单哈希一致
    (任务书要求实际读取路径落在配置资产根下,不以哈希一致替代边界)。
    若配置的 assets_root 本身是 symlink,边界取其物理目标,自洽部署不受影响。

    返回 identity dict(manifest 自身 SHA、逐文件哈希、总字节数)。
    任何缺失/不符/逃逸都抛 AssetManifestError 并点名文件。
    """
    root = Path(assets_root).resolve()
    if not root.is_dir():
        raise AssetManifestError(f"assets 根不存在:{root}", {"assets_root": str(root)})

    sha_manifest_path = root / MANIFEST_SHA_NAME
    if not sha_manifest_path.is_file():
        raise AssetManifestError(
            f"本仓 SHA 清单缺失:{sha_manifest_path}", {"assets_root": str(root)}
        )
    entries = parse_sha_manifest(sha_manifest_path)

    verified: dict[str, dict] = {}
    total_bytes = 0
    for rel in sorted(entries):
        _require_lexical_under(root, rel)
        path = root / rel
        if not path.is_file():
            raise AssetManifestError(
                f"清单文件缺失:{path}", {"assets_root": str(root), "file": rel}
            )
        physical = path.resolve()
        if physical != root and root not in physical.parents:
            raise AssetManifestError(
                f"文件物理路径逃逸:{path} 解析到 {physical},"
                f"不在配置的 assets 根 {root} 内",
                {
                    "assets_root": str(root),
                    "file": rel,
                    "physical": str(physical),
                },
            )
        actual = sha256_file(path)
        if actual != entries[rel]:
            raise AssetManifestError(
                f"文件哈希不符:{path}\n  manifest={entries[rel]}\n  actual  ={actual}",
                {
                    "assets_root": str(root),
                    "file": rel,
                    "manifest_sha256": entries[rel],
                    "actual_sha256": actual,
                },
            )
        size = path.stat().st_size
        verified[rel] = {"sha256": actual, "bytes": size}
        total_bytes += size

    # ---- MANIFEST.json 交叉核对(路径/字节数/哈希与 sha 清单及磁盘一致) ----
    json_manifest_path = root / MANIFEST_JSON_NAME
    if not json_manifest_path.is_file():
        raise AssetManifestError(
            f"本仓 JSON 清单缺失:{json_manifest_path}", {"assets_root": str(root)}
        )
    meta = json.loads(json_manifest_path.read_text(encoding="utf-8"))
    for key in ("schema_version", "asset_count", "total_bytes", "entries"):
        if key not in meta:
            raise AssetManifestError(
                f"MANIFEST.json 缺少字段 {key}:{json_manifest_path}",
                {"manifest_json": str(json_manifest_path)},
            )
    if int(meta["asset_count"]) != len(entries):
        raise AssetManifestError(
            f"MANIFEST.json asset_count={meta['asset_count']} 与 SHA 清单条数 {len(entries)} 不一致",
            {"manifest_json": str(json_manifest_path)},
        )
    if int(meta["total_bytes"]) != total_bytes:
        raise AssetManifestError(
            f"MANIFEST.json total_bytes={meta['total_bytes']} 与实际 {total_bytes} 不一致",
            {"manifest_json": str(json_manifest_path)},
        )
    seen = set()
    for entry in meta["entries"]:
        rel = str(entry.get("path", ""))
        if rel not in entries:
            raise AssetManifestError(
                f"MANIFEST.json 条目不在 SHA 清单中:{rel}",
                {"manifest_json": str(json_manifest_path), "file": rel},
            )
        if rel in seen:
            raise AssetManifestError(
                f"MANIFEST.json 条目重复:{rel}",
                {"manifest_json": str(json_manifest_path), "file": rel},
            )
        seen.add(rel)
        rec = verified[rel]
        if int(entry.get("bytes", -1)) != rec["bytes"]:
            raise AssetManifestError(
                f"MANIFEST.json 字节数不符:{rel}"
                f"(json={entry.get('bytes')} actual={rec['bytes']})",
                {"manifest_json": str(json_manifest_path), "file": rel},
            )
        if str(entry.get("sha256", "")).lower() != rec["sha256"]:
            raise AssetManifestError(
                f"MANIFEST.json 哈希与 SHA 清单不一致:{rel}",
                {"manifest_json": str(json_manifest_path), "file": rel},
            )
    missing_json = sorted(set(entries) - seen)
    if missing_json:
        raise AssetManifestError(
            f"MANIFEST.json 缺少条目:{missing_json}",
            {"manifest_json": str(json_manifest_path), "files": missing_json},
        )

    return {
        "manifest_sha256": sha256_file(sha_manifest_path),
        "manifest_json_sha256": sha256_file(json_manifest_path),
        "assets_root": str(root),
        "n_files": len(entries),
        "total_bytes": total_bytes,
        "files": {rel: rec["sha256"] for rel, rec in sorted(verified.items())},
    }


def _select_shas(identity: dict, rels: tuple[str, ...], label: str) -> dict:
    files = identity["files"]
    missing = [rel for rel in rels if rel not in files]
    if missing:
        raise AssetManifestError(
            f"{label} 不在本仓清单中:{missing}(assets_root={identity['assets_root']})",
            {"files": missing, "label": label},
        )
    return {rel: files[rel] for rel in rels}


def extension_file_shas(manifest_identity: dict) -> dict:
    """扩展引擎资产(模板/enviPath/EAWAG)的 relpath → sha256(须已通过总清单校验)。"""
    return _select_shas(manifest_identity, EXTENSION_FILES, "扩展引擎资产")


def analog_index_shas(manifest_identity: dict) -> dict:
    """两份 v4 类比最终索引的 relpath → sha256(须已通过总清单校验)。"""
    return _select_shas(manifest_identity, ANALOG_INDEX_FILES, "类比索引")
