"""S5b 题卷构建器 —— questions.jsonl → PPV1 run 输入 + 参考图/清单
(预注册 §2/§3 转换规则落地;契约登记 s5b-builder-1)。

职责与边界:

- 输入 = 题卷 questions.jsonl(每行 qid/substrate_smiles/products_smiles
  [金标]/...;运行时在 Chenyu 给真实路径,测试用合成夹具);
- 输出根**必须落在 gitignored 目录**(仓内只允许 ``reports/ppv1_s5b/``
  之下的路径;仓外路径合法;仓内其它路径 fail-closed 拒)——金标承载物
  (参考图 JSON、run 输入的题面+池)只进 gitignored,仓内代码/文档零
  金标取值;
- 每题产出一个 G1 参考图(一题一图,预注册 §2):root qid 进
  source_refs(evaluation-4 图侧一致性核)、参考边 = 底物→全部金标
  产物节点、全 principal(§3.2)、participant_list_status=partial +
  固定披露(§3.3)、step_scope=net_reaction 无守恒声明(§3.1)、
  node/edge status=reference_only(§3.4)、condition_requirements 空 +
  scenario_scope=rhea_generic_enzymology_no_scenario(§3.6)、
  known_gaps 固定清单仅披露不豁免(§4)、S1 一题一组(§7;跨题重复
  底物标 related,其余 unknown,永不 independent);
- 每题产出一条 PPV1 run 输入(根底物=substrate、无人工条件注入、
  模型 provider_kind=real;池 = 注入的 pool_provider 的确定性检索结果,
  **底物侧检索,零金标消费**);
- 冻结注册序 = questions.jsonl 行序(codex 复审 §5:构建器清单序是首
  注册锚,不得目录遍历偶然序/内容择优;重复 qid fail-closed 拒);
- 判分零 LLM;金标只在封存答卷后的判分进程(s5b_scoring)进入。

本模块不做真实模型调用、不写仓内文件(除调用方给定的 gitignored
输出根);合成测试夹具的 qid/分子与真实 298 集合零重叠由测试纪律
保证(本模块对 qid 前缀不做真实集校验,如实披露)。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import V43Config
from ..domain.models import stable_id
from .chemstate import build_chemical_state
from .profile import (
    PPV1_REFERENCE_GRAPH_VERSION,
    PPV1_SPLIT_MANIFEST_VERSION,
)
from .reference_graph import (
    reference_graph_sha256,
    validate_reference_graph,
)

S5B_BUILDER_VERSION = "s5b-builder-1"

# 仓内唯一允许的输出根(gitignored;.gitignore 由本批同步登记)
S5B_GITIGNORED_REPO_ROOT = "reports/ppv1_s5b"

# 固定披露(预注册 §3/§4;known_gaps 仅披露,不豁免分母)
S5B_KNOWN_GAPS = (
    "cofactors_cosubstrates_stripped_per_extraction_rules_2026_09_22",
    "no_per_question_conditions_metadata",
    "principal_vs_coproduct_undistinguished",
    "identity_underestimation_charge_difference_cn_only",
    "identity_underestimation_stereo_difference_cn_only",
    "identity_underestimation_tautomer_no_match",
    "no_balanced_coefficients_no_conservation_claim",
)
S5B_SCENARIO_SCOPE = "rhea_generic_enzymology_no_scenario"
S5B_SPLIT_RULE_VERSION = "ppv1-s5b-split-1"

# 参与物覆盖披露句(预注册 §3.3 固定披露句)
S5B_PARTICIPANT_DISCLOSURE = (
    "参与物 = 提取后的含碳组分;辅因子/共底物(NAD(P)±/H、ATP、GSH、"
    "水、金属离子、>80 字符大分子辅因子)按 2026-09-22 提取规则未列"
    "(反应物侧共剥 473 项);本参考边无配平系数(coefficient_status="
    "unknown),不作元素/电荷/电子供体计量声明,不构成守恒已核;"
    "本卷金标无角色标注,全列主产物是口径选择,不是化学认定;小分子"
    "共产物不豁免召回;相同结构的共同产物按结构集合匹配,份数不在"
    "判分面")


class S5bBuilderError(RuntimeError):
    """构建器契约违反(结构化 fail-closed)。"""

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


# ---------------------------------------------------------------- 输出根守卫


def check_output_root(output_root: str | Path, *,
                      repo_root: str | Path | None = None) -> Path:
    """金标承载物的输出根守卫:仓内只许 gitignored 授权根。

    - 仓外路径:合法(Chenyu 部署批次根本在仓外);
    - 仓内路径:必须位于 ``reports/ppv1_s5b/`` 之下(该根已进
      .gitignore;其它仓内路径 ⇒ 结构化拒,零写入)。
    """
    root = Path(output_root).resolve()
    if repo_root is None:
        from ..config import repo_root as _repo_root

        repo_root = _repo_root()
    repo = Path(repo_root).resolve()
    try:
        rel = root.relative_to(repo)
    except ValueError:
        return root  # 仓外:合法
    rel_posix = rel.as_posix()
    if rel_posix == S5B_GITIGNORED_REPO_ROOT or rel_posix.startswith(
            S5B_GITIGNORED_REPO_ROOT + "/"):
        return root
    raise S5bBuilderError(
        f"金标承载物输出根不合法:{root}(仓内路径只允许 "
        f"{S5B_GITIGNORED_REPO_ROOT}/ 之下的 gitignored 根;零写入)",
        {"kind": "s5b_output_root_unauthorized",
         "output_root": str(root), "repo_relative": rel_posix,
         "authorized_repo_root": S5B_GITIGNORED_REPO_ROOT})


# ---------------------------------------------------------------- 题卷读取


def load_questions(questions_path: str | Path) -> list[dict]:
    """读题卷(逐行 JSON;qid 唯一性核验;冻结注册序 = 行序)。

    返回逐行 dict(含金标 products_smiles——只允许流入 gitignored
    输出根,见 check_output_root)。缺 qid/substrate/products 字段 ⇒
    结构化拒(不静默跳行)。
    """
    path = Path(questions_path)
    if not path.is_file():
        raise S5bBuilderError(
            f"题卷文件不存在:{path}", {"kind": "s5b_questions_missing",
                                    "path": str(path)})
    questions: list[dict] = []
    seen_qids: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except ValueError as exc:
                raise S5bBuilderError(
                    f"题卷第 {line_no} 行不可解析为 JSON:{exc}",
                    {"kind": "s5b_questions_unparseable", "line": line_no,
                     "path": str(path)}) from exc
            if not isinstance(record, dict):
                raise S5bBuilderError(
                    f"题卷第 {line_no} 行不是 JSON 对象",
                    {"kind": "s5b_questions_not_object", "line": line_no})
            qid = str(record.get("qid") or "")
            substrate = str(record.get("substrate_smiles") or "")
            products = record.get("products_smiles")
            if not qid or not substrate or not isinstance(products, list):
                raise S5bBuilderError(
                    f"题卷第 {line_no} 行缺 qid/substrate_smiles/"
                    "products_smiles(缺字段明确失败,不静默跳行)",
                    {"kind": "s5b_questions_field_missing",
                     "line": line_no, "qid": qid})
            if qid in seen_qids:
                raise S5bBuilderError(
                    f"题卷 qid 重复:{qid}(qid 是样本↔导出配对键,重复即"
                    "歧义;fail-closed)", {
                        "kind": "s5b_questions_duplicate_qid", "qid": qid})
            seen_qids.add(qid)
            questions.append(record)
    if not questions:
        raise S5bBuilderError(
            "题卷为空(零题;fail-closed)", {
                "kind": "s5b_questions_empty", "path": str(path)})
    return questions


# ---------------------------------------------------------------- 参考图


def build_reference_graph(question: dict, *, repeated_substrate: bool,
                          domain: str = "298") -> dict:
    """一题一图(G1;预注册 §2/§3 全规则;金标产物进 nodes/to 参与物)。

    - root_entity:strict_structure_identity 由 PPV1 严格身份机制对
      substrate 现算(298 底物全显式 SMILES,不走 cn_only 分支);
    - 参考边 = 根 → 全部金标产物(一题一条边;共同产物不被报告 K 删);
    - 全部金标产物 role=principal_product(§3.2 口径,非化学认定);
    - source group S1 一题一组;重复底物 related,其余 unknown,永不
      independent(§7);
    - creation_review=pending_user_teacher_review(真实数据待评审;
      合成夹具由调用方如实改标 synthetic_rule_level)。
    """
    qid = str(question["qid"])
    substrate = str(question["substrate_smiles"])
    products = [str(p) for p in question["products_smiles"]]
    if not products:
        raise S5bBuilderError(
            f"题 {qid} 金标产物为空(空产物不合法;fail-closed)",
            {"kind": "s5b_empty_products", "qid": qid})
    try:
        state = build_chemical_state(substrate, "raw_input",
                                     [{"record": f"s5b-question:{qid}"}])
    except Exception as exc:  # noqa: BLE001 —— 结构化包装
        raise S5bBuilderError(
            f"题 {qid} 底物不可解析(严格身份现算失败):{exc}",
            {"kind": "s5b_substrate_unparseable", "qid": qid}) from exc
    graph_id = s5b_graph_id(qid)
    prov_id = f"prov-{qid}"
    group_id = f"sg-{qid}"
    root_node_id = f"n-{qid}-root"
    product_node_ids = [f"n-{qid}-p{i + 1}"
                        for i in range(len(products))]
    nodes = [
        {
            "node_id": root_node_id,
            "state_identity": f"strict:{state.smiles_isomeric}",
            "structure_smiles": substrate,
            "structure_identity_scope": "strict_structure",
            "role": "root",
            "occurrence_id": f"occ-{qid}-root",
            "source_group_refs": [group_id],
            "condition_scope": [],
            "provenance_refs": [prov_id],
            "node_status": "reference_only",
        },
    ]
    for i, product in enumerate(products):
        nodes.append({
            "node_id": product_node_ids[i],
            "state_identity": f"strict-ref:{product}",
            "structure_smiles": product,
            "structure_identity_scope": "strict_structure",
            "role": "principal_product",
            "occurrence_id": f"occ-{qid}-p{i + 1}",
            "source_group_refs": [group_id],
            "condition_scope": [],
            "provenance_refs": [prov_id],
            "node_status": "reference_only",
        })
    participants = [
        {"node_id": root_node_id, "side": "reactant", "role": "substrate",
         "coefficient": None, "coefficient_status": "unknown"},
    ]
    for node_id in product_node_ids:
        participants.append({
            "node_id": node_id, "side": "product",
            "role": "principal_product", "coefficient": None,
            "coefficient_status": "unknown",
        })
    graph = {
        "schema_version": PPV1_REFERENCE_GRAPH_VERSION,
        "reference_graph_id": graph_id,
        "domain": domain,
        "track": "known_evidence_reconstruction",
        "root_entity": {
            "entity_id": f"root-{qid}",
            "structure_smiles_raw": substrate,
            "strict_structure_identity": state.smiles_isomeric,
            "formal_charge": state.formal_charge,
            "stereo_information_status": state.stereo_information_status,
            "isotope_information_status": state.isotope_information_status,
            "source_refs": [qid],
        },
        "nodes": nodes,
        "edges": [
            {
                "edge_id": f"e-{qid}",
                "from_node_ids": [root_node_id],
                "to_node_ids": list(product_node_ids),
                "transformation_ref": qid,
                "transformation_signature_status":
                    "unsigned_directional_record",
                "participants": participants,
                "participant_list_status": "partial",
                "coefficient_status": "unknown",
                "step_scope": "net_reaction",
                "condition_requirements": [],
                "scenario_scope": S5B_SCENARIO_SCOPE,
                "provenance_refs": [prov_id],
                "source_group_refs": [group_id],
                "evidence_basis": "database_recorded_reaction",
                "edge_status": "reference_only",
            },
        ],
        "endpoint_annotations": [],
        "source_groups": [
            {
                "source_group_id": group_id,
                "independence_status":
                    "related" if repeated_substrate else "unknown",
                "member_records": [qid],
                "note": (
                    "S1 一题一组(预注册 §7);" +
                    ("跨题重复底物(related)" if repeated_substrate
                     else "单出现底物(unknown:研究级独立性未审计)") +
                    ";任何题不标 independent"),
            },
        ],
        "split_assignment": {
            "split": "held_out",
            "split_rule_version": S5B_SPLIT_RULE_VERSION,
            "route_group_keys": [qid],
        },
        "coverage_statement": {
            "covered_axes": ["single_step_net_reaction"],
            "known_gaps": list(S5B_KNOWN_GAPS),
            "not_evaluable_node_ids": [],
            "not_evaluable_edge_ids": [],
        },
        "provenance_manifest": [
            {
                "provenance_id": prov_id,
                "source_group_id": group_id,
                "source_origin": "database",
                "evidence_basis": "database_recorded_reaction",
                "citation_ref": qid,
                "structure_match_scope": "strict_structure",
                "observation_scope": (
                    "recorded_only+V6_chemistry_audit_and_microbe_confirmed"
                    "_literature_screening(count_level_fact)"),
                "source_conditions": [],
                "independent_status":
                    "related" if repeated_substrate else "unknown",
            },
        ],
        "creation_review": {
            "review_status": "pending_user_teacher_review",
            "reviewer": "s5b-builder",
            "note": (
                "S5b 构建器按预注册转换规则生成(真实题卷;评审后置——"
                "mimo 三触发点按 AGENTS.md 执行);" +
                S5B_PARTICIPANT_DISCLOSURE),
        },
    }
    validate_reference_graph(graph)
    return graph


def s5b_graph_id(qid: str) -> str:
    """rg298-<qid 派生稳定 ID>(预注册 §2)。"""
    return f"rg298-{stable_id('s5bg', str(qid))[:16]}"


def s5b_run_id(qid: str, batch_tag: str) -> str:
    """每题一个独立 run 的稳定 run_id。"""
    return f"{batch_tag}-{stable_id('s5br', str(qid))[:16]}"


# ---------------------------------------------------------------- run 输入


def build_run_input(question: dict, *, batch_tag: str,
                    pools: dict[str, list[dict]],
                    provider_kind: str = "real") -> dict:
    """每 qid 一条 PPV1 run 输入(根底物=substrate;无人工条件注入)。

    plan.pools = pool_provider 对该底物的检索结果(底物侧,零金标);
    plan.model.provider_kind=real(real 登记占 max_real_model_requests
    额度;额度由 profile_policy.search_limits 显式放开)。
    """
    qid = str(question["qid"])
    substrate = str(question["substrate_smiles"])
    return {
        "qid": qid,
        "run_id": s5b_run_id(qid, batch_tag),
        "substrate_smiles": substrate,
        "plan": {
            "pools": {substrate: [dict(s) for s in pools.get(substrate)
                                  or []]},
            "model": {"provider_kind": provider_kind},
        },
        "note": (
            "S5b run 输入:根底物=题面 substrate_smiles;无人工条件注入"
            "(condition_facts 空);池 = 底物侧确定性检索(零金标消费)"),
    }


# ---------------------------------------------------------------- 池供给


def default_pool_provider(config: V43Config | None, *,
                           max_pool: int = 8, threshold: float = 0.45):
    """真实跑的缺省池供给:类比模板底物侧相似检索(零金标)。

    - 通道 = ``AnalogSourceResolver.templates_similar_to``(供体反应物
      与当前底物的 Tanimoto 相似度;排序 (-sim, line_no, record_id)
      确定性;只召回带映射模板);
    - 每个模板 → PPV1 spec(产物/编辑/供体/对齐/预期按模板映射派生,
      确定性;派生失败如实跳过该模板并计数披露);
    - config 为 None(测试/无资产)⇒ 返回空池供给(空池 + 模型 novel
      提案仍合法:S3B-05);
    - **本 provider 零金标消费**:只看 substrate_smiles。
    """
    def provider(substrate_smiles: str) -> list[dict]:
        if config is None:
            return []
        from ..services.analog_source import AnalogSourceResolver

        resolver = AnalogSourceResolver(config)
        refs = resolver.templates_similar_to(
            str(substrate_smiles), threshold=threshold, top_k=max_pool)
        specs: list[dict] = []
        skipped = 0
        for ref in refs:
            spec = _template_to_spec(ref, str(substrate_smiles))
            if spec is None:
                skipped += 1
                continue
            specs.append(spec)
        specs.sort(key=lambda s: str(s["key"]))
        return specs[:max_pool]

    return provider


def _template_to_spec(ref, substrate_smiles: str) -> dict | None:
    """映射模板 → PPV1 池 spec(确定性;失败返回 None 如实跳过)。

    - 产物 = 模板 rhs(去映射);
    - 编辑 = 模板 lhs→rhs 的键差(生成/断裂/变阶/新原子)经对齐映射
      到当前底物原子 ID(MoleCode 空间);
    - 供体中心 = 模板 center_atoms(供体侧原子空间 D_*_*;对齐映射
      供体→当前);
    - 预期产物 = 模板 rhs。
    """
    from rdkit import Chem

    from ..services.atom_tool import align_donor_mapping, render

    try:
        lhs_mol = Chem.MolFromSmiles(ref.mapped_lhs or "")
        rhs_mol = Chem.MolFromSmiles(ref.mapped_rhs or "")
        sub_mol = Chem.MolFromSmiles(substrate_smiles)
        if lhs_mol is None or rhs_mol is None or sub_mol is None:
            return None
        current = render(substrate_smiles, "S")
        match, _strategy = align_donor_mapping(lhs_mol, sub_mol)
        if not match:
            return None
        # lhs idx → 当前 idx → MoleCode 原子 ID
        idx_to_current_id = dict(current.idx_atom_map)
        lhs_to_current_id: dict[int, str] = {}
        for query_idx, cur_idx in match.items():
            atom_id = idx_to_current_id.get(int(cur_idx))
            if atom_id is None:
                return None
            lhs_to_current_id[int(query_idx)] = str(atom_id)
        # 中心原子:map number → lhs idx(供体空间 ID)
        center_map_nums = set(int(x) for x in (ref.center_atoms or []))
        center_ids: list[str] = []
        for atom in lhs_mol.GetAtoms():
            map_num = atom.GetAtomMapNum()
            if center_map_nums and map_num not in center_map_nums:
                continue
            cur_id = lhs_to_current_id.get(atom.GetIdx())
            if cur_id is None:
                return None  # 中心原子须全部有映射,否则如实跳过
            center_ids.append(cur_id)
        if not center_ids:
            return None
        edits = _bond_diff_edits(lhs_mol, rhs_mol, lhs_to_current_id)
        if edits is None:
            return None
        record_id = str(ref.record_id or "tpl")
        donor_to_current = {
            f"D_{i}": lhs_to_current_id[i]
            for i in sorted(lhs_to_current_id)}
        return {
            "key": f"tpl-{record_id}",
            "product_smiles": str(ref.product_smiles or ""),
            "coefficient": 1,
            "transformation_ref": record_id,
            "origin_group_key": f"analog-template:{record_id}",
            "edits": edits,
            "donor": {"center_atom_ids": sorted(center_ids)},
            "alignment": {
                "status": "resolved",
                "donor_to_current": donor_to_current,
                "equivalence_classes": [],
                "ref": f"corpus-template:{record_id}",
            },
            "expectation": {"target_smiles":
                            str(ref.product_smiles or "")},
        }
    except Exception:  # noqa: BLE001 —— 派生失败如实跳过该模板
        return None


def _bond_diff_edits(lhs_mol, rhs_mol,
                     lhs_to_current_id: dict[int, str]) -> list | None:
    """模板 lhs→rhs 键差 → 当前底物原子 ID 的编辑协议列表。

    键以 (lhs_idx, lhs_idx) 标识(模板同原子映射保持 idx 对应);新增
    原子(add_atom)锚定到其在 rhs 侧的成键 lhs 原子。全部映射到当前
    ID 后无法表达(涉及无映射原子)⇒ None(跳过该模板,不猜)。
    """
    from rdkit import Chem

    def bonds(mol):
        out = {}
        for bond in mol.GetBonds():
            key = frozenset((bond.GetBeginAtomIdx(),
                            bond.GetEndAtomIdx()))
            out[key] = bond.GetBondType()
        return out

    def order_token(bond_type):
        return {
            Chem.BondType.SINGLE: "single",
            Chem.BondType.DOUBLE: "double",
            Chem.BondType.TRIPLE: "triple",
            Chem.BondType.AROMATIC: "aromatic",
        }.get(bond_type)

    lhs_bonds = bonds(lhs_mol)
    rhs_bonds = bonds(rhs_mol)
    edits: list[dict] = []
    # 新增原子:rhs 有、lhs 无的 idx(模板 rhs 保持 lhs 原子 idx 不变)
    new_atoms = sorted(
        {a.GetIdx()
         for key in rhs_bonds for a_idx in key
         for a in [rhs_mol.GetAtomWithIdx(a_idx)]
         if a_idx >= lhs_mol.GetNumAtoms() or
         not _atom_exists(lhs_mol, a_idx)})
    next_new = 1
    new_id_of: dict[int, str] = {}
    for idx in new_atoms:
        atom = rhs_mol.GetAtomWithIdx(idx)
        element = atom.GetSymbol()
        new_id = f"S_{element}_N{next_new}"
        next_new += 1
        new_id_of[idx] = new_id
        # 锚点 = 与该新原子成键且存在于 lhs 的原子
        anchor = None
        for key in rhs_bonds:
            if idx in key:
                other = next(iter(key - {idx}))
                if other in lhs_to_current_id:
                    anchor = lhs_to_current_id[other]
                    break
        if anchor is None:
            return None
        edits.append({"op": "add_atom", "element": element,
                      "new_atom_id": new_id, "atom1": anchor})
    for key in sorted(rhs_bonds, key=sorted):
        ids = sorted(key)
        a1 = _edit_target(ids[0], lhs_to_current_id, new_id_of)
        a2 = _edit_target(ids[1], lhs_to_current_id, new_id_of)
        if a1 is None or a2 is None:
            return None
        rhs_order = order_token(rhs_bonds[key])
        lhs_order = order_token(lhs_bonds.get(key)) \
            if key in lhs_bonds else None
        if lhs_order is None:
            edits.append({"op": "form_bond", "atom1": a1, "atom2": a2})
        elif lhs_order != rhs_order:
            edits.append({
                "op": "change_bond_order", "atom1": a1, "atom2": a2,
                "from_order": lhs_order, "to_order": rhs_order})
    for key in sorted(lhs_bonds, key=sorted):
        if key in rhs_bonds:
            continue
        ids = sorted(key)
        a1 = lhs_to_current_id.get(ids[0])
        a2 = lhs_to_current_id.get(ids[1])
        if a1 is None or a2 is None:
            return None
        edits.append({"op": "break_bond", "atom1": a1, "atom2": a2})
    return edits


def _atom_exists(mol, idx: int) -> bool:
    return 0 <= idx < mol.GetNumAtoms()


def _edit_target(idx: int, lhs_to_current_id: dict[int, str],
                 new_id_of: dict[int, str]) -> str | None:
    if idx in new_id_of:
        return new_id_of[idx]
    return lhs_to_current_id.get(idx)


# ---------------------------------------------------------------- 主入口


def build_question_batch(
    questions_path: str | Path,
    output_root: str | Path,
    *,
    batch_tag: str = "s5b-298",
    pool_provider=None,
    provider_kind: str = "real",
    repo_root: str | Path | None = None,
    question_limit: int | None = None,
    synthetic_review: bool = False,
) -> dict:
    """构建题卷批:参考图 + run 输入 + split 清单 + 批次清单。

    输出(output_root 之下;金标承载物,必须 gitignored 根):
    - ``reference_graphs/<graph_id>.json``(298 图,含金标产物);
    - ``run_inputs/<qid>.json``(每 qid 一条 run 输入);
    - ``split_manifest.json``;
    - ``batch_manifest.json``(冻结注册序、qid→run_id/graph 映射、
      题卷 SHA256;**不含金标取值**,可作判分输入的配对单一来源)。

    synthetic_review=True(测试夹具)⇒ 参考图 creation_review 改标
    synthetic_rule_level(如实)。
    """
    root = check_output_root(output_root, repo_root=repo_root)
    questions = load_questions(questions_path)
    if question_limit is not None:
        questions = questions[:int(question_limit)]
    substrate_counts: dict[str, int] = {}
    for record in questions:
        substrate_counts[str(record["substrate_smiles"])] = \
            substrate_counts.get(
                str(record["substrate_smiles"]), 0) + 1
    graphs_dir = root / "reference_graphs"
    inputs_dir = root / "run_inputs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)
    provider = pool_provider if pool_provider is not None \
        else default_pool_provider(None)
    entries: list[dict] = []
    for record in questions:
        qid = str(record["qid"])
        substrate = str(record["substrate_smiles"])
        graph = build_reference_graph(
            record, repeated_substrate=substrate_counts[substrate] > 1)
        if synthetic_review:
            graph["creation_review"] = {
                "review_status": "synthetic_rule_level",
                "reviewer": "s5b-builder",
                "note": "S5b 构建器合成夹具(无真实金标)",
            }
        graph_path = graphs_dir / f"{graph['reference_graph_id']}.json"
        graph_path.write_text(
            json.dumps(graph, ensure_ascii=False, sort_keys=True,
                       indent=1) + "\n", encoding="utf-8")
        pools = {substrate: provider(substrate)}
        run_input = build_run_input(
            record, batch_tag=batch_tag, pools=pools,
            provider_kind=provider_kind)
        input_path = inputs_dir / f"{qid}.json"
        input_path.write_text(
            json.dumps(run_input, ensure_ascii=False, sort_keys=True,
                       indent=1) + "\n", encoding="utf-8")
        entries.append({
            "qid": qid,
            "run_id": run_input["run_id"],
            "reference_graph_id": graph["reference_graph_id"],
            "graph_rel": f"reference_graphs/"
                         f"{graph['reference_graph_id']}.json",
            "graph_sha256": reference_graph_sha256(graph),
            "run_input_rel": f"run_inputs/{qid}.json",
            "substrate_smiles": substrate,
            "pool_size": len(pools[substrate]),
            "n_gold_products": len(record["products_smiles"]),
            "repeated_substrate": substrate_counts[substrate] > 1,
        })
    split_manifest = {
        "schema_version": PPV1_SPLIT_MANIFEST_VERSION,
        "split_manifest_id": f"sm-s5b-{batch_tag}",
        "split_rule_version": S5B_SPLIT_RULE_VERSION,
        "input_data_manifest_hash": _file_sha256(questions_path),
        "assignments": [
            {"reference_graph_id": e["reference_graph_id"],
             "source_group_id": f"sg-{e['qid']}",
             "split": "held_out"}
            for e in entries],
        "unseen_exclusion_manifest": {
            "track": "unseen_path_inference", "excluded": []},
    }
    (root / "split_manifest.json").write_text(
        json.dumps(split_manifest, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    questions_sha = _file_sha256(questions_path)
    manifest = {
        "s5b_builder_version": S5B_BUILDER_VERSION,
        "batch_tag": batch_tag,
        "questions_source": str(Path(questions_path)),
        "questions_source_sha256": questions_sha,
        "n_questions": len(entries),
        "provider_kind": provider_kind,
        "registration_order": [e["qid"] for e in entries],
        "entries": entries,
        "gold_policy": (
            "参考图/题面承载物只落本 gitignored 根;本清单零金标取值;"
            "判分时金标才进入判分进程(s5b_scoring;零 LLM)"),
    }
    (root / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                   indent=1) + "\n", encoding="utf-8")
    return manifest


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(
        Path(path).read_bytes()).hexdigest()
