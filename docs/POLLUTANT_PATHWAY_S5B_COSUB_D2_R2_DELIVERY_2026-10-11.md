# PPV1 S5b D2-R2 交付书（同源权威消费，2026-10-11）

状态：`implementation_ready_for_review`（主会话代为收尾提交——实施子代理
在完成全部实现与验证后进程死亡，工作树遗留 +633/−58 未提交改动，由主会
话核对后接管收尾；实现与测试为该代理原作，验证数字由主会话独立复跑确认）。

## 修法（Codex D2-R1 复审 §4.3/§8 为权威）

S5B-D2-01 产物侧剩余收口：NC-10 的记录产物权威改为**同源权威消费**——
记录产物在 contract 与 corpus 双来源声明时，首次消费先按 strict 身份键
**多重集**核同源一致性（保留重复组分意义），分歧 ⇒ 结构化拒（kind=
cosubstrate_record_products_conflict 族，坏声明保全），不得选择被收缩
的一侧作为新全量；无第二来源的合法默认路径按既有契约处理。

- 实现位置：src/pathway_v43/pollutant/production.py（NC-10 轴 2 同源
  权威核验）+ recorded_source.py（装配侧同源一致性）+ 三个测试文件
  （tests/test_ppv1_s5b_cosub_d2.py 新增 contract_products_shrink 反例
  族回归：test_d2_nc10_r2_contract_products_shrink_rejected 等 7 新测
  试；v4_wv41/v4b 版本字面量同步）
- 反例翻拒：三反例（contract_products_shrink_keep_copyrefs /
  shrink_keep_corpus / 公开 novel 同根）经新增回归测试钉死——修前
  行为在父基线红绿中记录（父上 1 缺产物 event），修后结构化拒零坏
  event（测试断言）

## 验证（主会话独立复跑 + 代理遗留证据）

- 定向三文件：80 passed（含新反例回归）
- 全量 not slow：**2038 passed / 0 failed / 16 deselected**（主会话复跑
  与代理最终 rerun 双一致；代理中间日志有 1 次
  test_workflow_recovery::test_resume_budget_respects_run_identity_limit
  失败——已知 flake，隔离重跑通过，如实披露）
- G01 隔离：exit 0（/private/tmp/g01_s5b_cosub_d2_r2，输入 SHA 清单在
  目录内；证据为易失目录，复审可复跑）
- 父基线红绿证据：/private/tmp/d2r2_parent_red_green（父 worktree 目录，
  新反例在父上红；易失）

## 版本登记

corpus-retrieval-4 → **5**（记录产物同源权威消费语义）；其余
（recorded-source-3/pool-policy-5/compiler-3）不变。

## 金标边界自查

零模型零花费零真实批不 push；金标/题面/封存逐题 run 零读取；三冻结
SHA/scorer/evaluation/AtomTool/金额链零触碰。

## 待复审

S5B-D2-01 产物侧剩余是否按 D2-R1 报告 §4.3 收口（同源权威消费+三反例
翻拒+正控族保持）；交付书为代理死后主会话代笔，代理的 fresh-tmp 公开链
复现证据未及产出（反例覆盖以仓内回归测试为准，复审如需公开链复现可
按 D2-R1 证据脚本复跑）；r34 互证沿 D2-R1 报告 §5 口径。
