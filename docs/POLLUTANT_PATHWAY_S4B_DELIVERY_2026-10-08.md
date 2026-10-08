# pollutant_pathway_v1:S4b 收尾批交付书(正式文件导出与 v3 有损
# 投影,2026-10-08)

- 基线:直接父 `fc40605819201ae4a7101fc500b19083d78383b0`
  (S4a 批次提交);开工 HEAD = fc40605(工作区仅评审侧未跟踪文件
  + 本批 S4b 改动,已核对 `git status`);本批 = S4 任务书 §7
  S4b 边界 + S4a 复审(备用通道 tokeasy,P1 清零)§6/§7 交接的
  **一次性实施**:**只做 S4b**(正式文件导出/文件级 G02/v3 有损
  投影/完整公共链/legacy 字节专项),不做 S5。
- 判据状态:ppv1-criteria-v1 已冻结;**本批未修改冻结判据正文**
  (判据一–五与 0d/0e/0f 语义零触碰;mimo 请求 v17 按版本规范附
  "语义未改变"声明,见 §17)。
- 证据根:`docs/review_evidence/ppv1_s4_impl_2026-10-08/s4b_r1/`
  (README + manifest.json + SHA256SUMS,40 文件;全部执行在仓外
  新 tmp 或新 worktree;G01 控制器与 legacy 字节探针随目录,均
  拒绝已存在输出目录)。

## 0. 结论一句话

S4b 十项全部落地:公共 start/resume 在 S4a endpoint/原生对象之后
把结果落为 **run 目录正式文件导出**(`native_export/<export_
digest>/payload.json + manifest.json`;payload = 原生结果全量载荷,
manifest = graph facts digest(15 张事实表逐表内容 digest,PPV1 的
graph revision 等价身份)+ 权威引用 + 策略 hash 新鲜度锚),首消费
读取按固定次序 fail-closed(五类结构化拒:missing/corrupt/version/
policy/stale/reference),**G02 七测**全过(含独立子进程逐字节一致
与自洽重写不可洗白);v3 适配为**显式 lossy_projection**(原生引用 +
十二条固定信息损失 + 不可投影摘要 + 反向消费禁止 + 只读反查);
legacy/export_v3 冻结路径经**当前树 vs 直接父 fc40605 专项字节
对比**:四产物逐字节一致、52 份 legacy code_identity 聚合保持
18007e6a…;完整公共链(崩溃→resume→endpoint→导出→投影→读取→
replay)实测零新业务写;PPV1 全量 **932 passed/0 skipped**(
914 存量 + 18 新 S4b,零存量行为改动;仅 2 个 profile 版本字面量
更新如实披露);直接父同字节对照 = 新文件 **18 collection 红(
模块缺失)+ 更新测试 2 字面量红 + 21 正控绿**,0 行为红;G01
**1534 passed/8 skipped/17 deselected exit 0(294 输入)**;
production.py 与全部 legacy/冻结共享核心逐字节同父。**S4b 复审
通过前不宣布完整 S4**(自审 §对齐证据)。

## 1. S4b 十项内容:源码位置与前后行为

