# M3 Tasks 1–7 验收 & Task 7 边界裁定 & MT-TQ-02 SNAPSHOT 放行

日期：2026-07-23
上游（学生交付）：
- 酶侧 Tasks 1/2/3/5 → `EnzymeCAGE-Teacher-Deliverables`（根目录）
  - `ENZYME_TASKS_1_2_3_5_FINAL_TEACHER_DELIVERY_2026-07-23.md`
- 微生物侧 Tasks 4/6 + Task 7 边界 → `EnzymeCAGE-MetaTraits-Teacher-Deliverables`（根目录）
  - `METATRAITS_TASKS_4_6_AND_TASK7_DECISION_REQUEST_2026-07-23.md`
依据：
- `TEACHER_REPLY_M3_P1_UNLOCK_CASE1_REBOUND_AND_METATRAITS_M4A_ADJUDICATION_2026-07-21.md`
- `TEACHER_REPLY_M3_CASE1_RHEA11880_FAIRNESS_AND_KNOWN_POSITIVE_EVIDENCE_2026-07-22.md`

状态：Tasks 1–6 全部验收 PASS / Task 7 裁定走 (a) / MT-TQ-02 SNAPSHOT 契约放行（M4b 仍不启动）/ 三案例 end-to-end 真跑全绿（导师侧本轮闭合 t5）。

---

## 一、总体评价

**本轮交付质量上乘，过程合规性尤其突出。** 两侧仓库均：无 force-push / rebase / 覆盖历史；
旧证据按字节保留；附逐任务审计 + 提交前总审计 + SHA256 清单；明确声明"不主张老师已验收"；
Task 5/7 边界诚实、不把未授权项包装成已完成。自审文化持续在线，予以肯定。

导师侧对两个 GitHub 仓库根目录主要交付逐行核对结论如下。

---

## 二、酶侧 Tasks 1/2/3/5 —— 逐项 PASS

### Task 1（Case 1 JSON, `case_1_rhea_46976.json`）→ **PASS**

逐行核对命中全部条件：

```text
[x] rhea_master_id=46976；ec=null（显式拒绝继承 RHEA:11880 的 EC 1.5.3.5）
[x] 底物 SMILES CN1CCC[C@H]1c1ccc(O)nc1 = (S)-6-hydroxynicotine
    （InChIKey 骨架 ATRCOGLZUCICIV，与导师侧 PubChem 独立核验一致）
[x] 反应式 …+O=O >> CN1CCC=C1…+OO 精确等于 RHEA:46976
[x] route_used=C-fallback；role=NICOTINE_DEGRADATION_C_FALLBACK_SUCCESS_DEMO
[x] B_pool=[]；C_pool=15 UID；known_positive=[Q93NH4, A0A075BSX9]（15/2）
[x] RHEA:11880 处理符合 2026-07-22 裁定：作为公平 Top-K 自然邻居（neighbor_rank=3）
    贡献候选、禁止人工剔除；不继承 EC、不替代查询身份、不作 known-positive 身份证据
[x] 两个 known_positive 均为 (a)+(b) 级证据（UniProt 直接标注 + 文献直接记载），
    非 c-only，合法保留
```

技术交叉验证：导师侧晨羽实测 **RHEA:46976 在 route_c index 里 0 命中**，
C pool 15 UID 确系底物 Morgan radius=8 公平 Top-K 相似检索所得，与学生 JSON 自洽。

### Task 2（三案例首页措辞, `THREE_CASE_HOMEPAGE.md`）→ **PASS**

三行系统角色说明**逐字**对齐 07-21 §3.3 第 3 条：

```text
Case 1 (RHEA:46976, 尼古丁降解): C-fallback 成功分支演示
Case 2 (RHEA:11532, EC 1.4.3.19): B-primary 排序统计意义
Case 3 (RHEA:24292, EC 2.3.1.1): 上游召回失败 fail-closed
```

冻结 pool 摘要（Case 1 0/0→15/2、Case 2 10/3→17/3、Case 3 0/0→79/0）与各 JSON 一致，
且均满足 pool ≤ 100 门。

### Task 3（deprecated 旧 Case 1 + `M3_CASE_REGISTRY.json`）→ **PASS**

旧 `case_1_rhea_40543.json` 按字节保留，标注 `deprecated:true / reason:business_direction_mismatch /
superseded_by:RHEA:46976`，与 07-21 §3.4 一致，未物理删除，审计可追溯。

