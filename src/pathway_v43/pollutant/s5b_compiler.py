"""S5b 共同 compiler —— 映射供体模板/recorded 源 → PPV1 池 spec
(W1;契约登记 s5b-compiler-1;零模型、零网络)。

单一构建源:同一编译器服务三个入口(入口矩阵,§2):

| # | 入口 | 消费 | 产出/校验 |
| 1 | compile_donor_template | 映射模板(mapped_lhs/mapped_rhs/center_atoms)+ 当前底物 | spec(edits/donor/alignment/expectation 由**同一迁移结果**产生)+ validate_edits + 离线 execute_edits + target/center 诊断 |
| 2 | compile_recorded_reaction(recorded_source) | 原生库记录(donor_smiles + 完整净产物集合) | 推断映射(枚举预算/歧义披露,标 inferred,非原生/机制证据)+ 同 1 |
| 3 | pool provider 消费(s5b_builder/W4) | 编译结果 spec 列表 | 编译成功才进可执行池;失败结构化原因计数披露,不吞 Exception 回 None |

W1 规则落地点(任务书逐条):

1. lhs/rhs 按 **atom-map number** 联结(不按两侧解析 idx);拒重复 map、
   坏引用、保留原子改元素;原 idx 只作临时索引。
2. 在当前底物施加供体变化;目标、expectation、edits、中心由**同一
   迁移结果**产生(离线执行产物),不复制 donor rhs。
3. donor 中心与 alignment 键同一供体命名空间(``D_<map_no>``);current
   IDs 在映射值与当前 edits(audit.check_edit_against_donor 的消费契约)。
4. from_order 从**当前底物的一次确定执行 base**(ID-labelled 键表,
   kekulé 化后与 execute_edits 同一事实源)读,不用模板 lhs 词面。
5. 键差比较在**芳香形式**做(aromatic≡aromatic 不算变):双侧独立
   canonical Kekulé 的 6 键反向不再产生伪键差;去 map 也非充分修复
   (map 号联结 + 芳香语义双约束)。
6. 新原子 ID 符合 ATOM_ID_RE 且无冲突;add_atom 自动接 single 锚定键,
   不再次 form 同键;新 double/triple 先成 single 再变阶。
7. 多新增原子按有依据锚点拓扑序(BFS from 已落位原子);电荷/立体
   等现协议不支持时稳定 ``unsupported``,不用空 edits 冒支持。
8. 编译后 validate + 离线 execute + 完整 target/center 诊断,再进
   可执行 pool;失败有结构化原因。
9. 对称对齐:全部枚举(有界);等价映射(同目标)合并保留;不同
   目标 ⇒ ambiguous(拒,竞争目标披露)。

W-V4b(S5b-stereo-dissolution-1,2026-10-10,mimo r28 E1-E3 评审方向
落地;**2026-10-10 R1 收口 S5B-V4B-01**:Codex v4b 复审 §4 P1 修正
+ mimo r33 S1/S2 采纳条件落地):**手性 sp3 碳中心随键级变化
sp3→sp2 消解**——消解谓词钉死(全部条件须满足):

- 0. **元素域 = C**(R1 新增,mimo r33 S2-b ②):非碳四面体中心
  (P/S/Si 等)在 single→double 后仍可为潜在立体中心(P 执行后
  Atom_Tetrahedral/未指派、S 为 Atom_TrigonalBipyramidal——Codex
  v4b §4 真实反例族),违背 r28 E2"执行+sanitize 后该原子非立体
  中心"放行条件;碳型是唯一有正控证据(二级醇→酮、bt0002#r0032)
  的放行面,其他元素维持 ``stereo_edit_unsupported`` 拒,扩展须
  新证据另轮;
- 1. lhs 原子带真四面体手性标签(CHI_TETRAHEDRAL_CW/CCW)∧ rhs 原子
  无手性声明(CHI_UNSPECIFIED)∧ 2. 该原子全部 lhs 键均为单键
  (sp3;双键/累积烯中央原子天然不满足 ⇒ 非四面体轴手性不消解)
  ∧ 3. 该原子涉及的全部键变化均为 change_bond_order 型(single→
  double/triple,无 form/break/芳香 —— 键表顺序不变,RDKit CW/CCW
  标签无重解读风险)∧ 4. 至少一个该型变化。满足 ⇒ 该 map 不落
  stereo_changed(手性 = 键级变化的派生属性,执行器 sanitize 自然
  结算);
- r28 反例族(**标签变化形态**,mimo r33 S1-a 限定)全拒:stereo_
  created(lhs 无声明→rhs 有声明)、仍为四面体中心的断/成键(有机
  磷/硫水解、SN2 型配体交换,标签变化书写)、非四面体标签、纯
  立体翻转(无键级变化)、非碳中心"标签消失"一律维持
  stereo_edit_unsupported。**同标签(及模板无声明而底物有声明的)
  断/成键落底物手性中心为已登记残留**(现状可编译、不落
  stereo_changed;守门扩展 = 执行后同源复核扩展到全部手性保留
  原子,列入下轮扩展选项,不在本轮);
- **执行后 rhs 立体同源复核**(E2-③;R1 双轴,mimo r33 S2-a/S2-b
  ①):消解开后的每例,执行产物该 map 上须同时过两轴——(a) 已
  指派四面体标签轴:标签 == rhs 声明(UNSPECIFIED);(b) **潜在
  立体中心轴**(R1 新增):该原子不得出现在执行产物 RDKit
  ``FindPotentialStereo`` 潜在立体中心清单(含未指派;任何原子轴
  类型)。复核 = 两轴合取,**已指派标签轴 ≠ 潜在立体中心感知**
  (旧单轴对"仍为潜在中心但未指派"是空窗,由 R1 ① 补上);任一
  轴不等、映射缺失或产物不可解析 ⇒ 结构化 ``stereo_derived_
  mismatch`` 拒(不靠"派生"假设放行;含显式氢手性底物的价态墙
  走 execution 诚实拒,不冒充消解);
- 机读诊断(E2-④):spec.compile 携带 ``stereo_dissolution_applied:
  maps``(下游统计多少命中依赖消解);E/Z 键立体**不在本放行面内、
  也不在拒面内**(检测面为原子四面体标签;执行产物 E/Z 未指定,
  对声明 E/Z 的参考走 cn_only 如实 miss——两头如实,不静默断言;
  参考亦无 E/Z 声明时 strict 相等成立,但该相等是**无声明对无
  声明**,非"E/Z 已核一致"——mimo r33 S1-b)。

版本:s5b-compiler-3(R1:消解许可收窄 + 复核双轴扩展,公共编译
判据链行为变化)。编译失败一律返回 ``{"status": "unsupported",
"reason": <稳定机读码>, "detail": {...}}``,不抛裸异常、不吞 Exception。

版本 s5b-compiler-4(T-G Step C2 重刀,R2' 解耦接线,2026-10-19):
**对齐从「全供体映射反应物整侧子结构匹配」放宽为中心锚定匹配**
(L1 变键/电荷/手性原子+新增原子保留锚;L2 两壳层:壳1=变键原子
邻域重原子边、壳2=邻域原子(N1)自身入射键集合;L3 其余差异豁免、
逐行机读披露)。规则落地:

- 中心查询与编译层中心枚举**共用同一实现**(``build_center_query`` /
  ``enumerate_center_alignments``);builder 侧准入 helper
  ``center_anchor_probe``(F5)复用同源查询构造;
- **歧义硬规则(D-1 收严)**:全部语义允许候选 M(=两壳层完整命中
  且预算未截断的全部匹配)**全量**执行冻结编辑段,按净产物目标归并
  ——唯一目标 ⇒ compiled(取确定性 prefer 序首个;度全等子集 G 优先,
  prefer 只作排序不裁量准入);**≥2 个不同可执行目标 ⇒ 结构化
  ``ambiguous_alignment`` 拒绝(必须,机读 ``competing_targets`` 只
  补充)**;被 prefer 排序靠后的非全等候选不得跳过;
- **预算截断诚实处置**:M 枚举触 ``_COMPILE_ALIGNMENT_LIMIT`` ⇒
  结构化 ``alignment_limit_exceeded`` 拒 + 未核范围机读披露
  (``truncation_axis``/``n_matches_at_limit``),不得称唯一目标已证;
- 中心为空变换(无 L1:removed-only 等)⇒ ``center_empty:*`` 结构化
  拒(D-3 登记:删除型中心定义另轮);
- L3 披露(``spec.compile.c2_l3_disclosure``):豁免原子/边数、异
  元素/手性/电荷旗标、H 计数差旗标(纯 H 差异 L2 不可见轴,如实
  披露;H 数不纳入查询,与判读 v3.2 H± 豁免同盲区);
- ``template_elements_fit`` 判据**原样保留**,角色降级为 builder
  侧路由真源(F1:决定是否尝试供给);**编译层准入=中心可落位**
  (与中心枚举同源),整侧元素账不再是编译的必要条件。
"""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem, RDLogger

from ..services.atom_tool import (
    ATOM_ID_RE,
    execute_edits,
    render,
    validate_edits,
)

RDLogger.DisableLog("rdApp.*")

S5B_COMPILER_VERSION = "s5b-compiler-4"

# 对齐枚举显式上限(超过 ⇒ truncated,不得把截断集合当唯一对齐;
# 与 donor_applicability._ALIGNMENT_ENUM_LIMIT 同纪律,独立常量:
# 编译入口预算更小 —— 池编译是每题逐模板调用)
_COMPILE_ALIGNMENT_LIMIT = 64

