# 资产与产物：不在本仓，按清单到仓外取

**本仓只放代码与文档。** 数据、模型权重、中间产物、跑批快照一律托管在仓库外
（陈宇 HPC 服务器 + Hugging Face），仓内只保留 **sha256 清单**（`assets_manifest.json`，386 条）与 **取回脚本**。

## 为什么

`main` 曾把 92.9 MB 里约 91.4 MB 的数据/产物（386 个文件）提交进 git（两个 12 MB 的 pool jsonl、
10.7 MB 的 `templates.json`、10.4 MB 的 tar.gz、多份 ranker 权重…）。后果：clone 慢、
diff 不可读、产物版本与代码版本混在一起、谁也不知道哪份 pool 是权威。

## 各类资产现在在哪

| 资产 | 原路径（已从 git 移除） | 托管处 |
|---|---|---|
| BBD pool / 预测结果 | `bbd_predictions/*.jsonl` | HF dataset（待填） + 陈宇 HPC |
| USPTO 模板库 | `reaction_analogy/templates.json` | 同上 |
| ranker 权重 / 训练集 | `data/**`、`reaction_analogy/data/**` | 同上 |
| 交付打包 | `reaction_analogy/deliverables/*` | 同上 |
| 跑批快照 | `reports/**` | 本地/陈宇 HPC（见 `reports/README.md`） |

## 怎么取回来

```bash
# 方式 A：从陈宇 HPC 服务器 rsync
export ENZYMECAGE_ASSET_REMOTE="<user>@<hpc-host>:/data/enzymecage/assets"
bash scripts/assets/fetch_assets.sh

# 方式 B：从 Hugging Face 数据集拉
export ENZYMECAGE_ASSET_HF_REPO="<org>/enzymecage-assets"
bash scripts/assets/fetch_assets.sh

# 只校验（不下载）：确认本地文件与清单一致
python3 scripts/assets/verify_assets.py
```

`assets_manifest.json` 列出每个出库文件的 **路径 + 字节数 + sha256**，取回后逐一校验。

## 待补（需要资产托管方确认）

1. 陈宇 HPC 上的资产根路径（`ENZYMECAGE_ASSET_REMOTE`）；
2. Hugging Face dataset 的 repo id（`ENZYMECAGE_ASSET_HF_REPO`）；
3. `data/hfix/README.md`、`reaction_analogy/data/*/MANIFEST.sha256` 等清单文件仍留在仓内（是文档，不是数据）。
