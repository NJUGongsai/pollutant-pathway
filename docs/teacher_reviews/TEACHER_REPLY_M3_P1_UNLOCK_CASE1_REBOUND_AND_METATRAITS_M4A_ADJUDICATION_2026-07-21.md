# M3-P1 解冻 & Case 1 边界重裁 & MetaTraits M4a 逐项裁定

日期：2026-07-21  
上游（学生交付）：  
- `ENZYMECAGE_M3_P1_UNLOCK_CLOSURE_CASE1_BOUNDARY_AND_CASE_EXTENSION_ADJUDICATION_REQUEST_2026-07-21.md`  
- `2026-07-21_M3_P1_Unlock_Closure_and_Case_Adjudication/`（三个正式 case JSON + stable_runtime_context.json）  
- `2026-07-21_MetaTraits_M4a_Teacher_Review_Decision_Request/`（Enzyme2OrganismTool / OrganismAggregator / 10-UID 离线测试 + 六项 MT-TQ）  
状态：M3-P1 解冻确认 / Case 1 采纳替换方案 B（RHEA:46976）/ M3-EXT 授权候选筛选阶段 / MetaTraits M4a 五项裁定完成 / MT-TQ-02 待 SNAPSHOT 草案单独裁定

---

## 一、总体评价

**本轮学生交付质量整体上乘。** 三个亮点：

1. **主动申报 Case 1 生物学方向问题**：学生在案例已"接受冻结"之后仍主动复核 Rhea:40543 的业务语义，发现该反应实为大环内酯抗生素**合成侧的羟化**（10-deoxymethymycin → neomethymycin），并非污水场景的抗生素**降解**，据此主动申报边界收紧或替换方案。这是自审文化落地的正向信号，予以肯定。
2. **晨羽稳定上下文一次到位**：三条 stable_logical_path（`D4_WRAPPER_ROOT` / `ENZYMECAGE_V1_PACKAGE_ROOT` / `ENZYMECAGE_CODE_ROOT`）+ 环境激活命令 + GPU 可见性手段 + Python/依赖版本三方一致，覆盖 M3I6-A 全部需要的稳定路径识别信息。
3. **MetaTraits M4a 边界诚实**：`Enzyme2OrganismTool`、`OrganismAggregator`、10 UID 离线测试完成；六项 MT-TQ 问题全部围绕"我不敢自作主张的合同级歧义"提出，未把边界模糊的问题包装成已解决。

**M3-P1 予以解冻**；Case 1 采纳学生方案 B（RHEA:46976 替换）；M3-EXT 仅授权候选筛选阶段；MetaTraits M4a 五项一次裁定，MT-TQ-02（SNAPSHOT 契约）待草案到位后单独裁定。

---

## 二、M3-Q1：M3-P1 解冻确认 → **同意解冻**

上游 M3-P1 剩余解冻条件（2026-07-20 回复文档第七节）为两项：

```text
[x] 6.1 三个正式 case JSON 到位            → 已到位（学生 2026-07-21 交付）
[x] 6.2 晨羽稳定上下文（三条 stable_logical_path + 环境激活 + GPU）  → 已到位
```

**M3-P1 予以解冻**，导师侧启动 Agent 正式实现。学生侧本轮不再有 M3-P1 阻塞交付项。

需注意：`ENZYMECAGE_CODE_ROOT` 由原 observed path 复核为学生提供的 stable_logical_path，请在正式实现的第一次晨羽联通验证中，用该稳定路径做一次 `python -c "import enzymecage_wrapper; print(enzymecage_wrapper.__file__)"` 冒烟测试，作为路径稳定性回执落库。

---

## 三、M3-Q2：Case 1 边界裁定 → **采纳方案 B（换成 RHEA:46976）**

### 3.1 裁定

**采纳学生方案 B**：Case 1 由 `RHEA:40543 / EC 1.14.15.33`（抗生素合成侧羟化）**替换为** `RHEA:46976`（(S)-6-hydroxynicotine + O2 → 6-hydroxy-N-methylmyosmine + H2O2），定位为"尼古丁降解真实场景 + B-empty→C-fallback 成功分支验证"。

### 3.2 三条采纳理由