# 中心查询壳层数(T-G C2:两壳层强读法 L2;壳1=变键原子邻域重原子边,
# 壳2=邻域原子(N1)自身的入射键集合亦须命中)
_CENTER_QUERY_SHELL = 2

# 推断映射(recorded 源,无原生映射)的枚举上限:超过 ⇒ 歧义披露拒绝
_INFER_ENUM_LIMIT = 200

_NONE = "none"
_AROMATIC = "aromatic"
_ORDER_NAME = {
    Chem.BondType.SINGLE: "single",
    Chem.BondType.DOUBLE: "double",
    Chem.BondType.TRIPLE: "triple",
    Chem.BondType.AROMATIC: _AROMATIC,
}
_ORDER_OF_TOKEN = {
    "single": Chem.BondType.SINGLE,
    "double": Chem.BondType.DOUBLE,
    "triple": Chem.BondType.TRIPLE,
}


class S5bCompileError(ValueError):
    """编译契约违反(fail-closed;reason 稳定机读码)。"""

    def __init__(self, reason: str, message: str, detail: dict | None = None):
        super().__init__(f"{reason}:{message}")
        self.reason = reason
        self.detail = detail or {}


def _unsupported(reason: str, detail: dict | None = None) -> dict:
    return {"status": "unsupported", "reason": reason,
            "detail": detail or {}, "compiler_version":
            S5B_COMPILER_VERSION}


def template_elements_fit(mapped_lhs: str, substrate_smiles: str) -> bool:
    """模板 lhs 元素多重集 ⊆ 当前底物元素多重集(**判据原样保留**)。

    **角色(s5b-compiler-4 / T-G C2 R2' 起)——builder 侧路由真源(F1),
    不再是编译层准入判据**:

    - builder(``default_pool_provider`` analog 通道)用本 verdict 决定
      **是否尝试伴生供给**(过 ⇒ 直编分支不加袋;拒 ⇒ 供给分支),
      即「路由真源」;该位置判据一字不改、原样冻结;
    - **编译层准入 = 中心可落位**(``center_anchor_probe`` /
      ``enumerate_center_alignments`` 的中心锚定匹配,判据单一来源
      与中心枚举同源)—— 整侧元素账不再是对齐的必要条件;本 helper
      在 builder 侧仍**只省预算/定路由**,不再承诺「不满足 ⇒ 编译必
      no_alignment」的单向蕴含(中心命中可编译而元素账短,这正是
      C2 647 面收益的来源);
    - 轻刀选项 B(改本函数判据为「主份元素 ⊆ 底物⊕袋」)= 另轮,且
      会改 F1 路由真源 ⇒ 与 R2' 互斥(同一函数、同一版本键内不得
      同时接线)。

    解析失败 ⇒ True(路由门不额外拦坏输入;坏输入由编译层结构化拒)。
    """
    try:
        lhs = Chem.MolFromSmiles(str(mapped_lhs or ""))
        sub = Chem.MolFromSmiles(str(substrate_smiles or ""))
        if lhs is None or sub is None:
            return True
    except Exception:
        return True
    lhs_elems: dict = {}
    for a in lhs.GetAtoms():
        lhs_elems[a.GetSymbol()] = lhs_elems.get(a.GetSymbol(), 0) + 1
    sub_elems: dict = {}
    for a in sub.GetAtoms():
        sub_elems[a.GetSymbol()] = sub_elems.get(a.GetSymbol(), 0) + 1
    return all(lhs_elems[e] <= sub_elems.get(e, 0) for e in lhs_elems)


def net_reaction_signature(spec: dict) -> tuple:
    """独特净反应签名(W3/W4 共用去重键):净产品集合严格身份多重集。

    - 同净产物集合 + step_scope(net_reaction)⇒ 同一独特净反应槽;
      不同反应/条件/角色不会只因主产物或 CN 一样被误并(签名取全部
      产物组分的**严格**身份,电荷/立体/组分差异都改变签名);
    - 解析失败按原始串兜底(确定性,不猜;不可解析串不同即不同槽);
    - **W-D2(s5b-corpus-retrieval-3 消费面)**:spec 携带
      declared_copy_components(声明式拷贝组分)时,拷贝组分进签名
      ——净反应签名含共底物贡献,corpus 拷贝型 spec 与整串/其他
      通道 spec 同净反应时合并留痕不双占槽(设计 §四.3.5/PC-3);
      无拷贝字段的 spec 签名**逐字节不变**(EAWAG/整串路径零影响;
      编译判据零触碰——W-D2 当期版本为 s5b-compiler-3,后续
      s5b-compiler-4(T-G C2)仍不触碰本函数)。
    """
    parts = [str(spec.get("product_smiles") or "")] + \
        [str(c) for c in (spec.get("coproducts") or [])] + \
        [str(e.get("smiles")) for e in
         (spec.get("declared_copy_components") or [])]

    def _ident(s: str) -> str:
        try:
            from .chemstate import strict_identity_of

            return strict_identity_of(s) or s
        except Exception:
            return s

    return tuple(sorted(_ident(p) for p in parts))


@dataclass
class _ParsedSide:
    """单侧(map 化)解析事实:map 号 → 原子对象/idx。"""

    mol: object
    maps: dict          # map_no -> atom idx


def _parse_mapped_side(smiles: str, side: str) -> _ParsedSide:
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        raise S5bCompileError(
            f"{side}_unparseable",
            f"模板 {side} 不可解析:{smiles!r}",
            {"side": side, "smiles": str(smiles)[:300]})
    maps: dict[int, int] = {}
    for atom in mol.GetAtoms():
        n = atom.GetAtomMapNum()
        if n:
            if n in maps:
                raise S5bCompileError(
                    f"duplicate_map_no:{n}:{side}",
                    f"模板 {side} 重复 map 号 {n}(map 号联结需双侧唯一)",
                    {"side": side, "map_no": n})
            maps[n] = atom.GetIdx()
    return _ParsedSide(mol=mol, maps=maps)


def _order_token(bond) -> str:
    if bond is None:
        return _NONE
    return _ORDER_NAME.get(bond.GetBondType(), str(bond.GetBondType()))


def _bond_table_by_map(mol, maps: dict) -> dict:
    """键表:map 对 (frozenset) → 芳香形式键级 token。"""
    out: dict = {}
    for b in mol.GetBonds():
        ni = b.GetBeginAtom().GetAtomMapNum()
        nj = b.GetEndAtom().GetAtomMapNum()
        if ni and nj:
            out[frozenset((ni, nj))] = _order_token(b)
    return out


def _kekulized_copy(mol):
    """与 execute_edits 同一事实源的 kekulé 化副本(失败按芳香形继续,
    键级前提将如实失配)。"""
    copy = Chem.Mol(mol)
    try:
        Chem.Kekulize(copy, clearAromaticFlags=True)
    except Exception:
        pass
    return copy


# ---------------------------------------------------------------- 供体变换表


def extract_mapped_transform(mapped_lhs: str, mapped_rhs: str) -> dict:
    """映射模板双侧 → 变化表(map 号联结;W1 #1/#5)。

    - retained/added/removed:map 号集合(added = rhs 独有,removed =
      lhs 独有 —— 离去组分断键后留在多组分产物);
    - bond_changes:[{map1, map2, order_lhs, order_rhs}](芳香形式 token;
      aromatic≡aromatic 不入表);
    - charge_changed / stereo_changed:保留原子上电荷/四面体手性差异
      (现编辑协议不支持 ⇒ 编译侧 unsupported 判据,见 _compile_edits);
    - stereo_dissolved(W-V4b;R1 元素域收窄为碳):消解开的手性
      map(手性 sp3 **碳**中心随 single→double/triple 键级变化消解,
      谓词 _is_stereo_dissolution 钉死;不落 stereo_changed,执行后
      同源复核(双轴:已指派标签 + 潜在立体中心清单));
    - 坏引用 = 键的 map 端点不在该侧 map 集(结构损坏)⇒ 拒。
    """
    lhs = _parse_mapped_side(mapped_lhs, "lhs")
    rhs = _parse_mapped_side(mapped_rhs, "rhs")
    if not lhs.maps or not rhs.maps:
        raise S5bCompileError(
            "transform_unmapped", "模板双侧均须带 atom map 号", {})
    # 半映射键(一端带 map 一端不带)合法:未映射原子是模板上下文
    # (对齐须匹配但不参与键差);键差表只收双侧均带 map 的键。
    retained_maps = sorted(set(lhs.maps) & set(rhs.maps))
    for n in retained_maps:
        la = lhs.mol.GetAtomWithIdx(lhs.maps[n])
        ra = rhs.mol.GetAtomWithIdx(rhs.maps[n])
        if la.GetSymbol() != ra.GetSymbol():
            raise S5bCompileError(
                f"map_element_changed:{n}",
                f"保留原子 map {n} 元素改变 {la.GetSymbol()}→"
                f"{ra.GetSymbol()}(map 号联结的元素守恒拒)",
                {"map_no": n, "lhs_element": la.GetSymbol(),
                 "rhs_element": ra.GetSymbol()})
    lb = _bond_table_by_map(lhs.mol, lhs.maps)
    rb = _bond_table_by_map(rhs.mol, rhs.maps)
    bond_changes = []
    for pair in sorted({tuple(sorted(p)) for p in set(lb) | set(rb)},
                       key=lambda p: (p[0], p[1])):
        key = frozenset(pair)
        ol, orr = lb.get(key, _NONE), rb.get(key, _NONE)
        if ol == orr:
            continue
        if ol == _AROMATIC and orr == _AROMATIC:
            continue  # 不可能(相等才跳过),防御
        bond_changes.append({"map1": pair[0], "map2": pair[1],
                             "order_lhs": ol, "order_rhs": orr})
    charge_changed, stereo_changed = [], []
    stereo_dissolved: list[int] = []   # W-V4b:消解候选(见下)
    for n in retained_maps:
        la = lhs.mol.GetAtomWithIdx(lhs.maps[n])
        ra = rhs.mol.GetAtomWithIdx(rhs.maps[n])
        if la.GetFormalCharge() != ra.GetFormalCharge():
            charge_changed.append(n)
        if _chiral_token(la) != _chiral_token(ra):
            if _is_stereo_dissolution(lhs, rhs, n, bond_changes):
                stereo_dissolved.append(n)
            else:
                stereo_changed.append(n)
    added = sorted(set(rhs.maps) - set(lhs.maps))
    removed = sorted(set(lhs.maps) - set(rhs.maps))
    if not (bond_changes or added or removed or charge_changed
            or stereo_changed or stereo_dissolved):
        raise S5bCompileError(
            "transform_no_change",
            "模板双侧在 map 联结后无净变化(空 edits 不能冒支持)",
            {})
    return {
        "lhs": lhs, "rhs": rhs,
        "retained_maps": retained_maps,
        "added_maps": added,
        "removed_maps": removed,
        "bond_changes": bond_changes,
        "charge_changed_maps": charge_changed,
        "stereo_changed_maps": stereo_changed,
        # W-V4b(S5b-stereo-dissolution-1):消解开的手性 map(不落
        # stereo_changed;执行后同源复核见 _compile_donor_template_impl)
        "stereo_dissolved_maps": stereo_dissolved,
    }