| # | 任务书 §7 S4b 项 | 源码位置(file:line) | 前行为(fc40605) | 后行为(本批) |
| 1 | 路径原生正式导出(文件级) | `src/pathway_v43/pollutant/native_export.py:275-346`(export_native_result:payload+manifest 落盘)、`native_export.py:102-120`(固定策略)、`native_export.py:215-259`(权威引用/不可变写)、`runflow.py:1347-1394`(公共链接线)、`profile.py:220-230`/`506-509`/`671`(版本注册) | 原生结果只到 S4a 对象底座(artifact) | run 目录 `native_export/<export_digest>/` 文件对;同 digest 不可变;summary 暴露 export_digest/dir/payload_sha256 |
| 2 | 确定性重复生成 | `native_export.py:102-120`(canonical 无时间戳策略)、`native_export.py:275-345`(export_digest=content_hash(manifest 核心))、测试 G02-①②(含独立子进程) | 对象级同 digest(S4a) | **文件级**:同进程/跨进程/崩溃恢复后重复导出逐字节一致;事实变化=新 digest 新目录,旧文件保全 |
| 3 | stale/integrity 识别 | `native_export.py:359-523`(read_native_export:固定次序核验)、`native_export.py:139-188`(graph_facts_digests:15 表内容 digest) | endpoint 记录级 stale(S4a) | 文件级:export_missing/manifest_corrupt/payload_corrupt/version_unknown/digest_mismatch/reference_mismatch/policy_stale/export_stale 八 kind;权威与事实 digest 从独立权威重算 |
| 4 | 全量事实导出 | `native_export.py:139-259`(15 表 facts digest + artifact 引用(含冻结计划)+ 权威引用);payload = `native_result.py:144-403` 全字段组(共同产物/备选/不同来路/条件/依赖/audit/proof scope/deferred 两类/budget/stop/endpoint) | 对象字段组已备未落导出契约 | 导出 payload 全量保留;manifest 覆盖 15 张事实表 + 四类 artifact 引用;S4b 修正 S4a 聚合缺口(见 §5 native_result 行) |
| 5 | v3 lossy_projection 适配 | `src/pathway_v43/pollutant/v3_projection.py:253-323`(build:lossy 标记/原生引用/损失清单/不可投影摘要/边界)、`v3_projection.py:86-152`(十二条固定损失)、`v3_projection.py:187-251`(逐事件步骤,不按 CN 合并) | 未实施(边界声明) | v3 形状 route(route_id/root_smiles/steps);每步=一个已提交事件;root_smiles=run identity 真实输入;空事件=空答卷 |
| 6 | 原生↔v3 双向引用边界 | `v3_projection.py:458-488`(读取核对原生导出 manifest 存在)、`v3_projection.py:491-531`(list_v3_projections_for_native 只读反查)、`v3_projection.py:285-294`+`397-400`(reverse_consumption=forbidden/不可变落盘) | 未实施 | 正向:投影引用 export_digest/内容 digest/task_key,断裂拒;反向:只读反查,原生 manifest 不内嵌投影清单;反向消费契约禁止(模块无写入入口,零 DB 写) |
| 7 | legacy/export_v3 冻结回归(字节专项) | 证据 `s4b_r1/scripts/legacy_export_byte_probe.py` + `s4b_r1/legacy_bytes/comparison.json`(冻结路径零触碰;export_v3.py/pathway_store/report_adjudication/identity/artifact_store 均不改) | 以全量绿+零触碰 diff 为证(S4a §20.7 遗留) | **专项**:当前 vs 父 fc40605 同探针四产物逐字节一致;legacy 聚合 18007e6a… 同父;另全量非 slow 1543 绿含 legacy/export_v3 全套 |
| 8 | 完整公共链 | `runflow.py:1347-1394`(start/resume → endpoint → 导出 → 投影 → 双首消费读回)、测试 test_full_public_chain(崩溃→resume→读取→replay) | 链止于对象底座+endpoint 首消费 | scripted 输入→start/resume→action/attempt/ledger→停止→四分账→导出→首消费→v3 投影(构建即读回)→再次读取→replay 零新写;网络 0 |
| 9 | G02 重复生成与过期场景 | `tests/test_ppv1_s4b_export.py`(G02-①…⑦ 七测 + 停止视图会话成分披露测试) | 未做 | 七测全绿(§8);额外:同 digest 不同字节重导出拒(不可变)、stop 行删除引用断裂拒 |
| 10 | S4 全量回归 + G01 + 交付书 + mimo | §7/§9/§10(回归与基线)、本交付书、mimo v17(§17)、证据目录(§11) | S4a 版 | 932/1543/1534 三组数字 + v17 请求 + s4b_r1 证据 |

## 2. 与规格 §10/§11/§17 逐项映射(S4b 范围行)