1. **业务真实性**：本项目对外定位是"污染物降解酶推荐"，一个抗生素**合成**方向的案例作为首页样例长期无解——即使加"仅作演示"限定语，仍会造成读者对系统场景的稳定误解；换成尼古丁降解这类真实污水/环境降解场景可以从根源上消除歧义。
2. **系统行为覆盖更好**：原 Case 1 的 B pool size = 1（O87605 单 UID）几乎不构成排序统计意义；RHEA:46976 的 B=0/0、C=15/2 恰好覆盖 **"B-empty → C-fallback 成功"** 这条此前三案例都没跑通的关键分支。三案例覆盖度从"B-min / B-rank / 上游召回失败 fail-closed"变为 **"B-rank（Case 2）/ C-fallback 成功（Case 1 新）/ 上游召回失败 fail-closed（Case 3）"**，系统性显著提升。
3. **边界处理专业**：学生在冻结后仍主动复核生物学方向并诚实申报，这本身是我们要鼓励的自审行为；采纳其替换方案是对这种行为最直接的正向反馈。

### 3.3 采纳附加四项条件（学生侧执行）

```text
1. 冻结身份必须显式标 ec=null（RHEA:46976 无 EC 官方号），
   不得为凑格式而人工填 6.3.3.5 之类的候选 EC 号；
   provenance 里保留"EC-null, Rhea master unambiguous"标注。

2. RHEA:11880（原 Case 1 学生自审阶段引用的 provenance）仅作为
   evidence_provenance 引用，不进入 known_positive_uids，不作为
   B/C 候选来源。

3. 三案例首页角色说明必须同步冻结更新为：
     Case 1 (RHEA:46976, 尼古丁降解): C-fallback 成功分支演示
     Case 2 (RHEA:11532, EC 1.4.3.19): B-primary 排序统计意义
     Case 3 (RHEA:24292, EC 2.3.1.1): 上游召回失败 fail-closed
   任何对外文档/README/首页说明必须使用此三行统一措辞，
   不得回退到"Case 1 = 抗生素降解"或"Case 1 = 最小 pipeline 验证"。

4. 不新增第四案例。M3 全周期三案例总数不变，本次为等量替换。
```

### 3.4 弃用记录

原 `RHEA:40543 / EC 1.14.15.33 / O87605` 冻结身份**弃用**，学生侧在 `M3_CASE_REGISTRY` 或等价索引里以 `deprecated: true, reason: business_direction_mismatch, superseded_by: RHEA:46976` 标注，不物理删除相关 evidence 文件，保留审计追溯能力。

---

## 四、M3-Q3：新污染物挑战案例授权 → **原则同意，仅授权候选筛选阶段**

### 4.1 裁定

**原则同意**学生后续在训练集/测试集之外筛选新污染物降解挑战案例，作为 **M3-EXT** 独立立项，与当前三案例（Case 1/2/3）**平行推进**、**互不阻塞**。

### 4.2 授权范围（仅第一阶段：候选筛选）

```text
授权：
  [x] 从训练集/测试集之外的 Rhea/BRENDA/文献中筛选候选反应
  [x] 出候选清单（每条：Rhea ID、EC、SMILES、污染物类别、
       候选依据、B/C 初步池大小、是否与训练集/测试集有 overlap 的证据）
  [x] 每条候选做"排除性证据"检查（是否泄漏训练集/测试集 query UID / EC / molecule）

不授权（需二次立项）：
  [ ] 任何数据资产补齐（不新增 D4/rhea140/route_b/route_c 文件）
  [ ] 将任一候选纳入 Case 1/2/3 首页三案例序列
  [ ] EnzymeCAGE wrapper 上晨羽 GPU 跑推理
  [ ] 对外 README / paper draft 引用为"系统已验证案例"
```

### 4.3 交付形式

学生把候选清单以 `M3_EXT_CANDIDATE_SHORTLIST_v0.md` 形式提交，字段最小集见 4.2。老师侧收到清单后再决定：

- 是否任一候选晋级为"官方挑战案例"（走完整案例冻结流程）；
- 是否需要为该候选补齐资产（若需要，走 D4/route_b/route_c 补齐立项）。

在此二次裁定发生前，M3-EXT **不消耗晨羽 GPU、不改动当前三案例、不进入 EnzymeCAGE 正式调用链**。

---

## 五、MetaTraits M4a：五项 MT-TQ 裁定

### MT-TQ-01：MT-D3 UID tie-break 歧义 → **采纳当前 NCBI taxon ID 数字升序实现**

