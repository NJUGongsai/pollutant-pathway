"""T8 G2 novel/analogy 守恒过滤 + 自产候选自排序 — 确定性纯函数层(v2)。

判据终版(v2):``reports/phase_s15_hit60/g2_arm/PREREGISTRATION_G2.md`` §2 +
§9 修订记录(mimo 终版评审 ``docs/mimo_g2_rules_final_review_response.md``
G 节 9 条必改逐条落地)。规则级实现,零 LLM、零金标、零题面;工作流挂接
(workflow.nodes._apply_novel/_apply_analogy)与离线重放(g2_arm 离线驱动)
共用本模块 —— 同一判定,两种驱动。

v2 相对 v1 的判据修订(对应评审 G 节 9 必改;详见 §各节注释):
1. **G1-b 裂解判据重构为"碎片可重构"**(评审 D-2):三 motif 快路径 +
   封闭小碎片清单(带官能团存在性)+ 有界杂原子单键切搜索;同一判据统一
   G1-b 允许集、ΔC=−1/−2 放行(R1 加条件)与②的第三条件三处——
   糖苷/酯/酰胺/醚/磷酯/肽断裂在碳侧同样被认(修复同一规则三处互斥)。
2. **②硬剔三条件**(A-3):声明完整 ∧ 总碳减少 ∧ 缺碳无可重构碎片同时
   成立才硬剔,否则降位;关键词表词边界+否定前缀+矿化措辞族
   (v43-cons-kw-2);冻结文本显式对齐判分口径 CO₂/H₂O 组分接口。
3. **key 2 改"化学矛盾"、unclassified 归中性**(E-2/D-3):仅"底物具备
   该可进攻基团而候选变换类与其化学矛盾"受排序惩罚;unclassified 一律
   中性落 key 3;补变换类:环氧化/S-氧化/N-氧化(+O 非羟化类,经底物
   基团+产物子结构差鉴别)。
4. **增侧惰性声明(选 (a),协调方建议、待用户确认)**(A-1):G1-a①增侧
   拒/G2-a 增侧/供体表放行在当前门禁次序的答案路径上不可达(v1 重放六批
   剔除侧零触发为程序证据);供体表(v43-donor-registry-2,按关键词分别
   定值/词边界/删裸词 coa/删 ThDP 行)降级为规格性文档;未来若放活增侧
   须另立臂走自己的判定线。
5. **R1 放行加碎片重构条件**(A-6)+ ②优先级显式化;保留四类应降位形态
   (碎片不可重构/跨元素不一致/ΔDoU 异常(|ΔDoU|≥2)/与完整性声明叠加)。
6. **编目对账+缺口补全**(D-4/D-5):34 条逐条枚举与计数一致(修复 v1
   "25 条"文本 vs 26/27 枚举不一致);补氨基甲酸酯/脲/磺酰胺/膦酸酯 C–P/
   季铵/过氧化物/1,2-二羰基/五元杂芳环;声明芳香性模型(RDKit 默认)与
   酯/缩醛 SMARTS 对内酯/糖苷端基的覆盖。
7. **DoU 带电荷项**(F-2:DoU=(2C+2+N−H−X+q)/2,q=去盐+Uncharger 后
   残余净电荷;非整数 → 不可审计)+ **去盐扩展到多原子反离子**(F-3/C-2:
   带电、独立组分、且存在严格更大碳数组分 → 剥离;覆盖 formate/acetate/
   sulfate/Tris/TEA/HCO₃⁻)。
8. **档位闭合**(C 节):共价金属新增 → G2-a 硬剔(写死);parse-fail
   分支与既有门同一解析器(工作流路径不可达,保留仅作重放防御,写明);
   hold 分账(hold_reason ∈ {substrate_undecidable, all_rejected} +
   reject_count);档位优先级显式(剔除 > 降位 > hold);金属配位不可判
   形态归不可审计降位+标注(不 hold)。
9. **判定线独立性**(E-3)属预注册文本层(离线重放读数标注 in-sample;
   确证 = 付费跑双采样符号检验;判定线加 spurious 净降 ≥3)。

工程红线(实现侧,评审背书不改的 8 处全部维持):
- **守恒只作违规降位,不作正向排序先验**(门 1 迭代 2 硬证据:s3x 守恒
  升序回撤 7/10/10;金标 11/22 题 cons>1)——cons 连续值不进任何排序键,
  档位只作降位分量;G3-a 不重复实现不放宽不收紧(= 既有 gate_smiles);
  G3-c 只提示不硬杀;同分异构恒放行(仅 key 1 同档内生效,不越过 key 2
  矛盾判据);剔空诚实弃权;解析失败不按零;去盐先于电荷归一;
  note 非供体登记源 + 卤素新增先验排除。
- **计数差不用集合差、比较前去盐、解析失败转"不可审计"不按零**
  (gold_health v2 断言 1/3 教训);
- 硬剔除仅"可证明违规"(增碳/增杂原子无登记供体;声明完整∧原子消失∧
  缺失不可重构);其余异常一律降位(误杀 7/22 硬数据,门 1 迭代 2 §3.3);
- 纯重排语义:无剔除时候选集合与排序前后集合不变(自排序分量只换顺序)。

模块全部函数为纯函数(无 IO、无网络、无模型调用),同输入同输出。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")

# ---------------------------------------------------------------- 版本常量(v2)

CONSERVATION_FILTER_VERSION = "v43-cons-2"
NORMALIZATION_VERSION = "v43-norm-2"
SELF_RANK_VERSION = "v43-selfrank-2"
G3B_CATALOG_VERSION = "v43-g3b-catalog-2"
DONOR_REGISTRY_VERSION = "v43-donor-registry-2"
COMPLETENESS_KEYWORDS_VERSION = "v43-cons-kw-2"
FRAGMENT_CATALOG_VERSION = "v43-cons-frag-1"

# 处置档(tier);档位优先级显式:剔除 > 降位 > hold(C 节 7)
TIER_PASS = "pass"
TIER_DOWNGRADE = "downgrade"
TIER_EXCLUDE = "exclude"
# 题级状态
STATUS_OK = "ok"
STATUS_HOLD = "hold"
# hold 分账(C 节 4):两个子类语义正确、诊断不混
HOLD_SUBSTRATE_UNDECIDABLE = "substrate_undecidable"   # 输入侧信号
HOLD_ALL_REJECTED = "all_rejected"                     # 模型侧信号(剔空)

# 杂原子硬门集合(G2-a/G2-b:N/S/P/卤素/金属;O 与 H 为自由元素,
# 默认隐式供体 {H2O, O2})
HARD_HETERO_ATOMS = frozenset({"N", "S", "P", "F", "Cl", "Br", "I"})
METAL_ATOMS = frozenset({
    "Li", "Na", "K", "Mg", "Ca", "Fe", "Zn", "Cu", "Mn", "Co", "Ni",
    "Cd", "Hg", "Pb", "Sn", "Al", "Ag", "Au", "Ba", "Sr", "Cr", "Mo",
    "W", "Se", "As", "Ti", "V", "B", "Si",
})
# 碎片重构的"硬元素"集(必须逐元素精确对账;O/H 为自由元素只设下界)。
# 碳是缺口对账的核心元素(G1-b 全部判据围绕 ΔC),与杂原子/金属同列。
GAP_HARD_ELEMENTS = frozenset({"C"} | HARD_HETERO_ATOMS | METAL_ATOMS)

# ---------------------------------------------------------------- ①关键词表

# 产物列表完整性声明(v43-cons-kw-2;评审 A-3 修缮):
# - 英文词边界正则(子串陷阱修复:"complete" 不再命中 "incomplete");
# - 否定前缀排除(前两个 token 内 not/no/never/n't/without/hardily/
#   scarcely/nor 之一 → 不算声明);
# - 封闭表补矿化措辞族(mineralized/mineralization/fully degraded/
#   completely converted/quantitatively/…);
# - 中文子串 + 否定前缀字(不/未/非/没/难)。
_EN_COMPLETE_PATTERNS: tuple[tuple[str, re.Pattern], ...] = tuple(
    (src, re.compile(src, re.IGNORECASE)) for src in (
        r"\bcomplete\b", r"\bcompletely\b", r"\bonly product\b",
        r"\bsole product\b", r"\bexhaustive(?:ly)?\b",
        r"\bmineraliz(?:ed|ation|es|ing)\b", r"\bfully degraded\b",
        r"\bquantitatively\b",
        r"\b(?:completely|fully|totally) "
        r"(?:converted|degraded|oxidized|mineralized|transformed)\b",
    ))
_EN_NEGATOR_TOKENS = frozenset({
    "not", "no", "never", "without", "hardly", "scarcely", "nor", "none",
})
_CN_COMPLETE_KEYWORDS = (
    "唯一产物", "产物完整", "全部产物", "彻底降解", "彻底矿化",
    "完全降解", "完全矿化", "完全转化", "矿化",
)
_CN_NEGATION_CHARS = frozenset("不未非没难")

# 供体登记表(v43-donor-registry-2;**规格性文档**——A-1 惰性声明下无
# 操作行为,数值供未来放活增侧的臂参考,不进本臂判定)。
# 评审 B 节修缮:按关键词分别定值(乙酰+2/丙二酰+3/丁酰·琥珀酰+4,删裸词
# coa);ThDP 行删除(+C 非可判定值,本题域几乎不出现;不授予 → 走增侧
# → A-1 惰性,现状无害);ASCII 关键词词边界;每元素授予 = 所有命中关键
# 词在该元素上的最大值(同元素不求和、跨元素天然并存)。
# 默认隐式供体恒为 {H2O, O2}。缺口清单(glucose/glycerol/succinate/
# pyruvate/acetate/methanol/谷胱甘肽/甘氨酸/半胱氨酸/牛磺酸/葡萄糖醛酸/
# formate/formaldehyde/methylene-THF/thiosulfate/sulfite/aspartate/
# asparagine/金属辅因子)登记于预注册 §2.2 规格性文档节,不入运行时表。
DONOR_REGISTRY: tuple[tuple[tuple[str, ...], dict[str, int]], ...] = (
    # 氨化类:N(转氨、还原氨化、酰胺转移)
    (("nh4+", "nh3", "ammonium", "谷氨酸", "glutamate",
      "丙氨酸", "alanine", "谷氨酰胺", "glutamine"), {"N": 1}),
    # 激酶磷酸化:P
    (("atp", "adenosine triphosphate"), {"P": 1}),
    # O-/N-甲基化:C1
    (("sam", "s-adenosylmethionine"), {"C": 1}),
    # 磺基转移:S
    (("paps", "phosphoadenosine phosphosulfate", "aps",
      "adenosine phosphosulfate"), {"S": 1}),
    # 糖基转移:C6(核苷糖供体)
    (("udp-glucose", "udp-glucuronate", "udpglucose", "udp-sugar",
      "udp-糖", "核苷糖", "nucleotide sugar", "udp-galactose"), {"C": 6}),
    # 酰化(按关键词分别定值):乙酰 C2
    (("acetyl-coa", "乙酰-coa", "乙酰辅酶a"), {"C": 2}),
    # 丙二酰 C3
    (("malonyl", "丙二酰", "malonyl-coa"), {"C": 3}),
    # 丁酰/琥珀酰 C4
    (("butyryl", "丁酰", "butyryl-coa", "succinyl", "琥珀酰",
      "succinyl-coa"), {"C": 4}),
    # 氨甲酰化:C1 + N
    (("carbamoyl phosphate", "羰基磷酸", "氨甲酰磷酸"), {"C": 1, "N": 1}),
    # 羧化:C1(CO₂ Unicode 归一在 registered_donors 内)
    (("co2", "hco3", "碳酸氢", "carboxylation", "羧化",
      "co2 fixation", "bicarbonate"), {"C": 1}),
)

# ---------------------------------------------------------------- ②SMARTS 编目

# 底物可进攻键型表(v43-g3b-catalog-2;**34 条**,逐条枚举与计数一致——
# D-4 对账修复:v1 文本写"25 条"而枚举 26/27 项不一致)。
# 芳香性模型声明(D-5):RDKit 默认(sanitize 感知,Kekulé 输入先归一);
# "芳环"= 任一 RDKit 芳香环(苯环与六元杂芳环经 aromatic_ring 条目);
# 五元杂芳环(呋喃/噻吩/吡咯/噁唑…)单列 heteroaromatic_5 条目;芳香噻吩
# S 不被脂肪族硫醚 SMARTS 覆盖([SX2] 不匹配芳香 [s]),属 heteroaromatic_5。
# 覆盖声明:酯条目无环限制 → 内酯已覆盖;缩醛条目 [CX4]([OX2])[OX2] →
# 糖苷端基碳(端基 C–O–C)已覆盖;酰胺 [CX3](=O)[NX3] 广义覆盖氨基甲酸酯/
# 脲的羰基 N,但两者另列名目入册(D-5 编目对账)。
ATTACKABLE_PATTERNS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    # 羧酸/羧酸根(电荷归一后为酸形)
    ("carboxylic_acid", "[CX3](=O)[OX2H]", ("decarboxylation", "c1_release")),
    # 酯(无环限制 → 内酯覆盖)
    ("ester", "[CX3](=O)[OX2H0][#6]", ("hydrolysis", "acyl_transfer")),
    # 酰胺
    ("amide", "[CX3](=O)[NX3]", ("hydrolysis",)),
    # 氨基甲酸酯(R–O–C(=O)–N;酰胺 SMARTS 不专 cover,D-5 显式补)
    ("carbamate", "[CX3](=O)([OX2])[NX3]", ("hydrolysis",)),
    # 脲/取代脲(N–C(=O)–N)
    ("urea", "[CX3](=O)([NX3])[NX3]", ("hydrolysis",)),
    # 磺酰胺(磺胺类)
    ("sulfonamide", "[SX4](=O)(=O)[NX3]", ("hydrolysis", "desulfurization")),
    # 磷酸酯/磷酸酐
    ("phosphate_ester", "[PX4](=O)([OX2])[OX2]",
     ("hydrolysis", "dephosphorylation")),
    # 膦酸酯/C–P 键(草甘膦类;C–P 裂合酶独立首步,D-5 显式)
    ("phosphonate_cp", "[P;X4](=O)[#6]", ("cleavage", "hydrolysis")),
    # 硫酸酯/磺酸/砜
    ("sulfate_sulfonate", "[SX4](=O)(=O)[OX2]", ("hydrolysis", "desulfurization")),
    ("sulfone", "[SX4](=O)(=O)[#6]", ("desulfurization",)),
    # 硫醚(硫醇烷基化产物可被裂解/氧化;芳香杂环硫见 heteroaromatic_5)
    ("thioether", "[SX2]([#6])[#6]",
     ("desulfurization", "oxygenation", "s_oxidation")),
    # 亚砜
    ("sulfoxide", "[SX3](=O)[#6]", ("reductive_deoxygenation", "oxygenation")),
    # 缩醛(糖苷键;端基 C–O–C 覆盖)
    ("acetal", "[CX4]([OX2])[OX2]", ("hydrolysis", "deglycosylation")),
    # 环氧化物(水解开环;环境降解经典中间体)
    ("epoxide", "[CX4]1[OX2][CX4]1", ("hydration", "hydrolysis")),
    # 醚 C-O-C(烷基/芳基醚水解断裂)
    ("ether", "[OD2]([#6])[#6]", ("hydrolysis", "deglycosylation")),
    # 碳-卤键
    ("c_halide", "[#6][F,Cl,Br,I]", ("dehalogenation",)),
    # 硝基
    ("nitro", "[NX3](=O)=O", ("reductive_deoxygenation",)),
    # N-氧化物(两性离子书写)
    ("n_oxide", "[NX4+][OX1-]", ("reductive_deoxygenation",)),
    # 腈
    ("nitrile", "[CX2]#N", ("hydration",)),
    # 胺/亚胺/芳族 N(C-N 水解、脱氨、转氨受体、N-氧化)
    ("amine_imine", "[$([NX3;H0,H1,H2,H3][#6]),$([NX2]=[#6]),$([n])]",
     ("deamination", "oxygenation", "amination", "n_oxidation")),
    # 季铵/甜菜碱 N(百草枯/敌草快/胆碱型;Uncharger 中和不了,F-2 残电荷)
    ("quaternary_ammonium", "[NX4+;H0]", ("c1_release", "demethylation")),
    # 醇/酚(氧化/缀合位点;磷酸化/磺化受体)
    ("hydroxyl", "[OX2H][#6]", ("dehydrogenation", "oxygenation",
                                "conjugation", "phosphorylation",
                                "sulfonation")),
    # 过氧化物/氢过氧化物(脂质过氧化;还原脱 O 白名单族)
    ("peroxide", "[OX2][OX2]", ("reductive_deoxygenation",)),
    # 烯(水合/环氧化/加氢)
    ("alkene", "[CX3]=[CX3]",
     ("hydration", "oxygenation", "hydrogenation", "epoxidation")),
    # 醛/酮(转氨/还原氨化的受体位点;加氢/水合;脱羰)
    ("carbonyl", "[CX3]=[OX1]", ("hydrogenation", "hydration",
                                 "oxygenation", "conjugation", "amination")),
    # β-羟基羰基(逆醛醇)
    ("beta_hydroxy_carbonyl", "[CX3](=[OX1])-[#6]-[#6]-[OX2H]",
     ("cleavage", "c2_release")),
    # 1,3-二羰基(硫解)
    ("beta_dicarbonyl", "[CX3](=[OX1])-[#6]-[CX3](=[OX1])",
     ("cleavage", "c2_release")),
    # 1,2-二羰基(α-二酮 C–C 断裂;D-1 缺口显式补)
    ("alpha_dicarbonyl", "[CX3](=[OX1])[CX3](=[OX1])",
     ("cleavage", "c2_release")),
    # α-羟基酸
    ("alpha_hydroxy_acid", "[CX4]([OX2H])-[CX3](=O)[OX2]",
     ("cleavage", "c2_release")),
    # 杂原子甲基(脱甲基供体位点)
    ("heteroatom_methyl", "[#7,#8,#16][CH3]", ("c1_release", "demethylation")),
    # 氰醇
    ("cyanohydrin", "[#6][CX4]([OX2H])([CX2]#N)", ("c1_release",)),
    # sp3 C-H(羟化/脱氢的泛位点;粒度只到"有没有",不到"哪一位"——G3-c)
    ("sp3_ch", "[CX4;H1,H2,H3]", ("oxygenation", "dehydrogenation",
                                   "hydroxylation")),
    # 芳环(经环信息判定,见 _has_aromatic_ring;RDKit 默认芳香性模型)
    ("aromatic_ring", "__ringinfo__",
     ("oxygenation", "hydroxylation", "cleavage", "dehydrogenation",
      "halogenation", "sulfonation")),
    # 五元杂芳环(呋喃/噻吩/吡咯/噁唑…;环氧化/开环单列,D-5)
    ("heteroaromatic_5", "__ringinfo5__",
     ("oxygenation", "hydroxylation", "cleavage", "dehydrogenation")),
)

# 断键裂解 motif 快路径(G1-b C–C 氧化断键族;碎片重构判据的第一条通道)
CLEAVAGE_MOTIFS = (
    "beta_hydroxy_carbonyl", "beta_dicarbonyl", "alpha_hydroxy_acid",
    "alpha_dicarbonyl",
)

# 可水解链接族(变换类命名消歧:杂原子键断裂 +H₂O 的"hydrolysis"与
# 烯/腈水合的"hydration"在公式层同签名;底物命中所列键型 ⇒ hydrolysis)
HYDROLYSABLE_LINKAGE_PATTERNS = (
    "ester", "amide", "carbamate", "urea", "sulfonamide", "phosphate_ester",
    "sulfate_sulfonate", "acetal", "ether", "phosphonate_cp", "epoxide",
)

# ---------------------------------------------------------------- ③碎片清单

# 封闭小碎片清单(v43-cons-frag-1;评审 D-2/A-6):`底物式 − 产物式` 反查
# 中性碎片。匹配条件:硬元素(C/N/S/P/卤/金属)逐元素精确相等;O/H 自由
# 元素只设下界(碎片 O/H ≥ 缺口 O/H——多出部分来自隐式供体 H₂O/O₂);
# 且母体命中所要求官能团之一(条件(ii):可断键/官能团存在性)。
# 大离去基团不经本清单,由有界杂原子单键切搜索覆盖(见 _gap_reconstructible)。
FRAGMENT_CATALOG: tuple[tuple[str, dict[str, int], tuple[str, ...]], ...] = (
    ("co2", {"C": 1, "O": 2},
     ("carboxylic_acid", "ester", "carbamate", "urea", "beta_dicarbonyl",
      "alpha_hydroxy_acid", "alpha_dicarbonyl")),          # 脱羧
    ("co", {"C": 1, "O": 1}, ("carbonyl", "carboxylic_acid")),  # 脱羰
    ("hcooh", {"C": 1, "H": 2, "O": 2}, ("ester", "carboxylic_acid")),
    ("ch2o", {"C": 1, "H": 2, "O": 1}, ("heteroatom_methyl", "acetal")),
    ("ch3oh", {"C": 1, "H": 4, "O": 1}, ("heteroatom_methyl", "ester")),
    ("acetic_acid", {"C": 2, "H": 4, "O": 2},
     ("ester", "carbamate", "urea", "carboxylic_acid")),    # 脱乙酰
    ("hcn", {"C": 1, "H": 1, "N": 1}, ("nitrile", "cyanohydrin")),
    ("ch3sh", {"C": 1, "H": 4, "S": 1}, ("thioether",)),    # S-脱甲基
    ("nh3", {"N": 1, "H": 3}, ("amine_imine", "amide", "urea", "carbamate")),
    ("h2s", {"S": 1, "H": 2}, ("thioether", "sulfate_sulfonate")),
)

# 有界键切搜索上限(D-2:有界;超出 → 不可审计 → 降位,绝不假放行)
MAX_CLEAVABLE_BONDS = 128     # 可切键数上限(超出 → unauditable)
MAX_CUT_DEPTH = 4             # 同时切键数上限(三酰甘油 = 3 键覆盖)
CUT_EVAL_BUDGET = 2048        # 每候选切分求值预算(超出 → unauditable)


@lru_cache(maxsize=1)
def _attackable_smarts() -> dict[str, Chem.Mol]:
    out: dict[str, Chem.Mol] = {}
    for name, smarts, _classes in ATTACKABLE_PATTERNS:
        if smarts.startswith("__ringinfo"):
            continue
        patt = Chem.MolFromSmarts(smarts)
        if patt is None:
            raise RuntimeError(f"v43-g3b-catalog-2 SMARTS 非法:{name}:{smarts}")
        out[name] = patt
    return out


@lru_cache(maxsize=1)
def _uncharger() -> rdMolStandardize.Uncharger:
    return rdMolStandardize.Uncharger()


@lru_cache(maxsize=1)
def _tautomer_enumerator():
    return rdMolStandardize.TautomerEnumerator()


# ---------------------------------------------------------------- ④规范化

@dataclass
class SideAnalysis:
    """一侧(底物/候选)的规范化分析(v43-norm-2 之后)。

    parse_ok=False ⇒ 无法判定(不按零:计数字段全部为 None,判定层
    按不可审计处置)。dou=None ⇒ DoU 非整数(F-2:带电荷项后仍非整数 →
    不可审计,不参与 DoU 依赖的判定)。
    """

    parse_ok: bool
    smiles: str
    formula: dict[str, int] | None = None       # 去盐+电荷归一后含 H 计数
    dou: int | None = None                       # 不饱和度(带电荷项)
    n_components: int = 0                        # 去盐后组分数
    salt_stripped: tuple[str, ...] = ()          # 被剥离的反离子(含多原子)
    main_formulas: tuple[dict[str, int], ...] = ()  # 全部并列最大 C 组分(A-5)
    main_mol: Chem.Mol | None = None             # 主组分分子(变换类鉴别用)
    pattern_names: tuple[str, ...] = ()          # 母体命中的可进攻键型
    tautomer_normalized: bool = False
    metal_covalent: bool = False                 # 去盐后存在共价键合金属
    mol: Chem.Mol | None = None                  # 规范化后分子(键切搜索用)


def _c_count(mol: Chem.Mol) -> int:
    return sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "C")


def _net_charge(mol: Chem.Mol) -> int:
    return sum(a.GetFormalCharge() for a in mol.GetAtoms())


def _desalt_components(mol: Chem.Mol) -> tuple[Chem.Mol, tuple[str, ...]]:
    """去盐(v43-norm-2;F-3/C-2 扩展):剥离 spectator 反离子。

    v1 只剥带电单原子;v2 按评审 F-3 扩展为:组分带电 ∧(不含碳 ∨ 存在
    严格更大碳数的保留组分)⇒ 剥离。覆盖多原子反离子(formate/acetate/
    sulfate/草酸/Tris/TEA/HCO₃⁻)与配位型抗衡离子;中性共结晶分子
    (结晶水/DMSO/甲醇)不剥(属列出产物,计数如实)。并列最大碳数的带电
    组分不剥(TEA+ 酚盐型边界:无法定谁是主体 → 保守保留并披露)。
    去盐先于电荷归一(评审背书):带反离子的盐整体净电荷为零,Uncharger
    不会中和组分 —— 先剥离再归一,酸/盐两形态才同计数。
    """
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=False)
    if len(frags) <= 1:
        return mol, ()
    # 确定性排序:C 数降序 → 重原子数降序 → SMILES 字典序(首名恒保留)
    order = sorted(
        range(len(frags)),
        key=lambda i: (-_c_count(frags[i]), -frags[i].GetNumAtoms(),
                       Chem.MolToSmiles(frags[i])))
    kept_idx = [order[0]]
    kept_max_c = _c_count(frags[order[0]])
    stripped: list[str] = []
    for i in order[1:]:
        frag = frags[i]
        charged = _net_charge(frag) != 0
        n_c = _c_count(frag)
        if charged and (n_c == 0 or n_c < kept_max_c):
            stripped.append(Chem.MolToSmiles(frag))
            continue
        kept_idx.append(i)
    kept = [frags[i] for i in sorted(kept_idx)]
    combined = kept[0]
    for frag in kept[1:]:
        combined = Chem.CombineMols(combined, frag)
    return combined, tuple(stripped)


def _formula_of(mol: Chem.Mol) -> dict[str, int]:
    """含 H 分子式计数(AddHs 后按元素求和;计数差不用集合差)。"""
    counts: dict[str, int] = {}
    mh = Chem.AddHs(mol)
    for atom in mh.GetAtoms():
        sym = atom.GetSymbol()
        counts[sym] = counts.get(sym, 0) + 1
    return counts


def _dou_of(mol_h: Chem.Mol) -> int | None:
    """不饱和度(F-2:带电荷项;分子图/价键算法)。

    DoU = 1 + Σ原子 (v−2)/2(v = sanitize 后总价键数,含形式电荷与
    P=S/P–O 五价磷、六价硫的 π 键贡献)——与 (2C+2+N−H−X+q)/2 在
    无 P/S 变价时同值,且对有机磷(P=S)/磺酸(v6 S)/季铵(q 项)给出
    整数正确值(v1 中性式算法对毒死蜱类读出半整数属实现缺陷)。
    **入参须为 AddHs 后的分子**(H 为显式原子,v(H)=1 才能入账)。
    非整数(自由基/断片形式电荷)→ None = 不可审计断言,调用方不使用
    DoU 依赖分支。
    """
    total = 2   # 2·DoU = 2 + Σ(v_i − 2)
    for atom in mol_h.GetAtoms():
        sym = atom.GetSymbol()
        try:
            v = atom.GetTotalValence()
        except Exception:
            return None
        total += (v - 2)
    if total % 2 != 0:
        return None
    return total // 2


def _patterns_of(mol: Chem.Mol) -> tuple[tuple[str, ...], bool]:
    """母体命中的可进攻键型(互变规范化后 SMARTS;失败回退原结构)。"""
    target = mol
    normalized = False
    try:
        can = _tautomer_enumerator().Canonicalize(mol)
        if can is not None and can.GetNumAtoms() == mol.GetNumAtoms():
            target, normalized = can, True
    except Exception:
        pass
    hits: list[str] = []
    for name, patt in _attackable_smarts().items():
        try:
            if target.HasSubstructMatch(patt):
                hits.append(name)
        except Exception:
            continue
    if _has_aromatic_ring(target):
        hits.append("aromatic_ring")
    if _has_heteroaromatic_5(target):
        hits.append("heteroaromatic_5")
    hits.sort()
    return tuple(hits), normalized


def _has_aromatic_ring(mol: Chem.Mol) -> bool:
    ring_info = mol.GetRingInfo()
    for ring in ring_info.AtomRings():
        if ring and all(mol.GetAtomWithIdx(i).GetIsAromatic() for i in ring):
            return True
    return False


def _has_heteroaromatic_5(mol: Chem.Mol) -> bool:
    """五元杂芳环(含 N/O/S 的 RDKit 芳香五环;芳香性模型声明见编目)。"""
    ring_info = mol.GetRingInfo()
    for ring in ring_info.AtomRings():
        if len(ring) != 5:
            continue
        atoms = [mol.GetAtomWithIdx(i) for i in ring]
        if all(a.GetIsAromatic() for a in atoms) and any(
                a.GetSymbol() in ("N", "O", "S") for a in atoms):
            return True
    return False


def analyze_side(smiles: str) -> SideAnalysis:
    """一侧规范化分析:解析 → **去盐** → 电荷归一 → 含 H 计数 + SMARTS。

    去盐先于电荷归一(评审 F-1 背书,顺序不变)。解析失败 ⇒
    parse_ok=False(不可判定,不按零);解析器与既有 gate_smiles 同源
    (MolFromSmiles + SanitizeMol)——工作流路径下 parse-fail 候选到不了
    本过滤器(既有门先行),本分支仅作离线重放的防御(C 节 3 写明)。
    """
    raw = (smiles or "").strip()
    if not raw:
        return SideAnalysis(parse_ok=False, smiles=raw)
    mol = Chem.MolFromSmiles(raw)
    if mol is None:
        return SideAnalysis(parse_ok=False, smiles=raw)
    mol, stripped = _desalt_components(mol)
    try:
        mol = _uncharger().uncharge(mol)
    except Exception:
        pass  # 电荷归一失败沿用原结构(计数仍可作;永久电荷经 DoU q 项入账)
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        return SideAnalysis(parse_ok=False, smiles=raw,
                            salt_stripped=stripped)
    formula = _formula_of(mol)
    # 全部并列最大 C 组分(A-5:逐一施加 G1-b;并列取全部)
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    max_c = max((_c_count(f) for f in frags), default=0)
    mains = [f for f in frags if _c_count(f) == max_c]
    main_formulas = tuple(_formula_of(f) for f in mains)
    patterns, taut_ok = _patterns_of(mol)
    metal_covalent = any(
        a.GetSymbol() in METAL_ATOMS and a.GetDegree() >= 1
        for a in mol.GetAtoms())
    return SideAnalysis(
        parse_ok=True, smiles=raw, formula=formula,
        dou=_dou_of(Chem.AddHs(mol)), n_components=len(frags),
        salt_stripped=stripped, main_formulas=main_formulas,
        main_mol=mains[0] if mains else None,
        pattern_names=patterns, tautomer_normalized=taut_ok,
        metal_covalent=metal_covalent, mol=mol,
    )


# ---------------------------------------------------------------- ⑤供体/声明


def _kw_hit(text_lower: str, kw: str) -> bool:
    """关键词命中:ASCII 词边界(B-3:`coa` 不命中 `coal`;`sam` 不命中
    `sample`);中文/含 Unicode 关键词子串。"""
    if any(ord(ch) > 127 for ch in kw):
        return kw in text_lower
    return re.search(
        rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text_lower) is not None


def registered_donors(surface_text: str) -> dict[str, int]:
    """题面文本扫描封闭关键词表 → 已登记供体的元素增量。

    **A-1 惰性声明**:当前门禁次序的答案路径上增侧不可达,本表为规格性
    文档(无操作行为);每元素授予 = 所有命中关键词在该元素上的最大值
    (B-2:同元素不求和、跨元素天然并存)。
    """
    text = (surface_text or "").lower()
    if not text:
        return {}
    text = text.replace("₂", "2").replace("₃", "3").replace("₄", "4")
    donors: dict[str, int] = {}
    for keywords, contribution in DONOR_REGISTRY:
        if any(_kw_hit(text, kw) for kw in keywords):
            for el, amount in contribution.items():
                donors[el] = max(donors.get(el, 0), amount)
    return donors


def declared_complete(note: str) -> bool:
    """产物列表完整性声明(v43-cons-kw-2)。

    词边界 + 否定前缀排除(A-3:`complete` 不命中 `incomplete`;
    "not completely" 不算声明);封闭表补矿化措辞族(R2 的声明侧防线)。
    """
    text = note or ""
    if not text:
        return False
    low = text.lower()
    # 中文:子串 + 否定前缀字
    for kw in _CN_COMPLETE_KEYWORDS:
        idx = low.find(kw)
        while idx != -1:
            prev = low[idx - 1] if idx > 0 else ""
            if prev not in _CN_NEGATION_CHARS:
                return True
            idx = low.find(kw, idx + 1)
    # 英文:词边界正则 + 前 2 token 否定回看
    for _src, patt in _EN_COMPLETE_PATTERNS:
        for m in patt.finditer(low):
            head = low[:m.start()].split()[-2:]
            tokens = [t.strip(".,;:!?()'\"") for t in head]
            if any(t in _EN_NEGATOR_TOKENS or t.endswith("n't")
                   for t in tokens):
                continue
            return True
    return False


# ---------------------------------------------------------------- ⑥碎片重构

def _cleavable_bond_indices(mol: Chem.Mol) -> list[int]:
    """可切键:非环单键,两端至少一端为杂原子(N/O/S/P/卤/金属)。

    C–C 键不进通用切搜索(烷烃任意切会假放行;C–C 断键仅经 motif 快路径
    与封闭碎片清单)——覆盖评审点名的全部教科书键型:P–O(有机磷)、
    酯 C–O(菊酯/大酯)、糖苷 C–O、酰胺 C–N(肽)、醚 C–O、磺酰胺 S–N、
    C–P(膦酸酯)。
    """
    ring_info = mol.GetRingInfo()
    out = []
    for bond in mol.GetBonds():
        if bond.GetBondType() != Chem.BondType.SINGLE:
            continue
        if ring_info.NumBondRings(bond.GetIdx()) > 0:
            continue
        a1, a2 = bond.GetBeginAtom(), bond.GetEndAtom()
        s1, s2 = a1.GetSymbol(), a2.GetSymbol()
        if s1 == "C" and s2 == "C":
            continue
        if s1 == "H" or s2 == "H":
            continue
        out.append(bond.GetIdx())
    return out


def _split_on_bond(mol: Chem.Mol, bond_idx: int
                   ) -> tuple[Chem.Mol, Chem.Mol] | None:
    """单键切分(碎片两端由 sanitize 补隐式 H = H 帽)。"""
    try:
        cut = Chem.FragmentOnBonds(mol, [bond_idx], addDummies=False)
        frags = Chem.GetMolFrags(cut, asMols=True, sanitizeFrags=True)
        if len(frags) != 2:
            return None
        return frags[0], frags[1]
    except Exception:
        return None


def _hard_of(formula: dict[str, int]) -> dict[str, int]:
    return {el: formula.get(el, 0) for el in GAP_HARD_ELEMENTS
            if formula.get(el, 0) > 0}


def _fits_need(frag: dict[str, int], need: dict[str, int]) -> bool:
    """碎片硬元素完全落入剩余缺口(逐元素 ≤ 且缺口非空)。"""
    if not need:
        return False
    return all(frag.get(el, 0) <= need.get(el, 0)
               for el in GAP_HARD_ELEMENTS)


def _search_cover(mol: Chem.Mol, need: dict[str, int], depth: int,
                  budget: list[int]) -> tuple[bool, bool]:
    """有界 DFS:杂原子单键切搜索,碎片并集精确覆盖硬元素缺口。

    O/H 为自由元素(隐式供体 H₂O/O₂;脱氢的 H、脱水的 O 可经未建模
    受体/水离开,§2.1 冻结口径"H 与 O 计数但不设硬门")——碎片侧不设
    O/H 界,只对硬元素精确对账。返回 (命中, 预算耗尽)。
    """
    if not need:
        return True, False
    if depth <= 0:
        return False, False
    bonds = _cleavable_bond_indices(mol)
    if len(bonds) > MAX_CLEAVABLE_BONDS:
        return False, True
    for b in bonds:
        if budget[0] <= 0:
            return False, True
        budget[0] -= 1
        pieces = _split_on_bond(mol, b)
        if pieces is None:
            continue
        for piece in pieces:
            hard = _hard_of(_formula_of(piece))
            if hard and _fits_need(hard, need):
                rest = pieces[1] if piece is pieces[0] else pieces[0]
                new_need = {el: v - hard.get(el, 0)
                            for el, v in need.items() if v > hard.get(el, 0)}
                ok, exhausted = _search_cover(rest, new_need, depth - 1,
                                              budget)
                if ok:
                    return True, False
                if exhausted:
                    return False, True
    return False, False


def _gap_reconstructible(substrate: SideAnalysis,
                         target_formula: dict[str, int]) -> tuple[bool, str]:
    """碎片可重构判据(评审 D-2;统一三处:G1-b 允许集 / ΔC=−1,−2 放行 /
    ②第三条件)。

    `底物式 − 产物式` 反查:三通道按序尝试——
    1. motif 快路径(β-羟基羰基/β-二羰基/α-羟基酸/1,2-二羰基:C–C 氧化
       断键族,条件(ii)由 motif 本身给出);
    2. 封闭小碎片清单(CO₂/CO/HCOOH/CH₂O/CH₃OH/乙酸/HCN/CH₃SH/NH₃/H₂S,
       条件(ii)= 母体命中该碎片要求的官能团);
    3. 有界杂原子单键切搜索(大离去基团:糖苷/酯/酰胺/醚/磷酯/肽/C–P;
       条件(ii)= 母体真实存在可断键;≤4 键、有预算,超限 → 不可审计)。
    匹配要求(i):硬元素(C/N/S/P/卤/金属)逐元素精确一致;O/H 为自由
    元素不设界(隐式供体 H₂O/O₂;脱氢 H/脱水 O 经未建模受体离开,
    §2.1 冻结口径"H 与 O 计数但不设硬门")。
    """
    sf = substrate.formula or {}
    gap = {el: sf.get(el, 0) - target_formula.get(el, 0)
           for el in set(sf) | set(target_formula)}
    need = {el: v for el, v in gap.items()
            if el in GAP_HARD_ELEMENTS and v > 0}
    # 硬元素不减少(或主产物硬元素超出底物)→ 非缺口形态,不属于本判据
    if not need:
        return True, "no_hard_gap"
    # 通道 1:motif 快路径
    if any(p in substrate.pattern_names for p in CLEAVAGE_MOTIFS):
        return True, "motif_cleavage"
    # 通道 2:封闭小碎片清单
    for name, fformula, required in FRAGMENT_CATALOG:
        if _hard_of(fformula) != need:
            continue
        if any(p in substrate.pattern_names for p in required):
            return True, f"fragment_catalog:{name}"
    # 通道 3:有界杂原子单键切搜索
    if substrate.mol is None:
        return False, "no_substrate_mol"
    bonds = _cleavable_bond_indices(substrate.mol)
    if len(bonds) > MAX_CLEAVABLE_BONDS:
        return False, "cut_search_bounded_out"
    ok, exhausted = _search_cover(
        substrate.mol, need, MAX_CUT_DEPTH, [CUT_EVAL_BUDGET])
    if ok:
        return True, "bond_cut_search"
    return False, ("cut_search_budget_exhausted" if exhausted
                   else "fragment_not_reconstructible")


# ---------------------------------------------------------------- ⑦逐候选判定


@dataclass
class CandidateJudgment:
    """单候选守恒判定(纯数据;tier ∈ pass|downgrade|exclude)。"""

    index: int
    smiles: str
    tier: str
    rules: list[str] = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    dC_main: int | None = None
    ddou: int | None = None
    g3b: dict = field(default_factory=dict)
    flags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": CONSERVATION_FILTER_VERSION,
            "tier": self.tier,
            "rules": list(self.rules),
            "original_position": self.index,
            "counts": self.counts,
            "dC_main": self.dC_main,
            "ddou": self.ddou,
            "g3b": self.g3b,
            "flags": self.flags,
        }


def _delta(sub: dict[str, int], prod: dict[str, int]) -> dict[str, int]:
    keys = set(sub) | set(prod)
    return {k: prod.get(k, 0) - sub.get(k, 0) for k in sorted(keys)}


def _hard_hetero_increase(delta: dict[str, int]) -> list[str]:
    """G2-a 增杂原子清单:硬门元素 + 金属的正增量。"""
    out = []
    for el, d in delta.items():
        if d > 0 and (el in HARD_HETERO_ATOMS or el in METAL_ATOMS):
            out.append(el)
    return sorted(out)


# key 2 语义(E-2/D-3):这三类变换不构成化学矛盾(unclassified = 分类器
# 覆盖失败,不是化学不可能的证据 → 中性落 key 3)
NEUTRAL_TRANSFORM_CLASSES = frozenset(
    {"unclassified", "isomerization", "parse_fail"})


def judge_candidate(
    *,
    index: int,
    substrate: SideAnalysis,
    product: SideAnalysis,
    note: str,
    donors: dict[str, int],
) -> CandidateJudgment:
    """单候选守恒判定(v43-cons-2;纯函数、确定性)。

    判定顺序(档位优先级显式:剔除 > 降位 > hold;②优先于 G1-b 的缺口
    放行——A-6 显式化):
    1. 候选解析失败 → 降位(不可审计,不按零;与既有门同一解析器,
       工作流路径不可达,重放防御分支);
    2. G1-a 违规①:全局增碳且超出已登记供体 → 剔除(**A-1 惰性**:答案
       路径上既有元素门先行,本分支不触发);
    3. G2-a:增 N/S/P/卤素/金属(含共价金属,C 节 1 归属档写死)且无登记
       供体 → 剔除;
    4. ②声明完整 ∧ 原子消失:仅当缺失不可重构碎片才硬剔,否则降位
       (A-3 三条件;CO₂/H₂O 接口:CO₂ 可重构的缺失永不硬剔);
    5. G1-b:主产物 ΔC 缺口经碎片可重构判据(三通道)放行或降位;四类
       应降位形态:碎片不可重构/跨元素不一致(硬元素精确对账)/ΔDoU
       异常(|ΔDoU|≥2)/与完整性声明叠加(②先行);
    6. 金属配位不可判形态(共价态在两侧翻转而计数不变)→ 不可审计降位
       +标注(C 节 6:不硬剔不 hold);
    7. 杂原子减少白名单族 → 通过+标注;G3-b 变换类 + 化学矛盾(仅矛盾
       受 key 2 惩罚;unclassified 中性)。
    """
    j = CandidateJudgment(index=index, smiles=product.smiles, tier=TIER_PASS)
    if not product.parse_ok:
        j.tier = TIER_DOWNGRADE
        j.rules.append("cons_unauditable:candidate_parse_fail")
        j.g3b = {"matched": False, "neutral": True, "contradiction": False,
                 "transform_class": "parse_fail",
                 "attackable": list(substrate.pattern_names)}
        return j

    sf = substrate.formula or {}
    pf = product.formula or {}
    delta = _delta(sf, pf)
    j.counts = {
        "substrate": dict(sf), "product": dict(pf), "delta": dict(delta),
    }
    if substrate.dou is None or product.dou is None:
        j.ddou = None
        j.flags["dou_unauditable"] = True   # F-2:非整数 DoU → 不可审计
    else:
        j.ddou = product.dou - substrate.dou
    sub_c = sf.get("C", 0)
    prod_c = pf.get("C", 0)
    mains = product.main_formulas or (pf,)
    main_c = max((f.get("C", 0) for f in mains), default=0)
    j.dC_main = main_c - sub_c

    # ---- G3-b 变换类 + 匹配(先算,供自排序键 2)
    transform = _classify_transform(delta, j.dC_main, substrate, product,
                                    j.ddou)
    attackable = list(substrate.pattern_names)
    allowed = _attackable_classes(substrate.pattern_names)
    # 同分异构恒放行(评审背书;E-4:仅在 key 1 同档内生效——tier 为首键,
    # 豁免不可能越过处置档边界,也不可能越过 key 2 的矛盾判据)
    matched = (transform in allowed) or (transform == "isomerization")
    neutral = transform in NEUTRAL_TRANSFORM_CLASSES
    contradiction = (
        (not matched) and (not neutral) and bool(allowed))
    j.g3b = {
        "matched": matched,
        "neutral": neutral,
        "contradiction": contradiction,
        "transform_class": transform,
        "attackable": attackable,
        "catalog_version": G3B_CATALOG_VERSION,
    }

    # ---- 2/3:增侧硬剔除(可证明:原子凭空出现,无登记供体)
    # A-1 惰性:答案路径上既有元素白名单门先于本过滤器拒掉一切 +C/+N/+P
    # 候选(重放六批剔除侧零触发为证),本分支与供体放行均为不可达 no-op。
    surplus_c = prod_c - sub_c - donors.get("C", 0)
    if surplus_c > 0:
        j.tier = TIER_EXCLUDE
        j.rules.append(f"G1a1_surplus_carbon:+{surplus_c}C_no_registered_donor")
        return j
    alien = [el for el in _hard_hetero_increase(delta)
             if delta[el] > donors.get(el, 0)]
    if alien:
        j.tier = TIER_EXCLUDE
        j.rules.append(
            "G2a_alien_heteroatom:+" + ",".join(
                f"{el}{delta[el]}" for el in alien) + "_no_registered_donor")
        return j

    # ---- 4:②声明完整 ∧ 原子消失(三条件硬剔;否则降位)
    if declared_complete(note):
        vanished_hard = {el: -delta.get(el, 0) for el in GAP_HARD_ELEMENTS
                         if delta.get(el, 0) < 0}
        if vanished_hard.get("C", 0) > 0 or any(
                v > 0 for k, v in vanished_hard.items() if k != "C"):
            reconstructible, why = _gap_reconstructible(substrate, pf)
            if not reconstructible:
                j.tier = TIER_EXCLUDE
                j.rules.append(
                    "G1a2_declared_complete_atom_loss:"
                    + ",".join(sorted(vanished_hard)) + f"_gap:{why}")
                return j
            # 缺失可重构(如 CO₂/H₂O 矿化形态;判分口径 CO₂ 省略时该候选
            # 仍可命中金标)→ 降位不硬剔(A-3 接口对齐)
            j.tier = TIER_DOWNGRADE
            j.rules.append(
                "declared_complete_loss_reconstructible:" + why)
            j.flags["declared_complete"] = True

    # ---- 5:G1-b 主产物碳骨架缺口(碎片可重构判据,统一三处)
    if j.dC_main < 0:
        # A-5:对全部并列最大 C 组分逐一施加(任一失败即降位)
        results = [_gap_reconstructible(substrate, f) for f in mains]
        reconstructible = all(ok for ok, _w in results)
        why = next(w for ok, w in results if not ok) if not reconstructible \
            else results[0][1]
        if not reconstructible:
            j.tier = TIER_DOWNGRADE
            j.rules.append(
                f"G1b_fragment_not_reconstructible:dC_main={j.dC_main}"
                f"_gap:{why}")
        elif j.dC_main <= -3:
            # 裂解族(≤−3):缺口碎片天然可携带 π 键/环(如三酰甘油→脂肪酸
            # 的两条未列酰基),ΔDoU 不设守卫——A-6 的 ΔDoU 异常仅约束
            # C1/C2 释放族
            j.flags["cleavage_reconstructible"] = why
        else:
            # C1/C2 释放族(−1/−2):ΔDoU 异常(|ΔDoU|≥2 或不可审计)提示
            # 环收缩/骨架数错而非脱除 ⇒ 降位(A-6 四类形态之三)
            if j.ddou is None or abs(j.ddou) >= 2:
                j.tier = TIER_DOWNGRADE
                j.rules.append(
                    f"G1b_ddou_anomaly:dC_main={j.dC_main}"
                    f"_ddou={'None' if j.ddou is None else j.ddou}")
            else:
                j.flags["fragment_inferred"] = (
                    "C1_family" if j.dC_main == -1 else "C2_family")
                j.flags["fragment_evidence"] = why
    elif j.dC_main > 0:
        j.flags["donor_backed"] = True   # A-1 惰性路径(不可达,规格性)

    # ---- 6:金属配位不可判形态(计数不变而共价态翻转)→ 降位+标注
    sub_metals = {el: sf.get(el, 0) for el in METAL_ATOMS if sf.get(el, 0)}
    prod_metals = {el: pf.get(el, 0) for el in METAL_ATOMS if pf.get(el, 0)}
    if sub_metals == prod_metals and sub_metals and \
            substrate.metal_covalent != product.metal_covalent:
        if j.tier == TIER_PASS:
            j.tier = TIER_DOWNGRADE
        j.rules.append("cons_unauditable:metal_coordination_shift")
        j.flags["metal_coordination_shift"] = True

    # ---- 7:杂原子减少侧(白名单族 → 通过+标注;O 自由,不设门)
    for el in sorted(HARD_HETERO_ATOMS | METAL_ATOMS):
        if delta.get(el, 0) < 0 and sf.get(el, 0) > 0:
            j.flags["reduction_whitelist"] = el
            break

    if j.tier != TIER_DOWNGRADE and contradiction:
        # G3-b 化学矛盾(底物具备可进攻基团而变换类与其矛盾):降位排序
        # 分量(key 2 靠后;不剔除)。unclassified/同分异构为中性,不惩罚。
        j.rules.append(f"g3b_chemical_contradiction:{transform}")
    return j


def _attackable_classes(pattern_names: tuple[str, ...]) -> frozenset[str]:
    classes: set[str] = set()
    for name in pattern_names:
        for _n, _s, allowed in ATTACKABLE_PATTERNS:
            if _n == name:
                classes.update(allowed)
    return frozenset(classes)


def _has_substruct(mol: Chem.Mol | None, smarts: str) -> bool:
    if mol is None:
        return False
    patt = Chem.MolFromSmarts(smarts)
    if patt is None:
        return False
    try:
        return mol.HasSubstructMatch(patt)
    except Exception:
        return False


def _classify_transform(delta: dict[str, int], dC_main: int,
                        substrate: SideAnalysis, product: SideAnalysis,
                        ddou: int | None) -> str:
    """候选变换类签名表 v2(全局计数差优先,主产物 ΔC 次之;确定性)。

    v2 补 +O 非羟化族(D-3):环氧化/S-氧化/N-氧化经"底物基团 + 产物
    子结构差"鉴别(公式层与羟化同签名);归属写明:脱烷基(N-dealkylation)
    归 c1_release 族;偶联/二聚归 conjugation(增侧,当前门禁下惰性,
    类目留位);重排归 isomerization。
    """
    def d(el: str) -> int:
        return delta.get(el, 0)

    patterns = substrate.pattern_names
    if all(v == 0 for v in delta.values()):
        return "isomerization"
    for el, cls in (("F", "dehalogenation"), ("Cl", "dehalogenation"),
                    ("Br", "dehalogenation"), ("I", "dehalogenation"),
                    ("N", "deamination"), ("S", "desulfurization"),
                    ("P", "dephosphorylation")):
        if d(el) < 0:
            return cls
    dC_global = d("C")
    if dC_global < 0:
        if dC_main <= -3:
            if any(p in patterns for p in CLEAVAGE_MOTIFS):
                return "cleavage"
            ok, _why = _gap_reconstructible(substrate, product.formula or {})
            if ok:
                # 杂原子链接断裂族(酯/酰胺/糖苷/醚/磷酯水解)归
                # hydrolysis(与编目允许类对齐);motif 外 C–C 断键归 cleavage
                if any(p in patterns for p in HYDROLYSABLE_LINKAGE_PATTERNS):
                    return "hydrolysis"
                return "cleavage"
            return "unclassified"
        if dC_main == -1:
            return "decarboxylation" if "carboxylic_acid" in patterns \
                else "c1_release"
        return "c2_release"
    if dC_global > 0:
        return "conjugation"
    # ---- 增侧变换类(登记供体放行后的形态;键 2 匹配用;A-1 惰性留位)
    if d("N") > 0:
        return "amination"          # 转氨/还原氨化(酮酸受体)
    if d("P") > 0:
        return "phosphorylation"
    if d("S") > 0:
        return "sulfonation"
    if any(d(el) > 0 for el in ("F", "Cl", "Br", "I")) or any(
            d(el) > 0 for el in METAL_ATOMS):
        return "halogenation_metalation"   # 有意先验排除档(禁用/配位)
    # ---- 全局 ΔC = 0:加成/消除/氧化还原/水解形
    if d("O") == 1 and d("H") >= 2:
        # 水解(片段已列,全局只差一分子水;底物有可水解链接)vs 水合(烯/腈)
        if any(p in patterns for p in HYDROLYSABLE_LINKAGE_PATTERNS):
            return "hydrolysis"
        return "hydration"
    if d("O") == -1 and d("H") == -2:
        return "dehydration"
    if d("O") == 1 and d("H") == 0:
        # +O 非羟化族鉴别(D-3):底物基团 + 产物子结构差
        if "alkene" in patterns and _has_substruct(
                product.main_mol, "[CX4]1[OX2][CX4]1"):
            return "epoxidation"
        if "thioether" in patterns and _has_substruct(
                product.main_mol, "[SX3](=O)[#6]"):
            return "s_oxidation"
        if "amine_imine" in patterns and _has_substruct(
                product.main_mol, "[NX4+][OX1-]"):
            return "n_oxidation"
        return "oxygenation"        # 羟化族(含多羟化经下一分支)
    if d("O") > 0:
        return "oxygenation"
    if d("O") < 0:
        return "reductive_deoxygenation"
    if ddou is None:
        return "unclassified"       # DoU 不可审计 → 中性(F-2)
    if d("H") < 0 and ddou > 0:
        return "dehydrogenation"
    if d("H") > 0 and ddou < 0:
        return "hydrogenation"
    return "unclassified"


# ---------------------------------------------------------------- ⑧过滤+自排序


@dataclass
class FilterResult:
    """一题的守恒过滤 + 自排序结果(题级)。"""

    status: str                       # ok | hold
    hold_reason: str = ""             # substrate_undecidable | all_rejected
    hold_detail: str = ""             # substrate_unparseable|no_candidates|all_excluded
    reject_count: int = 0             # hold 分账(C 节 4:带 reject_count)
    donors: dict[str, int] = field(default_factory=dict)
    substrate_parse_ok: bool = True
    ranked: list[CandidateJudgment] = field(default_factory=list)   # 新顺序
    excluded: list[CandidateJudgment] = field(default_factory=list)
    n_downgraded: int = 0
    n_excluded: int = 0
    versions: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "hold_reason": self.hold_reason,
            "hold_detail": self.hold_detail,
            "reject_count": self.reject_count,
            "donors": dict(self.donors),
            "substrate_parse_ok": self.substrate_parse_ok,
            "n_candidates": len(self.ranked) + len(self.excluded),
            "n_downgraded": self.n_downgraded,
            "n_excluded": self.n_excluded,
            "versions": dict(self.versions),
            "ranked": [j.to_dict() for j in self.ranked],
            "excluded": [j.to_dict() for j in self.excluded],
        }


def conservation_filter_and_rank(
    *,
    substrate_smiles: str,
    candidates: list[dict],
    surface_text: str = "",
) -> FilterResult:
    """守恒过滤 + 确定性自排序(v43-cons-2 + v43-selfrank-2)。

    入参:substrate_smiles = 题面母体(规范 SMILES);candidates =
    [{"smiles", "note"}](novel/analogy 提案候选,原始位次即列表序);
    surface_text = 题面条件文本(供体登记表扫描源,无则空;**规格性**,
    A-1 惰性声明下无操作行为)。

    出参 FilterResult:
    - status=hold:hold_reason ∈ {substrate_undecidable(输入侧),
      all_rejected(模型侧,剔空)} + reject_count 分账(C 节 4;剔空过
      触发经②计数留痕,不静默表现为空答)——诚实弃权,不空报告、不被迫
      回报最优违规者;
    - ranked:按冻结键序重排后的候选(纯重排语义:无剔除时集合不变);
      键序 = ①处置档(未违规在前,降位垫底)②G3-b 化学矛盾(仅矛盾靠后;
      unclassified/同分异构中性,E-2)③提案原位次(稳定序)。**守恒连续值
      不参与任何排序键;守恒档只作降位分量,不作正向先验**(迭代 2 硬
      证据);降位全空时按原位次照常报出(G2 no-op,无害,C 节 5);
    - excluded:被硬剔除的候选(可证明违规;结构化拒因)。
    """
    versions = {
        "cons_filter": CONSERVATION_FILTER_VERSION,
        "normalization": NORMALIZATION_VERSION,
        "self_rank": SELF_RANK_VERSION,
        "g3b_catalog": G3B_CATALOG_VERSION,
        "donor_registry": DONOR_REGISTRY_VERSION,
        "completeness_keywords": COMPLETENESS_KEYWORDS_VERSION,
        "fragment_catalog": FRAGMENT_CATALOG_VERSION,
    }
    substrate = analyze_side(substrate_smiles)
    donors = registered_donors(surface_text)
    result = FilterResult(status=STATUS_OK, donors=donors,
                          substrate_parse_ok=substrate.parse_ok,
                          versions=versions)
    if not substrate.parse_ok:
        # 底物不可判定 → 整题 hold(输入侧信号;不作违规软化通道)
        result.status = STATUS_HOLD
        result.hold_reason = HOLD_SUBSTRATE_UNDECIDABLE
        result.hold_detail = "substrate_unparseable"
        return result
    if not candidates:
        result.status = STATUS_HOLD
        result.hold_reason = HOLD_ALL_REJECTED
        result.hold_detail = "no_candidates"
        return result

    judgments: list[CandidateJudgment] = []
    for i, cand in enumerate(candidates):
        product = analyze_side(str(cand.get("smiles", "")))
        judgments.append(judge_candidate(
            index=i, substrate=substrate, product=product,
            note=str(cand.get("note", "")), donors=donors))

    excluded = [j for j in judgments if j.tier == TIER_EXCLUDE]
    kept = [j for j in judgments if j.tier != TIER_EXCLUDE]
    result.reject_count = len(excluded)
    if not kept:
        # 剔空即 hold(诚实弃权;模型侧信号,reject_count 留痕)
        result.status = STATUS_HOLD
        result.hold_reason = HOLD_ALL_REJECTED
        result.hold_detail = "all_excluded"
        result.excluded = excluded
        result.n_excluded = len(excluded)
        return result

    # ---- 自排序(v43-selfrank-2;稳定排序:Python sorted 为稳定序)
    tier_rank = {TIER_PASS: 0, TIER_DOWNGRADE: 1}
    ranked = sorted(
        kept,
        key=lambda j: (tier_rank[j.tier],
                       1 if j.g3b.get("contradiction") else 0,
                       j.index),
    )
    result.ranked = ranked
    result.excluded = excluded
    result.n_downgraded = sum(1 for j in ranked if j.tier == TIER_DOWNGRADE)
    result.n_excluded = len(excluded)
    return result
