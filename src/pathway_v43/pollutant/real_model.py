"""S5b 真实模型适配层 —— PPV1 proposals 协议的 real provider 接线
(prep §3.2 设计落地;契约登记 s5b-real-model-1)。

范围(本模块只做传输与调用状态,不做内容解释、不碰判分):

- 复用 legacy ``adapters/llm_client.OpenAICompatibleClient`` 整套传输
  语义(429 有界退避/401/403/402 付费停止/usage 归一/Idempotency-Key/
  FileRateGate 批级闸门),**不重写**;
- 凭证只从环境变量读取(``V43_LLM_BASE_URL`` / ``V43_LLM_API_KEY`` /
  ``V43_LLM_MODEL``,可选 ``V43_LLM_TIMEOUT_S`` /
  ``V43_LLM_REQUEST_PARAMS`` / ``V43_LLM_MAX_HTTP_RETRIES`` /
  ``V43_LLM_RATE_GATE``);密钥只在内存,不落盘不入仓不入日志
  (account 文件只记存在性布尔);
- S5b 缺省:timeout 3600s、HTTP 重试 4(沿老 298 复测参数);
- 逐调用记账:issued/response/timeout/传输失败/孤儿 + usage(缺 usage
  保守预留,known-usage 小计与总费用分开);逐调用落盘
  ``<run_dir>/s5b_real_calls.jsonl``(追加;零密钥零凭证);
- 调用序(prep §3.2):``register_model_request(provider_kind="real")``
  (预算在 ``max_real_model_requests`` 上,额度 0 ⇒ 登记被拒 ⇒ 网络发送
  被阻止)→ ``record_request_sent``(real 计 network=1)→
  ``OpenAICompatibleClient.complete`` → ``record_request_response`` /
  ``mark_request_failed`` → 响应文本交 runflow 既有确定性解析器
  (``parse_model_proposals``;JSON 失败走既有 format_feedback 轮逻辑,
  real 反馈轮同样占额度);
- 崩溃恢复:登记后未发(process death)⇒ resume 复用同 request 行
  首发发送;已发无响应(悬空)⇒ 记 failed(孤儿,占额不释放)+ 显式
  新 request(retry_of 记来源)——B2 pending 披露语义保持,不默发
  第二请求;
- ``identity_block()``:进入 PPV1 run identity 的 prediction 块
  (模型 ID/request_params/timeout/prompt 版本;resume 逐字段核对)。

模型只出假设(proposals),不碰判分;判分零 LLM 不变。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from ..adapters.llm_client import (
    DEFAULT_MAX_HTTP_RETRIES,
    LLM_BASE_URL_ENV,
    LLM_API_KEY_ENV,
    LLM_MODEL_ENV,
    LLM_TIMEOUT_ENV,
    OpenAICompatibleClient,
    real_provider_env,
)
from ..domain.models import now_iso, stable_id
from .candidate_evidence import CANDIDATE_EVIDENCE_SCHEMA_VERSION
from .controlled_vocab import (
    ALIGNMENT_STATUS_RESOLVED,
    BOND_ORDER_ALTERNATION,
    EDIT_OPS,
    OUTPUT_ORIGIN_NOVEL_OUTSIDE_POOL,
)
from .search import PROVIDER_KIND_REAL

S5B_REAL_MODEL_VERSION = "s5b-real-model-1"

# S5b 缺省超时/重试(沿老 298 复测:llm_timeout_s=3600、retries=4)
S5B_DEFAULT_TIMEOUT_S = 3600.0
S5B_DEFAULT_MAX_HTTP_RETRIES = DEFAULT_MAX_HTTP_RETRIES

# 逐调用账本文件名(run 目录内;gitignored runs 根)
S5B_CALL_ACCOUNT_FILE = "s5b_real_calls.jsonl"


class RealModelNotConfigured(RuntimeError):
    """真实模型装配失败(fail-closed;detail 结构化,零密钥)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 提示词

# proposals 协议提示词(冻结模板;内容变更 ⇒ 升 PROPOSALS_PROMPT_VERSION
# ⇒ 身份变化 ⇒ resume 拒)。规则级表述,不含金标不含题面。
# W5(S5b):任务改成中性"酶促单步转化"(不偏 degradation);一次至多
# 8 个不同净反应;短协议示例教合法 ID/自动锚定/单步/完整组分/unknown。
# F3(受控词表单一来源,2026-10-11):提示词的**词表声明段**改为由
# controlled_vocab(执行器/权威模块既有常量)拼接生成,不再手写 ——
# 防 57ea99b4 aromatic 事故型漂移再犯(提示词手写键级词表混入
# "aromatic"、执行器 _BOND_TOKENS 只认凯库勒三词,模型照提示词
# 规范输出 to_order=aromatic、执行器 KeyError 整题崩溃)。
# 渲染字节与手写版逐字节相同(PROPOSALS_PROMPT_VERSION = 基线
# 8da11cb7 冻结值,64 位 hex 锚点见 tests/test_controlled_vocab_ci.py
# 的哈希稳定断言),批身份/resume 语义零影响;执行器词表演进 ⇒
# 拼接结果变 ⇒ 内容哈希变 ⇒ 自动升版走既有流程,不静默漂移。
#
# 生成位(受控词表声明,单一来源 = controlled_vocab):
# - edits 四操作:EDIT_OPS(顺序 = 渲染顺序,内容身份一部分);
# - from_order/to_order 枚举:BOND_ORDER_ALTERNATION(凯库勒三词);
# - output_origin:OUTPUT_ORIGIN_NOVEL_OUTSIDE_POOL(runflow 默认同值);
# - alignment.status 示范:ALIGNMENT_STATUS_RESOLVED(audit 词表成员)。
# 规则文本(Rules 段)与 Example 段中的操作/键级词是叙述实例,保持
# 字面量,由 CI 检测器(提示词提取 ↔ 执行器词表双向 diff,tests/
# test_controlled_vocab_ci.py)兜底同步。
_OP_BREAK, _OP_FORM, _OP_CHANGE, _OP_ADD = EDIT_OPS