_TETRAHEDRAL_TAGS = (
    Chem.ChiralType.CHI_TETRAHEDRAL_CW,
    Chem.ChiralType.CHI_TETRAHEDRAL_CCW,
)
_UNSPECIFIED_TAG = Chem.ChiralType.CHI_UNSPECIFIED

# R1(S5B-V4B-01,mimo r33 S2-b ②):消解元素域 = 碳。非碳四面体
# 中心(P/S/Si 等)在 single→double 后仍可为潜在立体中心(P:
# Atom_Tetrahedral/未指派;S:Atom_TrigonalBipyramidal —— Codex v4b
# 复审 §4 真实反例族),违背 r28 E2"执行+sanitize 后该原子非立体
# 中心"放行条件;碳型是唯一有正控证据的放行面(执行后 sp2 碳不在
# FindPotentialStereo 清单),其他元素的扩展须新证据另轮预注册。
_DISSOLUTION_ELEMENTS = ("C",)

# R1(①复核轴):FindPotentialStereo 只认**原子轴**类型 —— 键轴条目
# (Bond_Double = E/Z、atropisomer)的 centeredOn 是键索引,与原子
# 索引数值可能碰撞(合成探针实测),不属"该原子潜在立体中心"轴。
_ATOM_STEREO_TYPES = (
    Chem.StereoType.Atom_Tetrahedral,
    Chem.StereoType.Atom_SquarePlanar,
    Chem.StereoType.Atom_TrigonalBipyramidal,
    Chem.StereoType.Atom_Octahedral,
)


def _is_stereo_dissolution(lhs, rhs, n: int, bond_changes: list) -> bool:
    """P1 消解谓词(mimo r28 E2 窄化版;钉死,逐条件):

    0. **元素域 = 碳**(R1):lhs/rhs 元素守恒已由 map 号联结守恒门
       保证;非碳四面体中心不消解(P/S/Si 反例族见
       _DISSOLUTION_ELEMENTS 注释);
    1. lhs 原子真四面体手性(CW/CCW)∧ rhs 原子无手性声明
       (UNSPECIFIED)——stereo_created(反向)与非四面体标签不进;
    2. 该原子全部 lhs 键均单键(sp3;芳香/双键/叁键/累积烯中央原子
       天然不满足 ⇒ 非四面体中心不消解,r28 E1-4);
    3. 该原子涉及的全部键变化均为 change_bond_order 型(single→
       double/triple):form/break 落在现存立体中心一律维持
       unsupported(键表顺序不变才无 CW/CCW 重解读风险,r28 E1-2
       有机磷/硫、SN2 型配体交换);
    4. 至少一个该型变化(纯立体翻转无键级变化不消解)。
    """
    la = lhs.mol.GetAtomWithIdx(lhs.maps[n])
    ra = rhs.mol.GetAtomWithIdx(rhs.maps[n])
    if la.GetSymbol() not in _DISSOLUTION_ELEMENTS:
        return False
    if la.GetChiralTag() not in _TETRAHEDRAL_TAGS:
        return False
    if ra.GetChiralTag() != _UNSPECIFIED_TAG:
        return False
    for b in lhs.mol.GetBonds():
        if n in (b.GetBeginAtom().GetAtomMapNum(),
                 b.GetEndAtom().GetAtomMapNum()) \
                and _order_token(b) != "single":
            return False  # 非 sp3(sp2/芳香/累积烯中央原子)
    n_changes = 0
    for ch in bond_changes:
        if n not in (int(ch["map1"]), int(ch["map2"])):
            continue
        if ch["order_lhs"] != "single" \
                or ch["order_rhs"] not in ("double", "triple"):
            return False  # 断键/成键/芳香/降阶落在本原子 ⇒ 不消解
        n_changes += 1
    return n_changes >= 1


def _executed_stereo_state(execution: dict, atom_id: str):
    """执行产物在指定原子(当前 ID)的立体状态(R1 双轴)。

    返回 ``(tag, potential)``:

    - ``tag`` = 已指派四面体手性标签(原子缺席/产物不可解析/映射
      缺失 ⇒ None —— 失配语义由调用方 fail-closed 处理);
    - ``potential`` = 执行产物 RDKit ``FindPotentialStereo`` 报告的
      **该原子**潜在立体类型(不在清单 ⇒ None;**仅限原子轴类型**
      —— 键轴条目(Bond_Double/E/Z、atropisomer)的 centeredOn 是
      键索引,与原子索引数值可能碰撞,不属本轴)。两轴独立:
      UNSPECIFIED 标签不排除潜在中心(未指派形态),非潜在中心也
      不排除残留标签(执行器/序列化异常防御)。

    经 product_mapped_smiles(映射号 = 执行图 idx+1,随 canonical
    排序穿越序列化/重解析,S0 取证 §6-2 免疫重排)还原 ID↔原子。"""
    idx = (execution.get("atom_id_map") or {}).get(str(atom_id))
    if idx is None:
        return None, None
    mapped = Chem.MolFromSmiles(
        str(execution.get("product_mapped_smiles") or ""))
    if mapped is None:
        return None, None
    target_idx = None
    for atom in mapped.GetAtoms():
        if atom.GetAtomMapNum() == int(idx) + 1:
            target_idx = atom.GetIdx()
            break
    if target_idx is None:
        return None, None
    tag = mapped.GetAtomWithIdx(target_idx).GetChiralTag()
    potential = None
    try:
        for info in Chem.FindPotentialStereo(mapped):
            if info.centeredOn == target_idx \
                    and info.type in _ATOM_STEREO_TYPES:
                potential = str(info.type)
                break
    except Exception:
        # fail-closed:潜在中心轴不可判 ⇒ 按失配报告,不放行
        potential = "potential_check_error"
    return tag, potential


def _stereo_dissolution_mismatch(
        execution: dict, map_to_current_id: dict,
        stereo_dissolved: list) -> list:
    """W-V4b 执行后 rhs 立体同源复核(mimo r28 E2-③;R1 双轴)。

    消解开的手性 map:执行产物该原子须同时过两轴——(a) 已指派
    四面体标签 == rhs 模板声明(消解谓词已钉 rhs = CHI_UNSPECIFIED);
    (b) 该原子不在执行产物 RDKit ``FindPotentialStereo`` 潜在立体
    中心清单(**含未指派**;任何原子轴类型——"无已指派标签"不
    等于"非立体中心",mimo r28 E2 原文口径)。返回失配清单
    ``[(map, state)]``——空清单 = 复核通过;映射缺失/产物不可解析/
    潜在中心轴不可判也按失配报告(不靠"派生"假设放行)。state:
    标签轴失配 ⇒ ``str(tag)``;潜在中心轴失配 ⇒
    ``potential:<类型>``(如 ``potential:Atom_Tetrahedral``)。"""
    mismatched: list = []
    for m in stereo_dissolved:
        cid = map_to_current_id.get(int(m))
        if cid is None:
            mismatched.append((int(m), "None"))
            continue
        tag, potential = _executed_stereo_state(execution, str(cid))
        if tag is None or tag != _UNSPECIFIED_TAG:
            mismatched.append((int(m), str(tag)))
        elif potential is not None:
            mismatched.append((int(m), f"potential:{potential}"))
    return mismatched


def _chiral_token(atom) -> str:
    tag = atom.GetChiralTag()
    # 仅四面体手性可比较(R4-07 语义:非四面体不支持 ⇒ 两轴 unknown,
    # 编译侧按不支持处理由 stereo_changed 判定覆盖 —— 非四面体标签在
    # lhs/rhs 间不同时同样落入 stereo_changed)
    return str(tag)


# ---------------------------------------------------------------- 中心锚定对齐
# (T-G Step C2 重刀,s5b-compiler-4;R2' 解耦接线:builder F5 准入 helper
#  与编译层中心枚举共用本节实现——判据单一来源,不得各自另建)


