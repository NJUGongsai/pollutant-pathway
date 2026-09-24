# v4.3 反应资产接线报告(ASSET WIRING REPORT)

- 完成日期:2026-09-24
- 任务书:`TASK_ASSET_WIRING.md`(v4.3 反应资产接线任务书)
- 结论:**任务完成**。本仓资产完整可验、v3 冻结引擎全部真实读取路径落在本仓 `assets/` 下、无任何到旧 v3/assets 的静默回退、7 个夹具 v4/v4.3 双臂对拍逐字段零差异、同进程第二套资产身份被结构化拒绝。

## 1. 新增文件与职责

| 文件 | 用途 |
| --- | --- |
| `pyproject.toml` | 最小可安装包定义(src 布局;pytest marker 注册) |
| `src/pathway_v43/__init__.py` | 包入口;导出 `resolve_config` |
| `src/pathway_v43/config.py` | `V3_CODE_ROOT`(v3 只读代码根)与 `V43_ASSET_ROOT`(本仓资产根)严格分离;优先级 CLI > 环境变量(`V3_CODE_ROOT`/`V43_ASSET_ROOT`)> 默认值;全部解析为绝对路径进入检查结果与 run identity |
| `src/pathway_v43/__main__.py` | `checkenv` / `probe` CLI;fail-closed 结构化 JSON 输出,非零退出,无凭证输出 |
| `src/pathway_v43/adapters/__init__.py` | LangGraph 后续调用的稳定接口出口 |
| `src/pathway_v43/adapters/asset_manifest.py` | 本仓 `MANIFEST.sha256`(21 条)逐文件哈希 + 与 `MANIFEST.json` 的路径/字节数/哈希三方核对;词法防路径逃逸;扩展资产与类比索引的 sha 选择器 |
| `src/pathway_v43/adapters/v3_engine.py` | v3 冻结引擎只读适配器:导入前 `dp_paths.ASSETS` 注入 + 原版 `resolve_and_verify` + 装载后路径断言 + 进程资产身份守卫;`predict/expand_raw/expand_merged/serialize_edge/cn_identity` 逐字镜像 v4 `V3Engine` |
| `src/pathway_v43/adapters/analog_index.py` | 两份 v4 类比最终索引装载(解析口径逐字镜像 v4 `UsptoIndex/CorpusIndex`),报告 available/rows/sha;启用时缺任一索引即 fail-closed |
| `scripts/compare_asset_roots.py` | v4/v4.3 双臂对拍:两臂各在独立子进程、同一解释器运行,父进程逐字段比较 |
| `tests/conftest.py` | v3/v4 代码根 fixture、清单校验 fixture、临时资产副本工厂(symlink 镜像,不触碰正本) |
| `tests/test_asset_manifest.py` | 正本 21 文件校验 + 合成清单的缺失/篡改/JSON 不一致/路径逃逸/无回退用例 |
| `tests/test_asset_root_isolation.py` | 缺核心文件/改扩展规则/缺类比索引/改索引哈希四类失败(点名文件);实测装载路径断言;第二套身份拒绝;同身份复用 |
| `tests/test_analog_assets.py` | 两索引装载(行数钉死 188,725 / 17,183)、SHA 与清单一致、缺一即错、与 v4 原版解析器逐项一致 |
| `tests/test_engine_asset_parity.py` | 驱动对拍脚本,断言全部夹具零差异 + 类别覆盖 + 两臂资产根归属正确;含比较逻辑防误报单元测试 |
| `tests/test_cli.py` | CLI fail-closed 契约:失败必须结构化 JSON + 非零退出、无 traceback;成功路径 JSON 摘要断言 |
| `tests/fixtures/asset_wiring_parents.json` | 7 个固定非 eval 输入夹具与预期类别 |
| `README.md` | 等价命令、Python 接口、许可声明 |
| `reports/asset_wiring_parity/{arm_old,arm_new,comparison}.json` | 双臂原始结果与比较报告(交付物) |