# 静态段(不含词表声明位;与手写版逐字节一致)
_PROMPT_STATIC_1 = """You are a hypothesis proposer for a deterministic enzymatic single-step transformation search system (PPV1).

Your ONLY job: return ONE JSON object proposing net reaction hypotheses for one substrate. The task is neutral: propose plausible enzymatic single-step transformations (oxidation, reduction, group transfer, hydrolysis, cleavage, isomerization, or ligation) that the substrate's functional groups support. You never write databases, never claim recorded status, never score anything, never invent EC numbers or reaction conditions. Downstream deterministic code parses, audits and scores your proposals. When you are not sure a transformation is chemically supported, abstain (unknown is legal and honest).

Output contract (strict JSON, no markdown fences, no commentary, no long reasoning):
{
  "proposals": [
    {
      "hypothesis_id": "<one of the provided pool hypothesis ids>",
      ... optionally "coproducts": ["SMILES", ...]
    }
    OR (novel, outside the pool):
    {
      "hypothesis_id": "<new stable id you invent, e.g. novel-1>",
      "proposal_context": {
        "reference_hypothesis_ids": ["<pool ids you relied on; may be empty>"],
"""

_PROMPT_STATIC_2 = """      },
      "reaction_spec": {
        "product_smiles": "<main product SMILES>",
        "coproducts": ["<coproduct SMILES; optional>"],
        "edits": [
"""

_PROMPT_STATIC_3 = """        ],
        "donor": {"center_atom_ids": ["<atom ids of the reaction center, donor side>"]},
        "alignment": {
"""

_PROMPT_STATIC_4 = """          "donor_to_current": {"<donor atom id>": "<current atom id>"},
          "ref": "<your alignment reference, e.g. a source reaction id or self-declared>"
        },
        "expectation": {"target_smiles": "<expected product SMILES>"}
      }
    }
  ],
  "rank_hypotheses": ["<hypothesis_id in your preference order, best first>"]
}

Rules:
- at most 8 DIFFERENT net reactions per response; each proposal is one single-step net reaction with its complete product set (main product + coproducts); do not fixate on ketones or lactams — propose what the functional groups support.
- pool proposals: "hypothesis_id" MUST be one of the provided pool ids; do not invent pool ids.
- novel proposals MUST carry "proposal_context" and a complete "reaction_spec" (all five fields: product_smiles, edits, donor, alignment, expectation). Incomplete novel proposals are rejected item-by-item (a bounded format-feedback round may ask you to fix the JSON shape only).
- "edits" operate on the current substrate atom ids provided in the user message (the execution graph payload). Every edit must reference ids that exist in that payload (or a new_atom_id you declare for add_atom, which must not collide). add_atom automatically creates a single anchor bond to "atom1"; to make that new bond double/triple, follow with change_bond_order (from_order "single"). Never form a bond that already exists.
- new bonds between existing atoms: use form_bond (single), then change_bond_order if a higher order is intended.
- "rank_hypotheses" may only reference hypothesis ids present in your proposals.
- abstention is legal and honest: {"proposals": [], "rank_hypotheses": []}.
- one JSON object only; no extra keys that are not in the contract above.

Candidate evidence notes (deterministic system-computed context):
- each pool entry may carry an "evidence" object (edit summary, participant roles, alignment quality, compile diagnostics, source reference), and the payload may carry a "substrate_evidence" object (functional-group hits, element counts, molecular formula, computed descriptors such as partial charges) plus a "candidate_evidence_schema_version" field.
- these fields are informational context computed by the system; they do not change the output contract above.
- a value of the placeholder token unknown means the fact is not available in this system: treat it as not available and never guess or invent a value for it (this applies in particular to anything the rules above already forbid inventing).
- functional-group hits and computed descriptors (for example partial charges) are reference context only: they are not assigned reaction sites and are not proof by themselves; the provided execution graph remains the only editable structure fact.
"""

_PROMPT_STATIC_5 = """
Example (ethanol CCO, atom ids S_C_1 S_C_2 S_O_1, bonds S_C_1~S_C_2 single, S_C_2~S_O_1 single):
{"proposals": [{"hypothesis_id": "novel-1", "proposal_context": {"reference_hypothesis_ids": [], "output_origin": "novel_outside_pool"}, "reaction_spec": {"product_smiles": "CC=O", "edits": [{"op": "change_bond_order", "atom1": "S_C_2", "atom2": "S_O_1", "from_order": "single", "to_order": "double"}], "donor": {"center_atom_ids": ["S_C_2", "S_O_1"]}, "alignment": {"status": "resolved", "donor_to_current": {"S_C_2": "S_C_2", "S_O_1": "S_O_1"}, "ref": "self-declared-alcohol-oxidation"}, "expectation": {"target_smiles": "CC=O"}}}], "rank_hypotheses": ["novel-1"]}
"""