### Task 5（`M3_EXT_CANDIDATE_SHORTLIST_v0.md`）→ **符合授权边界**

学生明确：仍处候选筛选 + 分阶段 D4 建议，等待二次裁定，未补资产、未跑模型、未纳入首页三案例。
完全踩在 07-21 §4.2/§4.3 授权线内。二次裁定（是否晋级官方案例 / 是否补资产）待另行处理。

---

## 三、微生物侧 Tasks 4/6 —— PASS

### Task 4（`SNAPSHOT_CONTRACT_DRAFT.md`）→ **PASS**（并见第四节 MT-TQ-02 放行）

老师要求的 6 项必覆盖字段全部命中，且超出要求：

```text
[x] 版本字段        → §3 upstream_version / contract_schema_version / snapshot_id
[x] 更新频率        → §8 discovery 30d / 自动激活 never / promotion trigger
[x] 许可展示        → §7 CC BY-SA 4.0 + URL + attribution（manifest/LICENSE/CITATION）
[x] 本地存储路径    → §6 data/metatraits/ 分层 + 原子激活/回滚
[x] hash 校验方式   → §7 V01–V12（SHA256 + gzip 完整性 + schema）
[x] 在线 fallback 切换 → §9.1 启用条件 + 熔断/退避返回条件
额外：snapshot_only 默认、fail-closed、TTL 缓存、请求间隔、完整 provenance 日志
```

### Task 6（去项目名, `METATRAITS_API_INQUIRY_EMAIL_DRAFT.md`）→ **PASS**

对外身份改为 "On behalf of an academic bioinformatics enzyme-to-microorganism mapping study"；
`USER_AGENT=ADRMATS-MicrobeCrew-Enzyme2Organism/1.0`（通用）；学生声明
`Enzyme2OrganismTool`/`OrganismAggregator` 源码本就无项目名、无额外对外披露，故无需改算法/重跑 HPC。
符合 07-21 MT-TQ-03。邮件保持未发送状态，收件人/落款待核，边界正确。

---

## 四、MT-TQ-02（SNAPSHOT 契约）→ **草案放行，M4b 仍不启动**

`SNAPSHOT_CONTRACT_DRAFT.md` 满足 07-21 §153 全部要求，**予以通过**。M4a 侧可依此契约推进
snapshot 收敛/校验工具的设计。

**但明确边界**：本放行仅确认"契约草案达标"，**不等于授权 M4b**。M4b（MicrobeTraitTool /
TraitValue 运行时）仍需单独立项，且硬依赖：官方 upstream 版本确定 + 完整校验 + 许可展示 +
更新回滚演练 + 老师批准（见草案 §11 Production Promotion Gate）。当前 upstream_version 未确定，
本地候选仍处 `UNVERSIONED_UPSTREAM_CANDIDATE`。

---

## 五、Task 7（not-applicable schema）→ **裁定走 (a)**

**裁定**：本轮只提交 `TraitValue` **schema 修订契约 + 示例**（含 `reason` / `note` 字段定义
及一条 not_applicable 输出示例），**不落 Pydantic 活代码、不写字段校验测试、不实现
MicrobeTraitTool、不接 M4b 调用链**。

三条理由：

```text
1. MT-TQ-06 要求的是"输出 schema 增加 reason+note 限定语"这一契约，
   与 SNAPSHOT 草案同级，契约层交付即可满足，无需活代码。
2. TraitValue / MicrobeTraitTool 属明确划入 M4b 的组件；落活代码+测试
   即种下 M4b 第一块代码，撞"MT-TQ-02 未闭前不启动 M4b"的门。
3. 正确时序：SNAPSHOT（MT-TQ-02，本轮才放行草案）→ M4b 正式立项 →
   TraitValue 活代码 + 字段校验测试并入 M4b 启动包。
```

Task 7 状态更新为：`CONTRACT_ONLY_APPROVED / CODE_DEFERRED_TO_M4B`。

示例契约需覆盖（学生下轮交付）：

```text
trait_name: oxygen_preference
value: not_applicable
reason: taxon-level record absent (species/strain 均无对应观测)
note: not_applicable 表示"当前证据链下无法归属"，不等于"生物学上不存在此性状"
```

---

## 六、07-22 裁定文档归档与审计链修复

