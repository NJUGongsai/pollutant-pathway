# 晨羽 wrapper.predict 层 2 冒烟结果 + 预热行为分析

- 日期: 2026-07-22
- 契约: enzymecage_m3_p1_stable_runtime_context_v1
- 部署: M3I6-A (LangGraph 与冻结 wrapper 同 Python 3.12.3 环境)
- 日志: [wrapper_predict_smoke_20260722T070344Z.log](wrapper_predict_smoke_20260722T070344Z.log)

## 一、层 2 结果（首次真跑）

### 输入
- **reaction_smiles**: route_c 索引首行 CANO_RXN_SMILES (525 chars, NAD/NADP-like)
- **enzyme_pool_uids**: d4 白名单前 5 (A0A011QK89, A0A017SP50, A0A017SR40, A0A024SMV2, A0A031WDE4)
- **top_k**: 3, **return_ci**: True

### 输出
| 字段 | 值 |
|---|---|
| model_version | `v1_20260714` (与 stable_runtime_context.business_model 一致) |
| evidence_hash | `5a88fa372c7070bfac48122063d726c17496b1c61798c862f11c406c2a4b11a1` |
| ranked_enzymes count | 3 |

```
#1  uid=A0A017SR40  score=0.1924896  rank=1  ci=(0.0065, 0.6385)
#2  uid=A0A011QK89  score=0.0151064  rank=2  ci=(2.5e-6, 0.0657)
#3  uid=A0A031WDE4  score=0.0043568  rank=3  ci=(9.0e-5, 0.0169)
```

### 时耗与显存

| 阶段 | 时间 | GPU 显存 |
|---|---|---|
| STAGE-A: `from enzymecage_wrapper import ...` | **2.58s** | 0 |
| STAGE-B: `EnzymeCAGERequest(...)` | <0.01s | 0 |
| STAGE-C: `predict(req)` (冷启动) | **664.64s** (~11min) | peak **389.6 MiB** |

CI 5 seed ensemble 的 wide 分布（如 #1 rank=1 但 ci 上界 0.638）反映了 3B backbone 单次样本判断的不确定性——业务侧下游若要卡置信度阈值，可参考 ci 上下界宽度。

## 二、学生 wrapper 首次预热行为（新发现）

### 现象
STAGE-C 的 664s 里，**前 ~610s GPU 显存 = 0**，仅 CPU + 磁盘 I/O。系统证据：

```
STAT=Dl (uninterruptible + disk wait)
WCHAN=folio_wait_bit_common
RSS: 17.5 GB → 30.8 GB → 39.0 GB → 46.7 GB → 稳定
fd 16 → /usrdata/EnzymeCAGE_data/feature/protein/ESM2_3B_corrected_107705/pocket_node_feature/esm_node_feature.torch.pt
```

### 结论

学生 `enzymecage_wrapper.predict` 内部**首次调用时会一次性 mmap ~50 GB 的 ESM2-3B 蛋白特征缓存**（107,705 个蛋白的 node feature），即使 pool 只有 5 个 UID。

- 首次: ~11 min（含 mmap + 5-seed ensemble load）
- 第二次: 预计秒返回（命中 OS page cache）—— 待验证

### 影响与建议

| 场景 | 影响 |
|---|---|
| 单次交互式 dry-run | 首次卡 11 min，用户体验糟 |
| 长驻服务化 (LangGraph server 常驻 python 进程) | 服务启动 warm-up 一次，后续秒响应 |
| 频繁重启的 Serverless | 每次冷启动都要付 11 min，不适合 |

**导师侧策略**（不改学生 wrapper）:
1. LangGraph 采用**常驻 python 服务**部署（不用 CLI 每次冷启）
2. 服务启动时立即触发一次 dummy predict 做 warm-up（避免首个真实 query 卡 11 min）
3. 未来对学生的 M3-EXT 或 M4 议题可选择性提出："能否支持 lazy load / per-UID load" —— 但**当前不阻塞**

## 三、契约验证

| 硬约束 | 状态 |
|---|---|
| CUDA_VISIBLE_DEVICES=0 单卡 | ✅ 生效 |
| visible_device_contract=1 | ✅ wrapper 未报警 |
| torch=2.7.1+cu126 | ✅ import 无冲突 |
| pydantic=2.12.5 model_fields introspection | ✅ 拿到 `['reaction_smiles', 'enzyme_pool_uids', 'top_k', 'return_ci']` |
| M3I6-A 同环境 Python import | ✅ 学生 env 内直接 `from enzymecage_wrapper import predict` |
| stable_logical_path 6 类路径 | ✅ 全部命中，SHA256 与 stable_runtime_context.json 一致 |

## 四、导师侧代码同步验证

同轮次并行完成：
- 本地 → 晨羽 tar over ssh: 692 KB → `/root/projects/enzymecage_crew/`
- 依赖桥接: `/usr/local/lib/python3.12/dist-packages/_enzymecage_crew_local.pth` → `/usr/local/lib/python3.12/site-packages`
- 装到系统层的包: `langgraph 1.2.9 · langchain-core 1.5.0 · dashscope 1.26.4 · httpx 0.28.1 · tenacity 9.1.4 · python-dotenv 1.2.2`
- 学生 env manifest hash **未变**（依赖装在 `/usr/local`，不在 manifest 覆盖范围）
- 晨羽端 `ENZYMECAGE_DRY_RUN=1 python scripts/run_case_dryrun.py`: **2/2 PASS**（与本地一致）
