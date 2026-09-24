# v4.3 反应资产接线任务书

> 编写日期：2026-09-24。交给独立执行模型实施；本会话负责后续 review。任务范围是让 v4.3 的检索与引擎适配器实际读取本仓 assets/，完成校验和对拍。v4.3 的 LangGraph 全流程、路径选择策略和 LLM 预测不属于本任务。

## 0. 开工事实与目标

目标仓：本目录 dependingv43。当前已有 ARCHITECTURE.md、REPO_DESIGN.md、ASSETS.md 和 assets/，尚无 Python 包或 Git 仓。反应资产已迁入：

| 路径 | 内容 |
|---|---|
| assets/v3_reactions/ | v3.5 运行语料、EAWAG 库及规则、enviPath 规则、USPTO 模板、ranker、calibrator，以及原始元数据 |
| assets/analog/ | v4 最终 USPTO relaxed index 与 corpus templates index，以及原始元数据 |
| assets/MANIFEST.sha256、assets/MANIFEST.json | 本仓完整性清单，21 个来源文件、149,475,454 字节 |

来源、排除项及哈希见 ASSETS.md。默认 v3 代码根为相邻的 ../dependingv3；v4 对照代码在 ../dependingv4 或本机 /Volumes/CC/tmp/Enzyme_Agent/dependingv4 的 feat/v42-fix。仅把旧代码和冻结评测器当作只读来源。

**完成定义**：v4.3 能以独立配置指定“v3 代码根”和“v4.3 资产根”，启动时先校验本仓清单，随后用 v3 冻结引擎代码从本仓资产产生候选；类比检索适配器同时加载本仓两份最终索引。若本仓资产缺失或篡改，即使 v3 原资产可用也必须失败。与 v4 同一引擎实现、同一输入的候选顺序和主要字段必须对拍一致。

## 1. 必须理解的旧代码路径陷阱

执行前先读以下文件，按实际实现记录依赖，不依赖旧文档中的口头描述：

- ../dependingv3/src/depending/dp_paths.py：导入时根据 DEPENDING_V3_ROOT 计算 ASSETS；v3 的模板、规则等模块在导入时调用 dp.asset 并缓存路径。
- ../dependingv3/src/depending/env_asset_root.py：显式资产根可由 resolve_and_verify(root) 校验；只校验核心运行文件，扩展规则和模板还需本仓总 manifest。
- ../dependingv3/src/depending/single_smiles_v32.py 与 expand_bbd_routes.py：加载模板、enviPath 规则、语料、ranker、EAWAG 规则的实际代码。
- ../dependingv4/src/pathway_agent/engine.py：现有 V3Engine 把代码根与 v3/assets 根耦合，是迁移参考，不应原样复制这个耦合。
- ../dependingv4/src/pathway_agent/analog.py：旧版允许缺一份类比索引仍返回可用；v4.3 在启用类比桥时须检查所需两份索引及哈希。

v3 的 MANIFEST.extensions.sha256 包含未迁入的 corpus_env_eval。它是原始来源记录，不是本仓验收清单；本仓验收只以 assets/MANIFEST.sha256 和 assets/MANIFEST.json 为准。不要把评测隔离语料加回默认检索目录。

## 2. 交付代码

在本仓新增最小可安装包和接线模块，推荐位置如下；可根据实际实现微调文件名，但职责必须清晰：

    pyproject.toml
    src/pathway_v43/__init__.py
    src/pathway_v43/__main__.py
    src/pathway_v43/config.py
    src/pathway_v43/adapters/asset_manifest.py
    src/pathway_v43/adapters/v3_engine.py
    src/pathway_v43/adapters/analog_index.py
    scripts/compare_asset_roots.py
    tests/test_asset_manifest.py
    tests/test_asset_root_isolation.py
    tests/test_analog_assets.py
    tests/test_engine_asset_parity.py
    docs/ASSET_WIRING_REPORT.md

本阶段只需实现资产校验、只读引擎适配、类比索引装载、checkenv / probe 入口和上述测试。LangGraph 后续工作流将调用这些适配器；请为它提供稳定 Python 接口，不为此任务搭完整的 StateGraph、PathwayStore 或 PredictionAgent。

### 2.1 配置与路径

- 分开暴露 V3_CODE_ROOT（默认 ../dependingv3）与 V43_ASSET_ROOT（默认本仓 assets/）；运行数据根为 V43_ASSET_ROOT/v3_reactions，类比根为 V43_ASSET_ROOT/analog。
- 允许 CLI 显式覆盖这些路径，环境变量只作默认值；所有实际解析后的绝对路径进入检查结果和 run identity。
- 不能由代码根隐式推导到 v3/assets，也不能在本仓资产校验失败时回退到旧 v3/assets。
- v3 模块存在导入时绑定的路径和进程全局模型对象。首次导入前必须完成资产根注入；单进程若请求第二套不同资产身份，应明确拒绝或在隔离进程执行，避免复用上一次加载的全局对象。

实现者可以选择明确的兼容层或运行时目录映射，使 v3 的 dp_paths 与本仓 v3_reactions/ 对齐；不得改动 v3 源文件，也不得靠全局修改旧仓资产目录完成接线。若采用 symlink 或进程内路径绑定，应在报告中解释生命周期、跨平台限制和为什么所有实际读取仍落在 v4.3 资产下。

### 2.2 校验与 fail-closed

