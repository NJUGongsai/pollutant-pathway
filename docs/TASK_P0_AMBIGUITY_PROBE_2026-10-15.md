# 任务书 — P0③ 歧义探针（信息饥饿实测；金标不出 HPC 模式，2026-10-15）

> 派单：CC。执行者：**受信分析执行代理**（本任务碰参考侧，CC 自选执行者）。
> 上游：GPT hit50 诊断 §5.1（信息区分度假设）+ CC 拍板 P0 三件套。
> 题域标签：**298=RHEA 通用酶学/已见题**；探针≠预注册≠成绩。
> 一句话：模型答题时只看到底物+候选清单（没有酶名/EC/条件），查有多少题
> 「凭模型可见的信息，存在多个说得通的目标」——这个数直接决定「候选证据卡」
> 杠杆要不要立项。

## 一、背景（自包含）

模型真实首调 payload 白名单只有：底物、atom ID、执行图、候选的 ID/产物/
变换引用/共产物（`real_model.py:204`）；builder 登记条件事实为空
（`s5b_builder.py:351`）。假设：若完整可见输入相同的题对应不同合法目标
（或同题候选面兼容多个参考），信息饥饿会限制首位命中。**判据面分歧结论
（分歧组数）只按聚合披露，不涉逐题对错。**

## 二、金标纪律（红线之首，违反=立即停）

1. **参考图/金标永不出 HPC**：判分侧参考数据在 HPC 批根
   `~/ppv1_hpc/batch/chain13_s5b_20261014/reference_graphs/`（只读封存）。
   Phase B 一律在 HPC 上算，**只回传聚合计数**（组数/大小分布/分歧组数/
   多重性分布），任何 per-qid 目标身份、SMILES、金标取值、qid↔答案映射
   **禁止出现在任何产物里**。
2. 本地 Phase A 只用零金标面（manifest 批准字段+payload 模型可见面）。
   上传 HPC 的只有「qid→签名组 id」映射（无金标内容）。
3. 批根只读：不在封存目录写任何东西；聚合产物写 HPC 家目录 `~/` 后拉回。
4. 零模型零网络（除 HPC ssh/scp）；不动 src/tests；不 commit 不 push；
   `PYTHONDONTWRITEBYTECODE=1`；对外数字带 298 标签。
5. 参考数据不可访问/结构对不上=停并报告，不猜不凑。

## 三、数据面

| 件 | 位置 |
|---|---|
| Phase A 输入（本地，零金标） | chain13 synced：manifest（`substrate_smiles`/`repeated_substrate` 批准字段）、payload `search_actions`（decide 的候选集与顺序）、run_identity（model/prompt 配置哈希） |
| Phase B 输入（HPC，只读） | `~/ppv1_hpc/batch/chain13_s5b_20261014/reference_graphs/`；python=`~/ppv1_hpc/venv_v44run/bin/python`（rdkit） |
| HPC 连接 | `ssh -i ~/.ssh/hpc_wuzh02_key -p 65091 -o BatchMode=yes aclhl3hbth@wuzh02.hpccube.com`；坑：中转走家目录不走 /tmp；登录节点只跑轻活（本任务分钟级；若担心被杀改 sbatch 上计算节点） |
| 解释器（本地） | `/Users/cc/miniconda3/envs/depending43/bin/python` |
| 仓根 | `/Volumes/CC/Enzyme_Agent/dependingv43`（HEAD `461844e`，收尾不变+树零 diff） |

## 四、分步（两阶段协议）

### Phase A（本地，零金标）

1. 逐题构造**完整可见输入签名**：`substrate_smiles`（manifest）+ decide
   候选集的有序身份列表（`model_rank_by_id` 键序 + novel 提案身份）+
   run_identity 的 model/prompt 配置哈希。签名算法（规范化/canonical 化）
   写进产物 meta。
2. 分组：a. 签名全等组；b. 仅底物相同组（manifest 有 `repeated_substrate`
   标志——先数它，对不上签名分组如实披露差异）。产出「qid→组 id」映射表
   （本地 gitignored）+ 组规模分布。
3. 把组映射 scp 到 HPC 家目录（仅 qid+组 id+底物身份哈希，无金标）。

### Phase B（HPC 上，碰参考侧，只出聚合）

4. 读批根 reference_graphs（只读）+ 组映射，对每个**底物相同组**计算：
   组内各题参考是否互异（判同/异在进程内完成，只输出同/异标志）。
5. 聚合输出（唯一允许回传的东西）：
   - 组总数/组规模分布（签名组+底物组两口径）；
   - **底物相同且参考互异的组数**（=歧义组数，核心数字）及其覆盖题数；
   - 每题参考边计数的分布（min/max/直方图——纯计数，不含边身份）；
   - （若可安全计算）单题候选面内可匹配不同参考的多重性分布——只在
     判分进程同款受保护逻辑下算，拿不准就标 unknown 不算。
6. 聚合 JSON 写 HPC `~/p0_ambiguity_agg.json` → scp 回本地。

## 五、自检锚点（对不上=停并报告）

| # | 锚 |
|---|---|
| 1 | Phase A 298 题全签名；组规模之和=298（两口径各闭合一次） |
| 2 | manifest `repeated_substrate` 标志数与底物组口径对账（差异如实披露） |
| 3 | Phase B 聚合 JSON 里**不含**任何 qid↔目标映射/SMILES/金标值（交付前自扫一遍正则） |
| 4 | 批根只读（HPC 侧 ls -la 批根 mtime 不变）；树零 diff、HEAD `461844e` |

## 六、产物

```
本地（gitignored）：
  reports/ppv1_s5b/p0_ambiguity_2026-10-15/
    phase_a_signature.py / phase_a_data.json   # 签名+分组+meta（零金标可公开）
    phase_b_agg.json                            # HPC 回传的聚合
    p0_ambiguity_summary.md                     # 大白话+聚合表（298 标签）
HPC 家目录（中转）：
  ~/p0_ambiguity_groups.json / ~/p0_ambiguity_agg.json
  ~/p0_ambiguity_phaseb.py（实体脚本，heredoc 会在满 /tmp 节点炸——写文件再跑）
```

## 七、回传义务（≤20 行）

①签名组/底物组数与规模分布一行；②**歧义组数+覆盖题数**（核心裁决数）；
③每题参考边计数分布一行；④锚点核对（含聚合产物金标零泄漏自扫结果）；
⑤产物路径。主会话抽查：Phase A 产物零金标扫、组闭合算术、聚合 JSON 逐键
检查（只允许计数字段）。

## 八、排障表

| 症状 | 处置 |
|---|---|
| HPC 连不上 | ConnectTimeout 重试一次；再败停 |
| reference_graphs 结构读不懂 | 停并报告结构样例（键名，不含值），等主会话定口径 |
| 签名组全部单题（无跨题组） | 如实报「签名唯一」——歧义裁决转靠 §四.5 单题多重性项；该项拿不准=unknown |
| 登录节点跑 Phase B 被杀 | 改 sbatch 上计算节点跑（脚本体已在 ~/） |
| 聚合产物不小心含敏感字段 | 删产物重跑；交付前自扫是硬门 |

## 九、结果判读框架（写进 summary，不预写结论）

歧义组覆盖面大 ⇒ 「候选证据卡/喂更多信息」杠杆立项证据强；几乎为零 ⇒
信息饥饿假设弱化，缺口主因转向覆盖/编译/选择面（由 P0①② 的账定）。
本探针只出数，不替 CC 拍板。
