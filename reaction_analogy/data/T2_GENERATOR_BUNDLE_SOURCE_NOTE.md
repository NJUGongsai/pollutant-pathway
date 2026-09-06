# T2 生成链资产来源与版本说明（owner 提供）

**日期**: 2026-09-06
**分支**: `feat/bbd-uspto-integrated`（GitHub: Water-Quality-Risk-Control-Engineering/depending）
**用途**: 回应 T2 所需生成链资产索取单——`predict_reactions(substrate_smiles, top_k, max_depth)` 封装所需的同版本组件。

## 1. 这些文件是什么、来自哪个运行版本

全部资产来自**本地开发仓库 `/Volumes/CC/Enzyme_Agent/depending` 的当前工作目录**，与生成 `bbd_product_pool_v3/v32` 及多步路线（P4/P5 交付物）时使用的**同一份文件**（这些基础资产在整个 v2→P5.1 迭代期间从未被修改，git 历史可证——各轮任务书只新建文件不动它们；例外见 §3 注）。

| 资产 | 角色 | 来源与许可 |
|------|------|-----------|
| `reaction_analogy/gnn_phase6_apply.py` | 引擎 A（USPTO 模板 graph-edit 应用器） | 自研代码（本项目） |
| `reaction_analogy/templates.json`（11MB） | 引擎 A 的 188,725 个 USPTO 反应模板 | 从 USPTO 专利反应数据集提取（公开学术用途；模板提取脚本 `gnn_phase6_extract.py` 同目录） |
| `reaction_v3/data/lib_envipath/templates.tsv.gz` | 引擎 B 的 enviPath EAWAG-BBD 规则库（286 条） | enviPath package 32de3cf4-e3e6-4168-956e-32fa5ddb0ce1（2026-08-15 抓取；PROVENANCE.txt 在同目录，含 api 与凭据读取说明——凭据不入库） |
| `reaction_analogy/data/corpus_v1/`（corpus_v1.jsonl + donor_index.jsonl，59MB） | 引擎 C 的检索语料（37,098 条 RHEA 完整反应 + 90,606 条 donor 索引） | RHEA 数据库公开反应数据（rhea-reaction-smiles/rhea2ec/rhea-directions 子集解析） |
| `reaction_analogy/src/ra/`（23 个模块） | 检索/语料/清洗/IO 公共库 | 自研代码（本项目） |
| `reaction_analogy/data/bbd_expand/donor_product.jsonl`（1,066 反应） | 引擎 D（lookup）的反应库 | EAWAG-BBD 公开 pathway/reaction 页面爬取整理（`bbd_crawl.py`/`bbd_build.py` 同目录） |
| `reaction_analogy/data/bbd_expand/rules_new_clean.jsonl`（49 条 SMIRKS） | 引擎 B 第二批规则（P5 引入） | EAWAG-BBD 反应 → RXNMapper 自动原子映射（24 条）+ 人工清洗，全部 roundtrip 验证 |
| `reaction_analogy/data/T2_GENERATOR_BUNDLE_MANIFEST.sha256` | 本 bundle 的 SHA256 清单 | 本次生成 |

## 2. 运行环境版本

- Python 3.11.8（conda, arm64 macOS）
- RDKit 2026.03.3
- LightGBM（训练用版本见 `data/uspto_v3loop/` 各 ranker 日志; 推理侧 3.x 皆可）
- torch 2.13.0（仅 MPNN 试水用; v3.2 生成链**不需要** torch——无 MPNN 特征）
- `pip freeze` 快照: 见 `reaction_analogy/environment.yml`（repo 内）——若与你的环境差异大，以 RDKit/LightGBM 版本对齐为优先

## 3. 已知边界（诚实声明）

1. **生成链不含 MPNN**: v3.2 排序已删除 MPNN 特征（消融证明无效，见 `reaction_analogy/reports/BBD_MPNN_TRIAL_REPORT_2026-08-31.md`）。任意新 SMILES 走三引擎生成 + LightGBM 排序即可复现 v3.2 行为，**不需要 chenyu/GPU**。
2. 排序所需 ranker 权重已在 repo: `data/bbd_v31/{uspto,envipath,retrieval}_ranker.txt`（v3.2 用的）+ `data/bbd_v5/rankers/`（P5 版）。
3. `predict_bbd_hybrid.py` 的 `--eawag-rules` 参数即指向 `rules_new_clean.jsonl`; 检索引擎参数（Morgan r=2 / 2048bit / top-20）硬编码于 `src/ra/retrieval.py`，与生成 v3 池时一致。
4. **无 93 案例外 SMILES 的 smoke 输出**——生成链此前只跑过 93 case。T2B 封装时的第一个动作就应该是一个无 gold 的新 SMILES smoke test（这正是审计要求的部分）。
5. 凭据说明: enviPath 抓取凭据**不在**任何入库文件中（runtime 读 .env）; 本 bundle 无 API key / 私钥 / .env / blind gold / 答案表。

## 4. 对应关系（索取单清单 → 本 commit）

索取单的 8 项最低需求全部包含，外加 `ra/` 库完整源码与 MANIFEST。同事可直接：

```bash
git clone -b feat/bbd-uspto-integrated https://github.com/Water-Quality-Risk-Control-Engineering/depending.git
cd depending && shasum -a 256 -c reaction_analogy/data/T2_GENERATOR_BUNDLE_MANIFEST.sha256
```