- 加载前按 assets/MANIFEST.sha256 校验本仓 21 个来源文件的 SHA256；核对 MANIFEST.json 的路径、大小与哈希一致。
- 对 v3 引擎调用原版 env_asset_root.resolve_and_verify，显式传入 V43_ASSET_ROOT/v3_reactions；其返回的每个运行路径必须位于此根下。
- 对扩展模板、EAWAG/enviPath 规则和两份 analog 索引，使用本仓总 manifest 校验，不以“文件存在”代替完整性。
- 缺失、校验失败、路径逃逸或启用类比桥时缺任一索引均以结构化错误退出，checkenv 返回非零；输出不得包含凭证。
- 为每次 probe 返回 asset_identity：本仓 manifest SHA、v3 运行根及核心文件 SHA、扩展规则 SHA、两份 analog 索引 SHA，以及 v3 代码版本。区分检索资产身份和引擎代码身份。

### 2.3 引擎与类比适配器契约

- 引擎最少提供 predict(smiles, case_id, top_k=None) 和 expand_raw(smiles, case_id)；候选保留原顺序、产物 SMILES、source、layer、engine_rank、原始 score 及 score_semantics。
- EAWAG 已记录反应的 eawag_reactions、donor_exact_match、n_evidence 等可用来源字段须保留，以便 v4.3 后续区分“已记录反应”和“规则匹配”。可增加字段，但对拍时先比较与 v4 共用字段。
- 类比适配器装载两份最终索引并报告可用、行数与 SHA；本任务不改变现有检索排名算法或索引内容。
- 入参无法解析或资产不可用时明确报错；不得返回空候选来伪装运行成功。

## 3. 接线验收与对拍

### A. 清单

在 assets/ 目录执行以下命令，全部文件必须为 OK：

    shasum -a 256 -c MANIFEST.sha256

checkenv 从任意工作目录启动时，也必须定位并校验同一批 v4.3 资产。ASSETS.md、ARCHITECTURE.md、REPO_DESIGN.md 中的实际路径说明随实现更新。

### B. 路径隔离

在临时副本中分别制造“缺一个核心文件”“改动一个扩展规则文件”“缺一份类比索引”“改动索引哈希”。各用例均应失败并指出文件；原 v3/assets 即使完好也不能兜底。测试只操作临时副本，不篡改本仓正本。

实测装载后断言模板、EAWAG/enviPath 规则、语料、库、ranker、calibrator 的实际路径均在 V43_ASSET_ROOT/v3_reactions 下；类比路径均在 V43_ASSET_ROOT/analog 下。若某旧模块仍读取 v3/assets，任务未完成。

### C. v4 对拍

使用相同 v3 代码版本和字节一致的 13 个 v3 运行数据文件，对以下两臂在独立进程运行，以免模块全局缓存串线；两份 analog 索引另由类比适配器测试：

1. 旧 v4 V3Engine + 原 v3/assets。
2. 新 v4.3 适配器 + v4.3/assets/v3_reactions。

建立至少 5 个固定、非 eval 的输入夹具，覆盖 EAWAG 已记录命中、规则产物、检索产物、重复候选合并和非法输入；若能找到有效但无候选的分子，再增加该夹具。具体 SMILES 与预期类别写入 tests/fixtures/asset_wiring_parents.json。比较规范产物身份、候选数、候选顺序、source/layer、engine_rank、共同 score 字段及 score_semantics。若旧版字段被 v4 序列化省略，新版新增来源字段单独检查，不把新增字段算成不一致。任何真实差异须定位成资产、导入顺序或算法适配差异，不能仅凭“看起来接近”通过。

在可复现的本地 Python 环境执行；记录 Python、RDKit、LightGBM、v3 代码提交和完整命令。运行 v3 引擎时可设 OMP_NUM_THREADS=1，以控制线程行为。对拍只调用确定性引擎，零 LLM，不运行冻结 eval 或 298 外考。

### D. 冒烟接口

至少提供：

    python -m pathway_v43 checkenv --v3-code-root ../dependingv3 --assets-root assets
    python -m pathway_v43 probe --smiles "Oc1ccccc1O" --v3-code-root ../dependingv3 --assets-root assets

probe 输出候选摘要与 asset_identity 到指定 JSON 文件或 stdout；检查路径必须指向 v4.3/assets。CLI 参数名称若调整，README/报告给出等价命令。

## 4. 实施纪律

1. 本任务不修改 dependingv3、dependingv4 的代码、资产和已冻结运行产物；不复制评测隔离语料、模型权重、密钥或考试答案。
2. 本任务不重建规则库、不改反应评分、不调提示词、不调用外部 LLM；遇到旧实现问题先在报告中列出证据和最小适配处理。
3. 本仓目前不是 Git 仓，不以提交记录代替交付；提供实际文件清单、测试命令与输出。
4. 本地第三方数据缺少可独立确认的公开再分发许可文本；内部接线可继续，报告需保留这一事实，不把本次迁移描述为获得公开发布授权。
5. 先让清单和路径隔离测试通过，再跑真实引擎对拍；对拍失败不得以空候选、跳过测试或改变旧基线口径交付。

## 5. 交付给 reviewer 的材料

在 docs/ASSET_WIRING_REPORT.md 写明：

- 新增/修改文件及用途，配置优先级和实际路径图；
- 本仓 manifest 校验结果、失败用例结果、类比两索引状态；
- ≥5 个输入的 v4/v4.3 逐项对拍结果与原始结果文件位置；
- 真实引擎加载统计、Python/依赖版本、资产和代码 identity；
- v3 导入时路径绑定的解决方法及进程缓存限制；
- 偏离本任务书的实现决定、剩余风险及复现命令。

review 的硬门槛：本仓资产完整、真实读取路径在本仓、无静默回退、对拍一致、恢复/重复初始化不会串资产。全部满足后，这组适配器才可作为后续 LangGraph ReactionFinder 节点的底座。