学生 Case 1 JSON 引用了
`TEACHER_REPLY_M3_CASE1_RHEA11880_FAIRNESS_AND_KNOWN_POSITIVE_EVIDENCE_2026-07-22.md`
（SHA256 `80a3be0c…`）作为 RHEA:11880 公平检索授权依据。导师侧 workspace 此前未归档该原件，
现已据项目记忆重建并归档同名文档，**但重建稿字节不等于 `80a3be0c…`**。

**请学生回传该 07-22 原件**（其 SHA256 应为 `80a3be0c8507a6cbf4f318de0c4735aa04d7c5106c2cc759fb5af7ee9ea356c0`），
导师侧将以原件字节替换重建稿，使两侧审计链字节一致。此为审计留痕修复，不影响 Task 1 的 PASS 结论。

---

## 七、三案例 end-to-end 真跑全绿板（导师侧本轮已完成）

裁定发出后，导师侧在晨羽 4090D（`DRY_RUN=0`，真实触达 `wrapper.predict`）完成三案例端到端首跑，
**同环境同日全绿**，闭合 07-21 §6.1 末项"三案例 end-to-end 首跑"：

```text
Case              分支                 route/pool          predict            verdict
case_1_realrun    B-primary(邻居 EC)   B, pool=14, rank=10  v1_20260714 ✅     PASS 9/9
case_2_realrun    B-primary(自匹配)    B, pool=31, rank=10  v1_20260714 ✅     PASS 9/9
case_3            fail-closed          substrate 阶段中止   不进 predict(正确)  PASS 3/3
```

Case 1 真跑证据：substrate(04:48:26) → reaction(top_score=1.0) → pool → ranking(04:58:28)，
wrapper 加载 `model_version=v1_20260714`，返回 10 条 ranked_enzymes（`evidence_hash=381275ff…`），
top1=P08159(0.884)。归档 `reports/chenyu_realrun/case_{1,2,3}_*_PASS/`（console/evidence/result/verdict 四件套）。

**一处重要发现（不影响 Task 1 PASS，供学生知悉）**：

```text
泛化裸 SMILES 查询下，Case 1 底物 (S)-6-hydroxynicotine 的指纹命中一个 Tanimoto=1.0 的
带 EC 邻居反应（(R) 型开环氧化），route_b 经 rhea2ec 得 7 ECs → 14 UID → 按 B-primary 走 B；
此时 route_c 也有 15 UID，仅作 provenance。故泛化查询实测走 B，而非 C。

这与官方冻结 Case 1 的 C-fallback 不矛盾：官方 Case 1 之所以是 C-fallback，是因为它把
RHEA:46976 定义为 ec=null（无 EC → route_b 空）——那是"策展身份约束"，泛化 SMILES 查询不吃此约束。
两条路径各自内部自洽：realrun 验证端到端可达性，官方冻结 JSON 验证策展身份。

佐证：官方两个 known_positive（Q93NH4、A0A075BSX9）均出现在本次 B 排序结果中（rank 7、10）。
```

---

## 八、下一步

```text
导师侧（本轮已完成）:
  [x] 三案例 end-to-end 真跑全绿（Case 1/2 触达 wrapper.predict；Case 3 fail-closed），
      闭合 07-21 §6.1 末项"三案例 end-to-end 首跑"

学生侧（下轮交付，全部走 GitHub teacher-deliverables 仓库；晨羽仅留给将来需真跑的数据资产）:
  [ ] 回传 07-22 原件（SHA256 应为 80a3be0c…）供导师侧字节对齐归档 —— 唯一硬需项
  [ ] Task 7 按 (a)：TraitValue schema 修订契约 + not_applicable 示例
  [ ] （并行，不阻塞）M3-EXT 候选二次裁定所需补充材料，待老师另行安排
```

**交付渠道判定原则**：要"留痕/被审计"的（文档、契约、schema、JSON、SHA256 清单）→ GitHub，
git 天然保字节且提交历史即审计；要"被跑"的（route_b/c、d4 白名单等数据资产、4090D 上执行的代码）→ 晨羽。
上述三项均无需在晨羽运行，故全部走 GitHub（尤其 07-22 原件必须字节对齐）。

本裁定不构成对 EnzymeCAGE v1、任一 case 排序结果、MetaTraits 真实世界生物学有效性的背书。
