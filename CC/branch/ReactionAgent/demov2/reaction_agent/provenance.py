"""Source record provenance (chatgpt_p1_train.md §8.5)."""
from __future__ import annotations
import os
from reaction_agent.schemas.common import StrictModel, NonEmptyStr

class SourceRecordProvenance(StrictModel):
    source_name: NonEmptyStr
    source_version: NonEmptyStr
    source_record_id: NonEmptyStr
    source_file_hash: NonEmptyStr
    raw_record_hash: NonEmptyStr
    normalizer_version: NonEmptyStr
    created_by_build_id: NonEmptyStr

# no-legacy-write 守卫：禁止写入 demov2 之外的遗留路径
# (../benchmark, ../core) 以及 P0 报告区 (../reports/p0)。
# 守卫基于解析后的绝对真实路径 + 目录边界检查，覆盖符号链接、大小写
# (macOS APFS 不区分大小写)、CWD 相对路径等绕过向量 (L2 security-review
# H1/H2/M3/M4)。
LEGACY_WRITE_PREFIXES = ("../benchmark", "../core", "../reports/p0")

# 项目根 = demov2/（本模块位于 reaction_agent/provenance.py）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve(path: str) -> str:
    """将路径解析为绝对真实路径并小写化。

    - realpath 解析符号链接、``..``、``//`` (H1/M3/M4)。
    - 显式 ``.lower()`` 覆盖 macOS APFS 不区分大小写场景 (H2)；
      ``os.path.normcase`` 在 POSIX 上是 no-op，无法闭合 H2，故显式小写。
      这是保守策略：在区分大小写的 FS 上可能过度拦截同名异大小写目录，
      对守卫语义可接受（宁可拒绝也不可放行遗留写入）。
    """
    if os.path.isabs(path):
        resolved = os.path.realpath(path)
    else:
        # 相对路径基于项目根 demov2/ 解析，而非 CWD（M4）。
        resolved = os.path.realpath(os.path.join(_PROJECT_ROOT, path))
    return resolved.lower()


# 预解析遗留目录为绝对、小写化的真实路径。
_LEGACY_ABS = tuple(
    os.path.realpath(os.path.join(_PROJECT_ROOT, pref)).lower()
    for pref in LEGACY_WRITE_PREFIXES
)


def assert_no_legacy_write(path: str) -> None:
    """拒绝向遗留目录写入。

    将输入路径解析为绝对真实路径（相对路径基于项目根 demov2/ 解析，
    而非 CWD），与预解析的遗留目录做目录边界比较。这样可阻止符号链接
    绕过、大小写变体绕过、CWD 相对绕过，同时避免子字符串误匹配。
    """
    resolved = _resolve(path)
    for legacy in _LEGACY_ABS:
        if resolved == legacy or resolved.startswith(legacy + os.sep):
            raise PermissionError(f"refuse legacy write: {path}")


