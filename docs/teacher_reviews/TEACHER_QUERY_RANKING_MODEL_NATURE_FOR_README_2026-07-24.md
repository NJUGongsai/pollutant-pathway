# 排序模型性质澄清问询（README 描述口径专用）

日期：2026-07-24
定位：本文是一份**问询件（TEACHER_QUERY）**，用于向学生澄清项目所用排序模型的真实性质。
起因：项目已完整上传至 GitHub（`Water-Quality-Risk-Control-Engineering/depending`），撰写公开 README 时发现——
当前排序底座**经过我们微调，不能完全等同于上游开源 EnzymeCAGE**，需要学生给出准确、可对外公开的描述口径后，我才能把 README 里所有涉及模型的表述一次性改准。

依据：
- `ESM2_DAPT_PLAN_PATHB_20260702.md`（ESM2 领域自适应预训练方案，标注 PROPOSED / planning only）
- `configs/chenyu_paths.yaml`（部署包 `enzymecage_v1_3b_ensemble_20260714`，3B + 600M 双 backbone）
- `reports/chenyu_smoke/LAYER2_SMOKE_REPORT_2026-07-22.md`（真跑观察到 `ESM2_3B_corrected_107705` 特征缓存）

状态：README 现暂仍写作 "EnzymeCAGE v1 冻结排序底座"，**在学生回复前我不擅自改口径**，以免公开文档失真。下列问题按对 README 落笔的重要性排序，**A2 / B3 为必答项**。

---

## A. 模型定位与命名（决定 README 怎么称呼它）

**A1.** 这个排序模型的**规范名称与版本号**是什么？当前部署包名为 `enzymecage_v1_3b_ensemble_20260714`——这就是最终对外名字，还是内部代号？README 里应采用哪个名字？

**A2.（必答）** 它相对上游开源 **EnzymeCAGE 是什么关系**？
- (a) "EnzymeCAGE 架构 + 我们微调的权重"，架构未改；
- (b) 架构也做了改动；
- 对外**能否仍称 "EnzymeCAGE"**，还是必须加限定词（如 "domain-adapted / 微调版 / EnzymeCAGE-Crew"）？

## B. 到底微调了什么（决定"职责分离 / 冻结"如何表述）

**B1.** 微调**对象**是哪一层？
- 只微调 **ESM2 蛋白特征骨干**（DAPT）？
- 还是也动了 **EnzymeCAGE 下游打分头 / GVP 结构**？
- 还是端到端全量微调？

**B2.** 训练**目标函数**是什么？（MLM 表征学习 / 分类 / 对比？——这关系到我们此前 M2 崩溃教训是否已规避）

**B3.（必答）** `ESM2_DAPT_PLAN_PATHB_20260702` 当时标注 "PROPOSED / planning only"。请确认：**部署的 `v1_20260714` 到底有没有真正吃进 DAPT 后的 ESM2？** 还是仍用官方 stock ESM2-3B 特征？（真跑日志里的 `ESM2_3B_corrected_107705`，其中 "corrected" 指的就是微调后特征吗？）

## C. 微调数据与规模（README 里写一句来源）

**C1.** 微调用了**什么数据、多大规模**？（酶序列条数、来源库；是否即那 107,705 蛋白）

**C2.** 用的**基座**是 3B 还是 650M？部署的 `3b_ensemble` / `600m_ensemble` 两个 backbone **是否都经过微调**，还是只有其一？

## D. 效果与冻结边界（可选，增强 README 可信度）

**D1.** 微调后相对 stock 有无**评估门控结果**（perplexity 下降 / 特征多样性 / 下游非劣效）？能否给一句可公开的结论？

**D2.** 部署时是否**完全冻结**（推理不再更新权重）？我拟在 README 写"训练时微调、部署时冻结"，请确认此表述准确。

## E. 合规

**E1.** 该模型派生自 **EnzymeCAGE + ESM2**，对外发布 / 署名有无需注明的 **License / 引用**要求？

---

## 我的落笔计划（学生回复后执行）

拿到 A2 / B3 两条必答项（及尽量其他项）答案后，我会把 README 中现写作 "EnzymeCAGE v1 冻结排序底座" 的 **5 处**（标题段、§二架构表、§一职责分离原则、§五配置说明、§六第三方依赖）一次性改为准确口径，并按 A1/A2 结论统一模型命名。**在此之前 README 维持现状。**