def _atom_id_for_idx(current, idx: int) -> str | None:
    return current.idx_atom_map.get(int(idx))


def l1_maps_of_transform(transform: dict) -> list[int]:
    """L1 集合 = 变键边两端 map(**限 lhs 侧存在者**)∪ 电荷/手性变化
    map ∪ 新增原子的保留锚(其 rhs 邻接保留原子)。判读 v3.2:中心=
    变键原子;电荷/手性变化原子亦为被编辑原子(编辑层结构化
    unsupported 保持不变,中心须落位);「两端原子**在执行输入中须
    存在**」⇒ 新增原子自身的 map(rhs 独有)不入 L1(其存在性由
    ``_place_new_atoms`` 落位链负责,不由查询要求)。消解开的手性
    map 必然是变键边端点(消解谓词要求 ≥1 键级变化落在该原子),
    已由 bond_changes 覆盖。"""
    l1: set[int] = set()
    lhs_maps = set(transform["lhs"].maps)
    for ch in transform["bond_changes"]:
        for x in (int(ch["map1"]), int(ch["map2"])):
            if x in lhs_maps:
                l1.add(x)
    for m in (transform.get("charge_changed_maps") or []):
        l1.add(int(m))
    for m in (transform.get("stereo_changed_maps") or []):
        l1.add(int(m))
    added = set(transform["added_maps"])
    if added:
        rhs = transform["rhs"]
        for b in rhs.mol.GetBonds():
            ni = b.GetBeginAtom().GetAtomMapNum()
            nj = b.GetEndAtom().GetAtomMapNum()
            for x, y in ((ni, nj), (nj, ni)):
                if x in added and y and y not in added:
                    l1.add(int(y))
    return sorted(l1)


def center_empty_reason(transform: dict) -> str:
    """无 L1 的变换形态机读码(D-3:删除型中心定义另轮,本刀结构化拒)。
    与 no_alignment「中心不落位」机读区分(§8.1-6 披露义务)。"""
    kinds = []
    if transform.get("removed_maps"):
        kinds.append("removed_only")
    if transform.get("charge_changed_maps"):
        kinds.append("charge_only")
    if transform.get("stereo_changed_maps"):
        kinds.append("stereo_only")
    if transform.get("stereo_dissolved_maps"):
        kinds.append("stereo_dissolved_only")
    if transform.get("added_maps"):
        kinds.append("added_without_anchor")
    return "center_empty:" + ("+".join(kinds) or "unclassified")


def _center_keep_atoms(lhs_mol, l1_idx: set[int], shell: int):
    """中心查询的原子/键保留集(同位移植探针原型;L2 两壳层强读法)。

    - 壳1(L1 入射键):``near`` = L1 原子;``keep_atoms`` 并 L1 与
      其入射键全部端点(邻域原子元素级在查询中原样保留);
    - 壳2:``near`` 再并 L1 的直接邻居(N1),``keep_atoms`` 再并
      与 near 相连的全部键端点(N1 自身入射键集合亦须命中;N1 的
      外围重边按「至少一端在 near」进入查询);
    - 键集 = 至少一端落在 ``near`` 且两端均保留的 lhs 键(键级原样;
      芳香键按芳香语义参与匹配——芳香正向要求,非原子旗标精确
      双向断言,见 §8.1-7 披露口径)。
    返回 ``(near, keep_atoms, keep_bonds)``(lhs 原子 idx 空间)。
    """
    near: set[int] = set(l1_idx)
    keep_atoms: set[int] = set(l1_idx)
    if shell >= 2:
        d1: set[int] = set()
        for b in lhs_mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            if i in near or j in near:
                d1.add(i)
                d1.add(j)
        near |= d1
        for b in lhs_mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            if i in near or j in near:
                keep_atoms.add(i)
                keep_atoms.add(j)
    else:
        for b in lhs_mol.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            if i in near or j in near:
                keep_atoms.add(i)
                keep_atoms.add(j)
    keep_bonds = []
    for b in lhs_mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if (i in near or j in near) and i in keep_atoms \
                and j in keep_atoms:
            keep_bonds.append((i, j, b.GetBondType()))
    return near, keep_atoms, keep_bonds


def build_center_query(lhs_mol, lhs_maps: dict, l1_maps: list[int],
                       shell: int = _CENTER_QUERY_SHELL):
    """中心查询 = 重原子骨架(元素 + 芳香旗标 + 键级)。

    与判读 v3.2 修订 1「比较前强制规范化;中心只比重原子骨架;L2 =
    变键原子其他重原子边(缺失侧)」同构:**不复制 H 数/形式电荷/
    noImplicit**(H± 与质子化按 v3.2 豁免;电荷变化由编辑层判)。
    L1 原子即使无键(孤立离子)也入查询。
    返回 ``(query_mol, {map_no: query_idx})``;qidx 覆盖**全部命中
    查询的 lhs map**(L1 与壳层原子——映射覆盖 = 查询覆盖,L3 不映射,
    由 c2_l3_disclosure 披露),编辑段消费 L1 端点(全部含于其中)。
    """
    l1_idx = {int(lhs_maps[int(m)]) for m in l1_maps
              if int(m) in lhs_maps}
    _near, keep_atoms, keep_bonds = _center_keep_atoms(lhs_mol, l1_idx,
                                                       shell)
    rw = Chem.RWMol()
    idx_map: dict[int, int] = {}
    for old in sorted(keep_atoms):
        src = lhs_mol.GetAtomWithIdx(old)
        na = Chem.Atom(src.GetAtomicNum())
        na.SetIsAromatic(src.GetIsAromatic())
        idx_map[old] = rw.AddAtom(na)
    for i, j, bt in keep_bonds:
        rw.AddBond(idx_map[i], idx_map[j], bt)
    q = rw.GetMol()
    qidx_of_map = {int(m): idx_map[int(lhs_maps[int(m)])]
                   for m in lhs_maps
                   if int(lhs_maps[int(m)]) in idx_map}
    return q, qidx_of_map


def enumerate_center_alignments(lhs_mol, lhs_maps, l1_maps, substrate_arom,
                                shell: int = _CENTER_QUERY_SHELL):
    """中心锚定对齐枚举(有界;s5b-compiler-4 替换全供体匹配)。

    返回 ``(matches, qidx_of_map, truncated)``:matches = RDKit 信封
    序的命中元组(确定性;uniquify=False、useChirality=False、显式
    maxMatches);truncated = 命中数触 ``_COMPILE_ALIGNMENT_LIMIT``
    (截断集合不得当唯一对齐;调用方结构化拒 + 未核披露)。
    """
    q, qidx_of_map = build_center_query(lhs_mol, lhs_maps, l1_maps,
                                        shell=shell)
    matches = substrate_arom.GetSubstructMatches(
        q, uniquify=False, useChirality=False,
        maxMatches=_COMPILE_ALIGNMENT_LIMIT)
    return list(matches), qidx_of_map, \
        len(matches) >= _COMPILE_ALIGNMENT_LIMIT


def center_anchor_probe(mapped_lhs: str, mapped_rhs: str,
                        substrate_smiles: str) -> dict:
    """F5 中心准入 helper(R2' 解耦接线;builder 侧调用)。

    与编译层中心枚举**共用同一实现**(``build_center_query``/
    ``enumerate_center_alignments``):对**已冻结执行输入**(F4)判定
    「中心可落位」。返回::

        {"status": "present" | "absent" | "defer",
         "reason": <机读码>, "detail": {...},
         "compiler_version": S5B_COMPILER_VERSION}

    语义(与编译层拒因同源;「省预算不改结果口径」不变量):

    - ``absent``(中心查询零命中)⇒ 编译层必 ``no_alignment`` ——
      唯一可短路的拒;builder 直接记 no_alignment、不发编译;
    - ``defer``(变换提取异常 / 中心为空 / 截断 / 底物不可解析)⇒
      编译层将给**其它**稳定拒因(或截断拒),不得冒名 no_alignment
      ——builder 照常发编译,由编译层如实出因;
    - ``present`` ⇒ 送编译(F5 只判准入,不保证编译/编辑层通过)。
    """
    try:
        transform = extract_mapped_transform(mapped_lhs, mapped_rhs)
    except S5bCompileError as exc:
        return {"status": "defer", "reason": exc.reason,
                "detail": {"stage": "transform"},
                "compiler_version": S5B_COMPILER_VERSION}
    except Exception as exc:  # noqa: BLE001 —— 与编译层同形如实披露
        return {"status": "defer",
                "reason": f"internal_error:{type(exc).__name__}",
                "detail": {"stage": "transform"},
                "compiler_version": S5B_COMPILER_VERSION}
    l1_maps = l1_maps_of_transform(transform)
    if not l1_maps:
        return {"status": "defer", "reason": center_empty_reason(transform),
                "detail": {"stage": "center"},
                "compiler_version": S5B_COMPILER_VERSION}
    try:
        _current, arom, _kek = _current_base(substrate_smiles)
    except S5bCompileError as exc:
        return {"status": "defer", "reason": exc.reason,
                "detail": {"stage": "substrate"},
                "compiler_version": S5B_COMPILER_VERSION}
    except Exception as exc:  # noqa: BLE001
        return {"status": "defer",
                "reason": f"internal_error:{type(exc).__name__}",
                "detail": {"stage": "substrate"},
                "compiler_version": S5B_COMPILER_VERSION}
    matches, _qidx, truncated = enumerate_center_alignments(
        transform["lhs"].mol, transform["lhs"].maps, l1_maps, arom)
    if truncated:
        return {"status": "defer", "reason": "alignment_limit_exceeded",
                "detail": {"stage": "align",
                           "n_matches_at_limit": len(matches),
                           "truncation_axis": "center_match_enumeration"},
                "compiler_version": S5B_COMPILER_VERSION}
    if not matches:
        return {"status": "absent", "reason": "no_alignment",
                "detail": {"stage": "align", "center_presence_matches": 0},
                "compiler_version": S5B_COMPILER_VERSION}
    return {"status": "present", "reason": "",
            "detail": {"stage": "align",
                       "center_presence_matches": len(matches)},
            "compiler_version": S5B_COMPILER_VERSION}


