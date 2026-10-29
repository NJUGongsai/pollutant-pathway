# Notebook 迁移与离线 build/prepare/score 报告（2026-10-23）

> **题域标签：[298 域] = RHEA 通用酶学 / 已见题（post-hoc）。** 本报告所有分数只在该题域内成立，
> 与 dev 域双向不外推。
>
> **性质：迁移与离线链路验证，不是 P2 正式评分或放行。** 本轮不调模型、不连 DashScope、
> 不配隧道、不 push、不改 HPC 源、不删源文件；score 结果只作诊断口径。

## 0. 结论

| 项 | 结果 |
|---|---|
| 迁移 | 完成。`v43cP2` + `dependingv3` + 选定 `ppv1_hpc` 数据 + 本地 P2 文档，合计 **1,535,523,212 B（1.43 GiB，4,675+ 文件）** |
| SHA 核对 | 全部通过：`v43cP2` **675/675**、`dependingv3` **143/143**、选定 `ppv1_hpc` **4,675/4,675**、本地 P2 文档 **202/202**；失败/缺失 **0** |
| 关键指纹 | `questions` = `9f5955d4…`；迁移两臂 `batch_manifest` = `837d38f5…`；`build_identity` 指纹 = `76858eb4…`；脚本锁 = `8ba2cbec…`；批准包 = `ccdb9d14…` |
| 环境 | Python **3.11.9**，RDKit **2026.03.5**；依赖齐全；`test_p2_evidence_card_v2.py` **18 passed / 5.45s** |
| 离线 build | 298 题全部生成；build-gate **OK**；墙钟 **2953 s（49m13s）**；内存峰值 **2.82 GiB**；build-copy 身份门 **PASS** |
| 新 build 指纹 | `de19dc6e…`（与 HPC `76858eb4…` 的差异仅为绝对路径标签；298 条逐题输入与 298 份 reference_graph 字节全同） |
| Prepare | 两臂各 **2.0 s**；P2-face 八项 **298/531/242/205/78/151/134/65** 全中 |
| Score（诊断） | v1card 54 case（旧 8 + r2 46），v2card 55 case（旧 8 + r2 47）；v1/v2 两口径均已跑通 |
| 主要阻塞 | 正式 score 被 `p2_full_status.json` 缺门挡住（r2 在 v2 fatal 停点，未 run 完）；本轮只能诊断口径 |

## 1. 两端与目标路径

| 端 | 地址/路径 | 说明 |
|---|---|---|
| 源（HPC） | `aclhl3hbth@wuzh02.hpccube.com:65091`，key `/Volumes/CC/Enzyme_Agent/aclhl3hbth_wuzh02.hpccube.com_RsaKeyExpireTime_2026-11-30_10-12-36.txt` | 只读使用，未改源 |
| 目标（notebook） | `root@ssh.zzai.scnet.cn -p 11009` | 128 核 / 503 GiB / `/` 约 728 GiB 空闲 |
| 目标根 | `/root/v43_migration`（700，root） | 金标只落这里 |
| 代码 | `/root/v43_migration/v43cP2` | 903M |
| v3 代码 | `/root/v43_migration/dependingv3` | 414M |
| 数据 | `/root/v43_migration/ppv1_hpc` | 155M，含 batch/runs/operations/env |
| 文档 | `/root/v43_migration/docs` | 4.9M，含脚本锁、批准包、P2 证据 |
| 证据 | `/root/v43_migration/evidence_notebook_migration_20261023` | 46 文件，3.0M |

`/root/group_data` 未使用；金标 `reference_graphs` 只读计数/哈希，未打印内容。

## 2. 迁移清单与 SHA 核对

### 2.1 清单