裁定：保留学生当前实现（NCBI taxon ID 数字升序做 tie-break），**不切换**为 enzyme UID 字符串升序。授权省略 A/B/C 三方案对照列的实现，直接落地此单一实现。

理由：taxon ID 数字升序是生物学场景下更自然的稳定序（enzyme UID 字符串序无生物学语义，仅是字典序偶然性）；三方案对照列会带来额外维护成本但不产生新信息。

### MT-TQ-03：项目名披露语义 → **改为通用生物信息学咨询**

裁定：`Enzyme2OrganismTool` 与 `OrganismAggregator` 的对外文档/日志/查询上下文中，**去除 "EnzymeCAGE" 项目名**，统一改为"通用生物信息学 / 酶-微生物映射咨询"。

理由：M4a 层的能力本身不绑定 EnzymeCAGE，将其解耦有利于后续在其他项目复用；同时避免第三方（含被查询 API 的维护方）把 M4a 的查询流量归因到具体上游项目。

### MT-TQ-04：预加载策略 → **继续 A（启动预加载）**

裁定：继续学生当前 A 方案（进程启动时预加载 allowlist / static index），不切换为 lazy load。

理由：M3 首页三案例 UID 规模有限，启动一次性预加载成本可控；相较 lazy load，可避免首次调用的冷启动延迟出现在演示时；也避免 lazy 场景下的并发首次加载竞态。

### MT-TQ-06：不适用边界 → **接受 not-applicable 边界，加限定语**

裁定：接受学生当前"某些 trait 对某些微生物 not-applicable"的边界处理，但对外表述必须**加限定语**：

```text
输出示例：
  trait_name: oxygen_preference
  value: not_applicable
  reason: taxon-level record absent (species/strain 均无对应观测)
  note: not_applicable 表示"当前证据链下无法归属"，不等于"生物学上不存在此性状"
```

理由：not-applicable 是证据边界，不是生物学否定；加限定语避免下游把 not-applicable 误读为"该菌确实没有此性状"。

### MT-TQ-07：strain vs species 归属 → **采纳学生 exact-tax-ID 保守方案**

裁定：采纳学生 **exact-tax-ID 优先原则**：strain 级 tax_id（如 211586）与 species 级 tax_id（如 70863）的性状记录**不相互继承**；只有当查询目标 tax_id 精确命中时才归属该条 trait 记录。

理由：strain 级性状差异（如某些 species 内不同 strain 的 oxygen_preference 差异）是真实存在的生物学信号；宽松继承（species → strain 或反向）会造成隐性数据污染。M3 阶段边界诚实优先于覆盖度。

### MT-TQ-02：SNAPSHOT 契约 → **待学生 SNAPSHOT_CONTRACT_DRAFT.md 到位后单独裁定**

裁定：**暂不裁定**。请学生按 MT-D5 裁定要求（2026-07-16 文档 §2.1）尽快提交 `SNAPSHOT_CONTRACT_DRAFT.md` 草案，需覆盖：版本字段、更新频率、许可展示、本地存储路径、hash 校验方式、与在线 fallback 的切换条件。老师侧收到草案后单独出裁定文档。

在 SNAPSHOT_CONTRACT_DRAFT.md 到位前，M4a 可继续推进 Enzyme2OrganismTool / OrganismAggregator 的完善工作，但**不启动 M4b**（M4b 上线硬依赖 snapshot 契约裁定完成）。

---

## 六、M3-P1 与 M4a 联动执行计划

### 6.1 M3-P1（导师侧主导，本地已完成 M3I6-A 适配）

```text
[x] 本地代码 M3I6-A 适配（config/settings.py、enzymecage_client.py、
    enzyme_pool_builder.py、reaction_retriever.py、.env.example）
[x] Dry-run 三案例 mock 验证（Case 1 1UID→1rank / Case 2 10UIDs→10rank
    / 空 pool→0）
[x] 图编译验证（10 节点）
[ ] Case 1 冻结身份重写为 RHEA:46976（等学生按 §3.3 附加条件重发 case_1 JSON）
[ ] 晨羽首次联通冒烟（stable_logical_path 三条路径 import 验证）
[ ] 三案例完整推理链首次 end-to-end 跑通
```

### 6.2 学生侧后续工作项（按溯源分类，无本轮新增要求）

以下 7 项均由**本轮学生自提问题的裁定后果**或**上一轮已要求本轮催缴**两类构成，本轮**未新增**任何要求。

