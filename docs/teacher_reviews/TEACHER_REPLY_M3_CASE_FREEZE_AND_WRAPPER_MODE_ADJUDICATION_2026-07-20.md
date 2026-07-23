# M3 三案例冻结裁定 & Wrapper 调用模式采纳

日期：2026-07-20  
上游：  
- `ENZYMECAGE_M3_CASE_SELECTION_AND_MECHANISM_SELF_REVIEW_REQUEST_2026-07-20.md`  
- `ENZYMECAGE_M3_ASSET_6_WRAPPER_INTERFACE_STATUS_AND_CALL_MODE_DECISION_REQUEST_2026-07-20.md`  
- `ENZYMECAGE_M3_CURRENT_DUE_MATERIALS_UNIFIED_TEACHER_SUBMISSION_2026-07-20.md`  
状态：三案例冻结确认 / 调用模式采纳 M3I6-A / M3-P1 剩余解冻条件明列

---

## 一、总体评价

**本轮 M3-P0 收官交付通过。** 三个质量点：

1. **交付边界诚实**：case 3 的"79 pool ∩ 295 正例 = 0"如实披露，未把候选召回失败包装成模型排序失败；#6 wrapper 现状把"当前无 HTTP、SSH port forwarding 无法转发不存在服务"写清楚，未把 observed path 冒充稳定服务路径
2. **数据资产内审扎实**：451 个 P0 query 反应全局排除、B/C 直接泄漏 0、八项变异测试全部按预期拒绝、外部 SHA256 与内部 manifest 双向可核
3. **调用模式认知精准**：`M3I6-A/B/C` 三选一按"零新增授权"到"独立立项"分层，与老师既有"M3 不做 FastAPI 服务化"边界一致

---

## 二、三案例逐项裁定

### Case 1（Rhea:40543 / EC 1.14.15.33）→ **接受冻结，定位为"最小 pipeline 验证 + 污水场景占位"**

冻结身份：

```yaml
reaction_sha256: 240655c6546e987d720edcb3f4467e2076ac97245172d81343831e7dfc97f3a8
rhea_master_id: 40543
ec: 1.14.15.33
difficulty_tier: STRONG_TOP_5
route_used: B-primary
wastewater_status: SUPPORTED_PLAUSIBLE_REQUIRES_REVIEW
```

**接受依据**：机理自审自洽（ferredoxin-dependent oxygenase 与 EC 1.14.15.33 匹配）；Rhea/EC/SMILES/唯一正例 UID `O87605` 四方一致；污水标注为 plausible 而非 established，边界诚实。

**冻结记录必须明标的边界**：

```text
B pool size = 1（唯一 UID O87605）→ 排序演示统计意义 ≈ 0；
本案例主要价值为 "B-primary 路线跑通" + "污水抗生素场景占位"，
不构成 "EnzymeCAGE strong 排序成功案例"。
```

**禁止表述**：任何"top-1 命中率 100%"的对外结论必须同时披露 B pool size = 1。

### Case 2（Rhea:11532 / EC 1.4.3.19）→ **接受冻结，作为唯一具备排序统计意义的案例**

冻结身份：

```yaml
reaction_sha256: 19fe5b26e16a1a8ca60628be8718d3162cabded0299e2276a8503aec787bcf15
rhea_master_id: 11532
ec: 1.4.3.19
difficulty_tier: MEDIUM_6_TO_30
route_used: B-primary
wastewater_status: NOT_ESTABLISHED
```

**接受依据**：机理自审自洽（D-amino acid oxidase 类型）；B pool = 10、C pool = 17，两路各召回 3/8 正例；历史 rank 8/9/10 全部位于 Top-10——这是三个案例中唯一能对 EnzymeCAGE 排序能力形成可测量证据的案例。

**污水策略**：认可学生按 M3D1 授权（污水 medium 候选正例不入池时改选非污水 medium）；不追溯要求虚构污水关联。

### Case 3（Rhea:24292 / EC 2.3.1.1）→ **采纳 M3C3-A，重定位为"上游召回失败 → fail-closed 演示"**

冻结身份：

```yaml
reaction_sha256: 03900c0cd72deb2cdbdc826defd03e694d0ac53cd1ec8fbba509845fe1b92152
rhea_master_id: 24292
ec: 2.3.1.1
difficulty_tier: WEAK_OVER_100
route_used: C-fallback
wastewater_status: NOT_ESTABLISHED
role: UPSTREAM_RECALL_FAILURE_FAIL_CLOSED_DEMO
```

**采纳 M3C3-A 的理由**：

1. 21 个 `WEAK_OVER_100` query 中唯一满足 B/C pool ≤ 100 的候选——不存在更优人造替代
2. 真实系统必然遭遇"pool miss"，M3 合同 fail-closed 行为需要真实边界样本
3. 用真实检索失败替代人造边界比强行降级 medium 更诚实