| 规格条目 | 本批落点 |
| §10 原生导出保留完整信息(不按 CN 合并/来路分别表示) | payload = S4a 对象全量(§1 行 4);测试 test_native_export_full_fact_coverage(共同产物/备选/来路/条件/audit/deferred/budget/stop/endpoint 全组 + 15 表 + 四类 artifact 引用断言) |
| §10 原生导出确定性(规范化字节/等价稳定序列) | G02-①(同进程+独立子进程字节一致)+ G02-②(恢复后重复导出);manifest/payload 无时间戳 |
| §10 导出过期识别(版本/revision/策略/依赖内容/输入不匹配/hash 不一致) | read_native_export 八 kind(§1 行 3);G02-④⑤⑥⑦ |
| §10 v3 有损适配(lossy 标注/原生引用/信息损失/版本/图修订/摘要/不反向/不冒充完整语义) | 0g 六–九(v3_projection.py 全量;测试 lossy 标记/损失清单/逐事件步骤/空答卷/反查/引用断裂) |
| §11 S4 阶段行(路径原生结果/v3 有损适配/端到端) | 前两项交付;端到端见 §1 行 8 |
| §17.3.5/§17.3.6(证据类型非强度/coverage 表核查范围) | 沿 0f(S4a)不变;投影 unprojectable_summaries 只摘要不重判 |

## 3. 与 S4a 复审 §6/§7 交接逐项(保留并扩展)

| 交接项(复审 §6/§7) | 本批落点 |
| stop/endpoint 独立权威保留 | 导出 manifest 只按 hash 引用两行(read 权威核对);endpoint 首消费在导出读取**之前**(动作漂移先以 endpoint_record_stale 浮出,G02-④a 如实断言该优先级) |
| unknown/partial/deferred/失败状态保持 | payload 全量保留这些组;投影不把 unknown/partial 改写成功;空池 run 导出/投影正常生成 |
| 不同来路控制保持 | payload events/appearances 逐事件逐出现;投影逐事件步骤(同父多备选不合并) |
| 协同改写边界(复审 §4.2) | 不对外宣称签名级防篡改:manifest 与 payload 自洽重写由**独立权威重算**(DB 行 + artifact store)兜底;payload+manifest 全部内部 hash 重算的"新 ID"导出仍拒(G02-⑦);全库协同改写(DB 行 hash 同步改)超出范围,沿 S3B-01/S4a 披露 |
| H07/内容身份分层(复审 §4.3) | native_export 不重复 from_dict 首消费:上下文内容身份校验由 endpoint 派生侧承担(沿 S4a 分层);导出侧只核 artifact 信封 payload_hash 与引用一致 |
| 对象级/文件级确定性边界(复审 §4.4) | 对象级(S4a)扩展为文件级:digest 键目录 + 不可变写 + 子进程字节一致;记录级 stale 扩展为文件级八 kind |

## 4. 入口矩阵(任务书 §6 要求的 S4b 行)

| 入口 | 消费事实 | 独立权威 | 身份/版本绑定 | proof scope | 失败/stale 表示 | 场景/控制 |
| start/resume → export(写) | 已验证 endpoint 记录 + 全部持久事实 + H07 artifacts | store 行 + endpoint/stop 行 + native result artifact | native-export-1/native-export-policy-1/全部契约版本入 manifest;export_digest 键 | 纯派生,零新判定 | endpoint 过期先拒;写冲突拒(不可变) | 公共链/幂等测试 |
| native export read(首消费) | payload/manifest 字节 + DB 行 + artifacts | 同左重算 | 版本门+sha+digest+引用+策略+facts 八重 | 不新判定 | 八 kind 结构化拒,原文件保全,零写入 | G02-③⑥ + 停止视图/引用断裂测试 |
| v3 adapter build | 原生结果(已验证)+ 导出 manifest 摘要 | native 层 | v3-projection-1 | 只投影 | 事件结构/state 缺失 ⇒ 结构化拒(不猜/不删边) | lossy/步骤/空答卷测试 |
| v3 projection read | 投影文件 + 原生 manifest 存在性 | 文件 digest + 原生导出 | 版本门+digest+lossy 标记 | 恒 lossy | missing/corrupt/version/digest/native_reference_missing 拒 | 投影读取/反查/引用断裂测试 |
| 反向消费(v3→native) | ——(禁止) | —— | 契约禁止 | —— | 原生入口拒;模块无写入入口;零 DB 写 | 反向污染负控 |
| replay/re-export | 同事实 | 同上 | 同 digest 同字节 | —— | 幂等 created=False | G02-①②/E2E |