| 迁移项 | 源 | 目标 | 大小 | 结果 |
|---|---|---|---|---|
| v43 代码 | `~/EnzymeAgent/v43cP2` | `/root/v43_migration/v43cP2` | 945,112,782 B | 675/675 文件 SHA OK |
| v3 代码 | `~/EnzymeAgent/dependingv3` | `/root/v43_migration/dependingv3` | 432,780,628 B | 143/143 文件 SHA OK |
| 题卷 | `~/ppv1_hpc/questions.jsonl` | `.../ppv1_hpc/questions.jsonl` | 165K | SHA `9f5955d4…` OK；298 行 |
| seed batch | `~/ppv1_hpc/batch/p2_298_20261021_seed` | `.../batch/p2_298_20261021_seed` | 29M | 全文件 OK |
| v1card batch | `.../batch/p2_298_20261021_v1card` | 同相对路径 | 30M | manifest/identity/face OK |
| v2card batch | `.../batch/p2_298_20261021_v2card` | 同相对路径 | 30M | manifest/identity/face OK |
| v1card runs | `.../runs/p2_298_20261021_v1card` | 同相对路径 | 34M | 62 run 目录，全文件 OK |
| v2card runs | `.../runs/p2_298_20261021_v2card` | 同相对路径 | 31M | 55 run 目录，全文件 OK |
| 批准记录 | `.../operations/p2_approved_record_20261021` | 同相对路径 | 130K | 全文件 OK |
| 主协调 | `.../operations/p2_coordination_p2-298-20261021` | 同相对路径 | 80K | 含 stop/waiver/日志，OK |
| r2 协调 | `.../operations/p2_coordination_p2-298-20261021_r2` | 同相对路径 | 47K | 含 stop/waiver/日志，OK |
| env | `.../env/llm_ds.env` | 同相对路径 | 158 B | SHA `cf708d3c…`；600；未打印 |
| 本地 P2 文档 | `docs/T_P2_SCRIPT_LOCK_2026-10-21.json`、`docs/P2_APPROVAL_PACKAGE_2026-10-21/`、`docs/review_evidence/p2_*` | `/root/v43_migration/docs/...` | 4.9M | 202/202 文件 SHA OK |

**失败/缺失文件：0。** 源端未删除、未改写。

### 2.2 传输

| 项 | 值 |
|---|---|
| 方式 | HPC → notebook：`rsync -a -z --partial --info=progress2 -e "ssh -i ~/.ssh/id_ed25519_nb -p 11009 -o StrictHostKeyChecking=no"` |
| 小文件测速 | `assets/analog/corpus_templates_v2.jsonl` 17,373,552 B / 1.70 s（rsync 进度 18.75 MB/s） |
| 总量/墙钟 | 1.43 GiB / 209 s（09:40:19Z → 09:43:48Z），约 7.0 MiB/s（含 4,675 个小文件开销） |
| 本地文档 | 先 rsync 到 HPC 暂存，再同链路推 notebook；未改源 |
| 权限 | notebook 根 700；`llm_ds.env` 600；`v43cP2/dependingv3/docs` 最终 chown root |

### 2.3 关键 SHA

| 项 | 期望/来源 | notebook 实测 | 判定 |
|---|---|---|---|
| `questions.jsonl` | `9f5955d418c2f3876f13cdc9bebea46a1d545d037b182fa5089f56293ff9211c` | 同值 | 一致 |
| v1/v2 臂 `batch_manifest.json` | `837d38f55cf5cbe6806f9e0a7d1f1bc56f0a9b22416d99f41a06e7ac7af45212` | 同值 | 一致 |
| v1/v2 臂 `build_identity.json` | `dc61db1bef28bac5288784344aaa4e89ce2ca2daacf667e0032a87866ebf0781` | 同值 | 一致 |
| `build_identity_fingerprint` | `76858eb41c5e5ce46c093ea1fdd69e7d5c9bff3a3a1223ec65b1574f49228ab9` | 同值 | 一致 |
| 代码聚合 | `cfd7406709b60344104c17513a0616b59380b971d5ede0d0909bc4f5c1322f07` | 同值 | 一致 |
| 脚本锁 | `8ba2cbec554b8a72c0f52a1e88d9fed5e19eb8c947e8d5a28ff70da90769920d` | 同值 | 一致 |
| 批准包 `preregistration_approval.json` | `ccdb9d14821ecb53c93df47aa6731739cd7c9b8f699d68741528bcf37975e46c` | 同值 | 一致 |
| `llm_ds.env` | `cf708d3c03c554a3cf3836a75867f90eec49fc4b32937f4304439075f8f8803a` | 同值；600；158 B | 一致 |
| P2-face 八项 | 298/531/242/205/78/151/134/65 | 两臂均同值 | 一致 |

## 3. Notebook 环境