**6.2.1 本轮 M3-Q2 裁定的必要连带（Case 1 变更连锁，源自学生自提生物学方向问题）**

```text
[ ] 按 §3.3 附加条件重发 case_1 JSON（RHEA:46976, ec=null, role 明标 C-fallback 成功）
[ ] 三案例首页角色说明更新为 §3.3 第 3 条统一措辞
[ ] deprecated 记录旧 Case 1（RHEA:40543）保留审计
```

**6.2.2 上一轮 MT-D5 §2.1 已要求、本轮催缴**

```text
[ ] MT-TQ-02 → 提交 SNAPSHOT_CONTRACT_DRAFT.md 草案
    （溯源：2026-07-16 MT-D5 §2.1 已明列必交项，非本轮新增）
```

**6.2.3 本轮学生自提问题的裁定执行动作**

```text
[ ] M3-EXT 候选清单（M3_EXT_CANDIDATE_SHORTLIST_v0.md）
    （溯源：学生 M3-Q3 主动申请授权 → 我裁定仅授权候选筛选阶段）
[ ] MT-TQ-03 → 从 Enzyme2OrganismTool/OrganismAggregator 相关文档、日志、
    查询上下文里移除 "EnzymeCAGE" 项目名
    （溯源：学生 MT-TQ-03 主动提问 → 我裁定改为通用生物信息学咨询）
[ ] MT-TQ-06 → 输出 schema 增加 not-applicable 限定语字段
    （溯源：学生 MT-TQ-06 主动提问 → 我裁定接受边界，加限定语）
```

### 6.3 并行与阻塞关系

```text
- Case 1 重发 JSON 阻塞 M3-P1 三案例 end-to-end 首跑（但不阻塞晨羽联通冒烟）
- SNAPSHOT_CONTRACT_DRAFT.md 阻塞 M4b 启动，不阻塞 M4a 继续完善
- M3-EXT 候选筛选与 M3/M4a 完全并行，无阻塞关系
```

---

## 七、边界与不做项

本裁定不涉及且不改动：

```text
- D4 wrapper 冻结身份（四项 SHA256）
- EnzymeCAGE 模型 v1_20260714 冻结版本
- Python 契约字段（reaction_smiles / enzyme_pool_uids / top_k / return_ci）
- M3D2 B-primary / C-fallback / pool ≤ 100 fail-closed 边界
- MT-D5 通过结论与 schema v1.1（is_ai / majority_label 独立字段）
- MT-D1–D8 既有裁定
- M4b / M4c 启动（MT-TQ-02 未闭前不启动 M4b）
- M5 三层资产架构（本轮仍不启动）
- FastAPI/HTTP 服务化（M3 全周期不启动）
```

本裁定不构成对 EnzymeCAGE v1、任一 case 排序结果、MetaTraits allowlist 真实世界生物学有效性的背书。

---

## 八、请学生按 §6.2 顺序推进；Case 1 重发 JSON 与 SNAPSHOT_CONTRACT_DRAFT.md 为下一轮两项主要交付。

---

# 附：2026-07-22 补充追加块

> 说明：本追加块不修改上文 §一–§八 的原始裁定。仅记录 M3-P1 解冻后首次晨羽联通验证的**路径稳定性回执**（兑现 §二末段要求），以及**学生侧欠交项现状**（对应 §6.2 的 7 项）。**学生侧本轮无新增交付要求**；下述状态清单仅做梳理与轻量催缴。

## 九、路径稳定性回执落库（§二末段要求的兑现）

§二末段要求：M3-P1 解冻后首次晨羽联通验证需用 stable_logical_path 做 `import enzymecage_wrapper` 冒烟，作为路径稳定性回执。已在晨羽 4090D 环境完成，回执如下：

- 6 类 `stable_logical_path` 全部命中，SHA256 与 `stable_runtime_context.json` 逐条一致
- `from enzymecage_wrapper import EnzymeCAGERequest, predict` 成功，无 torch / pydantic / rdkit 冲突
- wrapper 契约字段（pydantic v2 `model_fields` introspection）得到 `['reaction_smiles', 'enzyme_pool_uids', 'top_k', 'return_ci']`，与交付一致
- `model_version = v1_20260714`，与 `stable_runtime_context.business_model` 一致

以上作为 §二末段回执落库；**不构成对 §六以下任何执行项的状态变更**。