未修改本仓既有文件(ARCHITECTURE/REPO_DESIGN/ASSETS 及 assets/ 全部原样);未修改 dependingv3、dependingv4 任何文件。

## 2. 配置优先级与实际路径图

```
解析优先级:  CLI 参数  >  环境变量 V3_CODE_ROOT / V43_ASSET_ROOT  >  默认值
默认 v3 代码根:  <本仓>/../dependingv3        (只 import,只读)
默认 v4.3 资产根: <本仓>/assets               (只读,先校验后使用)
派生:  v3 运行数据根 = V43_ASSET_ROOT/v3_reactions
       类比索引根     = V43_ASSET_ROOT/analog
       v3 引擎源码目录 = V3_CODE_ROOT/src/depending   (sys.path 注入)

代码根不参与资产解析:dp_paths.REPO_ROOT 语义保留为 v3 代码根(与 v4 相同),
但 dp_paths.ASSETS 在导入任何 v3 引擎模块之前被重绑为 V43_ASSET_ROOT/v3_reactions,
因此 v3 引擎的全部实际读取都在本仓资产下;不存在“代码根隐式推导 v3/assets”,
也不存在本仓校验失败时回退旧 v3/assets 的路径。
```

## 3. 本仓清单校验与失败用例

- `cd assets && shasum -a 256 -c MANIFEST.sha256`:**21/21 OK**(交付前复跑确认)。
- `checkenv`(从 /tmp 任意工作目录启动):本仓 21 文件逐一 SHA256 通过;`MANIFEST.json` 的路径/字节数/哈希与 SHA 清单及磁盘三方一致(`asset_count=21`、`total_bytes=149,475,454`);原版 `env_asset_root.resolve_and_verify` 显式传入 `assets/v3_reactions` 通过,其返回的 8 个核心路径全部位于该根下;5 个扩展资产与 2 份类比索引哈希取自总清单。
- 失败用例(临时副本,正本未动;v3 原仓资产全程完好,证明无兜底):
  1. 删 `v3_reactions/corpus_env/donor_index.jsonl` → `AssetManifestError` 点名该文件;原版 `resolve_and_verify` 亦 `EnvAssetError`;
  2. 改 `v3_reactions/eawag/rules_new_clean.jsonl` 一个字节 → 总清单哈希不符点名该文件(该文件不在 v3 核心校验范围,只有本仓总清单能抓出——任务书要求的点);
  3. 删 `analog/corpus_templates_v1.jsonl` → 清单失败;传入已验清单时类比装载器自身也 `AnalogAssetError` 点名文件;
  4. 改 `analog/uspto_relaxed_index_v1.jsonl` 一个字节 → 哈希不符点名文件。
- 完整测试输出见第 6 节;`checkenv` 冒烟输出样例在交付记录中(`/tmp/checkenv_out.json`,可随时复现)。

## 4. 类比两份索引状态

| 索引 | 行数 | SHA256 | 与 v4 原版解析器一致 |
| --- | --- | --- | --- |
| `analog/uspto_relaxed_index_v1.jsonl` | 188,725(r1 空行跳过 0) | `28fdf6bfde881f8563032fc7f36d561728967cc1b8fd785dd87e5ebc80c2c4ab` | 行数/坏行/SHA 全同 |
| `analog/corpus_templates_v1.jsonl` | 17,183 | `8f3f2c1ac0cb17501e6a6f2ab65c22ae9e1768a3f1e8e4227b8305ba5ccfad92` | 行数/SHA 全同 |

v4 旧版“缺一份类比索引仍 available”的行为在 v4.3 被收紧:启用类比桥(`require_complete=True`,默认)缺任一索引或哈希不符即 `AnalogAssetError`;`require_complete=False` 仅供报告模式如实落 `None`。本任务不改检索排名算法、不改索引内容。

## 5. v4 / v4.3 对拍结果

双臂配置:**同一解释器**(python 3.11.16)、**同一 v3 代码提交** `eb24c1e50a94966c77fd108152d4ebff2d65032e`(main,工作区干净)、**字节一致的 13 个 v3 运行数据文件**(本仓总清单保证)、`OMP_NUM_THREADS=1`、零 LLM、未运行冻结 eval 或 298 外考。