| 项 | 值 |
|---|---|
| 主机 | `crdnotebook-2113560935535583233-aclhl3hbth-33553` |
| OS | `Linux-5.15.0-25-generic-x86_64-with-glibc2.35` |
| CPU | 128 核 Hygon C86（单 socket，单线程/核） |
| 内存 | 503.6 GiB（MemTotal 528,095,244 kB） |
| 磁盘 | `/` 1.8 TiB，约 727.7 GiB 空闲 |
| Python | 3.11.9 |
| RDKit | 2026.03.5 |
| 依赖 | numpy 1.26.4、pandas 3.0.5、langgraph ok、lightgbm 4.7.0、pytest 9.0.2、networkx 3.6.1、scipy 1.17.1、scikit-learn 1.9.0、pydantic 2.14.1 |
| `ulimit -n` | 1,048,576 |
| import | `import pathway_v43, rdkit` OK；`pathway_v43.pollutant.s5b_cli` OK |
| pytest 子集 | `tests/test_p2_evidence_card_v2.py`：**18 passed, 1 warning, 5.45 s** |
| 缺包 | 无；未联网安装 |

## 4. 离线 build

### 4.1 命令与参数

```bash
cd /root/v43_migration/v43cP2
PYTHONPATH=/root/v43_migration/v43cP2/src \
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 \
python3 -B -m pathway_v43.pollutant.s5b_cli build \
  --questions /root/v43_migration/ppv1_hpc/questions.jsonl \
  --batch-root /root/v43_migration/ppv1_hpc/batch/p2_nb_seed_20261023 \
  --batch-tag p2-298-20261021 \
  --provider-kind real --pool-mode template --recorded-source \
  --max-pool 8 --pool-threshold 0.45 \
  --v3-code-root /root/v43_migration/dependingv3 \
  --assets-root /root/v43_migration/v43cP2/assets
```

参数沿 P2 冻结面；`batch_tag` 刻意保持 `p2-298-20261021`，便于与 HPC seed 做逐字节比较。
新臂名 `p2_298_20261023_v1card` / `p2_298_20261023_v2card`（满足 `p2_298_*` 白名单），
seed 根按任务要求 `p2_nb_seed_20261023`。

### 4.2 结果

| 项 | 值 |
|---|---|
| 墙钟 | **2953 s（49m13s）**，09:47:49Z → 10:37:02Z |
| 题数 | 298/298 |
| build-gate | `BUILD-GATE-OK: n=298 sha=9f5955d4… entries_with_cosub_labels=298/298` |
| build-copy | `P2-BUILD-COPY-PASS`；两臂各 298 run_inputs / 298 reference_graphs |
| 资源 | 单核 100%；峰值 RSS 2,955,820 kB（2.82 GiB）；`ulimit -n=1048576` |
| 新 seed `batch_manifest` | `1ee69f35c85c913417c5f2d6305a6754b4ea51ff212fa149e78145470163a966` |
| 新 seed `build_identity` | `81d5534d8c920adfd5aa8135e2bcd688d04a0943de6842aba658c061cdaa838f` |
| 新 seed 指纹 | `de19dc6e76e94fa2394c1c1d704481292c004c3986decae991a19f864350696b` |
| 两新臂 manifest | 均 `1ee69f35…`（与 seed 同） |
| 两新臂指纹 | 均 `de19dc6e…` |

### 4.3 与 HPC seed 的逐字节比较（off-path 口径）

| 比较项 | 结果 |
|---|---|
| 298 条 `run_inputs` 字节 | **298/298 相同** |
| 298 份 `reference_graphs` 字节 | **298/298 相同** |
| manifest `entries` | **0 差异** |
| `build_identity.run_inputs` 逐题身份 | **0 差异** |
| `split_manifest.json` | 字节相同 |
| 路径标签差异 | `asset_identity.assets_root`、`batch_manifest.questions_source` |
| 指纹差异 | `de19dc6e…` vs HPC `76858eb4…`，仅由 `assets_root` 绝对路径派生 |

按 P2 发车书 §5.1 的 T-I off-path 先例：**只归一路径标签后比较非路径事实，不改指纹字段**。
因此本轮结论是“逐题科学输入与金标图完全一致；manifest/指纹差异属于路径标签差异”，
不是身份漂移。若后续要求与 HPC 指纹逐字相同，需要在 notebook 上使用同绝对路径重跑或
做正式路径归一，本轮未做、也没有改写指纹。

### 4.4 状态文件说明

`run_local.sh` 最初的 `write_status` 在拼 JSON 时有一个 shell 引号 bug，导致 build 成功后
状态文件写入报 `JSONDecodeError`；build/build-gate/build-copy 本身均 rc=0。该状态文件已按日志
重建为 `p2_nb_build_20261023.status.json`；脚本已修复并通过 `bash -n` 检查，后续可复用。
重建状态里明确标注了这一点。

## 5. Prepare 与 P2-face

两臂分别执行：