## 5. 实际源码 diff 与提交引用

- 新增:`src/pathway_v43/pollutant/native_export.py`(523 行)、
  `src/pathway_v43/pollutant/v3_projection.py`(531 行)、
  `tests/test_ppv1_s4b_export.py`(760 行,18 函数/18 用例);
- 修改:`src/pathway_v43/pollutant/profile.py`(版本注册+契约块
  +delivered_stages+runflow 常量单一来源)、
  `src/pathway_v43/pollutant/runflow.py`(接线 + summary +
  docstring;RUNFLOW_VERSION 改从 profile 导入,值不变语义)、
  `src/pathway_v43/pollutant/native_result.py`(**S4a 文件重构,
  如实披露**:(a) 抽出 artifact_reference_index 单一来源(build
  与 export manifest 共用,不另造第二套枚举);(b) **修正 S4a
  聚合缺口** —— 非事件动作完成的调度结论 artifact 键为
  stable_id("soutc", action_id)(runflow._complete_action 写入),
  S4a 只按 action.task_key 查导致 retrieve/decide 等调度结论
  outcome 全部漏聚;S4b 起两个键都枚举(缺失自然跳过),字段组
  "失败/unknown/partial/violated 原因"实际补全;S4a 35 测试零改
  动全绿为回归证据)、
  `tests/test_ppv1_profile.py`(2 处字面量:profile-16、
  S4b-export —— **本批唯一既有测试改动,如实披露**);
- 零触碰:output/export_v3.py、services/atom_tool.py、
  workflow/runner.py、production.py、chemstate.py、
  path_context.py、hypothesis.py、events.py、audit.py、
  search.py、queue.py、model_protocol.py、store.py 表结构(
  store 保持 -10,导出为 run 目录文件无新表;
  `git diff fc40605 --stat` 逐文件核对);
- 提交:v4.3 本地提交(不 push;显式路径 git add),哈希见
  `git log -1`(提交信息含本交付书摘要)。

## 6. 版本/身份/Hash 影响(逐项)

- **新增**:PPV1_NATIVE_EXPORT_VERSION=`ppv1-native-export-1`、
  PPV1_NATIVE_EXPORT_POLICY_VERSION=`ppv1-native-export-policy-1`
  (固定序列化/命名/无时间戳/不可变规则,无用户可配项)、
  PPV1_V3_PROJECTION_VERSION=`ppv1-v3-projection-1`;
- **升级**:profile `ppv1-profile-15 → -16`(契约注册 +
  delivered_stages S4b-export;旧 run resume 按身份门拒 = 旧 run
  不跨版本续跑)、runflow `ppv1-runflow-4 → -5`(公共入口接线;
  常量单一来源移入 profile 注册,native_export manifest 与 runflow
  共用同一常量,消除模块级循环导入);
- **保持**:store -10(无新表)、search-6/search-limits-3/
  format-feedback-1/model-proposals-2/frozen-plan-1/endpoint-1/
  endpoint-policy-1/native-result-1/ppv1-*-8 化学契约族全部不动;
- **legacy 影响:零**(52 份 legacy code_identity 文件父↔当前
  逐字节一致,聚合保持 `18007e6a7cc239606eb30921f91045540446
  a7d7298108be30d47fce2f1374d6`;legacy 字节专项四产物一致;
  production.py SHA 与父逐字节一致);
- **判据冻结面**:ppv1-criteria-v1 正文零触碰;行号锚定继续漂移
  (runflow/profile;行为互证以 914 存量零改动全绿 + 逐字节 diff
  为证;重锚待下一判据版本,如有)。

## 7. 实际测试命令与结果(depending43:Python 3.11.16 /
RDKit 2026.03.6 / SQLite 3.53.4;PYTHONDONTWRITEBYTECODE=1、
-B、pytest -p no:cacheprovider)

