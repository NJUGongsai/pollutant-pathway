# TEACHER_REPLY：T6-R3 bridge source_tool 空串/纯空白补充裁定（必填 vs 非空）

- 回复对象：陈浩然对 `MultistepRouteInput.source_tool` / `MultistepStep.source_tool` 两个字段「只需必填还是必须非空」的审计抉择请求（2026-09-14）
- 裁定日期：2026-09-14
- 裁定结论：**必须非空**，与 `CandidateReaction.source_tool` 同一合同。已补修并随本 commit 下发。

---

## 一、裁定结论

我判定：**必须非空**，不是「只需必填」。

你方已复核通过的三项 smoke（`CandidateReaction` 来源非空、Route C MISS 进 BioTransformer、bridge 空 UID 过滤）维持不变。本轮只补一件事：把「来源字段强制非空」的裁定语义，从单步反应层补齐到多步桥接层的两个 `source_tool`。

依据是 T6-R3 裁定 3 的完整语义：`source_tag`/`source_tool` 强制非空，指的是「拒绝缺参 + 拒绝空串 + 拒绝纯空白」，而不是「只要传了就算」。bridge 的两个 `source_tool` 与 `CandidateReaction.source_tool` 同字段名、同溯源职责（证据链上这条数据由哪个工具产出），必须执行同一合同。若这里只要求「必填」，等于给多步路径开一个「来源为空也能进证据链」的口子，审计时依然会暴露来源实质缺失的脏数据。

---

## 二、修复内容

- 修改文件：`src/schemas/bridge.py`
- `MultistepRouteInput.source_tool`：新增非空校验，`""` / 纯空白构造即抛校验异常。
- `MultistepStep.source_tool`：同样新增非空校验。
- 合法取值不变：`enviPath` / `BioTransformer` / `ECLIPSE` / `unknown` 等显式非空串照常接受。

---

## 三、回归测试与下发

- 回归：`tests/test_t6r3_contract_decisions.py` 新增 `TestGap4BridgeSourceToolNonBlank` 共 5 项用例（route 空串/纯空白拒绝、route 合法 `unknown` 接受、step 空串/纯空白拒绝），全套 **33 passed**（含上一轮 28 项）。
- 下发：随本 commit 推送至权威库 `depending` 的 `main` 分支。
- 你方职责：在本修复 commit 上做秒级复核（两个字段传空串/纯空白应报错），复核通过即可进入完整 T6 准备。

---

## 四、红线约束（沿用）

- 不把空串/纯空白当来源。
- 不把 MISS 当失败。
- 不改我未授权拓扑。