# RUN_JOURNAL — EC298 HIT60 S1 dev 三臂跑分(代理D)

进度账本:每阶段追加(时间 UTC+8 / 命令 / SHA / 数字 / 费用)。接任者按本文件续跑。
预算:总批准 ¥50;本段(代理D)硬顶 **¥22**,超即停。判定规则只认
[PREREGISTRATION.md](PREREGISTRATION.md);配置差异只认 [ARM_CONFIG_DIFFS.md](ARM_CONFIG_DIFFS.md)。

---

## 0. 发车前(2026-09-29,零付费调用)

- 读毕:任务书 T1 / PREREGISTRATION / ARM_CONFIG_DIFFS / split_manifest / 三配置 /
  Phase D 复测 driver + 登记。本地 `dev_questions.jsonl` SHA 复核 =
  `8869cd05…36 0c`(56 行)与冻结一致;`dev_gold.jsonl` SHA = `d285dc0b…62f2a`(敏感,仅记 SHA)。
- 价格快照:自 reports/phase_d/retest/provider_price_snapshot_2026-09-29.json 抄录,
  2026-09-29 重取阿里云官方页核对一致(input ¥0.8/M、output ¥2.8/M、cache ¥0.23/M、
  RPM 200、TPM 3M、max_in 1,048,576、max_out 131,072)。**三臂同值回填**。
- 配置回填(发车前、零付费调用):`batch_cost_cap_cny` C0=8.0 / E2=5.0 / E3=6.0
  (PREREG §2/§5 分摊;费用治理字段,已在 ARM_CONFIG_DIFFS §4.1 补登记);
  新 SHA:C0 `b1480fa0…b406c`、E2 `7a05ea59…5d8de`、E3 `74cbf5eb…620b0`(§4.1 全值)。
  另在 §4.1 预登记 E3 对照接力条件式(PREREG §3.2)。
- 新脚本(本地 `reports/phase_s1_hit60/scripts/`,随包部署):
  - `s1_dev_driver.py` — identity(含 dev 题卷→三字段白名单转换,fail-closed SHA
    8869cd05…)/run(20 worker,20 in-flight,三臂同值)/post(归并+终态+账目+门禁)。
  - `s1_dev_score.py` — 零 LLM 评分器,exam_v2 同口径(import 其 load_gold/
    agent_candidates/first_hit_rank);分母恒 56,空答留分母;@1/@3/@5、空答率、
    spurious 率;`--pair` 出四格/净赢/翻转数。合成夹具自检 **PASS**(6 题
    夹具:含不可解析占名次、双金标、空答、spurious、@1 翻转 2 例)。
  - `s1_dev_smoke.py` — 单路线计费烟测(pb_0002 底物,**E2 语义 temperature=0.0**,
    一次烟测同时验证连通/计费/温度通道;≤3 次调用;独立账)。
- 本地身份(发车前锚):代码聚合 SHA `fff3b417…4972c`(50 文件,含代理C T4+E2/E3
  开关,未提交工作树);prompts rank `864a5f30…` / analogy `6d228935…` / novel
  `1aa41393…`;资产清单 `ac9b97b8…48e6c`(22 文件 166,849,006 B,与 Phase D 一致)。
