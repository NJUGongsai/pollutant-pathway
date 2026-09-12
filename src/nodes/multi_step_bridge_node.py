# src/nodes/multi_step_bridge_node.py
# M5: 多步—单步桥接智能体（09-02 裁定 5 / 裁定 6）
#
# 背景：
#   现有 11 节点编排是「单步」流程。多步降解路径（A → B → C → D）需拆成单步反应
#   任务逐段匹配酶。裁定 5 同意增加本桥接智能体；裁定 6 要求按 reaction_task_id
#   统计宿主跨步骤覆盖，且严格保守 strain/species 边界。
#
# 硬约束（裁定 5）：
#   - 按「反应边」拆单步；每相邻两节点构成一条反应边；每步一个 reaction_task_id。
#   - 某步找不到酶 → enzyme_match_status = UNMATCHED_ENZYME，matched_enzyme_uids
#     必须为空，严禁拿其他步骤的酶替代（防跨步串线）。

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import hashlib

from src.state import EnzymeCrewState
from src.schemas.bridge import (
    MultistepRouteInput,
    MultistepStep,
    OrganismStepCoverage,
    MultistepBridgeResult,
)
from src.schemas.evidence import EvidenceRecord, SubstrateInfo

logger = logging.getLogger(__name__)


def _make_reaction_task_id(route_id: str, depth: int, branch_id: Optional[str]) -> str:
    """生成单步 reaction_task_id：统一公共 ID 合同 RT-{16hex}（T6-R3 裁定 4）。

    T5 只接受 RT-{16hex}；graph-native / bridge 统一生成 RT-*，不再使用 R-*。
    16hex = md5(路由种子)[:16]，确定性可复现，作为跨组件 crosswalk 锚定键。
    """
    branch = f".{branch_id}" if branch_id else ""
    seed = f"{route_id}:step{depth}{branch}"
    return f"RT-{hashlib.md5(seed.encode('utf-8')).hexdigest()[:16]}"


def split_multistep_route(route: MultistepRouteInput) -> List[MultistepStep]:
    """把多步路径按相邻反应边拆成单步任务（纯函数，可单测）。

    硬约束：相邻节点构成一条反应边；每步独立 reaction_task_id，绝不合并、绝不复用跨步酶。
    """
    reactants = route.reactant_smiles
    steps: List[MultistepStep] = []
    for i in range(len(reactants) - 1):
        depth = i + 1
        steps.append(
            MultistepStep(
                route_id=route.route_id,
                reaction_task_id=_make_reaction_task_id(route.route_id, depth, route.branch_id),
                source_node_id=f"{route.route_id}:n{i}",
                target_node_id=f"{route.route_id}:n{i + 1}",
                depth=depth,
                branch_id=route.branch_id,
                substrate_smiles=reactants[i],
                product_smiles=reactants[i + 1],
                reaction_smiles=f"{reactants[i]}>>{reactants[i + 1]}",
                reaction_source=route.reaction_source,
                source_tool=route.source_tool,
                predicted_ec=None,
                reaction_asset_status="missing",
                enzyme_match_status="PENDING",
                matched_enzyme_uids=[],
            )
        )
    return steps


def apply_step_enzyme_matches(
    bridge_result: MultistepBridgeResult,
    step_enzymes: Dict[str, List[str]],
) -> MultistepBridgeResult:
    """按 reaction_task_id 回填每步匹配酶（裁定 5 防跨步兜底，原地更新）。

    - 有酶：enzyme_match_status=MATCHED，matched_enzyme_uids=该步酶。
    - 无酶：enzyme_match_status=UNMATCHED_ENZYME，matched_enzyme_uids 必须为空，
      严禁从其他步骤借酶填充。
    """
    for step in bridge_result.steps:
        raw_uids = step_enzymes.get(step.reaction_task_id, [])
        # 过滤空串/纯空白 UID，防脏数据把步骤误标 MATCHED（T6-R3 缺口③）
        uids = [u.strip() for u in raw_uids if isinstance(u, str) and u.strip()]
        step.enzyme_match_status = "MATCHED" if uids else "UNMATCHED_ENZYME"
        step.matched_enzyme_uids = uids
    return bridge_result


def aggregate_organism_step_coverage(
    steps: List[MultistepStep],
    organism_step_hits: Dict[str, tuple[str, List[str]]],
) -> List[OrganismStepCoverage]:
    """裁定 6：按 reaction_task_id 统计宿主跨步骤覆盖（纯函数，供 microbe 层复用）。

    organism_step_hits: {organism_uid: (organism_name, [reaction_task_id, ...])}
    仅当某宿主在某 step 有 ≥1 条匹配酶时，该 step 计入其覆盖。
    排序与 MT-D3 对齐：覆盖步数降序 + organism_uid 升序。
    """
    depth_by_task = {s.reaction_task_id: s.depth for s in steps}
    coverages: List[OrganismStepCoverage] = []
    for uid, (name, task_ids) in organism_step_hits.items():
        valid = [t for t in task_ids if t in depth_by_task]
        coverages.append(
            OrganismStepCoverage(
                organism_uid=uid,
                organism_name=name,
                reaction_task_ids=valid,
                covered_step_count=len(valid),
                covered_depths=sorted(depth_by_task[t] for t in valid),
            )
        )
    coverages.sort(key=lambda c: (-c.covered_step_count, c.organism_uid))
    return coverages


def multi_step_bridge_node(state: EnzymeCrewState) -> dict:
    """MultiStepBridgeNode (M5): 多步路径拆单步桥接。

    触发条件: state.multistep_route 非空（多步降解场景）。
    输出: state.bridge_result（steps 列表）、首步底物下沉为 substrate_info、
          当前单步反应任务锚定到 state.reaction_task_id。

    无多步路径时静默透传（单步流程不受影响）。
    """
    route = state.multistep_route
    if route is None:
        return {}

    if len(route.reactant_smiles) < 2:
        return {
            "error": "MultiStepBridgeNode: 多步路径节点数 < 2，无法构成反应边",
            "fail_closed": True,
        }

    steps = split_multistep_route(route)
    bridge_result = MultistepBridgeResult(route_id=route.route_id, steps=steps)
    first = steps[0]

    # 首步底物下沉，供现有单步链路消费（substrate → reaction → ...）；
    # 后续步骤由上层以 checkpointer/thread 循环驱动，逐段匹配。
    substrate_info = SubstrateInfo(
        substrate_smiles=first.substrate_smiles,
        substrate_name=None,
        source="user_smiles",
        provenance=f"multistep_bridge[{first.reaction_task_id}]::{first.reaction_smiles}",
    )

    evidence = EvidenceRecord(
        stage="bridge",
        action="multistep_route_split",
        data={
            "route_id": route.route_id,
            "step_count": len(steps),
            "reaction_task_ids": [s.reaction_task_id for s in steps],
            "reactions": [s.reaction_smiles for s in steps],
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return {
        "bridge_result": bridge_result,
        "substrate_info": substrate_info,
        "reaction_task_id": first.reaction_task_id,
        "evidence_chain": state.evidence_chain + [evidence],
    }