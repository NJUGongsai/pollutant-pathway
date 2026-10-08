# PPV1 独立复审协议（备用通道）

日期：2026-10-08。适用仓库：`/Volumes/CC/Enzyme_Agent/dependingv43`。

本协议供**没有历史会话上下文**、有本仓读取与本机执行权限的新评审使用。目标是判断 pollutant_pathway_v1 的当轮工程交付是否满足已定验收：污染物路径的结构、条件、来源和搜索记账诚实表示，unknown／partial 不被升成 verified。只做独立复审，不实施回修，不以工程测试数证明降解机理、酶活性或科学性能。

## 1. 通道身份与权限

- 本协议的备用评审由 **opencode agent 通道、`tokeasy/gpt-6-sol`** 承载，**不是 ChatGPT 账号的 Codex 链式评审会话**。模型可用性由派单方提供，本协议不发起模型冒烟测试或配置变更。
- 报告头必须写：实际通道／模型（派单声明与可取得的运行元数据分开）、opencode 会话标识（拿不到写未取得）、时间／时区、实际 HEAD／父提交、输入清单、执行者、执行范围与中断事件。不得署名或声称“正链 Codex 已裁定”。
- 采信仍以**源码与程序证据互证**为限。备用通道可给出“本轮通过／不通过及建议放行”，**不替代正链 Codex 的最终裁定权**；正链额度恢复后，放行／冻结等重要轮次可由正链复核确认。实际阶段交接由主会话按授权处理，判据冻结仍由用户裁定。
- “不调用外部模型”指评审会话内不得另发模型请求、送 mimo、运行会调用 provider 的测试或用 LLM 判分；不禁止用户已经指定的本次备用评审托管通道本身。给定 mimo 回应作为只读输入。

## 2. 每轮派单绑定：缺什么，先补什么

主会话必须在派单提示词中给下表；这些值每轮变化，不得从本文日期、旧脚本常量或文件名猜测。

| 字段 | 必需内容 |
| --- | --- |
| 身份 | 阶段／批次／轮次；待审完整 HEAD；**直接父完整哈希**；本轮允许的验收焦点 |
| 文档 | 本协议、当轮交付书、上一轮复审报告、当轮 mimo 回应的**绝对路径** |
| 范围 | `/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md`；阶段任务书路径或已授权范围／验收摘录（可内联在派单中） |
| 反例 | 上轮复审永久证据目录 README；由 README 指定的脚本／输入／manifest 入口 |
| 执行 | 新回归文件清单（或准许按父子 diff 确认）；安全 G01 控制器、路径白名单与上轮缺席／排除清单入口（可由指定证据 README 导航） |
| 输出 | 报告与永久证据目录的命名；未指定时用 §7 默认名 |

读完这些起步材料即可开工；随后按验收矩阵点读源码、测试、合成输入与控制器，不需翻遍历史报告或依赖会话记忆。缺少验收基准／安全 G01 输入边界时，先做不依赖它们的只读核对并向主会话索取；**不可猜权限、扩数据根或宣布完整通过**。

开工先记录 `git rev-parse HEAD HEAD^`、工作树状态、已有用户差异和相关输入 SHA。与派单不符时停止依赖该身份的执行并报告，不 checkout／reset 主仓。审查途中 HEAD 或输入漂移，受影响结果标为不适用于当前版本，不把两版本日志混合。

工作树文件不自动等于HEAD内容：已有AGENTS等用户差异保留；若待审src／tests有未提交改动，应从指定提交取安全隔离副本，或先由主会话明确审核对象。不能把并行改动的运行结果冠以原提交哈希，也不回退别的agent改动。

## 3. 固定验收面与仓内红线

从上一轮报告提取 **P1编号→原验收出处→最低修复／验收→适用入口→合法控制→已关闭项→接受边界**，写成本轮矩阵。覆盖同规则的首次消费、恢复、重放和复用入口；不能只检查上一轮某个字符串变了。

