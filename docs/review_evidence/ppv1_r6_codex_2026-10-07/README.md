# R6 独立复审证据（合成公开入口）

审核 HEAD `6d9020130a481866ce2f3b79933907a33d8cfc9e`，基线 `293bc627f57b1f778aa433750f7f61d00b4a9d18`；日期 2026-10-07。完整裁定：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/POLLUTANT_PATHWAY_S0_S2_CODEX_REVIEW_R6_2026-10-07.md`。

这份证据只核查表示、证明覆盖、条件及账本契约，不证明污染物真实降解路线、生物可行性、机制或泛化性能。全部结构、条件、来源和 SQLite 为合成。真实 AtomTool 基准执行与接口只加原始 CX 标记的输入明确区分；SQL 只准备新合成库的损坏，接受/拒绝由 public submit 观察。没有金标、真实题面、封存逐题 run 或模型请求。

| 文件/目录 | 证据 |
| --- | --- |
| `admission_completion_probe.*`、`r5_admission_coverage_probe.py` | 14 条记录：旧覆盖及正控、实际新增原子、3 个复杂共底物、自由基作用域控制 |
| `chem/` | 新 CX 9 条记录（内含矩阵及 6 条完整公共链）、旧化学 6+17+40 条 |
| `conditions/` | 新10分段案例；旧7/19顶层、结果及 bootstrap-only/分段用 fixture |
| `storage/` | 新17cases+metadata；旧9+21+29；正常/损坏 submit、counts、manifest |
| `reports/` | 三线专项原报告，里面旧临时目录路径是执行来源；主报告/本复跑器提供永久入口 |
| `pytest_output.txt`、`pytest_subagent_output.txt` | 主审与专项各一遍隔离451项回归，无skip；唯一warning为文档转义 |
| `baseline_tests/`、`baseline_red_output.txt` | 70项R6新测试对R5源：44failed/26passed；仅临时化学测试缺失常量import换同值字面量 |
| `reproduce.py`、`assert_observed.py` | 隔离复制/复跑及当前观察断言；包含仍有缺口成立，不能作修后期望 |
| `manifest.json` | HEAD/版本/初始工作区状态、输入和附件SHA-256、报告hash及执行说明 |

记录数含metadata、对照和披露，不是漏洞数。旧脚本内HEAD常量有293bc62/e80等历史值，原样保留；实际执行身份以manifest/run_metadata为准。旧条件复合函数遇到已修契约拒绝后内部后半段未执行；wrapper只保证后续顶层继续，本次分段10案补足相关控制，不能称每条内部语句都通过。基线红日志有字段KeyError，不能把44红都当行为漏洞。

**不要直接在永久目录运行探针。** `reproduce.py` 只读取附件，复制完整源码（含冻结vendor完整性文件）和脚本到新建空目录，再执行。所有 SQLite、结果和cache禁用措施留在临时输出。只修改fixture路径为bundle相对位置，没有改变探针判断；条件历史fixture已打包，不依赖外部旧审核目录。storage/src临时链接指向同一隔离source，只用于脚本原有hash核查。

复跑当前 HEAD（把 `--out` 换成一个新的空临时目录路径）：

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/cc/miniconda3/envs/depending43/bin/python -B /Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/ppv1_r6_codex_2026-10-07/reproduce.py --repo /Volumes/CC/Enzyme_Agent/dependingv43 --out /private/tmp/ppv1_r6_verify_NEW
```

默认执行12份探针入口、451套件及观察断言；结果在out，程序不修改仓库/永久证据。附 `--baseline` 可再核查固定R5对照70项预期红；该步骤只git archive到临时目录。原基线已独立执行并保存，默认不重复。仅检查探针可用 `--skip-pytest`。

修复后要复跑旧探针时显式加 `--allow-head-change`。这会在临时storage脚本改核对HEAD为新HEAD，并记录实际身份，跳过R6观察断言；它不会改附件或将“缺口已变”误算失败。部分未捕获的新增严格契约拒绝可能使对应脚本退出，需要分段捕获并分别写修后期望，不能只看exit 0。正常控制依旧要保持。不要使用原始R6缺口断言作为新版本通过线。

交付的1062passed/16deselected是外部声明，本证据没有重跑全量legacy套件或G01/298，不外推性能。