| 执行 | 命令 | 结果 | 证据 |
| S4b 焦点(当前树) | `pytest -q tests/test_ppv1_s4b_export.py` | **18 passed / 0 failed,exit 0** | `current/s4b_focus.*` |
| PPV1 全量 | `pytest -q tests/ -k ppv1` | **932 passed / 627 deselected / 0 failed,exit 0**(914 存量 + 18 新;34 文件) | `current/ppv1_full.*` |
| 全量非 slow(含 legacy/export_v3 回归) | `pytest -q tests/ -m "not slow"` | **1543 passed / 16 deselected / 0 failed,exit 0** | `current/full_nonslow.*` |
| legacy 字节专项 | 探针脚本两树各跑 | **四产物 SHA256 两两相等**(legA/legB 的 predictions.jsonl+export_metadata.json) | `legacy_bytes/*` |
| 父基线(同字节) | 见 §9 | 18 collection 红 + 2 字面量红 + 21 绿 | `baseline/*` |
| G01 安全隔离 | 控制器(s4b_r1/scripts) | **1534 passed / 8 skipped / 17 deselected,exit 0** | `g01/*` |

## 8. §8 验收矩阵逐行结果(S4b 范围行)+ G02 七测

| 任务书 §8 行 | 入口→行为→断言→证据 | 结果 |
| 原生结果完整性(文件级) | 导出 payload 含 state/path/events/alternatives/products/conditions/dependencies/audit/deferred/budget/stop/endpoint;manifest 15 表 + artifact 引用 | **通过**(test_native_export_full_fact_coverage) |
| 导出确定性 | 同一结果重复 export:字节/规范化等价 | **通过**(G02-①:同进程重导 created=False + 独立子进程重导出 digest/sha/字节一致,单目录) |
| 导出过期 | 改 graph revision(动作漂移/新增事实行)/policy/source hash | **通过**(G02-④:动作漂移 ⇒ endpoint 权威先拒(endpoint_record_stale,优先级披露);新增行 ⇒ export_stale + changed_facts;重导出新 digest 新目录,旧文件字节保全;G02-⑤:策略版本 hash ⇒ export_policy_stale) |
| 导出完整性 | 破坏 manifest/payload/reference | **通过**(G02-⑥:payload 字节/manifest 不可解析/原生 artifact 缺失/文件缺失四负控,正控还原后恢复) |
| v3 有损适配 | native result→v3:lossy_projection/原生引用/适配版本/信息损失 | **通过**(lossy 标记/原生引用可解析/十二条损失轴/不可投影摘要/契约版本/边界声明) |
| v3 反向污染 | 读取 v3 适配→原生 state/event | **通过**(投影 digest 进原生导出入口 ⇒ export_missing 拒;投影载荷进原生结果读取 ⇒ 拒;模块无 put_/submit_/write_ 入口;消费投影前后 DB counts 不变) |
| legacy 回归 | legacy profile/export_v3 旧输入/报告/冻结导出字节行为不变 | **通过**(专项四产物字节一致 + 全量非 slow 1543 绿 + 零触碰 diff + 聚合同父) |
| resume/replay | crash/restart/replay:endpoint/export 不重复写;旧 run 不跨版本续跑 | **通过**(E2E:崩溃→resume→导出→投影→读取→再 resume,events/attempts/requests/reservations/network 全等;旧导出文件字节保全;profile-16 身份门拒旧 run) |
| scripted E2E | start/resume→native→v3→replay;网络 0;未到达段单列 | **通过**(完整公共链;model_requests 0 行;provider_kind 空集 = 无真实/scripted 请求登记;网络 0) |
| G02 | 七测矩阵 | **①②③④⑤⑥⑦ 全过**(§1 行 9;⑦=自洽重写全部内部 hash 重算仍拒:reference_mismatch/stale) |
| (停止会话成分) | 停止视图 session 成分的披露面 | **如实披露**(G02-② docstring + E2E:驱动结算后字节稳定;相邻会话 stop/endpoint 行合法更新 ⇒ 新 digest 新目录、旧文件保全 —— S4a P2 沿续,事件/预算零新增是硬边界) |
| G01 | 安全隔离源;skip/deselect 逐项披露 | **通过**(§10) |

## 9. 当前树 vs 直接父 fc40605 红绿分类

- 新文件 `tests/test_ppv1_s4b_export.py` 同字节复制到 detached
  worktree(fc40605):**collection 红 18**(ModuleNotFoundError:
  `pathway_v43.pollutant.native_export`;implementation missing
  如实登记 —— 未 stub、未改 import、未弱化期望、未复制实现);