- 已证关闭的组保持关闭；一般增强、保守过拒、unsupported、缺少单例和科学性能 pending 不单凭自身升阻塞。不提前要求后续阶段功能。当前 S3a 边界不包括 S3b 调度／生产中心证据接线、S4／S5或真实评测；不改冻结 legacy／G2／AtomTool。
- 新残余／重开旧组须有**既有契约出处＋具体源码＋可执行公共链反例＋合法控制**，例如坏权威仍被首次消费、必要 unknown 丢失或错误 verified／R6。不能用“固定范围”遮住同契约真缺陷，也不能借新建议逐轮扩验收。
- 状态恢复／ledger 首消费仍要核身份、版本、内容和适用引用；`put_state` 返回、索引命中或局部重算不是完整 ledger 证书。必要集合完整与每行有效分别核；合法共享、合法重建和幂等必须保留。
- 配平、strict、CN或局部 center 证据不扩大证明范围；失败 `None` 不等于通过。异常原文、内因与成功处置分开，必要时诚实 unknown／partial；不以全面拒绝换验收。
- **不访问真实金标、题面、封存逐题 run、dependingv4；判分零 LLM；不调用外部模型／真实 provider；不 push／commit。** 普通 dependingv3 源码仅限安全 G01 明确白名单，原 v3 assets／evaluation 不访问。
- 仓内**只新增本轮报告与本轮证据目录**。不动 src／tests／既有 docs／AGENTS.md、用户差异或旧未跟踪材料。临时脚本、库、日志、基线副本均在全新仓外 tmp。禁止在永久证据原地执行会写库／日志的脚本。

## 4. 独立执行：五项必做

### A. 环境与 PPV1 全量

使用 conda **depending43**，优先实际解释器 `/Users/cc/miniconda3/envs/depending43/bin/python`；若路径不同，解析同名环境并记录，不改包／环境凑结果。记录实际 Python／RDKit／SQLite 版本及新合成库 schema／profile 版本。

完整复制普通 `src`（**含其中 vendor**）、必要 metadata（如 pyproject.toml）、PPV1 测试与 worker到新隔离树；当前全量发现规则为 `tests/test_ppv1*.py`，另外复制其明确依赖（如 `tests/s3a_worker.py`），登记具体文件清单与 SHA。不在原仓根无边界收集所有测试。

在隔离副本运行以下等价命令；`PPV1_FILES`必须是已登记的实际文件列表，输出、basetemp也在新 tmp：

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<隔离副本>/src <depending43-python> -B \
  -m pytest -p no:cacheprovider -q -rs --junitxml <新tmp>/ppv1.xml \
  --basetemp <新tmp>/pytest_tmp <PPV1_FILES逐项展开>
