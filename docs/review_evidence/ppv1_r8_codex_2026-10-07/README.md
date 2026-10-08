# R8交付的第九轮独立复审证据（2026-10-07）

报告：[R8复审](/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R8_2026-10-07.md)。实际HEAD `00e509a974b40a7c9779fcd35e53b16637a13d60`，父提交/最低验收基线 `858dd94c7c6c8fc387940242403d67b6b36b5313`。

**放行S3工程，剩余P1=[]。** R7-01状态恢复/直接对象首验、R7-02显式重给载荷复用坏appearance首提都已修；原R6五组保持关闭。canonical+r现在守卫拒绝，符合原允许拒绝/unknown的验收；put_state幂等边界真实存在，但实际submit立即拒坏行、零新增，登记P2，不凭函数未加同形检查扩门。

## 结果与中断续跑

- PPV1完整21文件：**536 passed/0 skipped**，1文档转义warning，4.73s。
- R8新增当前：28passed；父858dd94原字节28项：**14行为failed/14passed，0字段或缺表红**。无import/预期适配；detached worktree已finally清理。
- G01安全隔离：**1138passed/8skipped/17deselected**，1warning，192.46s。270输入=本仓210+普通v3/src42+本仓非题面资产镜像18。8skip=真实评价5+v4对照1+派生metadata2；17desel=16slow+1明确排除需缺席评价脚本的export用例。R7历史1110/8/17另列；不冒充原环境1119/16。
- R6原12脚本全部exit0，修后关键控制断言exit0；R7条件16分段exit0。
- R7原化学55条后在手性恢复拒绝处exit1，尾部另补3条（原2案+直接对象补充）；新化学矩阵60条（59case+metadata）及新断言exit0。
- 原存储15case及新17case全部逐案达到预期；P1零新增、合法首次成功/幂等/多来源控制保持。
- 原观察断言是修前缺口记录，不是修后验收：R7化学旧assert首先在55/57计数失败，未执行行为分支；旧存储assert在prod-only错误created=True期望翻转处失败；R6旧assert在首个复杂共底物verified旧断言失败。
- 基线charge=99文案单独核实：clean R6；只改产物电荷后电荷violated、delta=-99、R5d retain。14行为红不是14个旧错误R6，测试说明应更正。

以上都是工程契约结果，不外推污染物路径、dev（B1环境中间步骤）或298（RHEA通用酶学）科学性能。

**账号额度中断-续跑：**运行验证已完成，永久证据尚未写入时被ChatGPT账号用量限制中断；非测试/程序失败。2026-10-07 18:03:40（UTC+8）收到继续指令后，复用已完成日志/源码身份，核463份既有输入及三专项SHA一致，未重跑任何套件/探针/G01。事件来源/未独立记录的中断时刻、续跑范围见 `INTERRUPTION_RESUME.json`，完整性检查见 `resumption_integrity.json`。归档前另观察到AGENTS并行流程文字更新，非审核写入，源码/测试不变；首次写入守卫在创建文件前停止，记录见`concurrent_policy_change.json`。续跑只补附件、静态语法/路径检查、报告与清单；新复跑控制器未在续跑时运行。

## 文件布局与采信范围

