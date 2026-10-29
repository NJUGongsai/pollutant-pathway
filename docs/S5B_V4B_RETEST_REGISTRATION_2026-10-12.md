# PPV1 S5b chain12 发车登记（2026-10-12）

状态：`ready_for_real_retest / launched`。正链 Codex D2-R3 复审
（docs/POLLUTANT_PATHWAY_S5B_COSUB_D2_R3_CODEX_REVIEW_2026-10-12.md）
：**D2-R3 通过、S5B-D2-01 清零、P1=[]、显式氢墙追加复审通过、D1-D3
设计线工程收口、chain12 工程侧有条件放行**——本登记即其条件执行
（新登记/身份冻结/硬门封包）。评审事件：正链两度撞额度（12.47M，第二次
发生在 D2-R3 复审中段），定时任务 4:05 自动 resume 续跑出报告，全程
如实入档。

## 一、评审链（本批累积）

- D2 设计线：D1 设计（r32 有条件通过）→ D2 实施（Codex P1=双删绕过
  →R1 修复）→ R1 复审（P1=产物收缩 →R2 修复）→ R2 复审（P1=在位损坏
  →R3 修复）→ **R3 复审全过**（S5B-D2-01 三同族洞全部闭合）
- 显式氢墙：v4b 交付 §十.1 登记项 → 50064933 落地 → Codex D2-R3 复审
  追加核验通过（AtomTool-2 登记）
- v4b 编译墙轮：stereo 消解（compiler-3 碳域+双轴复核）+ 推断枚举扩展
  + 池层计量（已审基线）
- mimo：r28-r34 七轮化学评审（r34 采纳核对+其 D3 面结论被正链订正的
  互证状态如实入档）
- 主会话每轮独立复跑全量（最近 2061/0/16 一致）

## 二、冻结身份（首次真实调用前冻结；任何变化即停批另立新登记）

- 代码：本地 `8da11cb7`（父链 …bd6e836←3725379←…←2e679b31←ea00297e
  ←59db0dac←50064933←8da11cb7）；Chenyu 部署 = 自 bd6e836 起 6 个变更
  src 文件 SHA 逐一字节一致（production/real_model/recorded_source/
  s5b_builder/s5b_compiler/atom_tool）
- 协议版本：**s5b-corpus-retrieval-6**（D2 语义三连修+在位损坏拒）、
  **v43-atomtool-2**（显式氢价态墙放宽）、s5b-pool-policy-5、
  s5b-recorded-source-3、s5b-compiler-3、s5b-rank-policy-1、
  s5b-submit-order-1、s5b-budget-guard-1、s5b-orchestrator-2、
  s5b-real-model-1
- 提示词：PROPOSALS_PROMPT_VERSION `e28b5342…`（与 v2-v4 批相同）；
  模型 GLM-5.3-Flash 现有授权 provider
- profile：depth=1、8 备选、width=2、1 logical/题、format0、
  HTTP retries4、workers/max_in_flight=40、RPM180/TPM2.7M、HTTP cap 1490
- 金额守卫：budget_guard.json cap 60 CNY、0.8/2.8 元/Mtok（沿用值披露）、
  input bound 30000、max_output_tokens 98304；发送前原子预留；
  保守保留/幂等/同源校验全部沿用（金额守卫族五轮复审已闭合）
- 供给：EAWAG recorded 直通（含显式氢墙恢复的 5 题）+ corpus 整串 +
  **corpus 组分级共底物语义（D2，拷贝型 22 spec/15 题，诚实 partial）**
  + 类比模板池
- 评分：零 LLM；主列 hit@1≥119/298；hit@5 150 参考；§9-4 程序门；
  U/H5/L 披露；**NC-12 范围限定**（共底物通道在剥除口径下 matched_strict
  恒 0——r32 CS5 口径，完整参考可 strict）
- 题源：ec298_gold_readonly/questions.jsonl SHA 9f5955d4…（发车日实核）

## 三、期望登记（诚实，非承诺）

- 供给增量：显式氢墙 +5 题（strict 层，72→77 编译成功）+ corpus 拷贝型
  15 题（partial 层，hit@1 贡献=0）→ **U 预期 106→~111±，hit@1 76→
  ~79±：119 本轮如实不达**
- 本批价值：干净兑现 D2 语义 + 显式氢墙 + 全部已审工程身份的首个真实
  批；为 P4 模型配对（教师提效包阶段三）钉死当前配置基线
- 298 题域标签、seen298_post_hoc_repair_check 诚实标注

## 四、批与执行

- 新批根：`/usrdata/EnzymeCAGE_data/workspaces/s5b_298_v4b_20261012`
- 执行链：chain12（SHA 门→envcheck→build --recorded-source→approve→
  budget→冒烟 10 前缀→闸→全量 298→零 LLM 判分→§9-4+U/H5/L→hit@1
  119 判定）
- 停批条件沿 v4 登记（401/403/402 停新付费、金额/HTTP/输出上限、身份
  变化即停）
