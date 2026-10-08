# S3a-r2 独立工程执行证据

固定仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`；实际 HEAD `dcb7ed62bd4271cfa7bde2732dc0b4fdd0360d03`，直接父基线 `9b78f4279cc6fa50b3b51c31a5c8e07abbeda207`。本包来自本审新 `/private/tmp/ppv1_s3a_r2_execution_review_MxKd0B`，没有复用实施方或主会话旧 scratch 的套件结果。仓库源码、测试、既有 docs/AGENTS 与永久证据均未改；父 detached sparse worktree 已清理。

- PPV1 24 文件：**648 passed /0 skipped /0 failed**，exit 0；pytest 7.37 秒，命令墙钟 7.816 秒。完整 stdout/stderr/JUnit 与逐 case 结果在 `ppv1_full/`。
- 父 9b78 同字节新回归 54 项：**52 failed /2 passed /0 collection error**，墙钟 1.270 秒。精确分类为 **48 行为断言失败 +3 返回形态 TypeError +1 旧拒绝 kind 先停 +2 合法正控**；不得裸称 52 项完整行为红。原输入和原结果未改，逐项达哪/后续未执行在 `baseline_case_classification.json`。
- G01 新白名单安全隔离：**1250 passed /8 skipped /17 deselected**，exit 0；pytest 194.23 秒，控制器墙钟 196.598 秒。275 输入=本仓 215 + ordinary dependingv3/src 42 + 本仓普通反应资产镜像 18；源与复制件 SHA 前后一致。逐 nodeid/理由在 `g01_exclusions_detail.json`，全部 stdout/stderr/JUnit 在 `g01/`。
- 额外四 B3 capture：父四类异身份均 event1/commit1/done，当前均0/0/claimed且 artifact 保全；独立于原测试早停分类，完整分段/全表在 `baseline_extended/`、`current_extended/`。
- runner start/resume 两公共入口的合成 PPV1 身份均 fail-closed；无新执行目录/恢复身份零变化。public store.submit_event 缺产物失败全表回滚，合法首提与重放一次写入、幂等全表相同；双方 trace 与全表 JSON 同在 extended 目录。
- runner.py/store.py 对父全字节相同。legacy code_identity 完整逐文件对象与聚合相同，聚合 `4ea99b698a05ab8685bbd5687835043a2bf07f0c7f219591beccbff2507c29ae`；这次没有合成跨代码变化或读取历史实际 run。代码身份/实际新库 meta与完整 schema见 current_runtime/baseline_runtime。
- 一次窄化学探针 **15 cases / assertions complete**；只适配本次基线输入、实际改动列表与 HEAD 元数据，保留原脚本和精确 diff。结果、mimo r10 多处事实纠错及可采纳限度见 [STATIC_FINDINGS.md](STATIC_FINDINGS.md)。小探针包含重复 runner 正控，不与套件计数相加。

环境：depending43 Python 3.11.16 / RDKit 2026.03.6 / SQLite 3.53.4；profile10 /search2 /store9 /search-limits3。全部 Python -B、PYTHONDONTWRITEBYTECODE=1、pytest no:cacheprovider。G01 固定空外部数据根、所有 engine/asset 路径到新隔离树，只读白名单 ordinary v3 source 与本仓已允许普通资产镜像；原 v3 assets/evaluation、dependingv4、真实题面/金标/封存逐题 run 未读取、未复制；无模型/provider/网络执行。工程数字不外推 dev/298 科学性能。

`commands.json`、`extended_commands.json`、chemistry_probe.run/static_precision.run 记录实际 argv/cwd、关键环境、退出码、墙钟及 stdout/stderr SHA。源/测试原 SHA和前后账、实际 HEAD/status、worktree建立/清理均留存。G01 被动插件只记录 pytest 实际 skip/deselect；selection/fixture/断言未改。`selected_nodeids` 是 collection hook 时点观测，不把它当最终选测清单，实际执行以JUnit和deselection hook为准。

归档包保存准确 ordinary 源/metadata、原测试、G01白名单输入（g01_inputs.tar.gz，275成员逐SHA复核）、所有结果附件；不保存运行中的 SQLite/pytest临时库/字节码/cache。唯一新便携主控制器 `scripts/reproduce_engineering_portable.py` **只做 syntax 检查，未执行**；本次实际执行脚本是 run_actual.py/run_extended_actual.py/run_chemistry_actual.py/static_precision_actual.py，不能把便携模板当又一次独立套件。

安全复现须新仓外输出目录并保持相同敏感数据边界：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  scripts/reproduce_engineering_portable.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_s3a_r2_new_engineering \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

本审未跑历史 655c7e8/更新既有测试的2/79，不伪称那些内部段完成；没有旧控制器硬编码 HEAD 顶替 actual HEAD。所有实际套件/探针首遍完成，无运行失败后的改源码/改测试/重跑；预期父基线失败保持原 stdout。manifest.json 与 SHA256SUMS 覆盖本包所有附件，不自我 hash。
