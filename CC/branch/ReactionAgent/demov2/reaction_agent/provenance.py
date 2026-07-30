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
# H1/H2/M3/M4 + Fix Round 1 IMPORTANT-1)。
# IMPORTANT-1 闭合：guard 返回解析后的绝对路径，调用方必须用该返回值写入，
# 使 guard 路径解释与实际写入路径一致，彻底闭合 CWD 相对绕过。
LEGACY_WRITE_PREFIXES = ("../benchmark", "../core", "../reports/p0")

# 项目根 = demov2/（本模块位于 reaction_agent/provenance.py）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve(path: str) -> str:
    """将路径解析为绝对真实路径（保留真实大小写）。

    - realpath 解析符号链接、``..``、``//`` (H1/M3/M4)。
    - 相对路径基于项目根 demov2/ 解析，而非 CWD (M4 + Fix Round 1 IMPORTANT-1)。
    - 保留真实大小写：返回值供调用方实际写入，小写化会破坏大小写敏感 FS
      上的写入。大小写不敏感比较在 ``assert_no_legacy_write`` 内完成。
    """
    if os.path.isabs(path):
        return os.path.realpath(path)
    # 相对路径基于项目根 demov2/ 解析，而非 CWD（M4 + IMPORTANT-1）。
    return os.path.realpath(os.path.join(_PROJECT_ROOT, path))


# 预解析遗留目录为绝对真实路径（保留真实大小写）。
_LEGACY_ABS = tuple(
    os.path.realpath(os.path.join(_PROJECT_ROOT, pref))
    for pref in LEGACY_WRITE_PREFIXES
)


def assert_no_legacy_write(path: str) -> str:
    """拒绝向遗留目录写入，返回解析后的绝对路径供调用方实际写入。

    将输入路径解析为绝对真实路径（相对路径基于项目根 demov2/ 解析，
    而非 CWD），与预解析的遗留目录做大小写不敏感的目录边界比较。

    返回值契约 (Fix Round 1 IMPORTANT-1)：调用方**必须**用返回的绝对路径
    写入，而非原始 ``path``。这样 guard 的路径解释与实际写入路径一致，彻底
    闭合 CWD 相对路径绕过——若调用方传 ``benchmark/x`` 且 CWD 在 parent，
    ``open(path)`` 会命中 legacy benchmark/，但 ``open(returned_path)`` 解析到
    demov2/benchmark/（非 legacy），安全。

    大小写策略：显式 ``.lower()`` 双侧比较覆盖 macOS APFS 不区分大小写
    场景 (H2)；``os.path.normcase`` 在 POSIX 上是 no-op，不足以闭合 H2。
    保守策略：区分大小写的 FS 上可能过度拦截同名异大小写目录，对守卫
    语义可接受（宁可拒绝也不可放行遗留写入）。
    """
    resolved = _resolve(path)
    resolved_lower = resolved.lower()
    for legacy in _LEGACY_ABS:
        legacy_lower = legacy.lower()
        if resolved_lower == legacy_lower or resolved_lower.startswith(legacy_lower + os.sep):
            raise PermissionError(f"refuse legacy write: {path}")
    return resolved


