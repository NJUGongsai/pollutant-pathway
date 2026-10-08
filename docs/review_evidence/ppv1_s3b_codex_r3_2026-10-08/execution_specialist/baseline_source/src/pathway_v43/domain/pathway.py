"""化学路径图操作 — 祖先链、路径内循环、展示名。

展示名(S1/S11/S211)只是由路径结构计算的视图;内部引用一律用稳定 ID,
禁止解析展示名推断父子关系。祖先链按顺序返回根→当前路径,供后续
PredictionAgent 组装完整任务书。
"""

from __future__ import annotations

from .models import PathInstance


class PathStoreProtocol:
    """pathway.py 需要的最小存储协议(PathwayStore 满足)。"""

    def get_path(self, path_id: str) -> PathInstance | None: ...


def ancestry_chain(store: PathStoreProtocol, path_id: str) -> list[PathInstance]:
    """从根到当前路径的祖先链(含首尾)。环状引用防御:超过链长上限即抛错。"""
    chain: list[PathInstance] = []
    seen: set[str] = set()
    current: str | None = path_id
    while current is not None:
        if current in seen:
            raise ValueError(f"路径父链出现环:{current}")
        seen.add(current)
        path = store.get_path(current)
        if path is None:
            raise KeyError(f"路径不存在:{current}")
        chain.append(path)
        current = path.parent_path_id
    chain.reverse()
    return chain


def ancestry_identities(chain: list[PathInstance]) -> list[str]:
    """祖先链上各路径底物的规范身份(含根与当前) — 循环判定与任务书素材。"""
    return [p.substrate_identity for p in chain]


def is_in_path_cycle(product_identity: str, ancestry_cns: list[str]) -> bool:
    """产物回到本路径任一祖先身份(含当前底物)→ 路径内循环。

    不同路线汇合到同一分子不是循环 —— 那由 Compound 身份共享表达,
    循环只看本路径的祖先链(身份字符串列表,含根与当前)。
    """
    return product_identity in set(ancestry_cns)


def display_name(chain: list[PathInstance]) -> str:
    """由路径结构计算展示名(任务书约定 S11 / S211):

    根 = S1;深度 d ≥ 1 的路径 = ``S{d}`` + 各代位次数字(1 起始)。
    即 S1 的第 1 个产物路径 = S11(深度 1);S11 的第 1 个子路径 =
    S211(深度 2,位次链 1,1);S12 的第 2 个子路径 = S222。
    展示名仅由结构计算,内部引用一律用稳定 ID。
    """
    if len(chain) == 1:
        return "S1"
    depth = len(chain) - 1
    digits = "".join(str((p.product_position or 0) + 1) for p in chain[1:])
    return f"S{depth}{digits}"


def ancestry_chain_records(
    store: PathStoreProtocol, path_id: str
) -> list[dict]:
    """祖先链的 JSON 记录(展示名+事件引用+底物身份),PredictionAgent 素材。"""
    chain = ancestry_chain(store, path_id)
    records: list[dict] = []
    for i, path in enumerate(chain):
        records.append(
            {
                "position": i,
                "path_id": path.path_id,
                "display_name": display_name(chain[: i + 1]),
                "substrate_identity": path.substrate_identity,
                "event_id": path.event_id,
                "product_position": path.product_position,
                "depth": path.depth,
            }
        )
    return records