# 词表声明段(生成位;f-string 静态部分与手写版逐字节一致)
_PROMPT_SEGMENT_OUTPUT_ORIGIN = \
    f'        "output_origin": "{OUTPUT_ORIGIN_NOVEL_OUTSIDE_POOL}"\n'

_PROMPT_SEGMENT_EDITS = (
    f'          {{"op": "{_OP_BREAK}", "atom1": "<id>", "atom2": "<id>"}}\n'
    f'          | {{"op": "{_OP_FORM}", "atom1": "<id>", "atom2": "<id>"}}\n'
    f'          | {{"op": "{_OP_CHANGE}", "atom1": "<id>", "atom2": "<id>",\n'
    f'             "from_order": "{BOND_ORDER_ALTERNATION}",\n'
    f'             "to_order": "{BOND_ORDER_ALTERNATION}"}}\n'
    f'          | {{"op": "{_OP_ADD}", "element": "<element symbol>",\n'
    f'             "new_atom_id": "<id>", "atom1": "<anchor id>"}}\n'
)

_PROMPT_SEGMENT_ALIGNMENT_STATUS = \
    f'          "status": "{ALIGNMENT_STATUS_RESOLVED}",\n'

_PROPOSALS_SYSTEM_PROMPT = (
    _PROMPT_STATIC_1
    + _PROMPT_SEGMENT_OUTPUT_ORIGIN
    + _PROMPT_STATIC_2
    + _PROMPT_SEGMENT_EDITS
    + _PROMPT_STATIC_3
    + _PROMPT_SEGMENT_ALIGNMENT_STATUS
    + _PROMPT_STATIC_4
    + _PROMPT_STATIC_5
)

PROPOSALS_PROMPT_VERSION = hashlib.sha256(
    _PROPOSALS_SYSTEM_PROMPT.encode("utf-8")).hexdigest()


def build_proposals_user_payload(
        *, substrate_smiles: str, atom_id_map: dict[str, str],
        pool_entries: list[dict], feedback_error: dict | None = None,
        execution_graph: dict | None = None,
        substrate_evidence: dict | None = None) -> str:
    """组 proposals 请求的用户载荷(JSON 文本;确定性,零金标)。

    - substrate_smiles:题面底物;
    - atom_id_map:原子 ID → 元素(向后兼容字段);
    - **execution_graph(W5:同一执行图载荷)**:ID→idx/元素/电荷/H/
      必要立体、ID-labelled 实际键表、mapped SMILES、图 hash 与能力
      版本 —— 由 ``execution_graph_payload``(与 W1 编译器同一 render
      事实源)产生;模型不自猜 RDKit 解析/Kekulé;
    - pool_entries:[{hypothesis_id, product_smiles, transformation_ref,
      coproducts}]——冻结池候选(检索来源,不含金标);
    - **evidence(候选证据卡,Plan v1 §2.1)**:池条目可携带 ``evidence``
      子对象(candidate_evidence.candidate_evidence_payload 产物,在线
      事实;缺席 ⇒ 该条目不渲染 evidence 键,载荷与既有路径逐字节同);
    - **substrate_evidence(底物档案卡)**:candidate_evidence.
      substrate_evidence_payload 产物(在位 ⇒ 载荷另携带
      ``candidate_evidence_schema_version``;缺席 ⇒ 两键都不渲染);
    - feedback_error:格式反馈轮携带上一轮错误类别与摘录(有界修复)。
    """
    payload = {
        "substrate_smiles": str(substrate_smiles),
        "substrate_atom_id_map": {
            str(k): str(v) for k, v in sorted(atom_id_map.items())},
        "pool_hypotheses": [
            dict(
                {"hypothesis_id": str(e.get("hypothesis_id")),
                 "product_smiles": str(e.get("product_smiles")),
                 "transformation_ref": str(e.get("transformation_ref")),
                 "coproducts": [str(c) for c in
                                (e.get("coproducts") or [])]},
                **({"evidence": dict(e["evidence"])}
                   if isinstance(e.get("evidence"), dict) else {}))
            for e in (pool_entries or [])],
        "protocol_version": S5B_REAL_MODEL_VERSION,
    }
    if execution_graph:
        payload["execution_graph"] = dict(execution_graph)
    if isinstance(substrate_evidence, dict) and substrate_evidence:
        payload["substrate_evidence"] = dict(substrate_evidence)
        payload["candidate_evidence_schema_version"] = \
            CANDIDATE_EVIDENCE_SCHEMA_VERSION
    if feedback_error:
        payload["format_feedback"] = {
            "error_kind": str(feedback_error.get("kind") or ""),
            "response_excerpt": str(
                feedback_error.get("response_excerpt") or "")[:800],
            "note": ("Your previous response violated the JSON contract "
                     "above. Return a corrected single JSON object."),
        }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def substrate_atom_id_map(substrate_smiles: str) -> dict[str, str]:
    """底物渲染的原子 ID → 元素(确定性;novel edits 的 ID 空间)。

    渲染失败 ⇒ 空 dict(提示词如实携带空映射;模型 novel 提案引用
    未知 ID 会在执行侧结构化拒,不伪造映射)。
    """
    from ..services.atom_tool import _id_element, render

    try:
        current = render(str(substrate_smiles), "S")
    except Exception:
        return {}
    out: dict[str, str] = {}
    for atom_id, _idx in current.atom_id_map.items():
        element = _id_element(str(atom_id))
        if element:
            out[str(atom_id)] = str(element)
    return out