- 远端环境实核:`V43_LLM_MODEL=ZHIPU/GLM-5.3-Flash`(**非 kimi-k3 系**,温度臂可发**;
  base_url/key 存在(不打印);`.venv` python 3.11.16 / rdkit 2026.03.6;128 核 503GB,
  磁盘余 242T。
- **部署偏差登记**:任务书说 `.env` 从 `../dependingv43/.env` 拷贝,该文件不存在;
  dependingv43 实际凭证文件 = `/usrdata/EnzymeCAGE_data/workspaces/.dependingv43-dashscope.env`
  (Phase D 同源,root:600)。改从该文件拷贝至新工作区 `.env`(chmod 600,凭证不打印不入仓)。
- 本地全仓回归:`pytest tests/ -q` 运行中(零费用);结果见下节。

## 1. 部署(2026-09-29 完成,零付费调用)

- 新工作区 `/usrdata/EnzymeCAGE_data/workspaces/dependingv43_s1/`(不碰既有
  dependingv43 任何内容;其 .venv/assets 只经符号链接只读复用)。
- 包内容:`src/pathway_v43`(50 文件,未提交工作树 = 代理C T4+E2/E3 开关版)、
  `configs/`(三 dev 配置[已回填]+prompts+dev_batch+phase 基线配置)、
  `scripts/`(仓分析脚本 + 本轮三脚本)、`tests/`(54 文件)、`pyproject.toml`。
  COPYFILE_DISABLE=1 打包,远端 `find -name '._*'` = **0**(AppleDouble 零污染)。
- 符号链接:`.venv → ../dependingv43/.venv`(python 3.11.16/rdkit 2026.03.6);
  `assets → ../dependingv43/assets`(verify_repo_manifest 对 symlink 根取物理
  边界 = 自洽部署,实测通过)。
- `.env`:自 `.dependingv43-dashscope.env` 拷贝,chmod 600(root),凭证零打印。
- 题卷:`exam/dev_questions.jsonl` SHA 复核 = `8869cd05…36 0c` ✓;
  金标 `exam/restricted/dev_gold.jsonl` SHA = `d285dc0b…62f2a` ✓,权限 **600 root**
  (只在评分进程读)。
- **远端↔本地身份逐一相同**:代码聚合 `fff3b417…4972c`(50 文件)、
  prompts(rank `864a5f30…`/analogy `6d228935…`/novel `1aa41393…`)、
  资产清单 `ac9b97b8…48e6c`(22 文件 166,849,006 B)。imports ok。
- `RELEASE_MANIFEST.sha256`:249 行(部署逐文件 sha;`.env` 凭证不进清单),
  清单自身 SHA `4c754fb6…b278`。
- 远端评分器合成夹具自检 **PASS**(与本地同一夹具输出一致)。
- 测试修正登记:代理C 的 `tests/test_s1_arm_switches.py` 两用例钉的是
  **施工时占位态**(cap/snapshot=null);按 ARM_CONFIG_DIFFS §3/§4.1 部署回填
  契约更新为钉 **§4.1 登记的回填值**(pairwise diff 集 + batch_cost_cap_cny;
  帽 C0=8.0/E2=5.0/E3=6.0;快照 model_id=ZHIPU/GLM-5.3-Flash、checked=2026-09-29)。
  该文件 28/28 过;本地全仓重跑中,远端全仓回归 nohup 运行中(均零费用)。

## 2. 回归与烟测(2026-09-29)

- 本地全仓回归(回填后配置):**508 passed / 0 failed**(493s;含修钉后的
  test_s1_arm_switches 28/28)。
- 远端全仓回归:首跑 504+2 失败 → ①`test_engine_asset_parity::test_arms_ran_on
  _expected_roots`:assets 符号链接拓扑(断言钉物理路径前缀)→ **改物理拷贝**
  (166,885,952 B,61 文件;manifest sha 复验 = `ac9b97b8…` 不变),复跑 10/10 过;
  ②`test_prediction_recovery::test_dangling…`:负载时序 flake,隔离复跑过。
  复跑(物理 assets 后):**505 passed / 1 failed** — 又一个 crash-injection
  时序用例(`test_crash_after_response_persisted…`),隔离复跑过、整文件复跑
  时好时坏、本地恒绿 → 判定:共享机高负载下崩溃注入时序 flake,非代码回归
  (两轮失败的用例各不相同且全部隔离可复绿)。
- **计费烟测(首个付费调用,2026-09-29T17:35Z)**:`runs/s1_dev_smoke_20260929T173517Z`,
  身份 cafc11d0,pb_0002 底物(已核原串与 cn 均不在 dev 56 题底物集),
  **E2 语义 temperature=0.0**:1 调用 / usage 齐 / 0 孤儿 / **温度逐调用留痕
  1/1 带 0.0(API 实收,无 400)**,completed + 导出 ok。费用 **¥0.0275**
  (2226 入 / 9197 出)。烟测账独立,不入臂账。

**费用台账(累计已花):** 已知 ¥0.0275;作废批预留见 §3。

## 3. C0 首批作废与基础设施修正(2026-09-29,进入任何判定之前)

- C0 首批 `runs/s1_dev_C0_20260929T175041Z`(身份 f9769daf,17:50Z 发车,
  18:10Z 完成):56/56 合法终态、pairing gate ok、0 429/0 forbidden/0 孤儿,
  **但 90 发 58 超时**(llm_timeout_s=300;usage-ok 调用中位 192s/最大 292s,
  紧贴墙)→ **58/90 缺 usage,费用账不完整**(已知部分 ¥0.862 + 输入预留
  ¥0.037;超时调用服务端生成不可证,输出侧无上界)。
- 处置(依 PREREGISTRATION §1.4/§2.1):该批**作废不进判定**(已写
  `_VOIDED.json`;其 scoring 仅留诊断);修基础设施:`llm_timeout_s`
  300→**3600**(Phase D 同款拆墙值;三臂同值,预登记 diff 纪律不破坏),
  新指纹登记于 ARM_CONFIG_DIFFS §4.2(C0 `313af38b…`/E2 `8ba59742…`/
  E3 `6770f3c3…`),配置已同步远端(逐字节同 SHA)。触发依据 = 超时账目,
  非分数(修正决定先于任何臂间对比)。
- **费用台账:作废批记账 ¥6.93** = 已知 ¥0.862 + 输入预留 ¥0.037 +
  超时输出保守预留 ¥6.0(58 × ~36.7K 输出 token 上界估计;真实账单回填前
  按此占位)。**累计(含烟测)= ¥6.96 / ¥22**。余 ~¥15:重跑 C0-a + C0-b
  + E2×2 + E3,按 Phase D 单价 56 题约 ¥1-2/批,预计落点 ¥11-15。
- 该作废批诊断评分(不进判定,仅记录):@1 3、@3 11、@5 11、空答 17、
  spurious 28(超时截断下的退化读出,不代表臂真实水平)。

## 4. C0-a 重跑(3600s 墙)— 完成,进判定

- `runs/s1_dev_C0_20260929T182619Z`,身份 **a20ba9b9**
  (sha `a20ba9b92525b95aa5e52b9709e7abd169afc47e18ba423272755545d00dd46d`),
  18:26:25Z 发车,~18:41Z 完成(约 15 分钟)。
- 完整性:56/56 合法终态、`completed`、pairing_gate ok、0 failed/export/missing;
  **50 发 / 0 缺 usage / 0 孤儿 / 0 429** → 费用账完整:**¥2.5069**
  (快照价计;thinking 按输出)。
- **C0 基线(dev 样本 a):@1=8(14.29%)/@3=16(28.57%)/@5=19(33.93%);
  空答 1;spurious 36;miss 37**。逐题表 `scoring/per_question.tsv`。
- **费用台账:累计已花 = 烟测 0.0275 + 作废批(已知 0.899+预留 6.0)+
  C0-a 2.5069 ≈ 记账 ¥9.43(其中真实已知 ¥3.40)/ ¥22 硬顶。**

## 5. C0-b 二次采样 — 完成,进判定

- `runs/s1_dev_C0_20260929T190054Z`(身份 a20ba9b9,同身份新批根),19:00:54Z
  发车,~19:17Z 完成。56/56 合法终态、gate ok;**49 发 / 0 缺 usage / 0 孤儿**;
  费用 **¥2.3159**。
- **C0 样本 b:@1=9(16.07%)/@3=16(28.57%)/@5=20(35.71%);空答 0;spurious 36。**
- **F_C0 = 7**(C0-a vs C0-b cn@1 结果翻转 7 题;含首位产物变化的宽口径 30 题)
  → **提供方缺省温度(T=1.0)下非确定,E2 臂必要**(PREREG §2.1 分支:
  F_C0≠0 → 继续 E2 两次采样)。C0 均值:@1 8.5、@3 16.0、@5 19.5、空答 0.5。
- **费用台账:记账累计 ≈ ¥11.75 / ¥22(真实已知 ¥5.75);余 ~¥10.25。**

## 6. E2 温度臂(temperature=0.0)

- 发车前核对:模型 `ZHIPU/GLM-5.3-Flash` 非 kimi-k3 系;烟测已实证 API 收
  temperature=0.0(1/1 调用留痕)。
## 6. E2 温度臂 — 完成,判 **rejected**

- E2-a `runs/s1_dev_E2_20260929T192739Z`(身份 1c0e9a73,19:27Z 发车):56/56
  合法、gate ok、48 发/0 缺 usage/0 孤儿、**¥2.7197**;**@1=8/@3=18/@5=20、
  空答 1、spurious 35**;温度逐调用留痕 **48/48 带 0.0**。
- E2-b `runs/s1_dev_E2_20260929T201603Z`(同身份新批根,20:16Z 发车):56/56
  合法、49 发/0 缺 usage、**¥2.1686**;**@1=8/@3=16/@5=19、空答 1、spurious
  36**;温度留痕 **49/49**。
- **判定(PREREGISTRATION §2.1 原文)**:F_E2=6,F_C0=7(F_E2+F_C0=13≥3 →
  符号检验适用:翻转 2×2 = both 3 / C0-only 4 / E2-only 3 / neither 46,
  不一致对 n=7,双侧 **p=1.0000 ≫ 0.05**;另一口径 F_E2=6 > max(0,7−3)=4)。
  两判据均不成立 → 方差未显著减少。均值条件本已满足(E2 均值 @1=8.0 ≥
  6.5)但不足以判 win。次级回退全守:@5 均值 19.5 = C0 19.5;空答均值
  1.0 vs 0.5(+0.5 ≤ 2);spurious 均值 35.5 vs 36(未升)。
  → **E2 = rejected**(均值未动、方差未显著减少;提供方 T=0 下仍有 6/56
  残余翻转,如实披露;单次采样不证因果)。
- **接力决定(先于任何 E3 分数,已登记 ARM_CONFIG_DIFFS §4.3)**:E2 非
  dev_candidate → **E3 对照 = C0**(直接配对,温度行为与 C0 一致)。
- **费用台账:记账累计 ≈ ¥16.64 / ¥22(真实已知 ¥10.64)。**

## 7. E3 窗口臂(max_candidates_for_ranking 8→16,对照 = C0)

## 7. E3 窗口臂 — 完成,判 **rejected**;止损门触发

- `runs/s1_dev_E3_20260929T204506Z`(身份 f77b2991,20:45:06Z 发车,~21:10Z
  完成):56/56 合法终态、gate ok、48 发 / 0 缺 usage / 0 孤儿 / 0 429、
  0 超时;费用 **¥2.2325**(≤ 对照 2.5× 与 ¥6 帽)。
- **E3:@1=9(16.07%)/@3=15(26.79%)/@5=16(28.57%);空答 0;spurious 40。**
- 判定(§4.3 登记口径):净赢 @1 vs C0-a **+1**、vs C0-b **0** → 两样本均
  ≥3 的门未达;**@5 净降 −3 / −4(回退上限击穿)**;spurious 40 > 36(击穿);
  空答 0 ✓。→ **E3 = rejected**。
- 四格(@1):vs C0-a both 3 / E3-only 6 / C0-only 5 / neither 42;
  vs C0-b both 6 / E3-only 3 / C0-only 3 / neither 44。

## 8. 身份核对与判定合规(2026-09-29)

- 判定批次配置 diff(远端 batch_identity.json 机读):E2 vs C0 = {arm,
  batch_root, batch_cost_cap_cny, temperature};E3 vs C0 = {arm, batch_root,
  batch_cost_cap_cny, max_candidates_for_ranking} — 均为登记字段,无越界。
- run_identity policy 块逐臂:C0 (temp null, 窗 8) / E2 (temp 0.0, 窗 8) /
  E3 (temp null, 窗 16);E2 两批 97/97 调用留痕 temperature=0.0,C0/E3 批
  该键 0 条。同臂两采样同身份新批根;跨身份 resume 由
  batch_identity_conflict_check 阻断(代码路径,引擎既有测试覆盖)。
- **止损门(PREREG §4)**:E2 净赢 −0.5 题(−0.89pp)、E3 +0.5 题(+0.89pp)
  → **累计 ≈ 0.0pp < +8pp → 触发**:S1 冲刺停止,止损结论;E1 不启动。
- **费用台账(终)**:已知合计 **¥12.87**(烟测 0.0275 + 作废批已知 0.862 +
  输入预留 0.0365 + C0a 2.5069 + C0b 2.3159 + E2a 2.7197 + E2b 2.1686 +
  E3 2.2325);作废批超时输出不可证上界保守预留 ≤¥6 → 记账口径 ¥18.87 <
  ¥22 硬顶,未触闸。真实账单回填前不报"已核总额"。
- 汇总:[ARMS_C0_E2_E3_RESULT.md](ARMS_C0_E2_E3_RESULT.md)。

## 9. 拉回本地产物

- `reports/phase_s1_hit60/artifacts_remote/`:五批 _arm_summary/_identity_phase/
  _VOIDED、scoring(score.json + per_question.tsv)、三份 pair json、
  烟测摘要、RELEASE_MANIFEST.sha256、remote pytest 两轮日志、远端配置
  SHA 复核(不含金标、不含 .env)。







## 10. E1 协议臂(rank_candidate_presentation v2;2026-09-30,用户批准补跑,帽 ¥6)

**授权与登记(先于任何 E1 付费调用)**:止损门在 E3 后已触发(§8),E1 由
用户明示批准补跑(预算帽单批 ¥6;总盘 ¥50 已记账 ¥18.87)。设计 =
[e1_design/](e1_design/E1_DESIGN.md)(E1_DESIGN.md + 两 diff,设计代理 E,
只设计不实施);判定规则不变,仍只认 PREREGISTRATION.md。

### 10.1 实施(本地,零付费调用)

- 两个 diff `git apply` 一次通过(基于当前工作树,无需手工适配 diff 本身):
  policy.py 开关 `rank_candidate_presentation`(默认 v1)/ llm_client.py
  `prompt_versions` 常驻键 `rank_candidates_v2` / prediction.py v2 分层卡 +
  密度预算 + 解析契约 / nodes.py prompt 选择与解析同开关;新增
  `configs/prompts/ranker_v2.md`。
- **一处最小手工适配(登记)**:E1_DESIGN §3.1 文本要求 uniform 候选字段
  "不恒真不上提,**该字段仍在逐卡层**",diff 原实现会把非恒真字段静默丢出
  任务书;已按设计文本补齐(非恒真键留逐卡层,预测预算前加入;
  `_rank_uniform_facts` 拆出恒真性核对)。正常 rank 任务四字段由入围资格
  保证恒真,本适配只影响病态输入,不改变真实载荷。
- **v1 黄金对照(对 reverse-patch 副本逐字节核对)**:v1 缺省/显式 payload
  SHA256 = `f7742643b71d5e55a2869bd7f2a49776b7a401b1ae2c488cf02e69303f875065`,
  打补丁前后逐字节一致(v1 路径零改动实证)。
- 测试(全离线零 API):test_prediction_task.py 增 12(v2 载荷形状/v1 黄金/
  解析 fail-closed 七坏形/合法 hold+完整 order/v1 回归钉)、新
  test_s1_e1_rank_v2.py 18(密度两级截断+确定性+病态耗尽/提示词枚举镜像/
  prompt_versions 四键/开关值域 fail-closed/身份+resume 拒绝)、
  test_prediction_workflow.py 增 3(端到端:prompt SHA=ranker_v2、hold_kind
  落 prediction.json、漏卡解析失败走有界重试 1+2)。测试修正登记:
  test_prediction_real.py 的 prompt_versions 键集钉 3→4(E1 设计规定的常驻
  第四键);test_s1_arm_switches.py 扩为四配置 diff 纪律(E1 入 ARMS,费用帽
  E1=6.0,EXPECTED_DIFF_FIELDS +rank_candidate_presentation)。
- 新配置 `configs/s1_dev_E1.json` = C0 + 唯一差异
  `prediction_policy_overrides.rank_candidate_presentation="v2"`(SHA
  `975c6e3a8d6464ce180100a577ff1babcfcf0ebbbcaec2e9e0fb4a4523cf7d06`),
  对 C0 机读 pairwise diff 恰为 {arm, batch_root, batch_cost_cap_cny=6.0,
  rank_candidate_presentation};llm_timeout_s=3600/价格快照/并发与 C0 同值。
  ARM_CONFIG_DIFFS §1/§2/§4.4/§5 已补登记(发车前)。
- 本地全仓回归:**541 passed / 0 failed**(529s;基线 508 + 33 个 E1 新测试)。

### 10.2 部署与烟测

- E1 增量 7 文件上行(4 src + ranker_v2.md + s1_dev_E1.json +
  scripts/s1_dev_smoke_e1.py),逐一 sha256 与本地一致;find `._*` = 0。
- RELEASE_MANIFEST 增 E1 delta 节(4 行 src 更新 + 3 行新增,注释块登记
  增量;**顺带修正前任遗留**:C0/E2/E3 三行 manifest 停在 §4.1 旧值,刷新为
  §4.2 实际 SHA(文件本就正确,清单行未跟上);pyc 行为易变噪声,不入结论)。
  新清单 252 行,自 SHA `fd0a4812…f5558d8`;sha256sum -c(除 pyc)全绿 =
  底座其他文件未动。
- 远端零费用 imports 烟测:代码聚合 SHA `3fe38c86…39c3c`(50 文件,与本地
  逐字节一致)、prompt_versions 4 键、ranker_v2 SHA 匹配、v3 值 fail-closed。
- **计费烟测(E1 语义,v2 通道端到端)**:`runs/s1_dev_smoke_e1_20260930T023119Z`
  (身份 b00d1ce1,pb_0002 路线,1 调用/0 缺 usage/0 孤儿,**¥0.024**,独立账):
  任务 schema v4 + 分层卡 + candidate_set ✓、调用产物 system_prompt_sha256 =
  ranker_v2.md SHA ✓、**真实模型响应按 v2 契约一次解析成功(selected,完整
  order)** —— E1 最大风险(解析变严)最前哨通过。

**费用台账:E1 段已花 = 烟测 ¥0.024(独立账)。**

### 10.3 E1 批次 — 完成,判 rejected

- `runs/s1_dev_E1_20260930T023702Z`,身份 **f6a6e18b**(sha
  `f6a6e18b4e76d7f062a3e58a105a6115a089bc39388655b5535a52acdf0bb4c1`),
  02:37Z 发车(20 worker,与三臂同值),~03:06Z 完成(约 29 分钟)。
- 完整性:**56/56 合法终态 completed**、pairing gate ok、0 failed/export/missing;
  **48 发 / 0 缺 usage / 0 孤儿 / 0 429** → 费用账完整:**¥2.2841 ≤ ¥6 帽**。
- **E1:@1=10(17.86%)/@3=16(28.57%)/@5=19(33.93%);空答 1;spurious 36。**
- 判定(§4.4 发车前登记口径,对照 = C0-a/C0-b 两样本):
  - 净赢 @1:**vs C0-a +2**(10−8)、**vs C0-b +1**(10−9)→ 两样本均 ≥3 的门
    **未达** → 主终点失败。
  - 回退:@5 净 0(vs a)/ **−1**(vs b,≤2 归因带内:两个 C0b-band 题在 E1
    掉为空/miss,见 10.4);空答 1 ≤ 1 ✓;spurious 36 = 36 ✓;费用 ✓。
  - → **E1 = rejected**(次级全守,但主增益不足;无红线击穿)。
- 四格(@1):vs C0-a both 4 / E1-only 6 / C0-only 4 / neither 42;
  vs C0-b both 7 / E1-only 3 / C0-only 2 / neither 44。
  翻转:vs a 10 题 / vs b 5 题(宽口径首位产物变化均 28)—— 与 C0 自身
  翻转带(F_C0=7)同量级。

### 10.4 机制诊断(E1_DESIGN 诊断口径)

- **路由面**:全批 48 次 LLM 调用 = 42 novel + 3 analogy + 3 rank;E1 机制
  (rank v2)只触达 **3/56 题**,且三臂(C0-a/b、E1)路由分布完全相同 ——
  差异只在 3 个 rank 任务的载荷/解析契约。
- **解析面(完全干净)**:48/48 一次解析成功(0 重试、0 解析失败、0 hold);
  3 个 rank 任务全部 selected 且 order 完整(长度 2/4/2);hold_kind 分布空。
  解析变严风险(R1)未发生。
- **机制题面**:3 个 rank 题在 E1、C0-a、C0-b **全部 miss**(rank=None)——
  E1 的杠杆落在三臂都排不进金标的题上;**@1 净赢 +2/+1 全部来自 novel 模式
  的采样噪声**(提供方非确定,F_C0=7 先例),不能归因于 E1 机制。
- **L1 型敏感读出(辅报)**:C0-a 金标@2-5 带 11 题 → E1 4 题升至 @1、1 题降
  (2→3);C0-b 带 11 题 → 3 题升 @1、2 题掉空(…068_S04、…079_S02)。
  升降两向并存且全部发生在 novel 模式题上 —— 与噪声解释一致。
- 密度机制读出:rank 任务候选块实测 median 1,278 / max 2,912 字符/卡集,
  截断未触发正常路径(预算 2× 余量设计成立)。
- **dev 集与池级前提的落差(登记)**:E1 设计依据 S0 池级结论(L1-rank 23 +
  L2-rank 13);56 题 dev 切片里 rank 路由仅 3 题、金标@2-5 带对 rank 机制
  可及的题 = 0 —— 池级机制在 dev 上**无统计可判的承载面**,这是 E1 在 dev
  上"测不出增益"的结构性原因(非机制被证伪;298 全卷上承载面更大)。

### 10.5 判定后账目与止损门

- **费用台账(终)**:已知合计 = 代理D ¥12.87 + E1 段(烟测 0.024 + 批次
  2.2841)= **¥15.18**;作废批超时输出保守预留 ≤¥6 → 记账口径
  **¥21.18 / ¥50 总盘**(本段 E1 帽 ¥6,实用 ¥2.31)。
- **止损门重估(§4,E1 判定点)**:E2 −0.89pp、E3 +0.89pp、E1 +2.68pp
  (净赢 1.5 题两样本均值)→ **累计 ≈ +2.7pp < +8pp,止损门维持触发**;
  S1 四臂全部判定完毕(E2/E3/E1 均 rejected,C0 基线 @1≈15–16%)。
- 汇总更新:[ARMS_C0_E2_E3_RESULT.md](ARMS_C0_E2_E3_RESULT.md) §E1;
  E1 产物已拉回 `artifacts_remote/s1_dev_E1_20260930T023702Z/`、
  `s1_pair_E1_vs_C0{a,b}.json`、烟测摘要(不含金标、不含 .env)。

## 11. 勘误节:作废批真实账单回填核查(2026-09-30,收尾代理,零 API/零 LLM)

- 授权:用户 2026-09-30 授权机械尾巴清理;本节**只追加勘误,不改写上文
  任何数字**。核查对象 = §3 作废批,远端
  `/usrdata/EnzymeCAGE_data/workspaces/dependingv43_s1/runs/s1_dev_C0_20260929T175041Z`
  (身份 f9769daf);费用口径 = 价格快照 2026-09-29(input ¥0.8/M、output ¥2.8/M、
  cache ¥0.23/M,thinking 按输出)。
- 远端核对(全部只读命令,零 API):
  - `_VOIDED.json` SHA256 `f4015407…d13756`(与本地拉回副本逐字节同):90 发 /
    58 超时 / 不进判定。
  - `_arm_summary.json` SHA256 `9a8b634f…29860`(与本地拉回副本逐字节同):
    usage 记录 32/90(prompt 40,038 / cached 6,400 / completion 297,709 /
    reasoning 281,966);known_usage ¥0.862;输入可证预留 ¥0.0365(45,596 tok
    上界);输出侧 `unprovable_no_request_output_cap`。
  - 逐条复核 90 个 `runs/*/results/*/prediction_response.a*.json`:32 条带
    usage(OpenAI 风格键 prompt_tokens/completion_tokens);**58 条全部
    `error_kind=timeout`、elapsed 300.1–300.2s、`usage={}`、`request_id=null`**
    ——响应从未到达客户端,客户端侧零用量痕迹。
  - 已知部分复算 = (40,038−6,400)×¥0.8/M + 6,400×¥0.23/M + 297,709×¥2.8/M
    = **¥0.8620**,与 _arm_summary 登记值一致。
  - 账单类文件搜索(workspaces/dependingv43_s1 与 dependingv43、/root、/tmp;
    关键词 bill/invoice/usage/账单,maxdepth 3)= **0 命中**,机器上无任何已导出
    的供应商用量/账单件。
- **结论:作废批真实账单不可回填。** 原因:① 58 条超时调用的用量只存在于
  DashScope/百炼账户账单侧——服务端生成是否完整发生、各占多少,客户端记录
  无从证明(引擎原判 `unprovable_no_request_output_cap` 成立);② 拉取供应商
  账单需走控制台或计费 API,本轮红线零 API,.env 凭证仅限模型推理不挪用;
  ③ 远端无任何账单导出件(如上搜索)。
- **已知上下界(维持 §10.5 记账口径,不改写)**:下界 = 已知 ¥0.8620 + 输入
  可证预留 ¥0.0365 = ¥0.8985;输出侧无上界证据 → 按用户授权预留帽 **≤¥6.0**
  继续占位,记账口径 **¥21.18/¥50 不变**。量级披露(仅参照,不改变记账):
  作废批 32 条 usage-ok 调用输出 median 9,248 / max 18,180 tok;重跑 C0-a
  (3600s 墙、同 56 题)输出 median 14,089 / max 51,874 tok——¥6.0 是预留帽
  而非数学上界(严格按 C0-a max 估 58×51,874×¥2.8/M≈¥8.4;若服务端断连即停
  则远低于此;两端均不可证,故维持占位)。
- 真实账单若要落地,唯一路径 = 供应商控制台用量导出(账号持有人操作,非代理
  职权);落地后回写本节,同样只追加。
