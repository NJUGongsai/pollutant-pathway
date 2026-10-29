# T-H 部署轮两处 delta 复核（2026-10-20）

> **最新终判定见 §5（HPC 独立补证阶段）：就本请求两处 delta 放行。** §1–4 的 SSH/V3 待项及有限通过结论为当时快照，原文与原证据保留。

**结论：两处源码 delta 在本次固定范围内通过；未发现有代码及公共链证据支持的新增阻塞。整体发车仍有远端访问和 V3 评分产物交付缺口，不能据本报告宣布已发车或交付闭合。**

题域标签：**298 = RHEA 通用酶学 / 已见题（post-hoc）**。本次只有规则级合成验证，不外推真实 298 科学性能。

## 1. 范围与来源

- 请求：`docs/T_H_DEPLOY_FIX2_REVIEW_REQUEST_2026-10-20.md`；遵守当前 `AGENTS.md`。
- 实际 HEAD：`abbfa39bc503a6034764eeb0b643b0baea3d8a42`；两 delta 为该 HEAD 上未提交改动。
- 只读源码复核与确定性本机测试；没有修改 src/tests、安装依赖、联网、调用外部模型、访问 reports 下真实题面/金标/封存 run、HPC 执行或 Git 提交。
- 独立本机执行证据：[证据目录](review_evidence/t_h_deploy_fix2_codex_2026-10-20/README.md)。HPC 与操作状态附记来自主会话/同轮部署检查，未混作本子审执行结果。

## 2. SHA 与 delta 判定

| 文件 | HEAD 文件 SHA256 | 当前/隔离副本文件 SHA256 | diff（numstat） | 判定 |
|---|---|---|---|---|
| `src/pathway_v43/pollutant/evaluation.py` | `a7e5ecfd8cdabbda4f4c99de40b7c9ee92a24e2d5a93525a506860f94c153eae` | `37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8` | +31/−2 | 本机有限范围通过；Linux/HPC 实测待独立验证 |
| `src/pathway_v43/pollutant/s5b_compiler.py` | `4cf61a8a0a6e19214e39b36879e6c1bf2526b8a8731dbc541ea70afb7ae3fbb3` | `f917762bf9ec43d70b85ef3740ab7f22b866b42c06a1461ec336882eb2685dfc` | +71/−1 | 本机有限范围通过；真实池分判待独立验证 |

完整 SHA 与请求一致。证据见 [source_verification.json](review_evidence/t_h_deploy_fix2_codex_2026-10-20/source_verification.json) 和 [source_delta.patch](review_evidence/t_h_deploy_fix2_codex_2026-10-20/source_delta.patch)。

**delta-1（平台化 transforms 指纹）**：macOS 原路径仍排第一；其后按 `sys.prefix/lib`、`purelib`、包父目录和 conda 包位置锚查找，候选内部排序稳定。全失败时原 `transforms_fingerprint_unavailable` 拒绝仍在。`environment` 赋值的 AST 与 HEAD 完全相同，六键零增删；路径死变量没有进入指纹。本机注册表 `available=True`、`resolve v3` 成功，四臂参数指纹与已有常量逐字节相同。未把 macOS 的通过外推到 Linux/venv/conda 任意组合。

**delta-2（产物身份自洽门）**：门位于公共编译包装层的 `compiled` 返回后；`_compile_donor_template_impl` 的 AST 与 HEAD 相同。主产物及全部共产物逐项交给现有 `build_chemical_state(..., "source_product", ...)`，与下游构建来源一致；拒绝时返回 `product_component_identity_invalid` 及逐组分信息，补映射路径继续披露 `template_remap`。没有新增化学判据；合法正控仍能编译、执行、提交、导出和重放。实测版本为 `s5b-compiler-6` / `product-identity-gate-1`，pool policy 仍为 `s5b-pool-policy-9`。

## 3. 本机独立执行

新隔离目录：`/var/folders/mg/7frznpjj7y16hqgk_g6h_28c0000gn/T/th_delta_local_20261020_ejqcjju_`。复制当前 src（含 vendor）、tests、pyproject 和安装包 dist-info；随后补齐资产清单及清单内文件，共 24 件、166,863,941 字节。未复制 reports。源码与测试原样，永久证据目录内未执行测试。

