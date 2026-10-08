# R7 交付的第八轮独立复审证据（2026-10-07）

仓库 `/Volumes/CC/Enzyme_Agent/dependingv43`，实际 HEAD `858dd94c7c6c8fc387940242403d67b6b36b5313`，父提交 `6d9020130a481866ce2f3b79933907a33d8cfc9e`。报告：[第八轮复审](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R7_2026-10-07.md)。

**不放行 S3；仅两项同契约 P1：恢复/直传 ChemicalState 未验 raw→严格身份；显式提供有效 payload 时首提复用损坏的同 hash appearance。** 五组 R6 原探针已修复；R6-01/03/05 关闭，02/04 原反例关闭但这两个消费入口残余仍在。本目录的缺口观察断言要求当前错误仍发生，不能当修后验收脚本。

## 独立执行数字

- PPV1：508 passed、0 skipped，1 文档转义 warning，3.97s（depending43）。
- R7 三份新增回归：父提交 detached worktree 33 failed /24 passed；当前57 passed。宽分类26行为+7披露；窄分类6字段/缺表+1新增violation披露，不把测试数当漏洞数。
- 主审 R6 12脚本全部 exit0；五组原反例翻转，旧关键控制保持。R6 assert_observed.py 在第一个“复杂共底物仍verified”旧断言 exit1，符合设计；该断言之后的分支未运行。
- 主审化学57顶层记录、条件16案例+metadata、存储15案例+metadata，完整输入输出和正负控保留。
- G01先隔离缺v3引擎：2failed /1099passed /18skipped /16deselected；补普通v3源码后：**1110passed /8skipped /17deselected**。8skip=5真实评价+1缺v4对照+2未复制派生metadata；17desel=16slow+1明确排除需缺席评价脚本的export用例。外部1119/16desel未在零真实金标访问条件下独立证成。

以上是工程契约数字，不外推 dev（B1环境中间步骤）、298（RHEA通用酶学）或污染物路径科学性能。无真实金标、题面、封存逐题run和外部模型调用。完整源码/vendor只复制到新tmp；永久附件保留版本/哈希，不收源码副本或SQLite数据库。

专项原附件中的“完整1119需读真实金标”按此限度采信：原测试在真实benchmark存在环境会访问相应文件，但不能据此猜外部会话实际访问；另有可核查隔离/替换证据时应据证裁定。本审只证成安全隔离1110结果，未核实外部1119及其零访问兼容性；保留专项原快照，主报告§2是最终裁定。

## 附件布局

- `run_metadata.json`、`input_snapshot.json`：本轮实际HEAD、命令、schema来源、完整隔离源码哈希、初始仓状态及既有文件hash；R6脚本内旧HEAD字面量不当本轮HEAD。
- `r6_original/`：旧永久R6脚本/fixture的只读复制；`r6_replay/`：主审实际执行的脚本、12份完整输出/错误流及条件results。执行时只适配隔离路径和实际HEAD，原脚本保留。所有损坏准备均合成。
- `assert_r7_replay.py`、`r6_selected_outcome_reference.json`：原五组翻转断言和六条旧lane关键行为比较。只比较判据/异常类型及错误存在，不比随修复更新的人话错误文字或版本/ID。参考来自R6快照，hash见输入清单。
- `chemistry_current/`、`conditions_current/`、`storage_current/`：主审独立再执行的公共链，完整payload/证明、审核准入及提交前后counts。`storage_current`仅将新tmp库目录固定在脚本父目录；其他逻辑与专项冻结脚本一致。
- `chemistry_specialist/`、`conditions_specialist/`、`storage_specialist/`：三专项完整附件、原始完整测试/红日志、原始与适配回归、分类、普通依赖hash、执行命令和专项报告。原manifest保留，外层清单覆盖整个新bundle。
- `storage_specialist/safe_g01_reproduce.py`：事后编写的精确白名单准备/执行脚本，只做语法检查，**未用该脚本重新执行G01**；原实际执行命令和完整日志在同目录。依赖两份同目录hash manifest及普通dependingv3源码，无真实evaluation/v4。
- `SHA256SUMS`、`manifest.json`、`report.sha256`：全部永久附件及报告hash；清单自身不自我哈希。后续不回写本证据或旧证据。
- `portable_validation/`：打包控制器在第二个新tmp验证的完整stdout/stderr和metadata；只重复短公共链/旧探针以验证路径可移植性，没有重复508、G01或基线57凑数字。

## 安全复跑

不要原地执行会写库或覆日志的探针。下例控制器从永久目录只读取脚本，把源码/脚本复制到全新tmp后执行；每次换新的`--out`。

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r7_codex_2026-10-07/reproduce.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_r7_review_new_replay
```

默认只跑合成12旧探针+新公共链+PPV1工程回归，不执行G01、不读评价数据。`--baseline`可加33/24 detached worktree复现，finally清理；`--skip-ppv1`仅跳过已独立执行的508工程回归。HEAD已变需要`--allow-head-change`，已修旧控制继续验证，R7缺口观察断言跳过并检查实际输出；化学探针expected_HEAD是历史预期，控制器actual_head才是执行版本。

基线也可只跑 `conditions_specialist/baseline_reproduce.py --repo … --out 新tmp --python /Users/cc/miniconda3/envs/depending43/bin/python`，不能对原57断言改预期。该脚本已在另一新worktree自验33/24，创建/清理日志都保留。

G01独立安全隔离复跑（耗时约4分钟）使用精确208仓内输入+42普通v3源码+18资产白名单；脚本拒绝hash漂移，不读取真实benchmark。不复制原v3资产，隔离v3资产来自已核本仓非题面反应资产：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r7_codex_2026-10-07/storage_specialist/safe_g01_reproduce.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_r7_g01_new_safe_replay \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

可用`--prepare-only`只检hash和准备隔离副本。完整1119与零金标访问的冲突及未证项详见主报告§2；本目录不把skip/deselect改成pass。