def _l3_disclosure(lhs_mol, lhs_maps: dict, l1_maps: list[int],
                   match, qidx_of_map: dict, substrate_arom,
                   shell: int = _CENTER_QUERY_SHELL) -> dict:
    """L3 豁免面逐行机读披露(交付义务:未披露=不发货;§3.2 风险 3)。

    - 豁免原子 = lhs 中不在中心查询保留集的原子(map 号清单);
    - 豁免边数 = 至少一端豁免的 lhs 键数;
    - 异元素/手性/电荷旗标 = 豁免原子是否含非碳元素、四面体手性
      标签、形式电荷;
    - **H 计数差旗标**(§8.1-2):被匹配原子(查询覆盖)的模板 H 总数
      与目标 H 总数不一致 ⇒ True(纯 H 差异 L2 不可见的如实披露轴;
      本刀不把 H 纳入查询)。
    """
    l1_idx = {int(lhs_maps[int(m)]) for m in l1_maps
              if int(m) in lhs_maps}
    _near, keep_atoms, _kb = _center_keep_atoms(lhs_mol, l1_idx, shell)
    exempt_maps: list[int] = []
    has_hetero = has_chir = has_charge = False
    for m, idx in lhs_maps.items():
        if int(idx) in keep_atoms:
            continue
        exempt_maps.append(int(m))
        atom = lhs_mol.GetAtomWithIdx(int(idx))
        if atom.GetAtomicNum() not in (1, 6):
            has_hetero = True
        if atom.GetChiralTag() not in (Chem.ChiralType.CHI_UNSPECIFIED,):
            has_chir = True
        if atom.GetFormalCharge() != 0:
            has_charge = True
    n_exempt_bonds = 0
    for b in lhs_mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i not in keep_atoms or j not in keep_atoms:
            n_exempt_bonds += 1
    n_h_diff = 0
    for m, qi in qidx_of_map.items():
        t_idx = match[qi]
        a_tpl = lhs_mol.GetAtomWithIdx(int(lhs_maps[int(m)]))
        a_tgt = substrate_arom.GetAtomWithIdx(int(t_idx))
        if a_tpl.GetTotalNumHs() != a_tgt.GetTotalNumHs():
            n_h_diff += 1
    return {
        "exempt_atoms_maps": sorted(exempt_maps),
        "n_exempt_atoms": len(exempt_maps),
        "n_exempt_bonds": n_exempt_bonds,
        "has_hetero_element": has_hetero,
        "has_chirality": has_chir,
        "has_charge": has_charge,
        "h_count_diff": n_h_diff > 0,
        "n_h_count_diff_atoms": n_h_diff,
    }


# ---------------------------------------------------------------- 编辑编译


def _current_base(substrate_smiles: str):
    """一次确定的 current 执行 base(W1 #4):渲染(ID 图)+ 芳香形 +
    kekulé 形(与 execute_edits 同一事实源:execute_edits 内部
    Kekulize(clearAromaticFlags=True) 后按 render 的 ID→idx 操作)。"""
    current = render(substrate_smiles, "S")
    arom = Chem.MolFromSmiles(substrate_smiles)
    if arom is None:  # render 已拒不可解析;防御
        raise S5bCompileError(
            "substrate_unparseable",
            f"当前底物不可解析:{substrate_smiles!r}", {})
    kek = _kekulized_copy(arom)
    return current, arom, kek


def _current_bond_token(kek, current, a1: str, a2: str) -> str | None:
    """当前图上 (ID,ID) 键的 kekulé 键级 token(执行器将看到的值)。"""
    i1 = current.atom_id_map.get(a1)
    i2 = current.atom_id_map.get(a2)
    if i1 is None or i2 is None:
        return None
    return _order_token(kek.GetBondBetweenAtoms(int(i1), int(i2)))


def _current_bond_aromatic(arom, current, a1: str, a2: str) -> bool:
    i1 = current.atom_id_map.get(a1)
    i2 = current.atom_id_map.get(a2)
    if i1 is None or i2 is None:
        return False
    b = arom.GetBondBetweenAtoms(int(i1), int(i2))
    return bool(b is not None and b.GetIsAromatic())


def _new_atom_id(element: str, taken: set[str]) -> str:
    """新增原子 ID:``SN_<elem>_<n>``(W1 #6/组4 正控)。

    合法性:匹配 ATOM_ID_RE(name=``SN``,elem 内嵌元素,n 数字;ID 内
    嵌元素与 add_atom.element 一致);``SN`` 前缀与当前底物渲染
    (name=``S``)天然不冲突;n 递增至不与 taken(当前渲染 ID + 已声明
    新 ID)冲突。旧实现 ``S_<Elem>_N<n>`` 不匹配 ATOM_ID_RE(组4 坏
    格式负控),已废弃。
    """
    n = 1
    while True:
        candidate = f"SN_{element}_{n}"
        m = ATOM_ID_RE.match(candidate)
        if m is not None and m.group(0) == candidate \
                and m.group("elem") == str(element) \
                and candidate not in taken:
            return candidate
        n += 1
        if n > 10_000:  # 防御:实际不可能触达
            raise S5bCompileError(
                "new_atom_id_exhausted",
                "新增原子 ID 序号耗尽(防御性上限;内部错误)",
                {"element": str(element)})


def _compile_edits(transform: dict, current, arom, kek,
                   map_to_current_id: dict) -> list[dict]:
    """变化表 + 对齐 → 当前 ID 编辑协议列表(W1 #2/#4/#6/#7)。

    - from_order 从 current kekulé 图读;模板 lhs 词面仅作上下文一致性
      核验(芳香语义:donor aromatic ⇒ current 须 aromatic;显式键级 ⇒
      current 须同键级);
    - to_order:rhs 显式键级直用;rhs aromatic ⇒ 取 rhs kekulé 形的
      对应键级(芳香化经显式 Kekulé 落图,执行后 sanitize 重感知芳香);
    - 去芳香化(lhs aromatic → rhs 显式):该芳香环系全部键一起落显式
      键级(单键改双/单落位;部分去芳香化 = 化学不一致 ⇒ 拒);
    - add_atom 自动接 single 锚定键;新键为 double/triple ⇒ 先落位
      (single)再 change_bond_order;既有原子间新键同规则(form single
      → change);不重复 form 同键;
    - 电荷/手性变化:现协议不支持 ⇒ 结构化 unsupported(不用空 edits
      冒支持;W1 #7)。
    """
    lhs, rhs = transform["lhs"], transform["rhs"]
    reasons: list[str] = []
    edits: list[dict] = []

    # ---- W1 #7:电荷/手性变化 ⇒ unsupported(协议 v2 无对应 op) ----
    # W-V4b:stereo_changed_maps 已剔除消解开的手性 map(sp3→sp2 派生
    # 属性;谓词见 _is_stereo_dissolution)——消解例不经立体 op,由
    # 键级编辑 + 执行器 sanitize 自然结算;执行后同源复核在编译主入口
    # (stereo_derived_mismatch),不在此处。
    if transform["charge_changed_maps"]:
        raise S5bCompileError(
            "charge_edit_unsupported",
            "供体变换含保留原子形式电荷变化(v43-editproto-2 无电荷 "
            "op;诚实 unsupported,不以空 edits 冒支持)",
            {"charge_changed_maps":
             [int(x) for x in transform["charge_changed_maps"]][:12]})
    if transform["stereo_changed_maps"]:
        raise S5bCompileError(
            "stereo_edit_unsupported",
            "供体变换含保留原子手性变化(v43-editproto-2 无立体 op;"
            "诚实 unsupported)",
            {"stereo_changed_maps":
             [int(x) for x in transform["stereo_changed_maps"]][:12]})

    def cur_id_of(map_no: int) -> str:
        cid = map_to_current_id.get(int(map_no))
        if cid is None:
            raise S5bCompileError(
                f"alignment_missing_endpoint:map{map_no}",
                f"map {map_no} 无当前对齐(模板原子未落位)",
                {"map_no": int(map_no)})
        return cid

    # ---- 去芳香化环系闭合核验(W1 #5 后半) ----
    # lhs aromatic → rhs 显式的键:所属 lhs 芳香环系的全部 map 键必须
    # 同步变显式(化学上芳香环不可半去芳香)。部分去芳香 ⇒ 拒。
    dearomatize_pairs: dict = {}
    for ch in transform["bond_changes"]:
        if ch["order_lhs"] == _AROMATIC and ch["order_rhs"] != _NONE \
                and ch["order_rhs"] != _AROMATIC:
            dearomatize_pairs[frozenset((ch["map1"], ch["map2"]))] = ch
    if dearomatize_pairs:
        ring_members = _aromatic_ring_closure(lhs.mol, dearomatize_pairs)
        for key in ring_members:
            if key not in dearomatize_pairs:
                # 环系内其他键必须在 rhs 也是显式键级(整环去芳香)
                ch = {"map1": sorted(key)[0], "map2": sorted(key)[1],
                      "order_lhs": _AROMATIC,
                      "order_rhs": _rhs_order_of(rhs, key)}
                if ch["order_rhs"] in (_NONE, _AROMATIC):
                    raise S5bCompileError(
                        "partial_dearomatization_inconsistent",
                        "芳香环系仅部分键去芳香化(rhs 环内混 aromatic/"
                        "缺席;化学不一致,不猜补)",
                        {"ring_pairs": sorted(
                            tuple(sorted(k)) for k in ring_members)[:8]})
                transform["bond_changes"].append(ch)
                dearomatize_pairs[key] = ch

    # ---- 键级变化编辑 ----
    for ch in transform["bond_changes"]:
        m1, m2 = int(ch["map1"]), int(ch["map2"])
        ol, orr = ch["order_lhs"], ch["order_rhs"]
        if ol == _NONE:
            continue  # 新成键在新增原子落位后统一处理(下方)
        c1, c2 = cur_id_of(m1), cur_id_of(m2)
        if orr == _NONE:
            # 断键(离去组分不删除,断键后留多组分产物)
            edits.append({"op": "break_bond", "atom1": c1, "atom2": c2})
            continue
        # 上下文一致性(from_order 源 = 当前图;lhs 词面只作核验)
        cur_token = _current_bond_token(kek, current, c1, c2)
        if cur_token is None:
            raise S5bCompileError(
                f"center_bond_missing:map{m1}~map{m2}",
                f"变化键 map{m1}~map{m2} 在当前底物无对应键",
                {"map_pair": sorted((m1, m2))})
        if ol == _AROMATIC:
            if not _current_bond_aromatic(arom, current, c1, c2):
                raise S5bCompileError(
                    f"bond_context_mismatch:map{m1}~map{m2}:"
                    "donor_aromatic_current_aliphatic",
                    f"键 map{m1}~map{m2} 供体芳香而当前非芳香",
                    {"map_pair": sorted((m1, m2))})
        elif cur_token != ol:
            raise S5bCompileError(
                f"bond_order_mismatch:map{m1}~map{m2}:"
                f"current_{cur_token}_donor_{ol}",
                f"键 map{m1}~map{m2} 当前键级 {cur_token} 与供体 lhs "
                f"{ol} 不一致(from_order 上下文核验)",
                {"map_pair": sorted((m1, m2)),
                 "current": cur_token, "donor_lhs": ol})
        # to_order 决定
        if orr == _AROMATIC:
            to = _rhs_kek_order(rhs.mol, m1, m2)
        else:
            to = orr
        if to not in _ORDER_OF_TOKEN:
            raise S5bCompileError(
                f"bad_to_order:map{m1}~map{m2}:{to}",
                f"目标键级不可执行:{to}", {"map_pair": sorted((m1, m2))})
        if cur_token != to:
            edits.append({"op": "change_bond_order", "atom1": c1,
                          "atom2": c2, "from_order": cur_token,
                          "to_order": to})
    return edits


