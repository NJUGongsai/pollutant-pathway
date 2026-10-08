# ppv1 S4a r1 实施证据(2026-10-08)

- 批次:pollutant_pathway_v1 **S4a 首批**(endpoint 分账与原生
  结果底座;S4 任务书 §7 S4a 边界)。
- 实施时实际 HEAD:`0e345e83de27e7369334fe092da7a6ccbc8afd6c`
  (评审文档入库态;src/tests 与直接父 adf0287 同字节)。实施期
  工作树 dirty 状态见 `metadata/working_tree_status.txt`(用户
  未跟踪 `.zcodeignore` 保持原样,未纳入提交)。
- 直接父基线:`adf0287abef0c4803962fee0df0065d8e6f3793d`。
- 环境:conda depending43,Python 3.11.16 / RDKit 2026.03.6 /
  SQLite 3.53.4 / macOS arm64;`PYTHONDONTWRITEBYTECODE=1`、
  `-B`、`pytest -p no:cacheprovider`;收尾清缓存。
- 交付书:`docs/POLLUTANT_PATHWAY_S4A_DELIVERY_2026-10-08.md`。

## 顶层结果

| 执行 | 结果 |
| 当前树 S4a 焦点(35 用例) | 35 passed / 0 failed,exit 0 |
| 当前树 PPV1 全量(`-k ppv1`) | 914 passed / 0 skipped / 0 failed(879 存量 + 35 新) |
| 当前树全量非 slow(含 legacy/export_v3) | 1525 passed / 16 deselected / 0 failed |
| 父基线 adf0287(同字节新测试) | 35 collection 红(模块缺失)+ 2 版本字面量红 + 21 正控绿 |
| G01 安全隔离(291 输入) | 1516 passed / 8 skipped / 17 deselected,exit 0 |

## 目录

- `current/`:当前树三次运行(s4a_focus / ppv1_full /
  full_nonslow;junit + stdout + stderr);
- `baseline/`:父基线 detached worktree(同字节测试文件)运行
  日志 + `parent_r1_classification.json` + worktree_setup.log;
- `g01/`:安全隔离 G01(控制器在 `scripts/`;preparation /
  input_sha256 / execution_result / junit / stdout / stderr);
- `mimo/`:v15 送审快照(字节同父提交 adf0287 的
  `docs/mimo_ppv1_chem_review_request.md`;SHA256
  `4d5974eebfd3ae8a0f0b2f6ed454c49bf559746f853b9a127902bcfdf
  59e600a`);
- `scripts/safe_g01_s4a_r1.py`:本批 G01 控制器(R7→…→S3b-r3
  谱系 + S4a 3 新输入);
- `metadata/`:实际 HEAD / 父提交 / dirty / 环境。

## 复现命令(在**新 tmp** 复制源码后;勿在本目录跑任何写库程序)

```bash
# G01(拒绝已存在输出目录;必须新 tmp)
python scripts/safe_g01_s4a_r1.py --repo <repo> --out <fresh-tmp> \
    --python ~/miniconda3/envs/depending43/bin/python

# 当前树回归(在源码树根)
~/miniconda3/envs/depending43/bin/python -B -m pytest \
    -p no:cacheprovider -q tests/test_ppv1_s4a_endpoint.py
~/miniconda3/envs/depending43/bin/python -B -m pytest \
    -p no:cacheprovider -q tests/ -k ppv1
~/miniconda3/envs/depending43/bin/python -B -m pytest \
    -p no:cacheprovider -q tests/ -m "not slow"

# 父基线(git worktree add --detach <tmp> adf0287 后同字节复制
# tests/test_ppv1_s4a_endpoint.py 与 tests/test_ppv1_profile.py)
~/miniconda3/envs/depending43/bin/python -B -m pytest \
    -p no:cacheprovider -q tests/test_ppv1_s4a_endpoint.py
~/miniconda3/envs/depending43/bin/python -B -m pytest \
    -p no:cacheprovider -q tests/test_ppv1_profile.py
```

## G01 缺席依赖逐项披露(8 skip)

- `tests/test_batch_runner.py:52` — v3 冻结基准不可用(真实
  评价数据,按边界不复制);
- `tests/test_score_report.py:110/163/172/184` — 同上(4 项);
- `tests/test_analog_assets.py:95` — 旧 v4 对照代码根不可用
  (dependingv4 不复制);
- `tests/test_analog_v2_corpus.py:62/153` — phase_d 派生
  provenance/summary 未生成(未复制派生产物)。
17 deselect = 16 `-m "not slow"` + 1 显式排除
(`tests/test_export_v3.py::test_charge_fixture_cn_hits_raw_sb_
misses_neutralization_forbidden`,沿 R7/R8 口径)。
网络请求 0(scripted provider);真实 provider 默认 off;
判分零 LLM;无金标/题面/封存/v4 访问;全部数字为工程安全口径,
不外推 dev(B1 环境路径中间步骤)或 298(RHEA 通用酶学)科学
性能。
