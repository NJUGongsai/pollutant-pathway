# mimo R6 化学评审独立证据(2026-10-07)

第 6 轮 pollutant_pathway_v1 判据 v6 评审的 mimo 独立程序证据。
规则级合成夹具,公开链,无金标/题面/封存逐题数据。
对应回应:`docs/mimo_ppv1_chem_review_response_r6.md`。

## 文件

| 文件 | 说明 |
|---|---|
| `mimo_r6_probe.py` | 主探针(45 条 HEAD 记录 + 11 条基线记录):A 覆盖/补全规则反例与控制、B CX 输入登记表、C known_absent 三分、D 镜像净效应与立体控制、E 快照往返/篡改、F 披露键、G 环轴、H_3b 镜像终态序列化 |
| `mimo_r6_probe_out_head.json` | 主探针 HEAD(293bc62 之后)输出,45 条 |
| `mimo_r6_probe_out_base.json` | 主探针基线 293bc62 输出(A1/A2/A3 覆盖反例、A5-A8、H_3b;v6 专属段跳过),11 条 |
| `mimo_r6_probe2.py` | 补充探针(10 条):X1/X1b 第三结构入口(current 带 `\|r\|` 被吸收进 bound_inputs、端到端 verified/expand)、X2 strict 分支拒绝与 product_identity 吸收的不对称、X3 签名子集规则行为验证、Y1-Y6 含空格登记类过拒边界(RDKit 侧对照) |
| `mimo_r6_probe2_out.json` | 补充探针输出,10 条 |
| `mimo_r6_ppv1_head.txt` | HEAD ppv1 全量:`451 passed in 3.65s` |
| `mimo_r6_red_base.txt` | 基线 293bc62 + 3 个 r6 测试文件红绿:`44 failed, 26 passed`(与交付书 §5.1 一致) |
| `mimo_r6_red_base_full.txt` | 同一基线红绿完整输出:44 条 FAILED 全名单 + 汇总行 |
| `mimo_r6_g01.txt` | G01 全量 not slow:`1062 passed, 16 deselected in 184.20s` |

## 复跑

```bash
# 主探针(HEAD)
PROBE_SRC=<repo>/src python mimo_r6_probe.py            # -> mimo_r6_probe_out_head.json
# 主探针(基线 worktree, 293bc62)
BASELINE=1 PROBE_SRC=<wt>/src python mimo_r6_probe.py   # -> mimo_r6_probe_out_base.json
# 补充探针
PROBE_SRC=<repo>/src python mimo_r6_probe2.py           # -> mimo_r6_probe2_out.json
# 测试
python -m pytest tests/test_ppv1_*.py -q                 # 451 passed
python -m pytest tests/test_ppv1_r6_*.py -q              # 基线(3 文件拷入后)红 44/绿 26
python -m pytest tests/ -m "not slow" -q                 # 1062 passed, 16 deselected
```

python 环境:`/Users/cc/miniconda3/envs/depending43/bin/python`(含 rdkit)。