- 旧臂:`pathway_agent.engine.V3Engine`(dependingv4 `dae1e8d49e7264a3cee741a547fab4cab61618de`, feat/v42-fix)+ 原 `dependingv3/assets`
- 新臂:`pathway_v43` 适配器 + 本仓 `assets/v3_reactions`

| 夹具 | 输入 | 旧臂候选数 | 新臂候选数 | 差异字段数 |
| --- | --- | --- | --- | --- |
| benzenediol | `Oc1ccccc1O` | 97 | 97 | 0 |
| phthalate_anion | `O=C([O-])c1ccccc1C(=O)[O-]` | 73 | 73 | 0 |
| toluene | `Cc1ccccc1` | 77 | 77 | 0 |
| hexane | `CCCCCC` | 84 | 84 | 0 |
| dbp_ester | `CCCCOC(=O)c1ccccc1C(=O)OCCCC` | 414 | 414 | 0 |
| ammonia | `N` | 33 | 33 | 0 |
| unparseable | `not_a_smiles` | 两臂同错(`unparseable_parent`) | — | 0 |

逐候选比较了 rank/engine_rank/layer/product_smiles/product_identity/source/score/score_semantics/v34_regime/eawag_reactions/p_uspto/p_envipath/p_retrieval/ion_filtered/wildcard_filtered/charge_variants(浮点两臂统一 round(·,6) 后精确相等),共 778 个候选 × 16 字段零差异。类别覆盖:EAWAG 已记录命中(benzenediol/phthalate/toluene 的 lookup 层)、规则产物(envipath)、检索产物(retrieval)、重复候选合并(uspto+envipath / uspto+retrieval / envipath+retrieval)、非法输入。所有含 lookup 候选的夹具无 budget_cut。

“有效但零候选”夹具:未找到——检索引擎 C 对任意可解析输入(H₂、NH3 亦然)都可能给出 Tanimoto>0 的 donor,任务书该可选项不适用,如实记录。

v4 序列化省略、v4.3 按任务书新增透传的字段(`donor_exact_match`、`n_evidence`、`cofactor_filtered`、`filtered`、`product_smiles_full`、`tanimoto`)单独检查:全部 lookup 层候选 `donor_exact_match=True` 且 `n_evidence≥1` 且带 `eawag_reactions`,未计入对拍差异。

原始结果文件:`reports/asset_wiring_parity/arm_old.json`、`arm_new.json`、`comparison.json`。

## 6. 真实引擎加载统计与运行环境

- 引擎加载(新臂,资产=本仓):`n_templates=188,725`,`n_envipath_rules=286`(+49 条 EAWAG 规则折叠进引擎 B),`n_corpus_records=42,646`,`n_donors=16,875`,`n_rankers=3`,加载 25.1s。
- 装载后断言:`X.TEMPLATES / ENVIPATH_RULES / ENVIPATH_TSV / CORPUS_DIR / MODEL_DIR / _G_V34_CALIB_PATH` 及 identity 的 library/corpus_v1/calibrator 路径全部位于 `V43_ASSET_ROOT/v3_reactions` 下,无一指向 v3 代码仓。
- 环境:macOS 27.0 arm64;Python 3.11.16;RDKit 2026.03.6;LightGBM 4.7.0;numpy 2.4.6;pytest 9.1.1(conda env `depending43`,与 v4 副本 venv 中留存的 v4 实际运行版本一致)。
- 资产 identity:`assets/MANIFEST.sha256` 自身 SHA `def94d82b65915f0ecd2377971cb082ba2b1c1464b4eb165a32d5e57e259aa34`;核心文件、扩展规则、两份类比索引的 SHA 全部进入 `asset_identity()` 输出(checkenv/probe 均返回)。
- 引擎代码 identity:v3 `eb24c1e50a94966c77fd108152d4ebff2d65032e`(main, clean);检索资产身份与引擎代码身份在 `asset_identity()` 中分列 `retrieval_assets` 与 `engine_code` 两节。

