# R7 条件/新增回归独立复核

- 实际 HEAD：858dd94c7c6c8fc387940242403d67b6b36b5313；基线：6d9020130a481866ce2f3b79933907a33d8cfc9e。
- 只读主仓：新建 tmp detached worktree 和 tmp git archive 源码副本；完成 git worktree remove --force，主仓 worktree 清单只剩原主仓。
- 未访问金标、题面、封存逐题run；无外部模型；无 source/tests/docs/AGENTS 修改。

## 结论

R6-03 可以关闭，未发现本线新 P1。派生入口在读取父字段前调用与恢复/审核同源的 validate_context_object；两侧签名/行集合分别单删均在三个公共入口拒绝；合法 unknown/conflict/satisfied 控制保持。不要求认证事实真实性或防止完全重造自洽历史。

独立基线57项为33 failed/24 passed；同57项R7隔离执行57 passed。自写16个条件顶层case逐个独立运行，全达预期；源码包含vendor，保留pyproject；-B、PYTHONDONTWRITEBYTECODE=1与pytest无cache。

## 实际行为

| 输入 | derive | from_dict | audit/admission |
|---|---|---|---|
| 合法旧pH unknown | 正常 | 正常且同ID | unknown/retain |
| 保留真实签名但删行/coverage/has_gate | signature_row_correspondence拒绝 | 同 | 同 |
| 留行但删签名 | signature_row_correspondence拒绝 | 同 | 同 |
| 事实就地改，原ID保留 | content_identity_mismatch拒绝 | 同 | 同 |
| 凭空签名 | 未单独执行 | signature_not_in_requirements拒绝 | 未单独执行 |
| 合法冲突往返 | 新回归公共链完整执行 | 正常 | violated/defer |
| 满足历史+正常转换+孙上下文 | 正常 | 正常 | verified/expand |
| 完全重造双方均空的自洽历史 | 正常 | 正常 | orphan_binding unknown/retain |

source: path_context.py:1040–1049,1487–1503,2320–2327。

## 回归与交付表述更正（P2；不因此重开R6-03）

1. tests/test_ppv1_r7_conditions.py:340 最末旗标控制 _audit(*_oxygen_hyp(), child2) 参数顺序错误：_oxygen_hyp返回hyp,states,evidence，而_audit需hyp,states,context,evidence，原控制因把evidence当context报 context_object_invalid_type，不是旗标不一致。自写探针正确参数顺序单独确认 gate_flag_mismatch；原控制只碰到一次预期类型的异常，不能说它有效验证旗标。其他旧控制及独立证据已有，不增加阶段门。
2. test_r6_03_from_dict_rejects_signature_without_rows docstring声称旧ID的篡改载荷在基线接受/R6错误；独立基线该项已绿，旧ID恢复本来拒绝。原R6事实为父未验的derive先生成新子ID，再restore接受，不能混成原ID恢复接受。
3. 原始日志有6项直接字段KeyError/新表缺失红，第7披露红是 test_r6_01_license_binds_strict_identity_not_class_name：基线已unknown/partial，新红为没有新增completion_license_unregistered_identity violation kind（AssertionError），不是KeyError。因此粗分26行为红+7披露/表结构红可确认，窄说“7项均KeyError/新表缺失”须更正。
4. license-binds测试用C1CC1数值本来不配平，不能单靠它证明“数值配平而非氢身份仍partial”；三C2H4O独立反例实际检验此承诺，测试名不能扩大其自身证明。
5. test_r6_01_hydrogen_equivalent_controls_stay_full 是复合三控制：基线跑完氧化full/expand与还原center/full，接着因新字段KeyError停止，还原admission及原子氢内部控制未执行。24基线通过顶层项也不等于全部复合内部控制完成。R7该项完整绿；原子氢/还原admission应由旧探针或独立公共链记录确认。

## mimo条件范围

- 判据四建议“已绑定要求不可变”是已有对象边界的文字补充，不形成新P1；正常转换与孙上下文已独立执行。
- C4“两根据”逐字句在request与src没有，grep属实；现实现有无未覆盖/full及注册精确补全两个分支。不凭缺规范措辞升级为本线P1，最终由主审结合机器scope披露判断。
- C6拒绝/早退建议属于异常路径口径，不能凭猜测调用方吞异常当新P1。公开调用守卫抛异常无返回对象；执行failed早退所有轴None，属已登记安全边界。
- C1/C3交化学线独立执行，本线不以mimo读码不可达作为事实背书。

## 证据

scratch目录 /private/tmp/ppv1_r7_conditions_858dd94_ZZFwTe。可纳入永久包：conditions_public_probe.py/.jsonl/.stderr、baseline_pytest_full.log、current_57_pytest_full.log、baseline_red_classification.json、metadata.json、original_tests、baseline_tests、baseline_import_adapter.patch、worktree_add.log、worktree_remove.log。current_isolated只作执行副本，不必永久打包整个源码；metadata已逐文件记录两个HEAD的src+pyproject SHA-256。