- 更新文件 `tests/test_ppv1_profile.py` 同字节:**2 版本/阶段
  字面量红**(ppv1-profile-16、S4b-export —— 父合法实现
  profile-15;**expected behavior difference 类**)+ 21 合法
  正控绿;0 行为红;
- 分类 JSON:`baseline/parent_r1_classification.json`;父存量
  914 全量绿为 S4a 复审在 fc40605 独立执行证成,本批不重跑冒称;
- "父基线出现红"≠ 旧错误;当前全绿 ≠ 科学正确(合成规则级)。

## 10. G01 安全隔离范围与结果

- 控制器:`s4b_r1/scripts/safe_g01_s4b_r1.py`(沿 R7→R8→S3a→
  S3b→r2→r3→s4a_r1 白名单谱系;**新增 3 输入**:native_export.py/
  v3_projection.py/test_ppv1_s4b_export.py;修改的 runflow/
  profile/native_result/test_ppv1_profile 为既有白名单路径按当前
  字节复制、新 SHA;**294 输入**(291 s4a_r1 + 3));
- SHA 前后一致(`g01/input_sha256.json`);固定空 BBD_DATA_ROOT/
  V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT;不复制
  evaluation/gold/benchmark/sealed/v4;实际 HEAD(fc40605 实施
  态)+dirty 记录(`g01/preparation.json`);
- **1534 passed / 8 skipped / 17 deselected,exit 0**
  (1534 = 1516 s4a_r1 + 18 新;skip 逐项:5 真实冻结评价
  (test_batch_runner:52、test_score_report:110/163/172/184)+
  1 缺 v4 对照(test_analog_assets:95)+ 2 phase_d 派生
  (test_analog_v2_corpus:62/153);17 = 16 slow + 1 明确排除
  export 用例);
- 历史 1110/1138/1196/1250/1299/1389/1453/1473/1481/1516 各自
  单列不混计;全部数字不外推 dev/298 科学性能。

## 11. 证据目录与 manifest

- 根:`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/
  ppv1_s4_impl_2026-10-08/s4b_r1/`;
- 组成:README.md、manifest.json、SHA256SUMS(40 文件)、
  scripts/(G01 控制器 + legacy 字节探针)、current/(焦点/PPV1
  全量/全量非 slow junit+stdout+stderr)、baseline/(
  worktree_setup.log、两父运行 junit+stdout+stderr、
  parent_r1_classification.json)、legacy_bytes/(current/parent
  四产物 + comparison.json)、g01/(preparation/input_sha256/
  execution_result/junit/stdout/stderr)、mimo/(v16 送审快照
  字节同 fc40605 + v17 请求快照)、metadata/(HEAD/父/dirty/env);
- 全部执行在 /private/tmp 新目录(父 worktree
  /private/tmp/ppv1_s4b_parent_wt、G01 tmp
  /private/tmp/ppv1_s4b_r1_g01、legacy 探针 tmp 保留至复审可随时
  删,证据已快照);永久证据目录未运行任何写库程序(仅复制结果
  文件与 junit);复现命令在 README。

## 12. scripted 输入、输出与断言(合成规则级;网络 0)

- 输入:计划 = 合成池(CCO→CC=O / CCO→O=C=O,冻结 AtomTool
  编辑协议形状;可选 coproducts=[H][H]、schedule_budget
  max_select、endpoint_evidence 直报夹具(study-A)、零深度/
  零预算/空池/崩溃注入);
- 公共链输出断言:summary["endpoint"](四分账)+
  endpoint_record_payload_hash + native_result.content_digest +
  **native_export.export_digest/dir/payload_sha256** +
  **v3_projection.projection_digest/lossy/损失轴/steps**;
- 文件断言:payload/manifest 落位、manifest 结构(版本/策略/
  facts/引用/无时间戳)、导出读回 = 原生 artifact 载荷;
- v3 断言:steps 逐事件(parent_smiles/predicted_products 形状
  冻结)、root_smiles=CCO、endpoint unknown 不编造、CO₂ 两备选
  逐事件不相加;