- `input_snapshot.json`：审核开始时463份既有源/tests/已知合成评审证据hash及HEAD/status，续跑初核逐项保持；最终写入前仅AGENTS并行流程文字变更，保留并单列`concurrent_policy_change.json`，其余462份未变。`resumption_integrity.json`和最终保全文件记录旧文件未改。
- `root_commands.json`、`root_replay_metadata.json`及`root_*_additional_commands.json`：主审实际argv/cwd/出口、实际源码hash/schema来源。原脚本硬编码旧HEAD是历史预期，不当当前执行HEAD。
- `r6_original/`：原R6只读脚本/fixture；`r6_replay/`：本轮实际执行的脚本和12份完整stdout/stderr、条件results、元数据。没有源码副本/库文件；临时源包含完整vendor。
- `chemistry_current/`：原R7化学输入脚本、55条原完整输出、补全脚本；根目录对应stderr/补全日志。`chemical_matrix/`：主审独立60条矩阵及修后观察断言、AST/grep完整证据、helper tests/metadata。
- `storage_current/`：原R7十五案/新矩阵和修后断言；根目录留实际17案完整stdout/stderr/命令。`conditions_current/`：16分段完整旧条件控制。
- `chemistry_specialist/`、`storage_specialist/`、`execution_specialist/`：已完成三专项冻结报告、脚本/输入、所有原日志、junit、版本/hash、分类及命令。原专项SHA清单原样保留，外层hash覆盖包括嵌套清单的所有附件。
- `assert_r7_replay.py`和`r6_selected_outcome_reference.json`：已修五组+六条旧lane关键行为比较，不比更新的人话错误文字/版本或再生成ID。
- `replay_review.py`：主审原运行体，**不可在永久目录直接执行**。`reproduce.py`将其与夹具复制到全新tmp后运行，固定R8HEAD；它是归档后生成的编排脚本，只做语法/依赖检查，不冒充又一次运行验证。
- `SHA256SUMS`、`manifest.json`、`report.sha256`：全部永久附件和报告SHA；仅外层两份清单不自我哈希，嵌套原清单也受外层保全。封存后不回写。

审计中的准备错误也保留：存储初次误传get_state envelope导致TypeError，已按首出现镜像完整重跑17案；主审初次化学assert漏 prior-run metadata导致FileNotFoundError，补齐实际记录后相同断言通过。这些不是被审源码回归，不能把未执行部分报通过。中断续跑没有借它们重复套件。

## 只在新tmp复现

禁止原地执行会写库/日志的脚本。以下每个`--out`必须是不存在的仓外新目录；固定本轮HEAD，依赖depending43及父提交git对象。用户没有要求本次再跑，下面是后续独立复现入口。安全入口需要同目录最终`SHA256SUMS`，先核其附件与源码输入，清单缺席或hash漂移即拒绝；静态检查记录见`archive_controller_static_check.json`。

短公共链（12旧脚本+R7分段+新化学/存储矩阵与修后断言；不执行pytest/G01）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r8_codex_2026-10-07/reproduce.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_r8_new_synthetic_replay
```

PPV1536+当前28+基线14/14（finally清理worktree）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r8_codex_2026-10-07/execution_specialist/reproduce_ppv1.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_r8_new_ppv1_baseline \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

必须保留同目录`independent_execution_as_executed.py`与`assert_ppv1_results.py`。原控制器收集基线红后总出口0仅表示汇总完成；wrapper随后核junit、真实pytest出口/14行为红/测试字节/清理，失败总出口非0。

G01精确安全隔离（约3–4分钟）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B \
  /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r8_codex_2026-10-07/execution_specialist/safe_g01_reproduce.py \
  --repo /Volumes/CC/Enzyme_Agent/dependingv43 \
  --out /private/tmp/ppv1_r8_new_safe_g01 \
  --python /Users/cc/miniconda3/envs/depending43/bin/python
```

同目录两份`input_hashes.json`/`g01_v3_source_addition_hashes.json`为独立当前270输入固定hash；普通v3/src默认兄弟目录或指定`--v3-src`，不读取原v3资产。`--prepare-only`只核hash和准备隔离树，历史已过；1138来自原safe_g01_r8.py的独立真实运行，不把prepare-only当全测。固定hash脚本会拒HEAD/hash漂移，不补真实evaluation/v4/金标题面。

原`safe_g01_r8.py`若需复现，要用`--r7-path-manifests <execution_specialist/allowlists>`；它默认指历史R7路径，所以优先用固定hash版本。`assert_execution_evidence.py`依赖当时完整源/资产物理副本并写slow名单，不能在只含日志的永久包原地执行。slow名单当时仅collect-only取得，未执行slow案例。
