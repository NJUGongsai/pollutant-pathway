"""路径展示名约定(任务书:根 S1、S11、S211)与路径内循环判定。"""

from __future__ import annotations

from pathway_v43.domain.models import PathInstance
from pathway_v43.domain.pathway import display_name, is_in_path_cycle


def _path(pid, parent, pos, depth):
    return PathInstance(
        path_id=pid, run_id="r", parent_path_id=parent, event_id=None,
        product_position=pos, substrate_identity=f"C{pid}", status="frontier",
        depth=depth, seq=0,
    )


def test_display_name_convention():
    root = _path("p0", None, None, 0)
    chain = [root]
    assert display_name(chain) == "S1"
    # 深度 1:S1 的第 1/2 个产物路径
    assert display_name(chain + [_path("p1", "p0", 0, 1)]) == "S11"
    assert display_name(chain + [_path("p2", "p0", 1, 1)]) == "S12"
    # 深度 2:S11 的第 1 个子路径 = S211(深度数字 + 位次链),不是 S111
    assert display_name(chain + [_path("p1", "p0", 0, 1),
                                 _path("p11", "p1", 0, 2)]) == "S211"
    assert display_name(chain + [_path("p1", "p0", 0, 1),
                                 _path("p12", "p1", 1, 2)]) == "S212"
    # 深度 3:S211(位次链 1,1)的第 2 个子路径 = S3112
    assert display_name(chain + [_path("p1", "p0", 0, 1),
                                 _path("p11", "p1", 0, 2),
                                 _path("p111", "p11", 1, 3)]) == "S3112"


def test_in_path_cycle_vs_junction():
    assert is_in_path_cycle("C", ["A", "B", "C"])      # 回到当前底物
    assert is_in_path_cycle("A", ["A", "B", "C"])      # 回到根
    assert not is_in_path_cycle("D", ["A", "B", "C"])  # 新分子不是循环
    assert is_in_path_cycle("X", []) is False          # 空祖先链(防御)
