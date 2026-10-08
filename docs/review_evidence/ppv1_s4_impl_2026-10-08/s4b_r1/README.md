# s4b_r1 证据目录 —— PPV1 S4b 收尾批(正式文件导出 + v3 有损投影)

批次:S4b r1(S4 任务书 §7 S4b 十项的一次性实施;S4a 复审已通过
—— 备用通道 tokeasy gpt-6-sol,P1 清零,报告见
`docs/POLLUTANT_PATHWAY_S4A_CODEX_REVIEW_2026-10-08.md`)。

- 实施 HEAD:fc40605(S4a 提交)+ 本批未提交 S4b 改动(见
  `metadata/metadata.json` 的 dirty 清单;本证据目录与交付书随本批
  一并提交);
- 直接父基线:fc40605819201ae4a7101fc500b19083d78383b0;
- 交付书:`docs/POLLUTANT_PATHWAY_S4B_DELIVERY_2026-10-08.md`;
- mimo 请求:v17(`mimo/mimo_ppv1_chem_review_request_v17.md`,
  主会话按 AGENTS.md 通道 A 送审;v16 送审快照字节同 fc40605 存
  `mimo/mimo_ppv1_chem_review_request_v16_sent.md`)。

## 目录组成

- `current/` —— 当前树(S4b 实施态):
  - `s4b_focus_*`:S4b 焦点 18 用例(**18 passed,exit 0**);
  - `ppv1_full_*`:PPV1 全量(**932 passed/627 deselected,exit 0**;
    914 存量 + 18 新,34 文件);
  - `full_nonslow_*`:全量非 slow(**1543 passed/16 deselected,
    exit 0**;含 legacy/export_v3 全量回归);
- `baseline/` —— 直接父 fc40605 detached worktree 同字节对照:
  - `worktree_setup.log`:worktree 创建与同字节拷贝记录(未 stub/
    未改 import/未弱化期望/未复制实现);
  - `s4b_new_file_*`:新文件 `tests/test_ppv1_s4b_export.py` ⇒
    **exit 2,18 collection 红**(ModuleNotFoundError:
    `pathway_v43.pollutant.native_export`;implementation missing);
  - `profile_updated_*`:更新的 `tests/test_ppv1_profile.py` ⇒
    **2 版本/阶段字面量红 + 21 合法正控绿**(expected behavior
    difference 类;父合法实现 profile-15);
  - `parent_r1_classification.json`:红绿分类;
  - 父存量 914 全量绿由 S4a 复审在 fc40605 独立执行证成,本批不
    重跑冒称;
- `legacy_bytes/` —— 冻结 legacy/export_v3 字节不变专项(S4a 交付
  §20.7 遗留):
  - `current/` + `parent/`:同一探针脚本(`scripts/
    legacy_export_byte_probe.py`)在当前树与父 worktree 各自构建
    两组合成 legacy run(单事件多产物 / 两事件竞争同父+deferred)
    并导出重导出;predictions.jsonl + export_metadata.json 四产物
    副本;
  - `comparison.json`:四产物 SHA256 两两相等(逐字节一致)+ 52 份
    legacy code_identity 文件聚合同 18007e6a…(父↔当前零差异);
- `g01/` —— G01 安全隔离工程回归(R7 白名单谱系 + R8/S3a/r2/r3/
  r4/S3b/r2/r3/S4a/S4b 输入,**294** 项输入;固定空
  BBD_DATA_ROOT/V3_CODE_ROOT/V43_ASSET_ROOT/DEPENDING_V3_ROOT;
  不复制 evaluation/gold/benchmark/sealed/v4):
  - `preparation.json`/`input_sha256.json`:输入清单与 SHA(实际
    HEAD + dirty 记录);
  - `execution_result.json`/`g01_junit.xml`/`g01_safe.std*`:
    **1534 passed/8 skipped/17 deselected,exit 0**
    (1516 s4a_r1 + 18 新;skip = 5 真实冻结评价 + 1 v4 对照 +
    2 phase_d 派生;deselect = 16 slow + 1 明确排除 export 用例);
- `scripts/` —— 本批执行脚本(G01 控制器 `safe_g01_s4b_r1.py`
  沿 R7→…→s4a_r1 白名单谱系,新增 3 输入;legacy 字节探针
  `legacy_export_byte_probe.py`,拒绝已存在输出目录);
- `mimo/` —— v16 送审快照(字节同 fc40605)+ v17 请求快照(本批
  送审版;主会话执行送审,实施 agent 未调用任何外部模型);
- `metadata/` —— HEAD/父基线/dirty/环境版本。

## 复现命令(全部在新 tmp 执行;本证据目录内不运行任何写库程序)

```bash
PY=/Users/cc/miniconda3/envs/depending43/bin/python
cd <repo>
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -q tests/test_ppv1_s4b_export.py -p no:cacheprovider   # 18 passed
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -q tests/ -k ppv1 -p no:cacheprovider                  # 932 passed
PYTHONDONTWRITEBYTECODE=1 $PY -B -m pytest -q tests/ -m "not slow" -p no:cacheprovider             # 1543 passed

# 父基线(先 git worktree add <fresh_tmp_wt> fc40605 --detach,再同字节拷贝两测试文件)
cd <fresh_tmp_wt> && $PY -B -m pytest -q tests/test_ppv1_s4b_export.py -p no:cacheprovider   # 18 collection 红
cd <fresh_tmp_wt> && $PY -B -m pytest -q tests/test_ppv1_profile.py -p no:cacheprovider      # 2 字面量红 + 21 绿

# legacy 字节专项(两树各跑一次,--out/--runs-root 用新 tmp;已存在即拒)
$PY -B scripts/legacy_export_byte_probe.py --src <tree>/src --out <tmpA> --runs-root <tmpA_runs>
$PY -B scripts/legacy_export_byte_probe.py --src <parent_wt>/src --out <tmpB> --runs-root <tmpB_runs>
# 对比四产物 sha256(见 legacy_bytes/comparison.json)

# G01(新 tmp;已存在输出目录即拒)
$PY -B scripts/safe_g01_s4b_r1.py --repo <repo> --out <fresh_tmp_g01> --python $PY
```

## 边界声明

- 全部数字为**合成规则级工程契约结果**:不代表 dev(B1 环境路径
  中间步骤)或 298(RHEA 通用酶学)科学性能,双向不外推;
- 网络请求 0;真实 provider 默认 off(scripted);判分零 LLM;
- 未访问:金标/题面/封存逐题 run/真实评价数据/reports/data/
  evaluation/benchmark/dependingv4/冻结 v3 资产;
- 判据 ppv1-criteria-v1 冻结正文零触碰(mimo v17 附"语义未改变"
  声明);冻结 G2/AtomTool/export_v3/production 零改动(字节专项为证);
- S4b 过审前不宣布完整 S4(交付书 §自审对齐证据)。