**重定位约束**（写入 M3 case YAML `role` 字段并锁死）：

```text
case 3 的验收标准为 "系统在 C pool 与 known positives 交集为 0 时能正确 fail-closed，
不产生虚假排序输出"，而不是 "模型能否在 top-100 内找到正确酶"。

case 3 的 EnzymeCAGE call 允许直接触发 fail-closed 分支，不进入 predict()。
```

**禁止表述**：case 3 不得以任何形式用于讨论"模型 rank 上限"或"weak 难度模型能力"；这两项在当前 D4 冻结域下根本不可测。

### 三案例整体角色说明（必须写入交付材料首页）

```text
Case 1：B-primary + strong pool=1 → pipeline 走通验证 + 污水占位（非排序验证）
Case 2：B-primary + medium 3/8 recall → EnzymeCAGE 排序能力测量（唯一）
Case 3：B 空 → C-fallback → pool ∩ positive = 0 → fail-closed 分支验证

组合覆盖 M3 三种系统行为：B 走通 / B 走通 / B 空 → C → fail-closed。
组合不覆盖 "EnzymeCAGE 效果全景评估"——后者不在 M3 契约范围内。
```

---

## 三、Wrapper 调用模式裁定

### 采纳 **M3I6-A**：LangGraph 与 EnzymeCAGE 运行在同一晨羽环境，直接 Python import

**采纳依据**：

1. 符合老师既有边界"M3 不做 FastAPI 服务化"，零新增授权
2. 首次 init 67.85 s / warm call 0.33–0.56 s，比任何 HTTP 层都更优
3. 数据资产、GPU、Python 3.12.3、模型 v1_20260714 冻结环境全部在晨羽，反向迁移代价大一个量级
4. 消除并发 HTTP 场景下 batch-context sensitivity 与 `last_trace` 线程安全的未验收风险

**M3I6-B（远程 SSH 作业协议）与 M3I6-C（新建 HTTP 服务）本轮不采纳**，不启动，也不在 M3 范围内讨论。

### 学生侧不需要新建 HTTP、不需要 SSH tunnel、不需要 OpenAPI

保持 Python 函数级 wrapper 作为唯一集成入口。

### 导师侧本地承诺的适配动作（不影响学生工作）

导师侧当前 LangGraph 代码 (`src/tools/enzymecage_client.py`) 从 httpx POST 内部改为：

```python
from enzymecage_wrapper import EnzymeCAGERequest, predict
request = EnzymeCAGERequest(
    reaction_smiles=..., enzyme_pool_uids=..., top_k=10, return_ci=True,
)
response = predict(request)
```

节点层调用签名 (`call_enzymecage(reaction_smiles, enzyme_pool_uids)`) 保持不变，学生 case YAML 与本轮已交付的 #2–#5 数据格式亦保持不变。

---

## 四、#2–#5 数据资产验收

### 4.1 外部身份与本地流程

```text
tar.gz SHA256: 734964077898de8dd3abd167fe1285d1d905f33296abe687edc54bcf65858dc1
tar.gz size:   9,334,420 bytes
identity file: m3_agent_data_assets.tar.gz.identity.txt
```

导师侧本地校验流程：拉取 tar.gz → 比对 SHA256 → 解压 → 逐资产字段/规模复核 → 挂载到 `data/` 对应目录。

### 4.2 接受的资产清单（与合同 5.5 节一一对应）

| 合同资产号 | 学生交付路径（tar.gz 内） | 导师侧本地落点 |
|---|---|---|
| #2 | `assets/rhea140/` 四个 TSV | `data/rhea140/` |
| #3 | `assets/route_c/reference_reaction_index.csv.gz`<br>`assets/route_c/reference_morgan_radius8.pkl` | `data/route_c/` |
| #4 | `assets/d4/uid_asset_availability.csv.gz` | `data/d4/` |
| #5 | `assets/route_b/ec_to_uid_query_excluded.csv.gz` | `data/route_b/` |

审计结论已接受：

```text
route-C 非 query 参考反应 = 4,051
route-C Morgan radius = 8
D4 完整资产 UID = 107,705
route-B 唯一完整 EC = 2,320
route-B 唯一 (EC, UID) = 101,638
B/C 对 451 query 的直接泄漏 = 0
```

导师侧接受这些数字为 M3 上游候选构造的证据基线，不再要求学生重新审计。

### 4.3 边界重申

这些数据证明"工具输入可复现"，不证明"候选召回、EnzymeCAGE 排序或真实污水生物学效果优秀"。学生已在提交文档中明确该边界，导师侧接受该边界表述。

---

## 五、微生物侧（占位）

M3 契约本身不包含 enzyme→organism 与 metaTraits 分支；该分支属于 M5。学生已告知微生物侧数据源现状与 metaTraits allowlist 校对将于次日反馈，本轮裁定不覆盖 M5，M5 相关代码节点保持占位状态，不阻塞 M3 端到端启动。