def _rhs_order_of(rhs, key) -> str:
    b = _bond_by_map_pair(rhs.mol, key)
    return _order_token(b) if b is not None else _NONE


def _bond_by_map_pair(mol, key):
    for b in mol.GetBonds():
        ni, nj = (b.GetBeginAtom().GetAtomMapNum(),
                  b.GetEndAtom().GetAtomMapNum())
        if ni and nj and frozenset((ni, nj)) == key:
            return b
    return None


def _aromatic_ring_closure(mol, changed_pairs: dict) -> set:
    """包含 changed_pairs 中键的 lhs 芳香环系(键级均为 aromatic)全键集。"""
    out: set = set()
    visited: set = set()
    for key in changed_pairs:
        if key in visited:
            continue
        # BFS over aromatic bonds sharing atoms
        stack = [key]
        ring = set()
        while stack:
            cur = stack.pop()
            if cur in ring:
                continue
            ring.add(cur)
            for atom_map in cur:
                for b in mol.GetBonds():
                    ni, nj = (b.GetBeginAtom().GetAtomMapNum(),
                              b.GetEndAtom().GetAtomMapNum())
                    if not (ni and nj):
                        continue
                    other = frozenset((ni, nj))
                    if atom_map in other and other not in ring \
                            and _order_token(b) == _AROMATIC:
                        stack.append(other)
        visited |= ring
        out |= ring
    return out


def _rhs_kek_order(rhs_mol, m1: int, m2: int) -> str:
    """rhs aromatic 键的目标执行键级 = rhs kekulé 形对应键级。"""
    kek = _kekulized_copy(rhs_mol)
    key = frozenset((m1, m2))
    for b in kek.GetBonds():
        ni, nj = (b.GetBeginAtom().GetAtomMapNum(),
                  b.GetEndAtom().GetAtomMapNum())
        if ni and nj and frozenset((ni, nj)) == key:
            return _order_token(b)
    return _NONE


# ---------------------------------------------------------------- 新原子落位


def _place_new_atoms(transform, current, map_to_current_id,
                     edits: list[dict]) -> dict[int, str]:
    """新增原子按有依据锚点拓扑序落位(W1 #6/#7)。

    - add_atom(element, new_atom_id=S_<E>_N<n>, atom1=锚):自动接
      single 锚定键;不重复 form 同键;
    - 新键 double/triple ⇒ 先落位 single 再 change_bond_order;
    - 既有原子间新成键:form_bond(single) + 必要变阶;
    - 新原子必须可达已落位原子(无锚 ⇒ 拒,不猜);
    - rhs 新键 aromatic ⇒ 诚实 unsupported(芳香环新合成不在 v2
      编辑协议表达范围)。
    返回 {新增 map 号 → new_atom_id}(供体命名空间 D_<map> 的映射值)。

    W-V2(S5b-recorded-bonddiff-1):**无新增原子时不再早退** —— 纯
    重排对应(保留原子间断键+成键,如推断映射的有界键差 fallback)
    的 rhs 新键(端点均为保留原子)同样经 form_bond 落位;旧实现
    ``if not added: return {}`` 把这类键静默丢弃(推断映射重排在
    编译层不可表达 —— 已证源码缺口)。
    """
    rhs = transform["rhs"]
    lhs = transform["lhs"]
    added = set(transform["added_maps"])
    taken_ids = set(current.atom_id_map)
    new_id_of: dict[int, str] = {}
    anchor_of: dict[int, str] = {}   # 新增 map → 其 add_atom 锚 ID
    if added:
        # rhs 新原子邻接(map 对):新增原子与其全部 rhs 键
        adj: dict[int, set[int]] = {m: set() for m in added}
        for b in rhs.mol.GetBonds():
            ni, nj = (b.GetBeginAtom().GetAtomMapNum(),
                      b.GetEndAtom().GetAtomMapNum())
            if ni in added or nj in added:
                adj.setdefault(ni, set()).add(nj)
                adj.setdefault(nj, set()).add(ni)
        # BFS from 已映射原子(锚点拓扑序)
        frontier = [m for m in added
                    if any(n not in added for n in adj.get(m, ()))]
        placed: set[int] = set()
        while frontier:
            m = frontier.pop(0)
            if m in placed:
                continue
            anchors = [n for n in adj.get(m, ()) if n not in added]
            anchor = None
            for n in anchors:
                if n in map_to_current_id:
                    anchor = map_to_current_id[n]
                    break
            if anchor is None:
                # 无直接锚:是否已落位邻接(新增-新增链)
                for n in adj.get(m, ()):
                    if n in new_id_of:
                        anchor = new_id_of[n]
                        break
            if anchor is None:
                raise S5bCompileError(
                    f"new_atom_unanchorable:map{m}",
                    f"新增原子 map {m} 无有依据锚点(不可达已落位原子;"
                    "不猜落位)",
                    {"map_no": m})
            atom = rhs.mol.GetAtomWithIdx(rhs.maps[m])
            element = atom.GetSymbol()
            if atom.GetFormalCharge() != 0:
                raise S5bCompileError(
                    "new_atom_charge_unsupported",
                    f"新增原子 map {m} 带形式电荷(协议无电荷 op)",
                    {"map_no": m})
            new_id = _new_atom_id(element, taken_ids)
            taken_ids.add(new_id)
            new_id_of[m] = new_id
            anchor_of[m] = anchor
            placed.add(m)
            edits.append({"op": "add_atom", "element": element,
                          "new_atom_id": new_id, "atom1": anchor})
            for n in adj.get(m, ()):
                if n in added and n not in placed:
                    frontier.append(n)
        if placed != added:
            raise S5bCompileError(
                "new_atom_placement_incomplete",
                "新增原子未全部落位(锚点拓扑序未覆盖)",
                {"unplaced": sorted(added - placed)})
    _emit_new_bonds(transform, map_to_current_id, new_id_of, anchor_of,
                    edits)
    return new_id_of