```bash
python3 -B scripts/hpc/p2_operations.py prepare \
  --arm v1card|v2card \
  --config /root/v43_migration/config/p2_arm_config_nb.json \
  --ws /root/v43_migration/ppv1_hpc \
  --batch-root .../batch/p2_298_20261023_<arm> \
  --code /root/v43_migration/v43cP2 \
  --source-commit 11aeeafded1b41185f24de49767933709aad49db
```

| 项 | v1card | v2card | 期望 |
|---|---|---|---|
| prepare 墙钟 | 2.0 s | 2.0 s | — |
| `files` | 298 | 298 | 298 |
| `specs_total` | 531 | 531 | 531 |
| `remap_applied` | 242 | 242 | 242 |
| `remap_add_atom_ge1` | 205 | 205 | 205 |
| `remap_add_atom_ge2` | 78 | 78 | 78 |
| `questions_remap` | 151 | 151 | 151 |
| `questions_with_add` | 134 | 134 | 134 |
| `questions_with_multi_add` | 65 | 65 | 65 |
| `p2_face_match` | true | true | true |

两臂 `arm_config.json`、批准文本快照、`budget_no_cap.json`、`p2_face_measure.json` 均已落
`/root/v43_migration/ppv1_hpc/batch/p2_298_20261023_<arm>/`。

## 6. 离线 score（诊断口径）

### 6.1 为什么是诊断口径

迁移过来的 P2 批在 r2 停点：v2card 出现 fatal `state_fact_rederivation_mismatch`，
触发两臂阶段停点；v1card 被手动 `scancel`。批根没有 `p2_full_status.json`，正式入口
`p2_operations.py score` 实测两臂均 rc=1，输出
`P2-OPERATIONS-STOP: RuntimeError: score 前缺 full 阶段门回执`。因此本轮按任务要求：
**复制批根到诊断目录，直接调用 `s5b_scoring.score_s5b_batch` 跑 v1/v2 两口径**；
不改迁移批根、不写正式 receipt、不构成 P2 放行。

### 6.2 参与评分的 runs

| 臂 | case 数 | 构成 | run 目录 | case 状态 |
|---|---|---|---|---|
| v1card | 54 | 旧 8 + r2 新 46 | 62（含 8 个 r2 在飞/未落 case 的 run 目录） | completed 54 |
| v2card | 55 | 旧 8 + r2 新 47 | 55 | completed 54，failed 1（`state_fact_rederivation_mismatch`） |

分母固定为 298；缺 case/无导出的题按 `not_evaluated_no_edges` 留在分母
（v1card 244 = 298−54；v2card 244 = 243 个无 case + 1 个 failed 无导出）。
失败题不剔除、不重试。

### 6.3 结果

| 臂 | 口径 | hit@1 | hit@3 | hit@5 | matched_strict | partial | unmatched | not_evaluated |
|---|---|---|---|---|---|---|---|---|
| v1card | v1 | 11（3.69%） | 21（7.05%） | 21（7.05%） | 21 | 4 | 29 | 244 |
| v1card | v2 | 11（3.69%） | 21（7.05%） | 21（7.05%） | 21 | 4 | 29 | 244 |
| v2card | v1 | 11（3.69%） | 20（6.71%） | 20（6.71%） | 20 | 2 | 32 | 244 |
| v2card | v2 | 11（3.69%） | 20（6.71%） | 20（6.71%） | 20 | 2 | 32 | 244 |

- v1/v2 两口径在这批已落 case 上 headline 相同；v2 豁免计数为 0
  （`edges_with_exemption=0`、`events_exempted_strict=0`），tier 计数只作披露。
- `aggregate_diagnosis`：v1card `H1=11, H3=21, H5=21, U=21, L=0`；
  v2card `H1=11, H3=20, H5=20, U=20, L=0`。`U<150` 在诊断上指向“供给/生成不足”，
  但本批只覆盖 54/55 题且中途停点，**不能当作 P2 正式结论**。
- 评分链路与金标读取已在 notebook 上跑通：298 份 reference_graph 全部装载成功；
  两口径各用时约 2.8–3.2 s；输出 `metrics.json`、`report.md`、`report_plain.md`。

## 7. 阻塞点与风险