## 十、学生侧欠交项现状（§6.2 三小节 7 项状态梳理）

**本节仅梳理已裁定项的当前欠交状态，未新增任何交付要求**。所有溯源均指向已定稿的裁定条款。

### 10.1 M3-Q2 裁定必要连带（源自 §3.3 附加条件，学生自审 Case 1 生物学方向的连锁）

| # | 交付项 | 溯源 | 状态 | 阻塞关系 |
|---|---|---|---|---|
| 1 | Case 1 JSON 按 §3.3 附加条件重发（RHEA:46976, ec=null, role=C-fallback 成功分支） | §3.3 第 1 条 | 待交付 | 阻塞 §6.1 三案例 end-to-end 首跑；**不阻塞晨羽联通冒烟（已完成）** |
| 2 | 三案例首页角色说明按 §3.3 第 3 条统一措辞 | §3.3 第 3 条 | 待交付 | 阻塞对外文档发布 |
| 3 | 旧 Case 1（RHEA:40543）在 M3_CASE_REGISTRY 标 `deprecated: true, superseded_by: RHEA:46976`，保留 evidence 文件 | §3.4 | 待交付 | 审计留痕，非阻塞 |

### 10.2 上一轮已催、本轮再催（无新增）

| # | 交付项 | 溯源 | 状态 | 阻塞关系 |
|---|---|---|---|---|
| 4 | `SNAPSHOT_CONTRACT_DRAFT.md` 草案（覆盖：版本字段 / 更新频率 / 许可展示 / 本地存储路径 / hash 校验方式 / 在线 fallback 切换条件） | 2026-07-16 MT-D5 §2.1；本轮 §MT-TQ-02 | 待交付 | 阻塞 M4b 启动；**不阻塞 M4a 继续完善** |

### 10.3 本轮 M3-Q3 / MT-TQ-03 / MT-TQ-06 裁定的执行动作

| # | 交付项 | 溯源 | 状态 | 阻塞关系 |
|---|---|---|---|---|
| 5 | `M3_EXT_CANDIDATE_SHORTLIST_v0.md` 候选清单（含 Rhea ID / EC / SMILES / 污染物类别 / B/C 初步池大小 / 训练测试集 overlap 排除证据） | §4.2 | 待交付 | 与 M3 / M4a 完全并行 |
| 6 | 从 `Enzyme2OrganismTool` / `OrganismAggregator` 相关文档、日志、查询上下文里移除 "EnzymeCAGE" 项目名 | §MT-TQ-03 | 待交付 | 无 |
| 7 | 输出 schema 增加 not-applicable 限定语字段（`reason` + `note`，见 §MT-TQ-06） | §MT-TQ-06 | 待交付 | 无 |

### 10.4 建议优先级

```text
P0（阻塞下轮）:
  #1  Case 1 JSON 重发                →  §6.1 三案例 end-to-end 首跑要用
  #4  SNAPSHOT_CONTRACT_DRAFT.md     →  M4b 启动前必闭

P1（阻塞对外发布）:
  #2  三案例首页角色说明统一措辞

P2（可与 M3 / M4a 并行推进）:
  #3 / #5 / #6 / #7
```

## 十一、新观察记录（仅记录，不构成新交付要求）

本轮首次真跑 `predict` 观察到：首次调用耗时 ~11 min，其中前 ~10 min GPU 显存为 0，仅 CPU + 磁盘 I/O；`/proc/<pid>/{fd,wchan,status}` 证据显示进程处于 disk-wait（`STAT=Dl`, `WCHAN=folio_wait_bit_common`），`fd` 指向 `esm_node_feature.torch.pt`，RSS 从 17.5 GB 增长到 46.7 GB 后稳定。推断为 3B backbone ESM2 蛋白特征缓存（107,705 蛋白 × node feature）首次 `mmap` 的正常代价。

**这是 3B backbone 的合理表现**。导师侧对策是把 LangGraph 部成常驻 python 服务并在启动时预热，属于**导师侧的部署工程，不请求学生调整 wrapper**。

以下两项仅作为"日后有余力可选优化"清单登记，**不构成本轮或后续任一轮的交付要求**：

```text
- 是否可支持 lazy load（按 pool UID 只加载相关 node feature）
- 是否可将 predict 拆分为 warmup() + predict() 两阶段 API
```

以上两项由老师侧择期评估是否立项；学生侧在收到具体立项文档前**不需要为此做任何工作**。