def _emit_new_bonds(transform, map_to_current_id: dict,
                    new_id_of: dict, anchor_of: dict,
                    edits: list[dict]) -> None:
    """rhs 有、lhs 无的 map 键落位(form_bond + 必要变阶;W-V2:
    无新增原子时同样执行 —— 保留原子间新成键是重排对应的表达)。"""
    rhs = transform["rhs"]
    lhs = transform["lhs"]
    lb = _bond_table_by_map(lhs.mol, lhs.maps)
    rb = _bond_table_by_map(rhs.mol, rhs.maps)
    for key in sorted(set(rb) - set(lb), key=sorted):
        m1, m2 = sorted(key)
        orr = rb[key]
        if orr == _AROMATIC:
            raise S5bCompileError(
                "aromatic_new_bond_unsupported",
                f"新成键 map{m1}~map{m2} 目标键级 aromatic(芳香环新"
                "合成不在 v43-editproto-2 表达范围;诚实 unsupported)",
                {"map_pair": sorted((m1, m2))})
        # 端点解析:新增原子取 new_id_of;保留原子取 current ID
        def endpoint(m):
            if m in new_id_of:
                return new_id_of[m]
            return map_to_current_id.get(m)
        a1, a2 = endpoint(m1), endpoint(m2)
        if a1 is None or a2 is None:
            raise S5bCompileError(
                f"new_bond_missing_endpoint:map{m1}~map{m2}",
                "新成键端点无落位", {"map_pair": sorted((m1, m2))})
        # add_atom 已接 single 锚定键(新→既有 或 新→已落位新):
        # 该键已存在,不重复 form 同键;仅目标非 single 时变阶
        anchor_bond = (
            (m1 in new_id_of and anchor_of.get(m1) == a2)
            or (m2 in new_id_of and anchor_of.get(m2) == a1))
        if anchor_bond:
            # add_atom 已接 single 锚定键:不重复 form 同键;目标非
            # single ⇒ 先成 single 再变阶(W1 #6)
            if orr != "single":
                edits.append({"op": "change_bond_order", "atom1": a1,
                              "atom2": a2, "from_order": "single",
                              "to_order": orr})
        else:
            edits.append({"op": "form_bond", "atom1": a1, "atom2": a2})
            if orr != "single":
                edits.append({"op": "change_bond_order", "atom1": a1,
                              "atom2": a2, "from_order": "single",
                              "to_order": orr})


# ---------------------------------------------------------------- 主入口


def compile_donor_template(
    *,
    mapped_lhs: str,
    mapped_rhs: str,
    center_atoms: list[int],
    substrate_smiles: str,
    record_id: str,
    mapping_origin: str = "native",
    alignment_ref: str | None = None,
    key_prefix: str = "tpl",
    render_name: str = "S",
) -> dict:
    """映射供体模板 + 当前底物 → PPV1 池 spec(单一构建源;W1 全规则)。

    成功返回 ``{"status": "compiled", "spec": {...}, "diagnostics": {...}}``;
    失败返回 ``{"status": "unsupported", "reason": <机读码>, "detail":
    {...}}``(不吞异常:内部 S5bCompileError 转结构化 reason,意外异常
    转 internal_error 如实披露)。

    spec 字段(与 prepare_hypothesis/production/audit 公共链对接):
    - edits/donor/alignment/expectation:全部由**同一迁移结果**产生;
    - donor.center_atom_ids = ["D_<map>", …](供体命名空间,与
      alignment.donor_to_current 键一致 —— audit 消费契约);
    - expectation.target_smiles = 离线执行产物(canonical 全组分);
    - product_smiles = 中心所在组分(主产物);coproducts = 其余组分
      (离去组分/共产物,完整净产物集合入参与物);
    - alignment.ref/mapping_origin:原生映射 vs 推断映射如实标注。
    """
    try:
        return _compile_donor_template_impl(
            mapped_lhs=mapped_lhs, mapped_rhs=mapped_rhs,
            center_atoms=center_atoms,
            substrate_smiles=substrate_smiles, record_id=record_id,
            mapping_origin=mapping_origin, alignment_ref=alignment_ref,
            key_prefix=key_prefix, render_name=render_name)
    except S5bCompileError as exc:
        return _unsupported(exc.reason, dict(exc.detail))
    except Exception as exc:  # noqa: BLE001 —— 内部错误如实披露,不吞
        return _unsupported("internal_error", {
            "error": f"{type(exc).__name__}:{str(exc)[:300]}"})


