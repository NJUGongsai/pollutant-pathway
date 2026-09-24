# v4.3 反应资产

这些文件于 2026-09-24 从本机的 dependingv3 和 dependingv4 副本逐字节复制。`assets/MANIFEST.sha256` 是本仓校验清单；`assets/MANIFEST.json` 逐项记录相对路径、字节数、SHA256、绝对来源路径、来源提交和来源说明。原始文件内容未修改。共 21 个文件、149,475,454 字节，其中运行数据 15 个、149,460,654 字节。

| 目录 | 内容 | 来源版本 |
| --- | --- | --- |
| `assets/v3_reactions/` | v3 冻结环境检索语料、EAWAG 与 enviPath 规则及反应库、USPTO 模板、ranker 和 calibrator；另存原始 README 与清单 | dependingv3 `eb24c1e50a94966c77fd108152d4ebff2d65032e`，v3.5 资产包（2026-09-18） |
| `assets/analog/` | v4 最终 USPTO relaxed index 与 corpus templates index；另存原始 manifest 和 USPTO 构建报告 | dependingv4 `3d46e3e2f3783094323f5dda7746ecba84ae870c`，`feat/v42-fix` |

v3 运行文件在复制前通过原始 `MANIFEST.sha256` 或 `MANIFEST.extensions.sha256` 校验；v4 两份最终索引在复制前通过原始 `derived/analog/MANIFEST.sha256` 校验。复制后又对每个文件比较了源与目标 SHA256。校验结果：21/21 一致。

在仓库根目录复核本仓全部文件：

```sh
cd assets
shasum -a 256 -c MANIFEST.sha256
```

`MANIFEST.json` 还可用于核对字节数和原始来源。保存的 v3/v4 **原始** manifest 含此次未迁入的评测语料或构建过程文件，不能拿它们作为本仓完整性清单；应使用 `assets/MANIFEST.sha256`。

## 范围与后续桥接

`corpus_env_eval/` 是隔离评测语料，没有迁入主检索资产。v4 的 checkpoints、probe 结果、日志和其他构建中间件没有迁入。密钥、`.env`、模型权重、考试或评测答案、运行产物均未迁入。

v4.3 的 ReactionFinder 可从 `assets/v3_reactions/` 和 `assets/analog/` 读取这些文件。v3 冻结引擎的只读适配器以后应把 `assets/v3_reactions/` 作为资产根传入，并先核验本仓 manifest；候选与排序对拍完成前，不应假定路径替换已经通过兼容性验证。两份 v4 类比最终索引都在 `assets/analog/`，可供 analog 检索适配器接线；本次只迁移数据，没有修改任何引擎代码或执行兼容性对拍。

来源说明来自本地 v3 README、资产 README、代码注释和 v4 构建报告。EAWAG/enviPath/USPTO 衍生内容及混合检索语料没有随本地副本附带可独立确认的再分发许可文本；此处是项目工作区内部迁移，公开分发前需另行核实各上游条款。
