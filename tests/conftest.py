"""pytest 共享夹具:仓库路径、v3/v4 代码根、清单校验、临时资产副本构造。

临时资产副本(路径隔离测试用)用 symlink 镜像未篡改文件、只复制被篡改文件,
绝不写本仓正本;v3 原仓资产在全部用例中保持完好,以证明失败并非旧仓兜底。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

V3_CODE_ROOT = REPO_ROOT.parent / "dependingv3"
V4_CODE_ROOT = REPO_ROOT.parent / "dependingv4"
ASSETS_ROOT = REPO_ROOT / "assets"

CORE_FILE_FOR_TAMPER = "v3_reactions/corpus_env/donor_index.jsonl"
EXTENSION_FILE_FOR_TAMPER = "v3_reactions/eawag/rules_new_clean.jsonl"
ANALOG_INDEX_FOR_DELETE = "analog/corpus_templates_v1.jsonl"
ANALOG_INDEX_FOR_TAMPER = "analog/uspto_relaxed_index_v1.jsonl"


def has_v3() -> bool:
    return (V3_CODE_ROOT / "src" / "depending" / "dp_paths.py").is_file()


def has_v4() -> bool:
    return (V4_CODE_ROOT / "src" / "pathway_agent" / "engine.py").is_file()


@pytest.fixture(scope="session")
def v3_code_root() -> Path:
    if not has_v3():
        pytest.skip(f"v3 代码根不可用:{V3_CODE_ROOT}")
    return V3_CODE_ROOT


@pytest.fixture(scope="session")
def v4_code_root() -> Path:
    if not has_v4():
        pytest.skip(f"v4 对照代码根不可用:{V4_CODE_ROOT}")
    return V4_CODE_ROOT


@pytest.fixture(scope="session")
def assets_root() -> Path:
    if not (ASSETS_ROOT / "MANIFEST.sha256").is_file():
        pytest.skip(f"本仓资产清单缺失:{ASSETS_ROOT}")
    return ASSETS_ROOT


@pytest.fixture(scope="session")
def manifest_identity(assets_root: Path) -> dict:
    from pathway_v43.adapters.asset_manifest import verify_repo_manifest

    return verify_repo_manifest(assets_root)


def _mirror_assets(dest: Path, *, drop: str | None = None,
                   tamper: str | None = None,
                   symlink_all: bool = False) -> Path:
    """构造临时 assets 副本(默认全物理复制:清单校验含物理边界检查)。

    - drop:        清单内文件从副本删除(缺文件用例);
    - tamper:      复制该文件并追加一个字节(哈希漂移用例);
    - symlink_all: 全部文件 symlink 指向正本 —— 专用于构造“物理路径逃逸”
      用例(逃逸必须被清单校验/类比装载器拒绝),正常用例不再使用。
    """
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    src = ASSETS_ROOT
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        rel_posix = rel.as_posix()
        if drop is not None and rel_posix == drop:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if tamper is not None and rel_posix == tamper:
            target.write_bytes(path.read_bytes() + b"\n")
        elif symlink_all:
            target.symlink_to(path)
        else:
            shutil.copyfile(path, target)
    return dest


@pytest.fixture(scope="session")
def make_assets_copy(tmp_path_factory):
    """工厂:为每个用例构造带指定篡改的临时 assets 副本(只操作临时目录)。"""
    counter = {"n": 0}

    def _make(*, drop: str | None = None, tamper: str | None = None,
              symlink_all: bool = False) -> Path:
        counter["n"] += 1
        dest = tmp_path_factory.mktemp("assets_copy") / f"copy_{counter['n']}"
        return _mirror_assets(dest, drop=drop, tamper=tamper,
                              symlink_all=symlink_all)

    return _make