def _compile_donor_template_impl(*, mapped_lhs, mapped_rhs, center_atoms,
                                 substrate_smiles, record_id,
                                 mapping_origin, alignment_ref,
                                 key_prefix, render_name) -> dict:
    transform = extract_mapped_transform(mapped_lhs, mapped_rhs)
    lhs, rhs = transform["lhs"], transform["rhs"]
    current, arom, kek = _current_base(substrate_smiles)

    # ---- 中心锚定对齐枚举(s5b-compiler-4;有界;预算截断结构化拒) ----
    # 中心查询 = L1 骨架 + L2 两壳层(§3.2 定义);整侧元素账不再是
    # 必要条件(降为 builder 路由真源 F1 的省预算面,见
    # template_elements_fit docstring)。
    l1_maps = l1_maps_of_transform(transform)
    if not l1_maps:
        # 中心为空变换(removed-only 等):本刀不定义删除型中心(D-3
        # 登记);结构化拒并与 no_alignment 机读区分(§8.1-6)。
        return _unsupported(center_empty_reason(transform), {
            "record_id": record_id,
            "note": "无 L1(无变键/电荷/手性原子与新增锚);删除型"
                    "中心定义另轮(D-3),本刀不猜"})
    matches, qidx_of_map, truncated = enumerate_center_alignments(
        lhs.mol, lhs.maps, l1_maps, arom)
    if not matches:
        return _unsupported("no_alignment", {
            "record_id": record_id,
            "center_presence_matches": 0,
            "note": "执行输入不含中心查询(L1 骨架+L2 两壳层)"
                    "(中心不可落位)"})
    if truncated:
        # 预算截断诚实处置(§3.2 风险 5/D-2):不得称唯一目标已证;
        # 未核范围机读披露(截断轴 + 触限命中数)。
        return _unsupported("alignment_limit_exceeded", {
            "record_id": record_id,
            "n_matches_at_limit": len(matches),
            "truncation_axis": "center_match_enumeration",
            "unverified_matches": None,
            "note": "中心命中枚举触 _COMPILE_ALIGNMENT_LIMIT;候选"
                    "核验被截断,未核范围不视为无歧义(默认结构化拒)"})

    # 度核(模板 L1 重原子度 = 目标位点重原子度)+ prefer 确定性排序:
    # prefer 只排序不裁量准入(G⊆M 均为语义允许候选;G 优先消歧,
    # G 空回退全体)——被排序靠后的非全等候选不得跳过(M 全量核验)。
    tpl_heavy_deg: dict[int, int] = {}
    for m in l1_maps:
        idx = lhs.maps.get(int(m))
        if idx is None:
            continue
        tpl_heavy_deg[int(m)] = sum(
            1 for n in lhs.mol.GetAtomWithIdx(int(idx)).GetNeighbors()
            if n.GetAtomicNum() > 1)

    def _deg_ok(match) -> bool:
        for map_no, need in tpl_heavy_deg.items():
            qi = qidx_of_map.get(int(map_no))
            if qi is None:
                continue
            tgt = match[qi]
            deg = sum(1 for n in arom.GetAtomWithIdx(int(tgt))
                      .GetNeighbors() if n.GetAtomicNum() > 1)
            if deg != need:
                return False
        return True

    deg_flags = [_deg_ok(m) for m in matches]
    prefer_used = ("degree_matched_subset" if any(deg_flags)
                   else "fallback_all_presence")
    order = [i for i, ok in enumerate(deg_flags) if ok] + \
        [i for i, ok in enumerate(deg_flags) if not ok]

    center_map_nums = ([int(x) for x in (center_atoms or [])]
                       if center_atoms else list(lhs.maps))
    # 中心是供体侧(lhs)概念:引用不在 lhs 的 map 号 ⇒ 坏引用拒
    bad_centers = [m for m in center_map_nums if m not in lhs.maps]
    if bad_centers:
        raise S5bCompileError(
            "center_map_not_in_donor",
            f"中心 map 号不在供体 lhs 侧:{bad_centers}(中心是供体侧"
            "原子;新增原子由编译自动并入中心,不由调用方声明)",
            {"bad_center_maps": bad_centers})
    # 显式声明的中心原子须全部可落位(部分缺 ⇒ 该对齐不可判,skip;
    # 与基线 skip 语义一致);声明为空时不额外要求(基线同:全映射)。
    required_center = [int(x) for x in (center_atoms or [])]
    # 新增原子(rhs 独有 map)由编译自动并入中心与对齐(新原子变化
    # 属供体变换自身;D_<map> → S_<Elem>_N<n> 映射值)
    added_maps = [int(x) for x in transform["added_maps"]]
    # W-V4b:消解开的手性 map(执行后同源复核;spec 机读诊断)
    stereo_dissolved = [int(x) for x in
                        (transform.get("stereo_dissolved_maps") or [])]
    compiled_per_match: list[dict] = []
    seen_targets: dict[str, dict] = {}
    # ---- M 全候选等价核验(歧义硬规则 D-1):被 prefer 排序靠后的
    # 非全等候选不得跳过;按净产物目标归并,≥2 个不同可执行目标 ⇒
    # 结构化 ambiguous_alignment(披露只补充不替代)。
    for order_i in order:
        match = matches[order_i]
        map_to_current_id: dict[int, str] = {}
        skip = False
        for map_no, qi in qidx_of_map.items():
            atom_id = _atom_id_for_idx(current, match[qi])
            if atom_id is None:
                skip = True
                break
            map_to_current_id[int(map_no)] = str(atom_id)
        if skip or not map_to_current_id:
            continue
        # 中心原子须全部有映射(部分缺 ⇒ 该对齐不可判;与基线同)
        missing_center = [m for m in required_center
                          if m not in map_to_current_id]
        if missing_center:
            continue
        edits = _compile_edits(transform, current, arom, kek,
                               map_to_current_id)
        new_id_of = _place_new_atoms(transform, current, map_to_current_id,
                                     edits)
        for map_no, new_id in new_id_of.items():
            map_to_current_id[int(map_no)] = str(new_id)
        # ---- 编译后 validate + 离线 execute(W1 #8) ----
        verdict = validate_edits(current, edits)
        if not verdict.get("ok"):
            compiled_per_match.append({
                "target": None, "reason": "edit_validation_failed",
                "reasons": verdict.get("reasons", [])[:8]})
            continue
        execution = execute_edits(current, edits)
        if not execution.get("ok"):
            compiled_per_match.append({
                "target": None, "reason": "execution_failed",
                "reasons": execution.get("reasons", [])[:8]})
            continue
        # ---- W-V4b:执行后 rhs 立体同源复核(mimo r28 E2-③;R1 双轴) ----
        # 消解开的手性 map:执行产物该原子须同时过两轴——(a) 已指派
        # 四面体标签 == rhs 声明(UNSPECIFIED);(b) 该原子不在执行产物
        # RDKit FindPotentialStereo 潜在立体中心清单(含未指派)。
        # 任一轴不等(仍为潜在立体中心/残留标签/映射缺失)⇒ 结构化
        # stereo_derived_mismatch 拒,不靠"派生"假设放行。
        if stereo_dissolved:
            mismatched = _stereo_dissolution_mismatch(
                execution, map_to_current_id, stereo_dissolved)
            if mismatched:
                compiled_per_match.append({
                    "target": None,
                    "reason": "stereo_derived_mismatch",
                    "reasons": [
                        f"stereo_derived_mismatch:map{m}:{tag}"
                        for m, tag in mismatched][:8]})
                continue
        target = str(execution["product_smiles"])
        compiled_per_match.append({"target": target, "reason": "",
                                   "edits": edits,
                                   "map_to_current_id": map_to_current_id,
                                   "execution": execution,
                                   "degree_matched": bool(deg_flags[order_i]),
                                   "match": match})
        if target not in seen_targets:
            seen_targets[target] = compiled_per_match[-1]
    if not compiled_per_match or all(
            entry["target"] is None for entry in compiled_per_match):
        first_fail = next((e for e in compiled_per_match if e["target"] is None),
                          None)
        return _unsupported(
            (first_fail or {}).get("reason", "no_compilable_alignment"),
            {"record_id": record_id,
             "reasons": (first_fail or {}).get("reasons", [])[:8]})
    if len(seen_targets) > 1:
        # 歧义硬拒(必须):全部语义允许候选 M(含被 prefer 排序靠后的
        # 非全等候选)已全量核验;不同可执行目标 ⇒ 结构化拒。
        return _unsupported("ambiguous_alignment", {
            "record_id": record_id,
            "competing_targets": sorted(seen_targets)[:8],
            "n_alignments": len(compiled_per_match),
            "n_targets": len(seen_targets),
            "all_matches_verified": True,
            "note": "全部语义允许候选(M)等价核验给出不同目标"
                    "(不取首个;等价映射才合并;prefer 只排序不裁量)"})
    # 全部成功对齐共享同一目标 ⇒ 等价映射合并(取 prefer 序首个确定性
    # 对齐的 edits —— 同目标下编辑路径可能不同但净效应一致,执行验证
    # 已过;度全等子集 G 优先)
    chosen = next(e for e in compiled_per_match if e["target"] is not None)
    target = chosen["target"]
    execution = chosen["execution"]
    map_to_current_id = chosen["map_to_current_id"]
    edits = chosen["edits"]
    # L3 豁免面机读披露(选定对齐;未披露=不发货)
    l3_disclosure = _l3_disclosure(lhs.mol, lhs.maps, l1_maps,
                                   chosen["match"], qidx_of_map, arom)

    # ---- donor 命名空间 + alignment(W1 #3;新增原子并入映射值与中心) ----
    donor_to_current = {f"D_{map_no}": map_to_current_id[map_no]
                        for map_no in sorted(map_to_current_id)}
    center_maps_all = sorted(set(center_map_nums) | set(added_maps))
    center_ids = [f"D_{map_no}" for map_no in center_maps_all
                  if map_no in map_to_current_id]
    if not center_ids:
        return _unsupported("center_atoms_unmapped", {
            "record_id": record_id})

    # ---- 产物组分划分:中心所在组分 = 主产物;其余 = coproducts ----
    principal, coproducts = _split_components(
        execution, current, center_ids, donor_to_current)
    spec = {
        "key": f"{key_prefix}-{record_id}",
        "product_smiles": principal,
        "coproducts": coproducts,
        "coefficient": 1,
        "transformation_ref": str(record_id),
        "origin_group_key": f"{key_prefix}-source:{record_id}",
        "edits": edits,
        "donor": {"center_atom_ids": center_ids},
        "alignment": {
            "status": "resolved",
            "donor_to_current": donor_to_current,
            "equivalence_classes": [],
            "ref": alignment_ref or f"{key_prefix}:{record_id}",
        },
        "expectation": {"target_smiles": target},
        "compile": {
            "compiler_version": S5B_COMPILER_VERSION,
            "mapping_origin": str(mapping_origin),
            "n_alignments_total": len(compiled_per_match),
            "n_equivalent_alignments": len(compiled_per_match),
            "truncated": truncated,
            "template_center_maps": [int(x) for x in center_map_nums],
            # ---- T-G C2(compiler-4)机读字段(冻结项③) ----
            "alignment_scope": "center_anchored_l1_l2_shell2",
            "alignment_semantics": (
                "center query = L1 (bond-change/charge/stereo atoms + "
                "added-atom anchors) heavy-atom skeleton + L2 two shells "
                "(shell1 = L1 incident bonds, shell2 = N1 atoms' own "
                "incident bond sets); L3 differences exempt and disclosed "
                "(c2_l3_disclosure); aromatic matching is a positive "
                "requirement on aromatic bonds, NOT an exact bidirectional "
                "atom-flag equality (see 8.1-7); H counts and formal "
                "charges are not part of the query"),
            "center_presence_matches": len(matches),
            "prefer_ordering": prefer_used,
            "all_matches_verified": True,
            "unverified_matches": 0,
            "c2_l3_disclosure": l3_disclosure,
        },
    }
    if stereo_dissolved:
        # W-V4b(E2-④;R1 S2-c 轴/元素限定):机读诊断——下游统计
        # "多少 strict 命中依赖消解";字符串限定元素域(C)与复核
        # 双轴,防止 sp3_to_sp2 字面被外推到非碳中心(mimo r33)
        spec["compile"]["stereo_dissolution_applied"] = [
            int(m) for m in stereo_dissolved]
        spec["compile"]["stereo_dissolution_semantics"] = (
            "chiral_sp3_center_dissolved_by_bond_order_change_sp3_to_sp2"
            "; element domain: C only (non-carbon tetrahedral centers"
            " such as P/S/Si are NOT dissolvable, they stay"
            " stereo_edit_unsupported); post-execution homology check"
            " on two axes — assigned tetrahedral label must equal the"
            " rhs declaration (CHI_UNSPECIFIED) AND the atom must be"
            " absent from the executed product's RDKit"
            " FindPotentialStereo potential-stereocenter list"
            " (unspecified entries included, atom-axis types only);"
            " mismatch -> stereo_derived_mismatch reject")
    return {"status": "compiled", "spec": spec, "diagnostics": {
        "record_id": record_id, "target_smiles": target,
        "n_alignments": len(compiled_per_match),
        "equivalent_alignments_merged": len(compiled_per_match)}}


def _split_components(execution: dict, current, center_ids: list[str],
                      donor_to_current: dict) -> tuple[str, list[str]]:
    """执行产物按连通组分划分:中心(首个中心原子的组分)= 主产物。

    中心原子的执行图 idx 来自 execution["atom_id_map"](ID→idx);
    中心在多个组分(裂解)⇒ 取**首个中心原子**所在组分为主产物
    (确定性;组分按 RDKit GetMolFrags 的原子 idx 集合序),其余组
    分按 idx 序为 coproducts。主产物/共产物共同构成事件参与物侧的
    完整净产物集合。
    """
    from rdkit import Chem as _Chem

    product = _Chem.MolFromSmiles(str(execution["product_smiles"]))
    if product is None:
        raise S5bCompileError(
            "internal:product_unparseable",
            "离线执行产物不可解析(内部错误)",
            {"product_smiles": str(execution["product_smiles"])[:200]})
    frags = [list(f) for f in _Chem.GetMolFrags(
        product, asMols=False, sanitizeFrags=False)]
    exec_id_to_idx = {str(k): int(v) for k, v in
                      (execution.get("atom_id_map") or {}).items()}
    center_current_ids = {donor_to_current.get(d) for d in center_ids}
    center_idx = {exec_id_to_idx[a] for a in center_current_ids
                  if a in exec_id_to_idx}
    principal_frag = None
    for frag in frags:
        if set(frag) & center_idx:
            principal_frag = frag
            break
    if principal_frag is None:
        # 中心原子全部是新原子或映射丢失:取第一组分(确定性)
        principal_frag = frags[0]
    principal = _Chem.MolFromSmiles(_Chem.MolFragmentToSmiles(
        product, list(principal_frag)))
    coproducts: list[str] = []
    for frag in frags:
        if frag is principal_frag:
            continue
        piece = _Chem.MolFromSmiles(_Chem.MolFragmentToSmiles(
            product, list(frag)))
        if piece is not None:
            coproducts.append(_Chem.MolToSmiles(piece))
    return _Chem.MolToSmiles(principal), coproducts