测试命令与结果(conda env depending43):

```
OMP_NUM_THREADS=1 PYTHONPATH=src python -m pytest tests/ -v
```

33 项全部通过(修订后),其中 4 项 slow(真实引擎加载 + 双臂对拍)与 9 项子进程/单元防误报测试。静态组可单独运行:`-m "not slow"`。

第二轮修订后全套 **37 项**全部通过(新增 v3_reactions symlink 逃逸回归 2 项——manifest/引擎入口/checkenv 三层拒绝——与比较器夹具全集核对单元测试 2 项)。

## 7. v3 导入时路径绑定的解决方法与进程缓存限制

**机制(按实际代码,非旧文档口径)**:`dp_paths.py` 在导入时由 `DEPENDING_V3_ROOT` 或文件位置计算 `REPO_ROOT/ASSETS`;`dp.asset()` 是普通函数,**调用时**动态读模块级 `ASSETS`。真正在导入时固化路径的是三个消费方:`expand_bbd_routes`(TEMPLATES/ENVIPATH_RULES/ENVIPATH_TSV/CORPUS_DIR/MODEL_DIR)、`single_smiles_hybrid`、`eawag_rules_engine`(RULES_PATH)。因此适配器的注入顺序是:先注入 `sys.path` 与 `DEPENDING_V3_ROOT`(语义=代码根)→ 导入 `dp_paths` → **重绑 `dp_paths.ASSETS = V43_ASSET_ROOT/v3_reactions`** → 再导入 `env_asset_root/bbd_v33_fusion/eawag_lookup/expand_bbd_routes/single_smiles_v32`。这样所有导入时绑定与运行时 `dp.asset` 调用都落在本仓;`X.MODEL_DIR/X.CORPUS_DIR` 再按 v4 同款从 `resolve_and_verify` 身份块重绑(双路一致)。AST 扫描确认导入链上无其它模块级文件读取。

**进程缓存限制与守卫**:v3 模块的导入时路径绑定、`expand_bbd_routes` 的进程级引擎全局(`_G_TPL_A/_G_RULES_B/_G_RECORDS/_G_RANKERS`)与 LightGBM Booster 都不可安全卸载。因此 v4.3 的规则是:进程首次 `get_engine` 前**必须**完成注入(适配器保证);进程内已加载过一套资产身份后再请求**不同**身份 → `EngineBootstrapError` 结构化拒绝(提示走隔离子进程,对拍脚本即按此实现);同身份重复调用返回同一实例。守卫范围覆盖 v3 引擎链模块预加载检测(`dp_paths/bbd_v33_fusion/eawag_lookup/expand_bbd_routes/single_smiles_v32/eawag_rules_engine/single_smiles_hybrid`)与链上模块 `__file__` 溯源(防同名模块被其它副本抢先占用)。

**symlink 说明**:v4.3 对实际读取路径执行**物理边界**约束,边界 = 配置的 assets_root(resolve 后的物理位置)。三层全部生效:① 清单校验逐条目做词法 + 物理检查——把 `v3_reactions`(或任何资产)用 symlink 指向旧仓/其它位置的部署会被以"文件物理路径逃逸"拒绝,即使字节与清单哈希一致;② 类比索引装载同样词法 + 物理(`_require_rel`);③ 引擎装载路径与 `resolve_and_verify` 返回的核心资产路径均以配置 assets 根为物理边界断言。若配置的 assets_root 本身是 symlink,边界取其物理目标,自洽部署不受影响;跨根逃逸一律 fail-closed。回归测试 `test_v3_reactions_symlink_escape_rejected` / `test_checkenv_rejects_v3_reactions_symlink_escape` 钉死该行为(后者即 review 的复现路径:checkenv 对 symlink 逃逸 exit 2 + 结构化 JSON)。测试的临时副本为全物理复制,正本未被触碰。

## 8. 偏离任务书的实现决定

