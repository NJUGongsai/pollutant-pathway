"""v4.3 路径与配置解析 — V3_CODE_ROOT 与 V43_ASSET_ROOT 严格分离。

优先级:CLI 显式参数 > 环境变量(V3_CODE_ROOT / V43_ASSET_ROOT)> 默认值。
默认 v3 代码根 = <本仓>/../dependingv3;默认资产根 = <本仓>/assets。
代码根绝不隐式推导资产根(v3 代码根下的 assets/ 不参与任何解析),
资产校验失败也不回退旧 v3/assets —— 由调用方在启动时 fail-closed。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

V3_CODE_ROOT_ENV = "V3_CODE_ROOT"
ASSET_ROOT_ENV = "V43_ASSET_ROOT"

# 本文件位于 <repo>/src/pathway_v43/config.py
_PACKAGE_REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    """定位本仓根(含 assets/MANIFEST.sha256 的目录)。

    源码内安装(editable / src 布局)时直接由包位置推导;包被拷走时退回
    “当前目录含本仓资产清单”这一显式信号,避免猜错仓根。
    """
    if (_PACKAGE_REPO_ROOT / "assets" / "MANIFEST.sha256").is_file():
        return _PACKAGE_REPO_ROOT
    cwd = Path.cwd()
    if (cwd / "assets" / "MANIFEST.sha256").is_file():
        return cwd
    return _PACKAGE_REPO_ROOT


@dataclass(frozen=True)
class V43Config:
    """一次运行的两条独立根:引擎代码(v3,只读)与检索资产(本仓,只读)。"""

    v3_code_root: Path
    assets_root: Path

    @property
    def v3_run_root(self) -> Path:
        """v3 冻结运行数据根(v3 引擎的全部资产都从这里读)。"""
        return self.assets_root / "v3_reactions"

    @property
    def analog_root(self) -> Path:
        """v4 类比最终索引根。"""
        return self.assets_root / "analog"

    @property
    def v3_depending_dir(self) -> Path:
        """v3 冻结引擎源码目录(加入 sys.path,只 import 不改)。"""
        return self.v3_code_root / "src" / "depending"

    def to_dict(self) -> dict:
        return {
            "v3_code_root": str(self.v3_code_root.resolve()),
            "assets_root": str(self.assets_root.resolve()),
            "v3_run_root": str(self.v3_run_root.resolve()),
            "analog_root": str(self.analog_root.resolve()),
            "v3_depending_dir": str(self.v3_depending_dir.resolve()),
        }


def resolve_config(
    v3_code_root: str | Path | None = None,
    assets_root: str | Path | None = None,
) -> V43Config:
    """解析最终配置;返回前把两条根都绝对化。"""

    def _pick(explicit: str | Path | None, env_name: str, default: Path) -> Path:
        raw = explicit
        if raw is None or str(raw).strip() == "":
            raw = os.environ.get(env_name, "")
        if raw is None or str(raw).strip() == "":
            return default.resolve()
        return Path(str(raw)).expanduser().resolve()

    root = repo_root()
    cfg = V43Config(
        v3_code_root=_pick(
            v3_code_root, V3_CODE_ROOT_ENV, root.parent / "dependingv3"
        ),
        assets_root=_pick(assets_root, ASSET_ROOT_ENV, root / "assets"),
    )
    return cfg