- provider:scripted(网络 0);model_requests 行数断言 0
  (provider_kind 空集);无真实模型调用。

## 13. 预算/事件/attempt/来源/endpoint/导出账(代表性数字)

- 完整夹具公共链(双备选+共同产物+证据):events=1(B 展开;
  C deferred)、attempts、reservations>0、model_requests=0、
  stop 主因 budget_limit、execution=completed、endpoint=
  supported_mineralization(直报证据)、bookkeeping=closed;
- manifest 账:graph_facts 15 表 digest、artifact_references
  4 类(path_context/production_report/expansion_outcome/
  frozen_plan)、authority_references(endpoint/stop 行 hash +
  native result task_key/digest);
- 导出账:export_digest 键目录;replay 后(停止视图会话成分)
  当前导出新 digest、旧导出保全(§8 披露行);E2E 零新业务写;
- v3 投影账:projection digest、steps=事件数、损失轴 12+动态、
  unprojectable_summaries 计数(endpoint_assessment/
  independent_source_support_count/deferred_entry_count/
  co2_product_occurrences/co2_aggregated=False 等)。

## 14. unknown/partial/deferred/stale/未执行段

- unknown:endpoint/根碳去向/依赖未解决 —— payload 与投影
  unprojectable_summaries 均保持 unknown 并披露(不升格);
- partial:证据字段缺失披露(S4a)随 payload 全量导出;
- deferred:payload deferred_entries 两类字段完整 + 投影计数摘要;
- stale:导出八 kind(§1 行 3);原文件/原行保全;
- 未执行段:本批不做 S5(§20);反向消费(v3→native 写)在契约
  上禁止,无对应执行段(负控以"零写入 + 入口拒 + 模块无入口"
  证成);模型结构失败场景的导出段未单列(S4a fail 夹具已证
  execution=failed 不转成功;导出在该场景正常派生,行为同
  completed 链,不再重复声明)。

## 15. legacy 未改动与回归证明(专项)

- `git diff fc40605` 名单(§5)不含任何 legacy/冻结文件;
- **字节专项**(S4a §20.7 遗留收口):`legacy_export_byte_probe.py`
  自包含合成夹具(单事件多产物 + 两事件竞争同父+deferred,与
  tests/test_export_v3.py 同构),当前树与父 worktree 各构建导出
  并重导出(树内幂等)⇒ **predictions.jsonl + export_metadata.json
  四产物逐字节一致**(SHA256 两两相等;含首现合并/位次/deferred
  语义路径);
- 52 份 legacy code_identity 文件聚合保持 18007e6a…(父↔当前零
  差异文件);
- legacy/export_v3 全量回归在全量非 slow(1543 绿)与 G01
  (1534 绿)内执行。

## 16. v3 信息损失清单(§1 行 5 的展开)

十二条固定轴(每项带 native_authority 指回原生字段组):
route_origins(来路/事件身份)、coproducts(角色)、
alternative_reactions(备选关系)、conditions_dependencies、
audit_proof_scope、deferred_unexpanded(未展开集合)、
endpoint_evidence_level(终点证据等级)、budget_stop_reason、
unknown_partial_axes、coefficients、path_identity、
source_provenance;动态轴:multi_reactant_events_collapse、
no_committed_events_empty_answer。不可投影摘要(unprojectable_
summaries)= 计数/键清单/状态值(endpoint 评估/独立支持计数/
依赖未解决 id/停止原因/CO₂ 逐事件数/条件键/…);**不为填满旧
字段编造终点/矿化/解毒/来源支持**(测试:v3_projection_steps_
per_event_no_cn_merge_no_fabrication)。

## 17. mimo v17 请求与送审状态

- `docs/mimo_ppv1_chem_review_request.md` 升级 **v17(S4b 批次
  版)**:新增 0g 节十二条(正式导出组成/graph revision 等价身份/
  确定性/首消费八 kind/防洗白/v3 有损投影/信息损失清单/不编造/
  双向引用边界/完整公共链与 G02/边界诚实/语义未改变声明),§0/
  §6/§7 同步;判据一–五与 0d/0e/0f 正文一字未改;