1. **模块位置微调**:任务书推荐 `adapters/asset_manifest.py` 等,全部按推荐位置实现;额外增加 `adapters/__init__.py`(接口出口)、`tests/conftest.py`、`README.md`。
2. **serialize_edge 增加透传字段**:任务书 2.3 允许;v4 共有字段比较不受影响(第 5 节)。
3. **`X.V3_POOL` 导入期常量**:`expand_bbd_routes` 导入时经 `bbd_data_root.resolve` 计算出指向 v3 仓 `bbd_predictions/` 的**路径字符串**。单分子 predict/expand 流程从不读取它(仅批量 CLI `main()` 使用),且它不属于 v3/assets。作为已知无害残留记录于此。
4. **`v3_reactions/MANIFEST.sha256` 含未迁入的 `corpus_env_eval` 条目**:原版 `verify_env_assets` 只查必需文件,不存在的 eval 条目被忽略;本仓验收只以 `assets/MANIFEST.sha256` 为准,评测隔离语料未回到检索目录(纪律 1)。
5. **“有效但零候选”夹具不存在**(第 5 节,如实记录)。

## 9. 剩余风险

- **许可**:assets/ 内 EAWAG/enviPath/USPTO 衍生数据与混合检索语料缺可独立确认的公开再分发许可文本;本仓为项目工作区内部迁移,不构成公开发布授权(与 ASSETS.md 一致)。
- **确定性边界**:对拍在同机同解释器成立。跨机需同版本 rdkit/lightgbm;引擎 A 的 30s 模板预算是唯一时间相关因素,本次全部夹具无 budget_cut,极端大分子跨机对拍前应先复核该标志。
- **Python 接口稳定性**:`predict/expand_raw/expand_merged/cn_identity/asset_identity` 为 LangGraph 承诺接口;`_X/_S/_EGD/_EAR` 等下划线成员是 v3 模块句柄,后续不应直接依赖。
- **单进程身份守卫是强约束**:LangGraph 若需并行多资产身份,必须用子进程/进程池,不能在同进程多 `get_engine`。

## 10. 复现命令

```sh
cd /Volumes/CC/Enzyme_Agent/dependingv43
export PY=/Users/cc/miniconda3/envs/depending43/bin/python

# A. 清单(21/21 OK)
( cd assets && shasum -a 256 -c MANIFEST.sha256 )

# B. checkenv(任意 cwd;路径参数用绝对值)/ probe
cd /tmp && OMP_NUM_THREADS=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src \
  $PY -m pathway_v43 checkenv \
  --v3-code-root /Volumes/CC/Enzyme_Agent/dependingv3 \
  --assets-root /Volumes/CC/Enzyme_Agent/dependingv43/assets
OMP_NUM_THREADS=1 PYTHONPATH=/Volumes/CC/Enzyme_Agent/dependingv43/src \
  $PY -m pathway_v43 probe --smiles "Oc1ccccc1O" \
  --v3-code-root /Volumes/CC/Enzyme_Agent/dependingv3 \
  --assets-root /Volumes/CC/Enzyme_Agent/dependingv43/assets --top-k 10

# B'. 不带路径参数时走默认配置(代码根=../dependingv3,资产根=本仓 assets/),
#     可在本仓任意父目录/仓内直接运行:
cd /Volumes/CC/Enzyme_Agent/dependingv43 && PYTHONPATH=src $PY -m pathway_v43 checkenv

# C. 测试(全套;静态组 -m "not slow")
OMP_NUM_THREADS=1 PYTHONPATH=src $PY -m pytest tests/ -v

# D. 双臂对拍(原始结果与比较报告落 reports/asset_wiring_parity/)
$PY scripts/compare_asset_roots.py
```

## 11. 修订记录(2026-09-24,响应 review)

review 核实了资产一致性、23 项测试与 778 候选零差异,提出三处验收缺口与一处命令错误,均已修复:

