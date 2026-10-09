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

版本:s5b-compiler-1。编译失败一律返回 ``{"status": "unsupported",
"reason": <稳定机读码>, "detail": {...}}``,不抛裸异常、不吞 Exception。
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

S5B_COMPILER_VERSION = "s5b-compiler-1"

# 对齐枚举显式上限(超过 ⇒ truncated,不得把截断集合当唯一对齐;
# 与 donor_applicability._ALIGNMENT_ENUM_LIMIT 同纪律,独立常量:
# 编译入口预算更小 —— 池编译是每题逐模板调用)
_COMPILE_ALIGNMENT_LIMIT = 64

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


def net_reaction_signature(spec: dict) -> tuple:
    """独特净反应签名(W3/W4 共用去重键):净产品集合严格身份多重集。

    - 同净产物集合 + step_scope(net_reaction)⇒ 同一独特净反应槽;
      不同反应/条件/角色不会只因主产物或 CN 一样被误并(签名取全部
      产物组分的**严格**身份,电荷/立体/组分差异都改变签名);
    - 解析失败按原始串兜底(确定性,不猜;不可解析串不同即不同槽)。
    """
    parts = [str(spec.get("product_smiles") or "")] + \
        [str(c) for c in (spec.get("coproducts") or [])]

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
    charge_changed, stereo_changed = [], []
    for n in retained_maps:
        la = lhs.mol.GetAtomWithIdx(lhs.maps[n])
        ra = rhs.mol.GetAtomWithIdx(rhs.maps[n])
        if la.GetFormalCharge() != ra.GetFormalCharge():
            charge_changed.append(n)
        if _chiral_token(la) != _chiral_token(ra):
            stereo_changed.append(n)
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
    added = sorted(set(rhs.maps) - set(lhs.maps))
    removed = sorted(set(lhs.maps) - set(rhs.maps))
    if not (bond_changes or added or removed or charge_changed
            or stereo_changed):
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
    }


def _chiral_token(atom) -> str:
    tag = atom.GetChiralTag()
    # 仅四面体手性可比较(R4-07 语义:非四面体不支持 ⇒ 两轴 unknown,
    # 编译侧按不支持处理由 stereo_changed 判定覆盖 —— 非四面体标签在
    # lhs/rhs 间不同时同样落入 stereo_changed)
    return str(tag)


# ---------------------------------------------------------------- 对齐枚举


def _atom_id_for_idx(current, idx: int) -> str | None:
    return current.idx_atom_map.get(int(idx))


def enumerate_template_alignments(lhs_mol, substrate_arom):
    """donor(lhs 芳香形)→ 当前底物(芳香形)全部子结构匹配(有界)。

    与 donor_applicability.enumerate_alignments 同纪律但**全供体匹配**
    (编译要求完整模板落位,中心子图回退属评估层策略,不属编译层):
    uniquify=False、useChirality=False、显式 maxMatches。返回
    (matches, truncated):matches = [{lhs_idx: current_idx}, …]。
    """
    matches = substrate_arom.GetSubstructMatches(
        lhs_mol, uniquify=False, useChirality=False,
        maxMatches=_COMPILE_ALIGNMENT_LIMIT)
    out = [{d: c for d, c in enumerate(m)} for m in matches]
    return out, len(matches) >= _COMPILE_ALIGNMENT_LIMIT


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
    """
    rhs = transform["rhs"]
    lhs = transform["lhs"]
    added = set(transform["added_maps"])
    if not added:
        return {}
    # rhs 新原子邻接(map 对):新增原子与其全部 rhs 键
    adj: dict[int, set[int]] = {m: set() for m in added}
    for b in rhs.mol.GetBonds():
        ni, nj = (b.GetBeginAtom().GetAtomMapNum(),
                  b.GetEndAtom().GetAtomMapNum())
        if ni in added or nj in added:
            adj.setdefault(ni, set()).add(nj)
            adj.setdefault(nj, set()).add(ni)
    taken_ids = set(current.atom_id_map)
    new_id_of: dict[int, str] = {}
    anchor_of: dict[int, str] = {}   # 新增 map → 其 add_atom 锚 ID
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
    # 新成键:rhs 有、lhs 无的 map 对(端点至少一个新增原子或全新)
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
        def endpoint_id(m):
            if m in new_id_of:
                return new_id_of[m]
            return map_to_current_id.get(m)
        # add_atom 已接 single 锚定键(新→既有 或 新→已落位新):
        # 该键已存在,不重复 form 同键;仅目标非 single 时变阶
        anchor_bond = (
            (m1 in new_id_of and anchor_of.get(m1) == endpoint_id(m2))
            or (m2 in new_id_of and anchor_of.get(m2) == endpoint_id(m1)))
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
    return new_id_of


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

    # ---- 对齐枚举(有界;等价映射合并,竞争目标 ambiguous) ----
    matches, truncated = enumerate_template_alignments(lhs.mol, arom)
    if not matches:
        return _unsupported("no_alignment", {
            "record_id": record_id,
            "note": "当前底物不含完整供体反应物(类比迁移无落位)"})
    if truncated:
        return _unsupported("alignment_limit_exceeded", {
            "record_id": record_id,
            "n_matches_at_limit": len(matches)})

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
    # 新增原子(rhs 独有 map)由编译自动并入中心与对齐(新原子变化
    # 属供体变换自身;D_<map> → S_<Elem>_N<n> 映射值)
    added_maps = [int(x) for x in transform["added_maps"]]
    compiled_per_match: list[dict] = []
    seen_targets: dict[str, dict] = {}
    for match in matches:
        map_to_current_id: dict[int, str] = {}
        for map_no, lhs_idx in lhs.maps.items():
            cur_idx = match.get(lhs_idx)
            if cur_idx is None:
                continue
            atom_id = _atom_id_for_idx(current, cur_idx)
            if atom_id is None:
                raise S5bCompileError(
                    "internal:current_id_missing",
                    "对齐原子的当前渲染 ID 缺失(渲染/对齐索引错位)",
                    {"map_no": map_no})
            map_to_current_id[int(map_no)] = str(atom_id)
        # 中心原子须全部有映射(部分缺 ⇒ 该对齐不可判)
        missing_center = [m for m in center_map_nums
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
        target = str(execution["product_smiles"])
        compiled_per_match.append({"target": target, "reason": "",
                                   "edits": edits,
                                   "map_to_current_id": map_to_current_id,
                                   "execution": execution})
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
        return _unsupported("ambiguous_alignment", {
            "record_id": record_id,
            "competing_targets": sorted(seen_targets)[:8],
            "n_alignments": len(compiled_per_match),
            "note": "对称对齐给出不同目标(不取首个;等价映射才合并)"})
    # 全部成功对齐共享同一目标 ⇒ 等价映射合并(取首个确定性对齐的
    # edits —— 同目标下编辑路径可能不同但净效应一致,执行验证已过)
    chosen = next(e for e in compiled_per_match if e["target"] is not None)
    target = chosen["target"]
    execution = chosen["execution"]
    map_to_current_id = chosen["map_to_current_id"]
    edits = chosen["edits"]

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
        },
    }
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