- v16 送审快照(字节同 fc40605)与本批 v17 快照存 `s4b_r1/mimo/`
  (SHA256 d0fd1972…/9bd6ed56…);旧回应 r5–r16 原样保留不覆盖;
- 本批实施 agent 未调用任何外部模型;送审由主会话按 AGENTS.md
  通道 A 执行;回应落盘后按"与程序证据互证"采信。

## 18. 判据/科学性能/敏感资料声明

- 判据已冻结(ppv1-criteria-v1);本批未改冻结正文、未自动宣布
  任何新冻结;
- 科学性能 pending:全部数字为合成规则级契约结果,不代表 dev
  (B1 环境路径中间步骤)或 298(RHEA 通用酶学)科学性能;
- 未访问:金标/题面/封存逐题 run/真实评价数据/reports/data/
  evaluation/benchmark/dependingv4/冻结 v3 资产;真实 provider
  默认 off,网络请求 0;判分零 LLM。

## 19. 残留 P2(继承 + 本批新增,如实登记)

1. **停止视图的会话成分(沿 S4a P2,导出面扩展)**:stop report
   含 session refusals(进 budget_exhausted_keys)与
   events_submitted_session;驱动未结算的相邻 resume 会话允许
   stop/endpoint 权威行合法更新 ⇒ 导出新 digest 新目录(旧文件
   保全;G02-②/E2E 如实区分"结算后字节稳定"与"相邻会话换新");
   事件/预算零新增是硬边界(已测试);
2. **导出不抗全库协同改写(沿 S3B-01/S4a P2)**:manifest+payload
   自洽重写被独立权威重算兜底(DB 行 hash + artifact store;
   G02-⑦);DB 行 hash 同步改写的全库协同场景超出范围,沿
   S4a endpoint 行披露;
3. **导出目录名截断 24 字符**:export_digest/projection_digest
   目录名取前 24 字符(完整 digest 在 manifest/载荷内并经读取
   核对;截断碰撞未处理 —— 64 hex 前 24 碰撞概率可忽略,如实
   登记);
4. **v3 投影步骤的父级表示**:多 reactant 事件 collapse 为首
   reactant(动态损失条目逐事件披露;当前生产链事件恒单底物,
   该分支未被公共链夹具实际触发 —— 负面披露);
5. **行号锚定漂移(沿 S4a)**:冻结判据正文行号锚 runflow/
   profile,本批继续漂移;下次判据版本(如有)统一重锚;
6. 继承 P2 不变:同机 flock、cache_hit 同构、两事务间外部 SQL
   窗口、foreign-run 反向诊断、stop 对象有界 100、三类
   RuntimeError 逃逸面、B2 口径、endpoint 证据为冻结计划合成
   输入、来源标签逐字一致性。

## 20. S5 不在本批范围(逐条)

1. S5 评测器/数据规范/预注册未启动;真实 provider/付费实验/
   检索质量实验未做;金标/题面/封存逐题 run 未触碰;阈值冻结/
   统计预注册执行属用户裁定;判据冻结状态未因本批改变。
2. (S4 内)无未闭合项:S4a §20 十一项 S4b 待办已全部交付
   (本交付书 §1);S4 完成与否以 S4b 复审通过为准 —— 复审
   前不宣布。

## 21. 提交

- v4.3 本地提交(不 push;git add 仅显式路径):
  `src/pathway_v43/pollutant/native_export.py`、
  `src/pathway_v43/pollutant/v3_projection.py`、
  `src/pathway_v43/pollutant/native_result.py`、
  `src/pathway_v43/pollutant/runflow.py`、
  `src/pathway_v43/pollutant/profile.py`、
  `tests/test_ppv1_s4b_export.py`、
  `tests/test_ppv1_profile.py`、
  `docs/POLLUTANT_PATHWAY_S4B_DELIVERY_2026-10-08.md`、
  `docs/mimo_ppv1_chem_review_request.md`、
  `docs/review_evidence/ppv1_s4_impl_2026-10-08/s4b_r1/`;
- 用户既有未跟踪文件(.zcodeignore、S4a 复审报告、mimo r16
  回应、s4a codex/mimo 证据目录)保持原样不纳入;父 worktree
  与 G01/legacy tmp 保留至复审(证据已快照,可随时删)。