def execution_graph_payload(substrate_smiles: str,
                            render_name: str = "S") -> dict:
    """同一执行图载荷(W5;与 W1 编译器/execute_edits 同一事实源)。

    内容(全部确定性、可复算):
    - ``atoms``:{atom_id: {idx, element, formal_charge, total_h,
      chiral_tag}}(必要立体 = 四面体手性标签;非四面体/增强组不在
      表达范围,如实在 capability 里声明);
    - ``bonds``:ID-labelled 实际键表 [{"atom1", "atom2", "order"}]
      (kekulé 执行空间 —— execute_edits 的 from_order 事实源);
    - ``mapped_smiles``:原子映射号 SMILES(映射号 = idx+1,canonical
      重排后仍可对回 ID);
    - ``graph_hash``:图内容哈希(同底物同图 ⇒ 同 hash);
    - ``capability``:{atomtool_version, edit_protocol_version,
      unsupported: [charge_edits, stereo_edits, aromatic_bond_tokens]}。
      **scope 注记(R1,mimo r33 采纳条件 S6)**:该 unsupported 描述
      的是**模型侧 novel 编辑协议面**(执行器确无立体 op,对
      novel 编辑仍然为真);编译侧 stereo 消解
      (S5b-stereo-dissolution-1,元素域限碳,经既有键级 op 编译,
      不经模型提议)存在且以 spec 的
      ``stereo_dissolution_applied`` 机读披露——两属不同协议面,
      防全系统级误读。

    渲染/解析失败 ⇒ 空 dict(调用方如实携带空载荷;模型引用未知 ID
    在执行侧结构化拒,不伪造)。edit order 按 single/double/triple 实际
    键级;合法小写芳香 product SMILES 仍可用(执行器 sanitize 重感知)。
    """
    from rdkit import Chem

    from ..services.atom_tool import (
        ATOMTOOL_VERSION,
        EDIT_PROTOCOL_VERSION,
        _id_element,
        render,
    )

    try:
        current = render(str(substrate_smiles), render_name)
        mol = Chem.MolFromSmiles(str(substrate_smiles))
    except Exception:
        return {}
    if current is None or mol is None:
        return {}
    try:
        kek = Chem.Mol(mol)
        Chem.Kekulize(kek, clearAromaticFlags=True)
    except Exception:
        kek = Chem.Mol(mol)
    idx_to_id = {int(v): str(k) for k, v in current.atom_id_map.items()}
    atoms: dict[str, dict] = {}
    for atom in mol.GetAtoms():
        atom_id = idx_to_id.get(atom.GetIdx())
        if atom_id is None:
            continue
        atoms[atom_id] = {
            "idx": atom.GetIdx(),
            "element": _id_element(atom_id) or atom.GetSymbol(),
            "formal_charge": atom.GetFormalCharge(),
            "total_h": atom.GetTotalNumHs(),
            "chiral_tag": str(atom.GetChiralTag()),
        }
    bonds: list[dict] = []
    for bond in kek.GetBonds():
        a1 = idx_to_id.get(bond.GetBeginAtomIdx())
        a2 = idx_to_id.get(bond.GetEndAtomIdx())
        if a1 is None or a2 is None:
            continue
        token = {
            Chem.BondType.SINGLE: "single",
            Chem.BondType.DOUBLE: "double",
            Chem.BondType.TRIPLE: "triple",
        }.get(bond.GetBondType(), "aromatic")
        bonds.append({"atom1": a1, "atom2": a2, "order": token})
    bonds.sort(key=lambda b: (b["atom1"], b["atom2"]))
    mapped = Chem.Mol(mol)
    for idx in range(mapped.GetNumAtoms()):
        mapped.GetAtomWithIdx(idx).SetAtomMapNum(idx + 1)
    graph_hash = hashlib.sha256(json.dumps(
        {"atoms": atoms, "bonds": bonds}, ensure_ascii=False,
        sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "atoms": atoms,
        "bonds": bonds,
        "mapped_smiles": Chem.MolToSmiles(mapped),
        "graph_hash": graph_hash,
        "capability": {
            "atomtool_version": ATOMTOOL_VERSION,
            "edit_protocol_version": EDIT_PROTOCOL_VERSION,
            # scope:模型侧 novel 编辑协议面无立体 op;编译侧碳消解
            # (S5b-stereo-dissolution-1)经键级 op 编译并以
            # stereo_dissolution_applied 披露,不在此 capability 面
            "unsupported": ["charge_edits", "stereo_edits",
                            "aromatic_bond_tokens"],
        },
    }


# ---------------------------------------------------------------- 适配器


class RealModelAdapter:
    """PPV1 proposals 的 real provider 适配器(传输层;身份可冻结)。

    - ``client``:legacy ``OpenAICompatibleClient``(复用,不重写);
    - ``call_account_path``:逐调用账本(JSONL 追加;None ⇒ 不落盘
      账本,调用状态仍在 ledger model_requests 表);
    - ``identity_block()`` 供 runflow ``_prediction_block`` 消费
      (resume 逐字段核对拒绝静默继续)。
    """

    provider = "openai_compatible"

    def __init__(self, client: OpenAICompatibleClient, *,
                 call_account_path: str | Path | None = None) -> None:
        self.client = client
        self.call_account_path = (
            Path(call_account_path) if call_account_path else None)
        self.model_id = client.model
        self.request_params = dict(client.request_params)
        self.timeout_s = float(client.timeout_s)
        self.max_http_retries = int(client.max_http_retries)

    # ------------------------------------------------------------ 装配

    @classmethod
    def from_env(cls, *, timeout_s: float | None = None,
                 request_params: dict | None = None,
                 max_http_retries: int | None = None,
                 call_account_path: str | Path | None = None,
                 ) -> "RealModelAdapter":
        """从环境装配(缺凭证 ⇒ RealModelNotConfigured,零密钥 detail)。

        凭证读取(部署定案 2026-10-09):主名 ``V43_LLM_BASE_URL`` /
        ``V43_LLM_API_KEY`` / ``V43_LLM_MODEL``(受限专用文件
        ``.dependingv43-dashscope.env`` 注入);v41 老名
        ``LLM_API_BASE_URL`` / ``LLM_API_KEY`` / ``LLM_MODEL`` 只作
        只读回退(值只进内存,不打印不落盘不写入任何 detail)。
        """
        base_url = os.environ.get(LLM_BASE_URL_ENV) or os.environ.get(
            "LLM_API_BASE_URL") or ""
        api_key = os.environ.get(LLM_API_KEY_ENV) or os.environ.get(
            "LLM_API_KEY") or ""
        model = os.environ.get(LLM_MODEL_ENV) or os.environ.get(
            "LLM_MODEL") or ""
        missing = [name for name, value in (
            (LLM_BASE_URL_ENV, base_url),
            (LLM_API_KEY_ENV, api_key),
            (LLM_MODEL_ENV, model),
        ) if not value]
        if missing:
            raise RealModelNotConfigured(
                "真实提供者环境变量缺失(主名 V43_LLM_* 与 v41 老名均"
                "缺席;凭证只从环境读取,不落盘):" + ",".join(missing),
                {"missing_env": missing})
        client = OpenAICompatibleClient(
            base_url=base_url, api_key=api_key, model=model)
        client.timeout_s = float(
            timeout_s if timeout_s is not None
            else (os.environ.get(LLM_TIMEOUT_ENV) or
                  S5B_DEFAULT_TIMEOUT_S))
        if request_params:
            merged = dict(client.request_params)
            merged.update(request_params)
            client.request_params = merged
        client.max_http_retries = int(
            max_http_retries if max_http_retries is not None
            else (os.environ.get("V43_LLM_MAX_HTTP_RETRIES")
                  or S5B_DEFAULT_MAX_HTTP_RETRIES))
        return cls(client, call_account_path=call_account_path)

    # ------------------------------------------------------------ 身份

    def identity_block(self) -> dict:
        """进入 run_identity 的 prediction 块(不含 client/密钥)。

        R5:模型身份包含 **retry/timeout 参数**(max_http_retries 与
        timeout_s、request_params)—— 重试/超时变化 = 不同身份,同批
        resume 逐字段核对拒绝静默继续。

        S5B-V3-02:客户端闸门带冻结金额守卫配置 ⇒ ``budget_guard``
        块入身份(帽/价格/输入保守界/输出上限/配置哈希;resume 逐字段
        核对 —— 金额配置变化 = 不同批次身份;配置坏形状 ⇒ GateCorrupt
        上抛,装配期 fail-closed,不静默发送)。"""
        from ..domain.policy import PREDICTION_POLICY_VERSION

        block = {
            "enabled": True,
            "provider": self.provider,
            "model_id": self.model_id,
            "prompt_versions": {"proposals": PROPOSALS_PROMPT_VERSION},
            "policy_version": PREDICTION_POLICY_VERSION,
            "policy": {},
            "request_params": dict(self.request_params),
            "timeout_s": float(self.timeout_s),
            "max_http_retries": int(self.max_http_retries),
        }
        gate = getattr(self.client, "gate", None)
        if gate is not None:
            cost_config = gate.cost_guard_summary()
            if cost_config is not None:
                block["budget_guard"] = {
                    "schema": str(cost_config["schema"]),
                    "cap_cny": float(cost_config["cap_cny"]),
                    "currency": str(cost_config["currency"]),
                    "input_per_mtok": float(
                        cost_config["input_per_mtok"]),
                    "output_per_mtok": float(
                        cost_config["output_per_mtok"]),
                    "input_tokens_conservative_bound": int(
                        cost_config["input_tokens_conservative_bound"]),
                    "max_output_tokens": int(
                        cost_config["max_output_tokens"]),
                    "per_attempt_bound_cny": float(
                        cost_config["per_attempt_bound_cny"]),
                    "config_sha256": str(cost_config["config_sha256"]),
                }
        return block

    # ------------------------------------------------------------ 账本

    def _append_account(self, record: dict) -> None:
        if self.call_account_path is None:
            return
        path = Path(self.call_account_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {**record, "provider_env": real_provider_env(),
             "recorded_at": now_iso()},
            ensure_ascii=False, sort_keys=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # ------------------------------------------------------------ 取响应

    def _complete(self, *, system_prompt: str, user_payload: str,
                  idempotency_key: str):
        """传输入口(真实 = legacy 客户端;scripted 桩子类覆写)。"""
        return self.client.complete(
            mode="proposals", system_prompt=system_prompt,
            user_payload=user_payload,
            idempotency_key=idempotency_key)

    # ---- R3(S5b W6):响应 blob 原子持久化与零调用重放 ----

    def _blob_path(self, request_id: str):
        if self.call_account_path is None:
            return None
        return self.call_account_path.parent / "s5b_responses" / \
            f"{request_id}.json"

    def _save_response_blob(self, request_id: str, request_key: str,
                            purpose: str, content: str) -> dict | None:
        """完整最终 content 先原子 blob 保存(摘要可截断,权威响应不可
        截断),SHA/字节/字符校验元数据随 blob;失败 ⇒ 持久化失败不能
        授可重放(如实返回 None,调用方不标记 responded)。"""
        path = self._blob_path(request_id)
        if path is None:
            return None
        raw = str(content).encode("utf-8")
        blob = {
            "blob_version": "s5b-response-blob-1",
            "request_id": str(request_id),
            "request_key": str(request_key),
            "purpose": str(purpose),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "chars": len(str(content)),
            "content": str(content),
            "saved_at": now_iso(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(blob, ensure_ascii=False, sort_keys=True),
                       encoding="utf-8")
        os.replace(tmp, path)
        # 读回校验(原子写后同字节)
        back = path.read_bytes()
        if hashlib.sha256(back).hexdigest() != \
                hashlib.sha256(json.dumps(
                    blob, ensure_ascii=False, sort_keys=True)
                    .encode("utf-8")).hexdigest():
            return None
        return blob

    def _load_response_blob(self, request_id: str) -> dict | None:
        """读取并核验响应 blob(SHA/字节/字符/引用一致性;缺失/篡改 ⇒
        None —— 不授可重放)。"""
        path = self._blob_path(request_id)
        if path is None or not path.is_file():
            return None
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        content = str(blob.get("content") or "")
        raw = content.encode("utf-8")
        if blob.get("blob_version") != "s5b-response-blob-1":
            return None
        if blob.get("request_id") != str(request_id):
            return None  # 引用不一致(拿别的响应冒充)⇒ 拒
        if blob.get("sha256") != hashlib.sha256(raw).hexdigest():
            return None  # 篡改
        if blob.get("bytes") != len(raw) or blob.get("chars") != len(content):
            return None
        return blob

    def ppv1_real_fetch(self, *, ledger, run_id: str, action_id: str,
                        attempt_id: str, prompt_payload: dict,
                        request_key: str, purpose: str = "proposals",
                        request: dict | None = None,
                        feedback_error: dict | None = None,
                        provider_kind: str = PROVIDER_KIND_REAL) -> dict:
        """登记 → 发送 → 传输 → blob 保存 → 记账,返回响应与请求行
        (runflow 消费)。

        调用序(prep §3.2;失败/超时/悬空均占额,永不释放):
        1. request 行已给(格式反馈轮)⇒ 直接消费;否则登记
           (``provider_kind`` 沿 plan;real ⇒ 占 max_real_model_requests
           额度,额度 0 ⇒ SearchBudgetExhausted,网络发送被阻止);
        2. 既有行状态:
           - **responded + 有效完整 blob**(R3):零调用消费既有响应,
             继续同一公共链(同 1logical 的 resume;仅保存 blob 不等于
             恢复 —— blob 缺失/篡改 ⇒ replay_unavailable 结构化拒,
             不补调用、不猜补);
           - **sent**:悬空。blob 已原子保存 ⇒ 响应实际已收到,恢复为
             responded 并零调用消费(blob 先于 responded 落盘,crash
             窗口不生成假 responded);blob 缺失 ⇒ 保守 failed 并占
             额度,**禁止孤儿自动新 logical 请求**(R5:题级/适配层
             新 logical retry 0;未知费用不凭空退款);
           - registered/空 ⇒ 首发;
           - 其他状态 ⇒ 生命周期拒绝(request_not_consumable);
        3. 首发:``record_request_sent`` → ``complete``(Idempotency-
           Key=请求稳定 ID;429/闸门/付费停止语义全在客户端内);
        4. ok ⇒ **先原子 blob 保存 + SHA/字节/字符校验,再
           ``record_request_response``**(持久化失败不能授可重放);
           传输失败/超时/空响应 ⇒ ``mark_request_failed`` + 结构化
           失败上抛(失败题留分母);
        5. 逐调用记账(usage 归一;缺 usage 保守预留;费用字段分
           input/visible content/billed output/reasoning/usage
           unknown/延迟)。
        """
        if request is None:
            request = ledger.register_model_request(
                run_id=run_id, action_id=action_id, attempt_id=attempt_id,
                provider_kind=provider_kind, request_key=request_key,
                purpose=purpose, payload={
                    "prompt_digest": hashlib.sha256(
                        json.dumps(prompt_payload, ensure_ascii=False,
                                   sort_keys=True).encode("utf-8")
                        ).hexdigest(),
                    "purpose": purpose,
                    "feedback": bool(feedback_error),
                })
        request_id = str(request["request_id"])
        row = ledger.conn.execute(
            "SELECT * FROM model_requests WHERE request_id = ?",
            (request_id,)).fetchone()
        status = str(row["status"]) if row is not None else ""
        # ---- R3:responded + 有效 blob ⇒ 零调用消费(同 1logical) ----
        if status == "responded":
            blob = self._load_response_blob(request_id)
            if blob is None:
                raise RealModelNotConfigured(
                    f"请求 {request_id} 已 responded 但响应 blob 缺失/"
                    "篡改/校验失败(不能授可重放;不补调用、不猜补 —— "
                    "截断摘要不能确认原始完整性 ⇒ replay_unavailable)",
                    {"request_id": request_id, "status": status,
                     "kind": "replay_unavailable"})
            self._append_account({
                "request_id": request_id, "request_key": request_key,
                "purpose": purpose, "status": "replayed_from_blob",
                "note": "responded+valid blob: zero-call consumption "
                        "(same 1-logical request)",
            })
            return {
                "request": dict(request),
                "response_text": str(blob["content"]),
                "call": {
                    "request_id": request_id, "request_key": request_key,
                    "purpose": purpose, "ok": True, "replayed": True,
                    "error_kind": "", "elapsed_s": 0.0,
                    "http_attempts": [], "usage": {},
                    "usage_unknown": True,
                    "response_chars": int(blob.get("chars") or 0),
                    "note": "R3 blob replay(零调用;费用已在首发记账)",
                },
            }
        if status == "sent":
            # ---- 悬空(crash 后 resume)----
            blob = self._load_response_blob(request_id)
            if blob is not None:
                # blob 已原子保存(先于 responded 落盘):响应实际已
                # 收到 —— 恢复为 responded 并零调用消费(不生成假
                # responded:blob 存在是响应已收到的持久证据)
                ledger.record_request_response(
                    request_id, response_ref=f"s5b-blob:{request_id}")
                self._append_account({
                    "request_id": request_id, "request_key": request_key,
                    "purpose": purpose,
                    "status": "recovered_sent_to_responded_via_blob",
                    "note": "sent + valid blob: crash window closed "
                            "(blob saved before responded)",
                })
                return {
                    "request": dict(request),
                    "response_text": str(blob["content"]),
                    "call": {
                        "request_id": request_id,
                        "request_key": request_key, "purpose": purpose,
                        "ok": True, "recovered": True, "error_kind": "",
                        "elapsed_s": 0.0, "http_attempts": [],
                        "usage": {}, "usage_unknown": True,
                        "response_chars": int(blob.get("chars") or 0),
                    },
                }
            # sent 无完整 blob:保守 failed 并占额度;**禁止孤儿自动新
            # logical 请求**(R5:不默发第二请求;未知费用不退款)
            ledger.mark_request_failed(request_id)
            self._append_account({
                "request_id": request_id, "request_key": request_key,
                "purpose": purpose, "status": "orphan_marked_failed",
                "note": ("sent-without-complete-blob: failed, quota kept; "
                         "NO new logical request (R5 retry0)"),
            })
            raise RealModelTransportFailure(
                f"请求 {request_id} 悬空(sent 且无完整响应 blob;"
                "保守 failed 并占额;禁止孤儿自动新 logical 请求 —— "
                "失败题留分母,不默发第二请求)", {
                    "request_id": request_id, "request_key": request_key,
                    "error_kind": "orphan_sent_without_blob",
                    "error_message": "sent-without-complete-blob",
                    "kind": "real_model_transport_failure"})
        if status not in ("registered", ""):
            raise RealModelNotConfigured(
                f"请求 {request_id} 状态 {status} 不可消费(生命周期拒绝;"
                "同键幂等复用须 registered)", {
                    "request_id": request_id, "status": status,
                    "kind": "request_not_consumable"})
        ledger.record_request_sent(request_id)
        self._append_account({
            "request_id": request_id, "request_key": request_key,
            "purpose": purpose, "status": "issued",
        })
        response = self._complete(
            system_prompt=_PROPOSALS_SYSTEM_PROMPT,
            user_payload=build_proposals_user_payload(
                substrate_smiles=str(prompt_payload.get(
                    "substrate_smiles") or ""),
                atom_id_map=dict(
                    prompt_payload.get("atom_id_map") or {}),
                pool_entries=list(
                    prompt_payload.get("pool_entries") or []),
                feedback_error=feedback_error,
                execution_graph=dict(
                    prompt_payload.get("execution_graph") or {}) or None,
                substrate_evidence=dict(
                    prompt_payload.get("substrate_evidence") or {})
                or None),
            idempotency_key=stable_id(
                "s5b", run_id, action_id, request_key),
        )
        usage = _normalized_usage(response.usage)
        call_record = {
            "request_id": request_id, "request_key": request_key,
            "purpose": purpose,
            "ok": bool(response.ok),
            "error_kind": str(response.error_kind or ""),
            # W5 费用字段:input/visible content/billed output/reasoning
            # (provider 若有)/usage unknown 与延迟分开列示
            "elapsed_s": round(float(response.elapsed_s or 0.0), 3),
            "http_attempts": [
                {k: v for k, v in (a or {}).items()}
                for a in (response.http_attempts or [])],
            "usage": usage,
            "usage_unknown": not bool(usage),
            "input_tokens": usage.get("input_tokens"),
            "visible_content_chars": len(response.raw_text or ""),
            "billed_output_tokens": usage.get("output_tokens"),
            "reasoning_output_tokens": usage.get(
                "reasoning_output_tokens"),
            "provider_request_id": response.request_id or "",
            "sent_at_epoch": response.sent_at_epoch,
            "done_at_epoch": response.done_at_epoch,
            "response_chars": len(response.raw_text or ""),
        }
        if response.ok:
            # ---- R3:先原子 blob 保存(权威响应不可截断;摘要可截断),
            # 校验通过才标记 responded(持久化失败不能授可重放)。无
            # blob 存储配置(未给 call_account_path 的 scripted 桩)⇒
            # 跳过 blob(resume 重放如实 replay_unavailable,不补调用)。 ----
            blob = None
            if self.call_account_path is not None:
                blob = self._save_response_blob(
                    request_id, request_key, purpose,
                    str(response.raw_text))
                if blob is None:
                    ledger.mark_request_failed(request_id)
                    self._append_account({
                        **call_record, "status": "failed",
                        "note": "response blob persistence failed: "
                                "not consumable as replayable",
                    })
                    raise RealModelTransportFailure(
                        f"请求 {request_id} 响应 blob 持久化失败(权威"
                        "响应不可截断;不能授可重放 ⇒ 记 failed,不冒充"
                        "成功)",
                        {"request_id": request_id,
                         "request_key": request_key,
                         "error_kind": "blob_persistence_failed",
                         "error_message": "blob save/verify failed",
                         "kind": "real_model_transport_failure"})
            ledger.record_request_response(
                request_id,
                response_ref=(
                    f"s5b-blob:{request_id}" if blob is not None
                    else f"s5b-call:{request_id}"))
            self._append_account({
                **call_record, "status": "responded",
                **({"response_blob_sha256": blob["sha256"]}
                   if blob is not None else {}),
                "response_text": str(response.raw_text or "")[:20000],
            })
        else:
            ledger.mark_request_failed(request_id)
            self._append_account({
                **call_record, "status": "failed",
                "response_text": str(response.raw_text or "")[:20000],
            })
            raise RealModelTransportFailure(
                f"真实模型调用失败({response.error_kind or 'unknown'};"
                "失败/超时/悬空占额,失败题留 298 分母;传输层 429 重试"
                "已在客户端内有界完成)", {
                    "request_id": request_id, "request_key": request_key,
                    "error_kind": str(response.error_kind or ""),
                    "error_message": str(response.error_message or ""),
                    "kind": "real_model_transport_failure"})
        return {"request": dict(request), "response_text":
                str(response.raw_text or ""), "call": call_record}


class RealModelTransportFailure(RuntimeError):
    """真实模型传输失败/超时/空响应(结构化;失败题留分母)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


def _normalized_usage(usage: dict) -> dict:
    """provider usage → 归一口径(缺席字段显式缺,不估算冒充实测)。"""
    from ..adapters.llm_client import normalize_usage

    normalized = normalize_usage(dict(usage or {}))
    out = {k: v for k, v in normalized.items() if k != "raw"}
    return out


# ---------------------------------------------------------------- scripted 桩


class ScriptedRealModelAdapter(RealModelAdapter):
    """scripted 模型桩(测试/冒烟;与真实适配器**同一**取响应调用序
    与同一确定性解析器,provider_kind 按 plan 注册(scripted ⇒ 网络 0、
    不占真实额度);不冒充在线模型验证)。

    - ``strategy="first_pool"``:从提示词载荷里解析冻结池,提案首个
      池条目(确定性;完整链验收用——不预知 hypothesis_id);
    - ``strategy="responses"``:按序消费 ``responses`` 列表(耗尽 ⇒
      合法弃权 ``{"proposals": []}``);
    - ``fail_with``:可选 {error_kind, error_message}(传输失败桩)。
    """

    provider = "scripted-stub"

    def __init__(self, *, strategy: str = "first_pool",
                 responses: list[str] | None = None,
                 fail_with: dict | None = None,
                 model_id: str = "s5b-scripted-stub-v1",
                 call_account_path: str | Path | None = None) -> None:
        self.strategy = str(strategy)
        self.responses = [str(r) for r in (responses or [])]
        self.fail_with = dict(fail_with or {})
        self.model_id = model_id
        self.request_params: dict = {}
        self.timeout_s = 0.0
        self.max_http_retries = 0
        self.client = None  # type: ignore[assignment]
        self.call_account_path = (
            Path(call_account_path) if call_account_path else None)
        self.seen_user_payloads: list[str] = []

    def identity_block(self) -> dict:
        from ..domain.policy import PREDICTION_POLICY_VERSION

        return {
            "enabled": True,
            "provider": self.provider,
            "model_id": self.model_id,
            "prompt_versions": {"proposals": PROPOSALS_PROMPT_VERSION},
            "policy_version": PREDICTION_POLICY_VERSION,
            "policy": {"strategy": self.strategy},
            "request_params": {},
            "timeout_s": 0.0,
            "max_http_retries": int(self.max_http_retries),
        }

    def _complete(self, *, system_prompt: str, user_payload: str,
                  idempotency_key: str):
        from ..adapters.llm_client import LLMResponse

        self.seen_user_payloads.append(str(user_payload))
        if self.fail_with:
            return LLMResponse(
                ok=False,
                error_kind=str(self.fail_with.get("error_kind")
                               or "transport_error"),
                error_message=str(
                    self.fail_with.get("error_message") or "stub-failure"))
        if self.strategy == "responses" and self.responses:
            raw = self.responses.pop(0)
        elif self.strategy == "responses":
            raw = '{"proposals": []}'
        else:  # first_pool:从载荷解析冻结池,提案首个池条目
            try:
                payload = json.loads(user_payload)
                pool = payload.get("pool_hypotheses") or []
            except (ValueError, TypeError):
                pool = []
            if pool:
                first = str(pool[0].get("hypothesis_id") or "")
                raw = json.dumps(
                    {"proposals": [{"hypothesis_id": first}],
                     "rank_hypotheses": [first]},
                    ensure_ascii=False)
            else:
                raw = '{"proposals": []}'
        return LLMResponse(
            ok=bool(raw.strip()), raw_text=raw,
            error_kind="" if raw.strip() else "empty_response",
            elapsed_s=0.0, usage={"fake": True})