1. **[P1] CLI 失败路径输出结构化错误**:`__main__.py` 误用不存在的 `sys.environ`,失败时抛 `AttributeError` + traceback 而非任务书要求的 JSON。已改 `os.environ`,并以子进程测试钉死契约(`tests/test_cli.py`):缺资产根/缺 v3 代码根/坏根 probe 均 exit 2、stdout 为 `ok=false` 的 JSON、无 Traceback;另补 checkenv 成功路径的 JSON 契约断言。
2. **[P1] 类比索引物理路径逃逸**:`analog_index._require_rel` 原先只做词法检查,symlink 指向仓外文件会被接受。现加双重约束:词法(相对、无 `..`)+ 物理(resolve 后必须位于本仓 assets 根内),逃逸抛 `AnalogAssetError` 并带 `physical` 详情。测试 `test_analog_symlink_escape_rejected` 以纯 symlink 镜像副本复现;conftest 镜像工厂相应改为 analog/ 文件物理复制,其余 symlink。v3 引擎装载路径本就做物理检查,不变。
3. **[P2] 对拍误报防护**:`compare_asset_roots.py` 原把有效输入的运行异常记作 `parseable=False`,两臂同错会误判通过。现区分 `runtime_failure`(记录异常类型/摘要)与 `unparseable_parent`(引擎明确定义),并新增逐夹具**预期验收**:按夹具声明核对两臂实际解析状态、候选数下限、lookup 命中与实际来源类别(由候选 source/layer 推导,合并 source 按词素拆分),任一臂不满足即 FAIL。比较报告新增 `declared_categories/found_categories` 字段。新增单元测试:两臂同报 runtime_failure → FAIL、单臂失败 → FAIL、unparseable 仅在两臂均报 `unparseable_parent` 且无候选时通过、类别/候选数/lookup 缺失 → FAIL。
4. **报告复现命令**:§10 B 组命令原用相对路径(`../dependingv3`、`assets`)在 /tmp 执行会失败,已改绝对路径,并补充不带参数走默认配置的等价命令。

修复后全套测试 33 项通过(23→33:CLI 契约 4 项、类比 symlink 逃逸 1 项、比较逻辑与预期验收 5 项;对拍重跑仍 7/7 零差异,比较报告新增 declared/found categories 字段)。

### 第二轮修订(2026-09-24,响应 review 复核)

1. **[P1] v3 资产根 symlink 逃逸**:review 实测把 `v3_reactions` 整体链接到 `dependingv3/assets` 后 checkenv 仍 exit 0,并把旧仓 `library_full.jsonl` 报为核心文件——原因是一级清单校验只做词法检查,目录 symlink 下字节哈希逐一对得上。现 `verify_repo_manifest` 对每个条目增加**物理边界检查**(边界 = 配置的 assets_root resolve 后的物理位置),任何条目解析后落在边界外即 `AssetManifestError`(带 `physical` 详情);引擎入口(`get_engine`/`V43Engine`)与 checkenv 对 `resolve_and_verify` 返回路径及引擎装载路径的断言边界同步改为配置 assets 根。回归测试三层钉死:`test_v3_reactions_symlink_escape_rejected`(manifest + get_engine)与 `test_checkenv_rejects_v3_reactions_symlink_escape`(review 复现路径:exit 2 + 结构化 JSON 点名 dependingv3)。配置的 assets_root 本身是 symlink 时边界取其物理目标,自洽部署不受影响。
2. **[P2] 两臂同时遗漏夹具误报通过**:比较器原只遍历两臂结果并集。现 `_coverage_problems` 核对两臂结果与声明夹具名单**完全一致**——缺失、多余、重名(夹具名或任一臂结果名)均记入 `__coverage__` 条目并整体 FAIL;逐夹具比较只遍历声明名单。新增单元测试:两臂空结果 → FAIL(含 `old/new_missing_fixtures`)、重复名 → FAIL、未声明名 → FAIL。
3. **文档**:`REPO_DESIGN`/§10 复现命令注释的"全部 23 项"更正(不再写死数字);§7 symlink 政策改为物理边界表述。

第二轮后全套 **37 项**全部通过(33→37),对拍重跑仍 7/7 零差异。
