"""PPV1 确定性完全矿化与宿主中心碳代谢终点判定器 (ppv1-mineralization-sink-v1)。

零 LLM、零外部状态、100% 基于 RDKit 分子拓扑与精确连通性身份判定。
严格兑现 2026-11-11 CC 拍板的三道硬门槛：
1. A0 无碳无机物 + A 档直接无机碳 (CO2 / H2CO3)；一碳有机物 (CH3OH/CH2O/HCOOH/HCN/urea 等)
   与乙醛 (CH3CHO) 显式排除，必须继续氧化至 CO2 或乙酸；
2. B 档宿主中心碳代谢核心白名单 (~23 个 TCA/糖酵解下段/短链酰基-CoA 核心分子)，
   外源毒害基团一票否决；
3. 儿茶酚、原儿茶酸、龙胆酸、苯甲酸等未开环漏斗中间体显式排除，必须开环裂解后汇入中心代谢池。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from rdkit import Chem, RDLogger
from rdkit.Chem import inchi, Lipinski
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.rdMolDescriptors import CalcMolFormula

RDLogger.DisableLog("rdApp.*")

MINERALIZATION_POLICY_VERSION = "ppv1-mineralization-sink-v1"

# 冻结标准中心碳代谢核心池名称 -> 标准中性 SMILES
CENTRAL_CARBON_SINK_CANONICAL_SPECS: dict[str, str] = {
    # TCA 循环与乙醛酸支路
    "citrate": "O=C(O)CC(O)(CC(=O)O)C(=O)O",
    "cis_aconitate": "O=C(O)CC(=CC(=O)O)C(=O)O",
    "isocitrate": "O=C(O)CC(C(O)C(=O)O)C(=O)O",
    "2_oxoglutarate": "O=C(O)CCC(=O)C(=O)O",
    "succinate": "O=C(O)CCC(=O)O",
    "fumarate": "O=C(O)/C=C/C(=O)O",
    "malate": "O=C(O)CC(O)C(=O)O",
    "oxaloacetate": "O=C(O)CC(=O)C(=O)O",
    "glyoxylate": "O=CC(=O)O",
    # 糖酵解下段与丙酮酸节点
    "glyceraldehyde_3_phosphate": "O=CC(O)COP(=O)(O)O",
    "dihydroxyacetone_phosphate": "O=C(CO)COP(=O)(O)O",
    "1_3_bisphosphoglycerate": "O=C(OP(=O)(O)O)C(O)COP(=O)(O)O",
    "3_phosphoglycerate": "O=C(O)C(O)COP(=O)(O)O",
    "2_phosphoglycerate": "O=C(O)C(CO)OP(=O)(O)O",
    "phosphoenolpyruvate": "C=C(OP(=O)(O)O)C(=O)O",
    "pyruvate": "CC(=O)C(=O)O",
    "lactate": "CC(O)C(=O)O",
    # 短链中心碳汇入点（注意：乙醛 CC=O 不入池，须继续氧化至乙酸或乙酰-CoA）
    "acetate": "CC(=O)O",
    "acetoacetate": "CC(=O)CC(=O)O",
    # 核心短链酰基-CoA 汇入点
    "acetyl_coa": "CC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O",
    "propionyl_coa": "CCC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O",
    "succinyl_coa": "O=C(O)CCC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O",
    "acetoacetyl_coa": "CC(=O)CC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O",
}

# 冻结内源货币辅因子排除表（仅在 role == "coproduct" 时生效）
# 注意：严禁包含游离腺嘌呤/鸟嘌呤/胞嘧啶/尿嘧啶碱基，防止误放行含氮杂环污染物裂解产物
CURRENCY_COFACTOR_CANONICAL_SPECS: dict[str, str] = {
    "NAD+": "NC(=O)c1ccc[n+](c1)C1OC(COP(=O)(O)OP(=O)(O)OCC2OC(n3cnc4c(N)ncnc34)C(O)C2O)C(O)C1O",
    "NADH": "NC(=O)C1=CN(C=CC1)C1OC(COP(=O)(O)OP(=O)(O)OCC2OC(n3cnc4c(N)ncnc34)C(O)C2O)C(O)C1O",
    "NADP+": "NC(=O)c1ccc[n+](c1)C1OC(COP(=O)(O)OP(=O)(O)OCC2OC(n3cnc4c(N)ncnc34)C(OP(=O)(O)O)C2O)C(O)C1O",
    "NADPH": "NC(=O)C1=CN(C=CC1)C1OC(COP(=O)(O)OP(=O)(O)OCC2OC(n3cnc4c(N)ncnc34)C(OP(=O)(O)O)C2O)C(O)C1O",
    "FAD": "Cc1cc2nc3c(=O)[nH]c(=O)nc-3n(CC(O)C(O)C(O)COP(=O)(O)OP(=O)(O)OCC3OC(n4cnc5c(N)ncnc54)C(O)C3O)c2cc1C",
    "FADH2": "Cc1cc2c(cc1C)N(C1=NC(=O)NC(=O)C1N2)CC(O)C(O)C(O)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1O",
    "FADH2_alt": "CC1=CC2=C(C=C1C)N(C3=C(N2)C(=O)NC(=O)N3)CC(O)C(O)C(O)COP(=O)(O)OP(=O)(O)OCC4OC(n5cnc6c(N)ncnc65)C(O)C4O",
    "FMN": "Cc1cc2nc3c(=O)[nH]c(=O)nc-3n(CC(O)C(O)C(O)COP(=O)(O)O)c2cc1C",
    "FMNH2": "Cc1cc2c(cc1C)N(C1=NC(=O)NC(=O)C1N2)CC(O)C(O)C(O)COP(=O)(O)O",
    "FMNH2_alt": "CC1=CC2=C(C=C1C)N(C3=C(N2)C(=O)NC(=O)N3)CC(O)C(O)C(O)COP(=O)(O)O",
    "ATP": "Nc1ncnc2c1ncn2C1OC(COP(=O)(O)OP(=O)(O)OP(=O)(O)O)C(O)C1O",
    "ADP": "Nc1ncnc2c1ncn2C1OC(COP(=O)(O)OP(=O)(O)O)C(O)C1O",
    "AMP": "Nc1ncnc2c1ncn2C1OC(COP(=O)(O)O)C(O)C1O",
    "adenosine": "Nc1ncnc2c1ncn2C1OC(CO)C(O)C1O",
    "GTP": "Nc1nc2c(ncn2C2OC(COP(=O)(O)OP(=O)(O)OP(=O)(O)O)C(O)C2O)c(=O)[nH]1",
    "GDP": "Nc1nc2c(ncn2C2OC(COP(=O)(O)OP(=O)(O)O)C(O)C2O)c(=O)[nH]1",
    "GMP": "Nc1nc2c(ncn2C2OC(COP(=O)(O)O)C(O)C2O)c(=O)[nH]1",
    "UTP": "O=c1cc[nH]c(=O)n1C1OC(COP(=O)(O)OP(=O)(O)OP(=O)(O)O)C(O)C1O",
    "UDP": "O=c1cc[nH]c(=O)n1C1OC(COP(=O)(O)OP(=O)(O)O)C(O)C1O",
    "UMP": "O=c1cc[nH]c(=O)n1C1OC(COP(=O)(O)O)C(O)C1O",
    "CTP": "Nc1ccn(C2OC(COP(=O)(O)OP(=O)(O)OP(=O)(O)O)C(O)C2O)c(=O)n1",
    "CDP": "Nc1ccn(C2OC(COP(=O)(O)OP(=O)(O)O)C(O)C2O)c(=O)n1",
    "CMP": "Nc1ccn(C2OC(COP(=O)(O)O)C(O)C2O)c(=O)n1",
    "free_CoA_SH": "CC(C)(COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O)C(O)C(=O)NCCC(=O)NCCS",
    "SAM": "C[S+](CC[C@H](N)C(=O)O)C[C@@H]1O[C@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1O",
    "SAH": "Nc1ncnc2c1ncn2C1OC(CSCCC(N)C(=O)O)C(O)C1O",
    "PAPS": "Nc1ncnc2c1ncn2C1OC(COP(=O)(O)OS(=O)(=O)O)C(O)C1OP(=O)(O)O",
    "PAP": "Nc1ncnc2c1ncn2C1OC(COP(=O)(O)O)C(O)C1OP(=O)(O)O",
    "THF": "Nc1nc2c(c(=O)[nH]1)NCC(CNc1ccc(C(=O)NC(CCC(=O)O)C(=O)O)cc1)N2",
    "glutathione_GSH": "N[C@@H](CCC(=O)N[C@@H](CS)C(=O)NCC(=O)O)C(=O)O",
    "glutathione_GSSG": "O=C(O)C(N)CCC(=O)NC(CSSCC(NC(=O)CCC(N)C(=O)O)C(=O)NCC(=O)O)C(=O)NCC(=O)O",
}

# 外源毒害元素原子序数集合 (F, Cl, Br, I, As, Hg, Pb, Sn, B)
XENOBIOTIC_ATOMIC_NUMBERS: frozenset[int] = frozenset({
    5, 9, 17, 33, 35, 50, 53, 80, 82
})

# 外源毒害基团 SMARTS（硝基、亚硝基、偶氮、叠氮、磺酸、膦酸 C-P、硫代磷酸酯 P=S）
XENOBIOTIC_SMARTS: dict[str, Any] = {
    "nitro": Chem.MolFromSmarts("[$([NX3](=O)=O),$([NX3+](=O)[O-])]"),
    "nitroso": Chem.MolFromSmarts("[NX2]=O"),
    "azo": Chem.MolFromSmarts("[#7]=[#7]"),
    "azido": Chem.MolFromSmarts("[$([NX1]#[NX2+]#[NX1-]),$([NX1-][NX2+]#[NX1])]"),
    "sulfonic": Chem.MolFromSmarts("S(=O)(=O)[O,OH]"),
    "phosphonate": Chem.MolFromSmarts("[#6]-[PX4]"),
    "phosphorothioate": Chem.MolFromSmarts("[PX4]=S"),
}

_UNCHANGER = rdMolStandardize.Uncharger()

# 预计算白名单签名映射表
def _precompute_signature_map(specs: dict[str, str]) -> dict[str, tuple[str, str]]:
    sig_map: dict[str, tuple[str, str]] = {}
    for name, smi in specs.items():
        m = Chem.MolFromSmiles(smi)
        if m is None:
            continue
        u = _UNCHANGER.uncharge(m)
        ik14 = inchi.MolToInchiKey(u).split("-")[0]
        formula = CalcMolFormula(u)
        sig_map[ik14] = (name, formula)
    return sig_map

CENTRAL_CARBON_SINK_SIGS: dict[str, tuple[str, str]] = _precompute_signature_map(CENTRAL_CARBON_SINK_CANONICAL_SPECS)
CURRENCY_COFACTOR_SIGS: dict[str, tuple[str, str]] = _precompute_signature_map(CURRENCY_COFACTOR_CANONICAL_SPECS)

# CO2 与碳酸 InChIKey-14
INCHIKEY14_CO2 = "CURLTUGMZLYLDI"
INCHIKEY14_H2CO3 = "BVKZGUZCCUSVTD"
INORGANIC_CARBON_IK14S = frozenset({INCHIKEY14_CO2, INCHIKEY14_H2CO3})

# 富马酸/马来酸与顺/反乌头酸区分签名
FUMARATE_IK14 = "VZCYOOQTPOCHFL"
MALEATE_STEREO_HASH = "UPHRSURJSA"  # cis-maleate stereo key block

ACONITATE_IK14 = "GTZCVFVGUGFEME"
TRANS_ACONITATE_STEREO_HASH = "IWQZZHSRSA"  # trans-aconitate stereo key block


@dataclass(frozen=True)
class MineralizationSinkResult:
    is_terminal_sink: bool
    sink_tier: str  # "A0_noncarbon_inorganic", "A_inorganic_carbon", "B_central_carbon_sink", "ENDOGENOUS_CURRENCY_COFACTOR", "NONE"
    track_branch: bool
    reason: str
    carbon_count: int
    canonical_smiles: str
    inchi_key_14: str
    policy_version: str = MINERALIZATION_POLICY_VERSION


def classify_mineralization_sink(
    smiles: str,
    *,
    role: str = "principal_product",
) -> MineralizationSinkResult:
    """确定性完全矿化与中心碳代谢终点判定。

    参数:
        smiles: 待分类分子结构式
        role: 产物角色 ("principal_product" 或 "coproduct")

    返回:
        MineralizationSinkResult
    """
    if not isinstance(smiles, str) or not smiles.strip():
        return MineralizationSinkResult(
            is_terminal_sink=False,
            sink_tier="NONE",
            track_branch=False,
            reason="empty_smiles",
            carbon_count=0,
            canonical_smiles="",
            inchi_key_14="",
        )

    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        return MineralizationSinkResult(
            is_terminal_sink=False,
            sink_tier="NONE",
            track_branch=False,
            reason="unparseable_smiles",
            carbon_count=0,
            canonical_smiles=smiles.strip(),
            inchi_key_14="",
        )

    # 1. 计算碳原子数
    carbon_count = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 6)

    # Step 1: 无碳无机物 A0_noncarbon_inorganic
    if carbon_count == 0:
        can_smi = Chem.MolToSmiles(mol, isomericSmiles=True)
        try:
            ik = inchi.MolToInchiKey(mol).split("-")[0]
        except Exception:
            ik = ""
        return MineralizationSinkResult(
            is_terminal_sink=True,
            sink_tier="A0_noncarbon_inorganic",
            track_branch=False,
            reason="noncarbon_inorganic",
            carbon_count=0,
            canonical_smiles=can_smi,
            inchi_key_14=ik,
        )

    # 去电荷标准化
    try:
        u_mol = _UNCHANGER.uncharge(mol)
    except Exception:
        u_mol = Chem.Mol(mol)

    can_smi = Chem.MolToSmiles(u_mol, isomericSmiles=True)
    full_ik = ""
    ik14 = ""
    try:
        full_ik = inchi.MolToInchiKey(u_mol)
        ik14 = full_ik.split("-")[0]
    except Exception:
        pass

    formula = CalcMolFormula(u_mol)

    # Step 2: 内源货币辅因子排除（仅当 role == "coproduct" 且命中白名单时）
    if role == "coproduct" and ik14 in CURRENCY_COFACTOR_SIGS:
        cofactor_name, _ = CURRENCY_COFACTOR_SIGS[ik14]
        return MineralizationSinkResult(
            is_terminal_sink=True,
            sink_tier="ENDOGENOUS_CURRENCY_COFACTOR",
            track_branch=False,
            reason=f"currency_cofactor_{cofactor_name}",
            carbon_count=carbon_count,
            canonical_smiles=can_smi,
            inchi_key_14=ik14,
        )

    # Step 4 先行检查: 外源毒害基团一票否决（包含一碳外源分子如氟乙酸、甲磺酸、甲基膦酸）
    for a in mol.GetAtoms():
        if a.GetAtomicNum() in XENOBIOTIC_ATOMIC_NUMBERS:
            sym = a.GetSymbol()
            return MineralizationSinkResult(
                is_terminal_sink=False,
                sink_tier="NONE",
                track_branch=True,
                reason=f"xenobiotic_element_{sym}",
                carbon_count=carbon_count,
                canonical_smiles=can_smi,
                inchi_key_14=ik14,
            )

    for group_name, pat in XENOBIOTIC_SMARTS.items():
        if mol.HasSubstructMatch(pat) or u_mol.HasSubstructMatch(pat):
            return MineralizationSinkResult(
                is_terminal_sink=False,
                sink_tier="NONE",
                track_branch=True,
                reason=f"xenobiotic_group_{group_name}",
                carbon_count=carbon_count,
                canonical_smiles=can_smi,
                inchi_key_14=ik14,
            )

    # Step 3: 直接无机碳 A_inorganic_carbon
    # 严格仅限 CO2 (O=C=O) 与碳酸/碳酸氢根/碳酸根 (O=C(O)O)
    if ik14 in INORGANIC_CARBON_IK14S or can_smi in ("O=C=O", "O=C(O)O"):
        return MineralizationSinkResult(
            is_terminal_sink=True,
            sink_tier="A_inorganic_carbon",
            track_branch=False,
            reason="inorganic_carbon",
            carbon_count=1,
            canonical_smiles=can_smi,
            inchi_key_14=ik14,
        )

    # 显式拦截所有其他 C1 物种（甲醇、甲醛、甲酸/甲酸根、CO、HCN、尿素、甲胺、甲烷、CS2、甲酰胺等）
    if carbon_count == 1:
        return MineralizationSinkResult(
            is_terminal_sink=False,
            sink_tier="NONE",
            track_branch=True,
            reason="c1_organic_must_oxidize_to_co2",
            carbon_count=1,
            canonical_smiles=can_smi,
            inchi_key_14=ik14,
        )

    # Step 5: 宿主中心碳代谢核心白名单 B_central_carbon_sink
    if ik14 in CENTRAL_CARBON_SINK_SIGS:
        sink_name, exp_formula = CENTRAL_CARBON_SINK_SIGS[ik14]
        # 校验分子式精确一致
        if formula == exp_formula:
            # 富马酸 vs 显式顺式马来酸细化区分
            if ik14 == FUMARATE_IK14:
                # 若全 InChIKey 明确标记为顺式马来酸，令其再异构化 1 步
                if MALEATE_STEREO_HASH in full_ik:
                    return MineralizationSinkResult(
                        is_terminal_sink=False,
                        sink_tier="NONE",
                        track_branch=True,
                        reason="cis_maleate_must_isomerize_to_fumarate",
                        carbon_count=carbon_count,
                        canonical_smiles=can_smi,
                        inchi_key_14=ik14,
                    )
            # 顺乌头酸 vs 显式反乌头酸细化区分
            if ik14 == ACONITATE_IK14:
                if TRANS_ACONITATE_STEREO_HASH in full_ik:
                    return MineralizationSinkResult(
                        is_terminal_sink=False,
                        sink_tier="NONE",
                        track_branch=True,
                        reason="trans_aconitate_must_isomerize_to_cis",
                        carbon_count=carbon_count,
                        canonical_smiles=can_smi,
                        inchi_key_14=ik14,
                    )
            return MineralizationSinkResult(
                is_terminal_sink=True,
                sink_tier="B_central_carbon_sink",
                track_branch=False,
                reason=f"central_sink_{sink_name}",
                carbon_count=carbon_count,
                canonical_smiles=can_smi,
                inchi_key_14=ik14,
            )

    # 未命中白名单的所有其他分子（儿茶酚、原儿茶酸、龙胆酸、苯甲酸、粘康酸、3-氧代己二酸、乙醛等）
    return MineralizationSinkResult(
        is_terminal_sink=False,
        sink_tier="NONE",
        track_branch=True,
        reason="unmineralized_intermediate",
        carbon_count=carbon_count,
        canonical_smiles=can_smi,
        inchi_key_14=ik14,
    )


# -----------------------------------------------------------------------------
# 禁祖先倒车 (Non-Backtracking) 反应事件选择器
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class EventBacktrackCheckResult:
    has_backtrack: bool
    collisions: list[dict[str, Any]]


@dataclass(frozen=True)
class EventSelectionResult:
    status: str  # "SELECTED", "ALL_CANDIDATES_BACKTRACK", "NO_CANDIDATES"
    selected_event: dict[str, Any] | None
    selected_rank: int | None
    skipped_events: list[dict[str, Any]]
    reason: str


def check_event_backtracking(
    event: dict[str, Any],
    history_strict_ids: tuple[str, ...] | list[str],
) -> EventBacktrackCheckResult:
    """检查候选事件产物是否与当前分支的祖先分子集合发生环路碰撞。

    碰撞定义：
    候选事件产生的非终点含碳碎片中，存在任何碎片的严格身份 (strict_identity_of)
    存在于 history_strict_ids (包含根到底物 X 的全部历史节点)。
    若存在碰撞，计算倒车步距 lag = len(history) - ancestor_index。
    """
    from pathway_v43.pollutant.chemstate import strict_identity_of

    history_list = list(history_strict_ids)
    history_set = set(history_list)
    collisions: list[dict[str, Any]] = []

    all_prods = event.get("principal_products", []) + event.get("coproducts", [])
    for pt in all_prods:
        if isinstance(pt, dict):
            psmi = pt.get("smiles", "")
            prole = pt.get("role", "principal_product")
        else:
            psmi = str(pt)
            prole = "principal_product"

        if not psmi:
            continue

        sink = classify_mineralization_sink(psmi, role=prole)
        # 忽略无碳无机物与内源货币辅因子
        if sink.sink_tier in (
            "ENDOGENOUS_CURRENCY_COFACTOR",
            "A0_noncarbon_inorganic",
        ):
            continue
        # 终点产物 (CO2, TCA/糖酵解中心碳代谢池) 正常闭合，不视为倒车碰撞
        if sink.is_terminal_sink:
            continue

        # 提取非终点含碳碎片的严格身份
        try:
            psid = strict_identity_of(psmi)
        except Exception:
            psid = psmi.strip()

        if psid in history_set:
            ancestor_idx = history_list.index(psid)
            lag = len(history_list) - ancestor_idx
            collisions.append({
                "smiles": psmi,
                "strict_id": psid,
                "lag": lag,
                "ancestor_index": ancestor_idx,
            })

    return EventBacktrackCheckResult(
        has_backtrack=len(collisions) > 0,
        collisions=collisions,
    )


def _get_carbon_count(smi: str | None) -> int:
    if not smi or not isinstance(smi, str):
        return 0
    m = Chem.MolFromSmiles(smi)
    return sum(1 for a in m.GetAtoms() if a.GetSymbol() == "C") if m else 0


def _get_ring_info(m: Chem.Mol | None) -> tuple[int, int]:
    if not m:
        return 0, 0
    ri = m.GetRingInfo()
    return ri.NumRings(), Lipinski.NumAromaticRings(m)


def _get_xenobiotic_count(m: Chem.Mol | None) -> int:
    if not m:
        return 0
    xc = sum(1 for a in m.GetAtoms() if a.GetAtomicNum() in XENOBIOTIC_ATOMIC_NUMBERS)
    for pat in XENOBIOTIC_SMARTS.values():
        xc += len(m.GetSubstructMatches(pat))
    return xc


def _get_c1_oxidation_level(m: Chem.Mol | None) -> int:
    if not m:
        return -10
    c_atoms = [a for a in m.GetAtoms() if a.GetSymbol() == "C"]
    if len(c_atoms) != 1:
        return -10
    c = c_atoms[0]
    ox = 0
    for bond in c.GetBonds():
        other = bond.GetOtherAtom(c)
        if other.GetSymbol() != "H":
            ox += int(bond.GetBondTypeAsDouble())
    return ox


def _is_full_sink_closing_event(ev: dict[str, Any]) -> bool:
    all_prods = ev.get("principal_products", []) + ev.get("coproducts", [])
    carbon_prods: list[MineralizationSinkResult] = []
    for p in all_prods:
        smi = p.get("smiles", "")
        role = p.get("role", "principal_product")
        sink = classify_mineralization_sink(smi, role=role)
        if sink.sink_tier in ("ENDOGENOUS_CURRENCY_COFACTOR", "A0_noncarbon_inorganic"):
            continue
        carbon_prods.append(sink)
    if not carbon_prods:
        return False
    return all(s.is_terminal_sink for s in carbon_prods)


def _eval_substantive_catabolic_progress(
    ev: dict[str, Any],
    c_curr: int,
    tr_curr: int,
    ar_curr: int,
    xc_curr: int,
) -> bool:
    ev_prods = [
        p["smiles"]
        for p in ev.get("principal_products", []) + ev.get("coproducts", [])
        if p.get("smiles")
    ]
    ev_c_prods = [_get_carbon_count(s) for s in ev_prods if _get_carbon_count(s) > 0]
    max_c_ev = max(ev_c_prods) if ev_c_prods else 0
    ev_m_main = Chem.MolFromSmiles(ev_prods[0]) if ev_prods else None
    tr_ev, ar_ev = _get_ring_info(ev_m_main)
    xc_ev = _get_xenobiotic_count(ev_m_main)

    # 1. 切减碳链：主含碳产物碳数递减，或裂解为多个更短碳碎片
    c_cut = (max_c_ev < c_curr) or (
        len(ev_c_prods) >= 2 and all(c < c_curr for c in ev_c_prods)
    )
    # 2. 劈开环系：总环数或芳环数减少
    ring_cut = (ar_ev < ar_curr) or (tr_ev < tr_curr)
    # 3. 拔除外源毒害基团：毒害基团减少
    xeno_cut = xc_ev < xc_curr

    return c_cut or ring_cut or xeno_cut


def select_event_non_backtracking(
    candidate_events: list[dict[str, Any]],
    history_strict_ids: tuple[str, ...] | list[str],
    *,
    policy: str = "non_backtracking_b1",
    current_smiles: str | None = None,
    carbon_history: list[int] | None = None,
    k_drift: int = 3,
) -> EventSelectionResult:
    """根据策略从候选事件列表中选择推进事件。

    支持策略:
    - "naive_b1": 盲取排序第 1 的 Event #1，不做任何祖先碰撞检测；
    - "non_backtracking_b1": 按排序依次检查，若候选事件产生倒车回祖先的非终点碎片，则跳过并记录，
      顺延选用第一个无祖先倒车的合规事件；若所有事件均倒车，返回 ALL_CANDIDATES_BACKTRACK。
    - "catabolic_progress_b1": 在 non_backtracking_b1 基础上，加入：
      1. 终点直达优先（若存在能让所有碎片 100% 进终点池的候选事件，优先选择）；
      2. C1 氧化递进优先（C1 底物优先选用氧化态递增或进终点的候选）；
      3. 抗等碳漂移顺延（连续 >= k_drift 步等碳漂移且 Event #1 无突破时，顺延选用切碳/破环/除毒候选）。
    """
    if not candidate_events:
        return EventSelectionResult(
            status="NO_CANDIDATES",
            selected_event=None,
            selected_rank=None,
            skipped_events=[],
            reason="no_candidates",
        )

    if policy == "naive_b1":
        top1 = candidate_events[0]
        rank = top1.get("rank", 1)
        return EventSelectionResult(
            status="SELECTED",
            selected_event=top1,
            selected_rank=rank,
            skipped_events=[],
            reason="naive_b1_first",
        )

    if policy == "non_backtracking_b1":
        skipped: list[dict[str, Any]] = []
        for idx, ev in enumerate(candidate_events):
            rank = ev.get("rank", idx + 1)
            chk = check_event_backtracking(ev, history_strict_ids)
            if chk.has_backtrack:
                skipped.append({
                    "rank": rank,
                    "event_id": ev.get("event_id"),
                    "collisions": chk.collisions,
                })
            else:
                return EventSelectionResult(
                    status="SELECTED",
                    selected_event=ev,
                    selected_rank=rank,
                    skipped_events=skipped,
                    reason="first_non_backtracking",
                )

        return EventSelectionResult(
            status="ALL_CANDIDATES_BACKTRACK",
            selected_event=None,
            selected_rank=None,
            skipped_events=skipped,
            reason="all_candidates_backtrack",
        )

    if policy == "catabolic_progress_b1":
        # 1. 过滤祖先倒车事件（Hard Gate）
        non_bt_events: list[tuple[int, dict[str, Any]]] = []
        skipped: list[dict[str, Any]] = []
        for idx, ev in enumerate(candidate_events):
            rank = ev.get("rank", idx + 1)
            chk = check_event_backtracking(ev, history_strict_ids)
            if chk.has_backtrack:
                skipped.append({
                    "rank": rank,
                    "event_id": ev.get("event_id"),
                    "collisions": chk.collisions,
                })
            else:
                non_bt_events.append((rank, ev))

        if not non_bt_events:
            return EventSelectionResult(
                status="ALL_CANDIDATES_BACKTRACK",
                selected_event=None,
                selected_rank=None,
                skipped_events=skipped,
                reason="all_candidates_backtrack",
            )

        rank1, ev1 = non_bt_events[0]

        # 2. 规则 A1：全碎片一步直达终点优先（Sink-Closing Priority）
        if not _is_full_sink_closing_event(ev1):
            for rank_k, ev_k in non_bt_events[1:]:
                if _is_full_sink_closing_event(ev_k):
                    return EventSelectionResult(
                        status="SELECTED",
                        selected_event=ev_k,
                        selected_rank=rank_k,
                        skipped_events=skipped,
                        reason="sink_closing_priority",
                    )

        # 3. 规则 A2：C1 有机物正向氧化优先（C1-Oxidation Priority）
        c_curr = _get_carbon_count(current_smiles)
        m_curr = Chem.MolFromSmiles(current_smiles) if current_smiles else None
        if c_curr == 1 and not _is_full_sink_closing_event(ev1):
            ox_curr = _get_c1_oxidation_level(m_curr)
            for rank_k, ev_k in non_bt_events[1:]:
                if _is_full_sink_closing_event(ev_k):
                    return EventSelectionResult(
                        status="SELECTED",
                        selected_event=ev_k,
                        selected_rank=rank_k,
                        skipped_events=skipped,
                        reason="c1_sink_closing_priority",
                    )
                prods_k = ev_k.get("principal_products", []) + ev_k.get("coproducts", [])
                for p in prods_k:
                    psmi = p.get("smiles", "")
                    if _get_carbon_count(psmi) == 1:
                        m_p = Chem.MolFromSmiles(psmi)
                        if _get_c1_oxidation_level(m_p) > ox_curr:
                            return EventSelectionResult(
                                status="SELECTED",
                                selected_event=ev_k,
                                selected_rank=rank_k,
                                skipped_events=skipped,
                                reason="c1_oxidation_priority",
                            )

        # 4. 规则 B：抗等碳漂移顺延（Anti-Iso-Carbon-Drift Fallback）
        consec_iso = 0
        if carbon_history and len(carbon_history) >= 2:
            for i in range(len(carbon_history) - 1, 0, -1):
                if carbon_history[i] == carbon_history[i - 1]:
                    consec_iso += 1
                else:
                    break

        ev1_prods = [
            p["smiles"]
            for p in ev1.get("principal_products", []) + ev1.get("coproducts", [])
            if p.get("smiles")
        ]
        ev1_c_prods = [_get_carbon_count(s) for s in ev1_prods if _get_carbon_count(s) > 0]
        max_c_ev1 = max(ev1_c_prods) if ev1_c_prods else 0
        tr_curr, ar_curr = _get_ring_info(m_curr)
        xc_curr = _get_xenobiotic_count(m_curr)
        ev1_has_sink = any(
            classify_mineralization_sink(s).is_terminal_sink for s in ev1_prods
        )

        ev1_m_main = Chem.MolFromSmiles(ev1_prods[0]) if ev1_prods else None
        tr_ev1, ar_ev1 = _get_ring_info(ev1_m_main)
        xc_ev1 = _get_xenobiotic_count(ev1_m_main)

        is_inconsequential = (
            max_c_ev1 == c_curr
            and not ev1_has_sink
            and tr_ev1 >= tr_curr
            and ar_ev1 >= ar_curr
            and xc_ev1 >= xc_curr
        )

        trigger_drift = (consec_iso >= k_drift and is_inconsequential) or (
            max_c_ev1 > c_curr
        )

        if trigger_drift:
            for rank_k, ev_k in non_bt_events[1:]:
                if _eval_substantive_catabolic_progress(
                    ev_k, c_curr, tr_curr, ar_curr, xc_curr
                ):
                    return EventSelectionResult(
                        status="SELECTED",
                        selected_event=ev_k,
                        selected_rank=rank_k,
                        skipped_events=skipped,
                        reason="catabolic_progress_fallback",
                    )

        return EventSelectionResult(
            status="SELECTED",
            selected_event=ev1,
            selected_rank=rank1,
            skipped_events=skipped,
            reason="catabolic_progress_first_non_backtracking"
            if skipped
            else "catabolic_progress_top1",
        )

    raise ValueError(f"Unknown event selection policy: {policy}")