---

## 六、学生下一步动作清单

在导师侧本地适配的同时，学生请推进以下四项，任何一项完成即可提交，无需打包：

### 6.1 生成三个正式 case YAML/JSON（本轮裁定解冻）

要求：

```text
每个 case 一个 YAML 或 JSON，字段至少包含：
  - reaction_sha256 / rhea_master_id / ec
  - canonical_reaction_smiles
  - difficulty_tier / route_used / wastewater_status / role
  - B_pool_uids: [...]
  - C_pool_uids: [...]
  - known_positive_uids: [...]
  - historical_d4_ranks: {uid: rank, ...}
  - mechanism_self_review: 学生原文
  - evidence_provenance: {rhea140_hashes, b1_evidence_ref, a1a_evidence_ref}

case 3 的 role 字段必须显式包含 "UPSTREAM_RECALL_FAILURE_FAIL_CLOSED_DEMO"。
不新增其他 case，不合并 B+C，不改动 pool 成员。
```

### 6.2 晨羽侧材料就位（学生只需放文件，不涉及访问授权）

晨羽访问权限由导师侧另行安排，学生**不需要**提供账号、SSH 公钥或 quota。学生只需确认以下内容在晨羽指定路径可读：

```text
1. 冻结 wrapper 与模型包位于稳定绝对路径（非 observed path），并给出：
   - D4_WRAPPER_ROOT              （已验收 d4b1a wrapper 目录）
   - ENZYMECAGE_V1_PACKAGE_ROOT   （已验收 enzymecage_v1_20260714 目录）
   - ENZYMECAGE_CODE_ROOT         （observed 为
                                    /usrdata/EnzymeCAGE_data/EnzymeCAGE-master，
                                    请复核为稳定路径）

2. 冻结 Python 3.12.3 环境的激活命令（conda activate xxx / source xxx/bin/activate /
   module load xxx，任选其一，导师侧照做即可）

3. GPU 可见性配置手段（wrapper 硬约束 = 1 张 GPU；
   请说明是 CUDA_VISIBLE_DEVICES 手动导出，还是队列脚本自动分配）
```

如任一路径当前只是 observed path，请学生复核后给出稳定绝对路径；若 `enzymecage_v1_20260714` 目录同名但已被替换/未验收，请立即声明并停止 M3-P1 直至重新验收。

### 6.3 数据资产就位（保持晨羽路径不变即可）

学生已把 `m3_agent_data_assets/` 放在晨羽以下稳定路径：

```text
/root/projects/EnzymeCAGE-master/HPC_Returned_Result_Summaries/m3_agent_data_assets/
```

学生**不需要**为导师侧开权限或重复上传，导师侧登录后直接读取即可。仅需在有新增/更新时保持该目录布局不变、tar.gz 的 SHA256 与 identity 文件同步更新。

### 6.4 微生物侧反馈（M5 铺垫，不阻塞 M3）

按学生原计划次日提交，包含 enzyme→organism 数据源现状 + metaTraits allowlist 校对结果即可。

---

## 七、M3-P1 剩余解冻条件

M3-P1 Agent 正式代码将在以下**两项完成后**由导师侧启动实现：

```text
[  ] 三个正式 case YAML/JSON 到位（6.1）
[  ] 晨羽侧稳定绝对路径 + Python 3.12.3 激活命令 + GPU 可见性手段就位（6.2）
```

晨羽访问由导师侧自行完成，不作为解冻条件。

在此两项就绪前，导师侧可推进的本地工作（不涉及案例正式冻结、不占用晨羽资源）：

```text
[  ] enzymecage_client.py 从 HTTP client 改为 Python import wrapper
     （函数签名不变，节点层零改动）
[  ] tar.gz 本地下载 → SHA256 校验 → 解压
[  ] 三个工具的路径/格式适配（.csv.gz 直读、assets/rhea140/、Morgan pkl 结构对齐）
[  ] 本地 mock 三 case dry-run（不调用 EnzymeCAGE，验证 B/C pool 构造正确性）
```

以上四项本地工作与学生并行推进，互不阻塞。

---

## 八、边界与不做项

本裁定不涉及且不改动：

```text
- D4 wrapper 冻结身份（四项 SHA256）
- EnzymeCAGE 模型 v1_20260714 冻结版本
- Python 契约字段（reaction_smiles / enzyme_pool_uids / top_k / return_ci）
- M3D2 B-primary/C-fallback 与 pool ≤ 100 fail-closed 边界
- M4/M5 三层资产架构（本轮仍不启动）
- FastAPI/HTTP 服务化（M3 全周期不启动）
```

本裁定也不构成对 EnzymeCAGE v1 或任何 case 排序结果的真实世界生物学有效性背书。

---

## 九、请学生按 6.1–6.4 顺序推进；6.1 与 6.2 完成即可解冻 M3-P1。