```

固定外部数据／资产环境到隔离树或明确空根，不继承真实评价路径。保存 stdout、stderr、JUnit、exit和墙钟耗时。通过数按实际，不锁死697或其他历史数字；子集包含全量时不重复相加。不得因新失败改源码／测试，应定位与报告。

### B. 直接父基线，同字节新回归

独立核对父子 diff 后确定新增回归和更新的既有测试，分别登记。创建仓外 detached worktree，**先不 checkout，再稀疏限定普通 src／vendor／必要metadata**，不取整仓敏感目录；示意顺序：

```text
git -C <仓根> worktree add --detach --no-checkout <新tmp>/parent <直接父>
git -C <新tmp>/parent sparse-checkout init --cone
git -C <新tmp>/parent sparse-checkout set src vendor
git -C <新tmp>/parent checkout --detach <直接父>
```

从父取安全源码／metadata到独立执行副本，把**当前新增测试原字节**及明确依赖复制进去，核对 SHA 相同，以相同环境／选择运行。不得修改 import、输入、异常期待或 assertion 来“适配父”。父版本本来缺模块／表／字段，就如实分类；补充行为捕获另存脚本与结果，不能改原基线记录。

逐失败项登记到达哪个公共操作、为何失败、后段是否执行：

| 类别 | 报法 |
| --- | --- |
| 未发生预期拒绝 | 实际异常类期待与公共操作；属有效行为红 |
| 值／写入效果断言 | 实际返回或前后表不符；属有效行为红 |
| 错误 kind 首断言先停 | 拒绝是否已发生、内部链未到哪；不冒充完整行为翻转 |
| 返回形态／缺字段／缺表／collection | TypeError／KeyError／schema／模块缺失单列，不当已证漏洞数 |
| 保持控制 | 合法行为控制与既有坏输入拒绝控制分开；不统称化学正控 |

清理的只限本审创建的 worktree；不强删未知路径／用户材料。保存创建、选择、退出与清理记录。

### C. 安全隔离 G01

必须使用已指定／已审查的**路径白名单控制器**，不能运行原环境 G01 全量冒充隔离数。上一轮 hash用于保护历史输入；**本轮当前源码重新逐项SHA**，复制后及执行后核对。只增加当前明确安全的源码／新测试依赖，逐项登记，不复制整树 assets／data／reports。

可用的 R3 参考入口（不是固定本轮HEAD或结果；派单可给新入口）：

- 控制器：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r3_2026-10-08/execution_specialist/scripts/safe_g01_supplied.py`。
- 路径清单目录：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_s3a_codex_r3_2026-10-08/execution_specialist/allowlists/`，含 `input_hashes.json`、`g01_v3_source_addition_hashes.json`。
- 缺席清单：同 `execution_specialist/g01_exclusions_detail.json`；具体本轮输入SHA同 `execution_specialist/g01/input_sha256.json`。

先复制控制器到新tmp、检查其默认路径与硬编码HEAD；只在副本适配本轮路径／新增安全输入／metadata，保留原件与diff，不改选择／fixture／断言凑数。该参考控制器参数为 `--repo <仓根> --out <不存在的新仓外目录> --python <depending43-python> --r7-path-manifests <上述allowlists>`；可显式 `--v3-src` 指普通白名单源码。**不要直接跑硬编码旧轮的总控制器或把仅syntax检查的portable脚本当已执行。**

环境固定 `PYTHONPATH=<隔离repo>/src`、`BBD_DATA_ROOT=<空根>`、`V3_CODE_ROOT`／`DEPENDING_V3_ROOT=<隔离普通v3>`、`V43_ASSET_ROOT=<隔离准入资产>`。v3资产镜像只从本仓已准入普通资产取，不读原v3资产。观察插件仅被动记录pytest skip／deselect，不改变执行选择。

历史隔离口径为 **8 skip／17 deselect**：真实评价5（test_batch_runner、test_score_report）、v4对照1（test_analog_assets）、phase_d metadata2（test_analog_v2_corpus）；16 slow（`-m 'not slow'`）＋显式排除 `tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_misses_neutralization_forbidden`。本轮必须逐 **nodeid＋理由／缺席依赖**披露；历史行号仅导航。数量变化如实记并解释，不补真实依赖、不伪造skip、不改选择凑8／17；不同白名单范围／历史轮次数字分别登记。

### D. 上轮永久反例与继承控制

先核上轮manifest，再复制脚本、合成输入、必要source／metadata到**新tmp**。辨认硬编码输出目录、旧HEAD和版本；仅在副本改路径／实际metadata／当前动态契约版本，保存diff，不改反例语义或期待来制造绿。

按P1矩阵分案执行：输入→公共入口→返回／异常→相关权威表前后→event／commit／consume／artifact效果。已有event时核“零新增／无成功补账”，不误报绝对event=0。核必要集合、内容、角色／归属、状态、proof_scope、首次消费与恢复的一致性；保留合法共享、幂等、unknown／partial等控制。

`assert_observed.py`或同类旧观察断言**钉的是修前缺口**，修好后按设计失败；不得改旧永久断言让它绿。旧脚本早停，只能认已捕获／已达的部分；未到内部控制标未执行。另写分段合同断言／捕获补证，原失败日志、准备错误与更正均留存。

继承抽查按当轮阶段与上轮报告：已关闭组、S0–S2首消费／重放、runner双入口fail-closed、legacy code_identity、四硬杀B1–B4、双独立进程barrier、H07／H08等适用控制。源码未改可用字节差分＋对应回归／必要窄探针收口，**不宣称跑过全部历史脚本**；没有新同契约证据不重开旧组。

### E. mimo与交付声明互证

逐条列 mimo 条件／待执行清单，对源码名称、行号、异常外层／内因、实际分支和公共调用结果核对。标“文本精度／本轮代码／后续阶段／未确认”。读码、测试存在、版本注释或实施方数字不当本审执行；mimo事实错与本审夹具错均明确更正，不照搬虚构分支。

逐入口核交付书承诺是否与实际链一致，超出证据的全称点名。不确定写“待执行验证＋缺什么”；保留被拒与未核范围，不用风险备注仍授全覆盖。

## 5. 裁定与停止纪律

- **建议通过**：本轮既定P1逐项关闭，合法／诚实unknown／partial与适用继承控制保持，交付声明和证据一致，必要执行完成。
- **不通过**：具体同契约阻塞尚存；按原组登记残余入口，写最小修复和验收。探针记录／参数组合数含对照，不能当漏洞数；测试数不等于漏洞数或科学性能。
- **未完成**：关键输入／环境／执行缺失或中断，不能当通过，也不把环境准备失败凭空归产品P1。明确已完成、未执行、原因与下一动作。
- 每套完成后不为增加数字重跑；只有新变更、真正失败或未闭合问题需要再执行。限额／断流续跑复用**来源明确、HEAD与输入未变的本审结果**，登记中断及续跑、适配／重试；他人日志不能换成本审执行。
- 不自行实施修复、发起新阶段、送外模或推进自动循环。只把报告交主会话，由其按既有授权处理。

## 6. 证据归档：先执行，再冻结

永久目录必须新建、不得覆盖已有轮次。推荐结构：`README.md`、`run_metadata.json`、`input_snapshot.json`、`commands.json`、`scripts/`、`inputs/`、`logs/`、`cases/`、`workspace_integrity.json`、`manifest.json`、`SHA256SUMS`；可按专项分子包。

必须包含：原脚本／副本适配diff、完整合成输入与stdout／stderr／JUnit、每案前后相关表／公共返回／异常detail、实际argv／cwd／必要env／exit／耗时、实际HEAD／父／schema／版本、输入源／副本执行前后SHA、合法控制与早停范围。不要写入token／凭据；记录必要环境键，不能dump整个进程环境。

SQLite可留只读合成快照或省略二进制：省略时保存完整相关表、schema、重建输入／脚本和省略库SHA清单，不能继续拿旧含DB manifest冒充新目录清单。禁运行缓存／bytecode／逸出链接；tar成员路径和SHA也核对，不为归档触碰禁区。

manifest按**实际归档附件**生成，SHA覆盖脚本、输入、输出、适配diff及**嵌套manifest／SHA**。外层自排除仅限外manifest与外SHA控制文件，说明self-hash规则；另校验报告SHA。发布前后核HEAD、原src／tests／AGENTS／既有输入及工作树，确认仅新增报告＋证据目录。归档和哈希校验不重跑suite，也不在永久目录写库。

## 7. 复审报告与最终回复

默认报告：`docs/PPV1_BACKUP_REVIEW_<阶段批次>_<轮次>_<实际日期>.md`；证据：`docs/review_evidence/ppv1_backup_<阶段批次>_<轮次>_<实际日期>/`。主会话若指定原命名风格也可，**头部仍须写备用通道身份**，不覆盖正链报告。日期按实际落盘Asia/Shanghai，同日碰撞加session后缀，不覆盖。

报告至少按以下结构，可直接保持§8位置：

1. provenance／固定验收／实际身份／安全边界／中断记录。
2. 独立执行数字表：实际／来源／命令证据／缺席与排除；基线红分类、合法与拒绝控制分开。
3. 原P1逐项矩阵：已修、残余、未验、合法控制与继承状态。
4. 残余P1：原验收出处、公共链复现、源码、前后效果、最小修复／验收。
5. 已登记边界与P2：接受理由及证明限度，不暗增阶段门。
6. mimo条件、读码事实纠错、交付声明互证。
7. 结论：建议通过／不通过／未完成＋P1清单、下一阶段注意事项、备用通道权限边界。
8. **自包含的下一轮有限回修提示词**：基线完整哈希、必读绝对路径、只修哪些原组／入口、保留哪些控制、不做什么、同字节红绿与安全G01、证据／提交纪律。通过时写交接注意事项，不捏造回修项。

最终回复大白话、结论先行：本轮通过与否／P1清单或启动注意事项、报告与证据路径、独立PPV1／父基线／G01数字；注明“备用通道建议，未冒充正链最终裁定”。原始输出与长表留文件。

## 8. 主会话每轮使用模板

在仓根启动备用agent，把下列变量填实后派单；本协议只读，不逐轮改它：

```text
你是PPV1备用通道独立评审，承载模型tokeasy/gpt-6-sol，经opencode。
工作目录固定 /Volumes/CC/Enzyme_Agent/dependingv43。
执行协议：/Volumes/CC/Enzyme_Agent/dependingv43/docs/PPV1_REVIEW_PROTOCOL_2026-10-08.md
阶段/批次/轮次：<填写>
待审完整HEAD：<填写>；直接父完整哈希：<填写>
交付书：<绝对路径>
上轮复审报告：<绝对路径及P1/最低验收/放行章节>
mimo回应：<绝对路径；有需要再给当轮请求>
上轮复审证据README：<绝对路径；专项入口由它导航>
AGENTS：/Volumes/CC/Enzyme_Agent/dependingv43/AGENTS.md
阶段任务书/已授权范围摘录：<填写>
验收焦点/保持关闭的组/已接受边界：<填写，不扩大协议范围>
新增回归文件：<填写，或从父子diff独立确认>
安全G01控制器/白名单目录/缺席排除清单：<绝对路径或README准确入口>
报告/证据目标：<备用通道新路径，日期用实际日期>
独立执行并出具同规格报告和完整证据。只新增报告及证据目录，
不改src/tests/既有docs/AGENTS，不访问金标/题面/封存逐题run/dependingv4，
不外模/真实provider/LLM判分，不push/commit；不要实施回修。
报告注明备用通道，不替代正链Codex最终裁定。
```