复用 `/Volumes/CC/Enzyme_Agent/dependingv43/v44/.venv/bin/python`：Python 3.11.16、RDKit 2026.3.6、pytest 9.1.1；chemstate schema 为 `ppv1-chemstate-8`。设置 `PYTHONDONTWRITEBYTECODE=1`、`-B`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`、`-p no:cacheprovider`；实际导入路径均位于隔离副本，检查未生成 `__pycache__` 或 `.pytest_cache`。

| 执行 | 结果 | 解释 |
|---|---|---|
| 首轮，隔离输入未齐 | 97 passed / 7 failed | 5 项因缺少 assets，2 项因 pytest tmp 放在隔离仓内触发既有输出根守卫；属于本次布置错误，不报源码失败 |
| 补齐清单资产、pytest tmp 移到仓外后，同一套件复跑 | **104 passed / 0 failed，2.86 秒** | 69 项编译门/补映射/谱系/v4b/w1 + 35 项 v3/v2 |
| 全量 not-slow | 本次未执行 | 请求中 2299/0/16 为实施方声明，本报告不把它写作独立执行结果 |

七个实际测试文件：`test_ppv1_s5b_product_identity_gate.py`、`test_ppv1_s5b_template_remap.py`、`test_ppv1_s5b_pool_lineage.py`、`test_ppv1_s5b_hit50_v4b.py`、`test_ppv1_s5b_hit50_w1.py`、`test_ppv1_criteria_v3.py`、`test_ppv1_criteria_v2_exemption.py`。实际命令见 [commands.txt](review_evidence/t_h_deploy_fix2_codex_2026-10-20/commands.txt)；[首轮日志](review_evidence/t_h_deploy_fix2_codex_2026-10-20/pytest.log)、[复跑日志](review_evidence/t_h_deploy_fix2_codex_2026-10-20/pytest_complete.log)、[运行版本和四臂指纹](review_evidence/t_h_deploy_fix2_codex_2026-10-20/runtime_observation.json) 均保留。唯一 warning 是既有 chemstate 模块 docstring 的转义字符弃用提示，不影响结果。

## 4. 未验证项与发车状态

| 项目 | 本次证据边界/后续义务 |
|---|---|
| HPC `available=True` / lib SHA `06cbe785…` | 请求中的实施方声明；本次未独立连接或复现。可连接后用远端 `venv_v44run/bin/python -B` 在同步源码上打印 `_criteria_v3_arm_registry()` 的 available/environment/arms，并调用 `resolve_criteria_version(PPV1_CRITERIA_V3)`，同时复核完整源码 SHA |
| 550 spec 中 21 拒/529 过、14 题余池/7 题池清空 | 实施方声明且扫描脚本/产物未存档；本次未访问真实题面/金标/批根，**没有独立复现，也不认证“零误伤”**。后续在获授权的新批根按同源 helper 执行计数并落盘，以批根实测为准 |
| 原预注册/no-cap | 主会话已核两份文本 SHA 匹配现有批准记录，无需为相同文本重签；本报告没有改写已签 PREP/TASK，也不产生新批准 |
| 远端连接 | 主会话报告：文档所列 key 文件不存在，登录返回 permission denied，已停止；当前远端运行状态不能确认 |
| V3 档 A 披露与评分产物 | 同轮 launch readiness 已确认 `scripts/hpc/sbatch_th_score.sh` 只跑 v1/v2，尚未接入 V3 披露；`score_s5b_batch` 固定写批根 metrics/report。直接追加 v3 会覆盖根部 v2 产物。发车/交付脚本须先闭合并保留并列产物；这是操作链缺口，不据此判定两源码 delta 存在未证错误 |

本次源码结论限于上述两处 delta 及现有 104 项合成回归；不确认 HPC 作业状态、不代签预注册/费用/发车指令、不确认真实批结果。

## 5. 补充终判定（2026-10-20，HPC 只读独立补证阶段）

**就 `T_H_DEPLOY_FIX2_REVIEW_REQUEST_2026-10-20.md` 两处 delta 放行。** 原报告的源码/104 项合成回归证据继续有效；本阶段未重复测试。当前本地 HEAD 为 `04b94cb75be74e0b72b2b103f5bbfae2fe83ab8c`，本地及 HPC 两文件完整 SHA 均仍为 §2 当前锁值 `evaluation.py=37c092310d34d9f417234ccacd508942b3ce3edef640c73ab94022fd8dc75ad8`、`s5b_compiler.py=f917762bf9ec43d70b85ef3740ab7f22b866b42c06a1461ec336882eb2685dfc`。

本阶段采信同轮 HPC 只读代理的独立执行证据，经读取安全结果和实际扫描脚本核对；不是本子审重新连接 HPC。新证据见 [HPC 补证说明](review_evidence/t_h_deploy_fix2_hpc_readonly_2026-10-20/README.md)、[运行环境/指纹](review_evidence/t_h_deploy_fix2_hpc_readonly_2026-10-20/runtime_observation.json)、[逐件分判安全结果](review_evidence/t_h_deploy_fix2_hpc_readonly_2026-10-20/replay_observation.json)、[只读扫描脚本](review_evidence/t_h_deploy_fix2_hpc_readonly_2026-10-20/replay_probe.py) 和 [实际 SSH 命令](review_evidence/t_h_deploy_fix2_hpc_readonly_2026-10-20/commands.md)。

| 请求项 | 补证与判定 |
|---|---|
| delta-1：Linux/venv/conda 实际覆盖 | Python 3.11.15、RDKit 2026.03.5、chemstate-8/compiler-6；v3 `available=True`、四臂指纹可计算、`resolve v3` 成功，实际引擎库 SHA 为 `06cbe785e3f86b58a91e8abe2d77e27bf0a4d676644a902904469ddad3999ea2`。结合 §2 候选顺序、回退与六键不变证据，放行。本机 Mac 与 HPC 环境不同，四臂各自按实测环境登记，不要求跨环境指纹相同 |
| delta-2：真实旧池同源门分判 | 298 个旧批 run_inputs 中 **550 次 spec 出现**，含 **546 个不同 `(qid,key)` 对、4 次重复键出现**；逐次 helper 判定 **529 过/21 拒**，21 拒全 remap-applied、涉及 21 题，invalid kind 均为 `unregistered_cx_class`；过滤旧池后 **14 题余池/7 题清空**。按完整 `(qid,spec.key)` Counter 与旧 face_v2 逐件多重集合相等，双方差集为空，题级集合也相等。结合 §2 包装层、拒因/披露、合法正控证据，放行 |
| P3-IDENT/P3-LABEL 附带确认 | `s5b_builder.py` 批级键两处及注记均动态引用 `S5B_COMPILER_VERSION`（当前行 1202/1681/1751），既有 104 项内的 pool_lineage 测试已断言 compiler-6；仅确认源码及既有测试。**r2 实际批级键须待 build 完成后实核** |
| 早期 SSH/V3 操作待项 | 本轮 SSH 只读补证已成功，原连接失败为历史状态；V1/V3/V2 产物并存、根 V2、V3 不提升 strict，以及留证/重试/防重复提交等操作面已通过独立本机短审，见 [r2 操作链短审](review_evidence/t_h_r2_operations_shortaudit_2026-10-20/README.md)。不据本机操作审宣称远端整链已执行完成 |

分判结论只认证既定 chemstate **机器身份可表示门**的结果与旧诊断逐件闭合；“529 过”不认证化学有效性或化学零误伤。相同 `(qid,key)` 不证明 spec 全内容相同，因此保留逐次计数，不把 550 写作独特 spec 数。14/7 是对旧批池过滤后的效应，**不是 r2 重建实测**，r2 分母及批级版本仍以其 build 后产物为准。

HPC 补证未读取题卷/参考图/金标或逐题 case/run；安全输出不含结构，输入处理前后 mtime/size 一致，未写远端文件、调用模型或变更调度。2026-10-20 09:58:57 +08:00 的 r2 build RUNNING 记录仅为状态快照。此次放行不外推真实 298 科学性能，不代替成绩/化学复核；**2299/0/16 全量 not-slow 仍是实施方声明，本轮未独立执行**。本次仅更新本报告导航和本节，不回写历史证据，不修改源码/测试，不提交。