| # | 阻塞/风险 | 影响 | 处置/建议 |
|---|---|---|---|
| 1 | 正式 score 缺 `p2_full_status.json` | 不能出正式 P2 分数/回执 | 保持诊断口径；如要正式评分，需先完成 full 批并过 full 阶段门 |
| 2 | 新 build 指纹与 HPC 不同（`de19dc6e…` vs `76858eb4…`） | 跨站身份不能逐字对齐 | 已按 off-path 先例比较非路径事实；要求逐字一致时需同绝对路径重跑或正式路径归一 |
| 3 | notebook 无出网 | 未做隧道/模型/联网安装 | 本轮按任务不配；依赖已齐，无需安装 |
| 4 | 无 Slurm/tmux | 长任务只能用 nohup | 已用 nohup + PID + 日志 + 状态文件；build 49m13s 稳定完成 |
| 5 | r2 v2 fatal | v2card 停在 55/298 | 失败题保留在 298 分母；诊断评分不改变停点事实 |
| 6 | build 状态写入 bug | 首次状态文件缺失 | 已重建状态并修复 `run_local.sh`；build 本体 rc=0 |
| 7 | HPC 暂存目录 | 新增 `~/ppv1_hpc/_nb_migration_20261023` | 只含迁移脚本/日志/manifest；未改现有源文件 |
| 8 | 文件属主 | rsync 带入 HPC uid | notebook 上已 `chown -R root:root`，根目录 700 |
| 9 | 新 build 沿用旧 `batch_tag` | 新臂 run_id 会与旧 P2 同 qid 相同 | 仅用于本轮身份/链路比对；若要在新臂跑模型，必须先换 `batch_tag`/新批名，避免撞旧 run_id |

**硬约束核对：** 未调模型；未连 DashScope；未配隧道；未改 HPC 现有源文件；未删源；
未 push；金标只在 `/root/v43_migration`（700）；`llm_ds.env` 只搬不改、600、未打印内容；
`/root/group_data` 未使用。

## 8. 复现与证据

### 8.1 notebook 上的复用入口

| 文件 | 用途 |
|---|---|
| `/root/v43_migration/scripts/run_local.sh` | `config` / `build` / `prepare` / `score-diag` / `status`；nohup 友好 |
| `/root/v43_migration/scripts/score_diag.py` | 诊断评分（复制批根、v1/v2、保存 aggregate/metrics/report） |
| `/root/v43_migration/config/p2_arm_config_nb.json` | notebook 臂配置（不含密钥；`batch_tag` 保持 P2 值） |
| `/root/v43_migration/logs/` | build/prepare/score 日志、PID、内存采样 |
| `/root/v43_migration/ppv1_hpc/operations/` | build/prepare 状态 JSON |

示例：

```bash
cd /root/v43_migration
nohup bash scripts/run_local.sh build > logs/build_20261023.log 2>&1 &
echo $! > logs/build_20261023.pid
bash scripts/run_local.sh prepare
bash scripts/run_local.sh score-diag
bash scripts/run_local.sh status
```

### 8.2 证据目录

| 位置 | SHA256SUMS | 文件数 |
|---|---|---|
| notebook `/root/v43_migration/evidence_notebook_migration_20261023/SHA256SUMS` | `623a5d604f87da2d7377c037c395c4aaa170aeded8d4abff5357159dc559a938` | 48 |
| 本地 `/Volumes/CC/Enzyme_Agent/dependingv43/docs/review_evidence/notebook_migration_2026-10-23/SHA256SUMS` | 同上（已本地逐项校验 48/48） | 48 |

证据包含：四份 SHA manifest 及核对结果、notebook 环境事实、build/prepare/score 日志与状态、
正式 score 入口被拒的实测输出、新 build 与 HPC seed 的逐字节比较、诊断评分的
summary/aggregate/metrics/report、`run_local.sh`、`score_diag.py`、`p2_arm_config_nb.json`、
`transfer_to_nb.sh`、HPC 源事实 JSON。

### 8.3 本报告路径

- 本地：`/Volumes/CC/Enzyme_Agent/dependingv43/docs/NOTEBOOK_MIGRATION_2026-10-23.md`
- notebook：`/root/v43_migration/docs/NOTEBOOK_MIGRATION_2026-10-23.md`

## 9. 下一步选项

1. **只保留诊断口径**：本轮交付即可；不把分数写进 P2 正式结论。
2. **要正式 P2 score**：先完成 full 批（或明确对 r2 stop 做新尝试），过 full 阶段门后再跑
   `p2_operations.py score`；本轮不自动做。
3. **要跨站逐字身份**：在 notebook 上用与 HPC 相同的绝对路径重跑 build，或实现正式路径归一；
   本轮按 off-path 先例只做非路径事实比对。
4. **出网/模型**：等平台工程师；本轮未配隧道、未调模型。