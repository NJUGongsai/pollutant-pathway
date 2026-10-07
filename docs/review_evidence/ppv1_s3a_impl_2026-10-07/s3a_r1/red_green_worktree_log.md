# S3a 基线红绿与 worktree 操作记录(2026-10-07)

实际 HEAD(开工=收尾): 00e509a974b40a7c9779fcd35e53b16637a13d60
分支: v4.3

## 基线 detached worktree(创建/清理)
```
git worktree add --detach /private/tmp/ppv1_s3a_baseline_wt 00e509a
cp tests/test_ppv1_s3a_search.py tests/test_ppv1_s3a_recover.py tests/s3a_worker.py tests/test_ppv1_profile.py /private/tmp/ppv1_s3a_baseline_wt/tests/  # 同字节、无 import 适配
# (运行 3 份文件;profile 单独再跑一次以分类行为红)
git worktree remove --force /private/tmp/ppv1_s3a_baseline_wt
```

worktree 移除后剩余: 1 个(仅主仓)

## 红分类
collection 阶段错误文件数: 2(test_ppv1_s3a_search.py / test_ppv1_s3a_recover.py,ModuleNotFoundError: pollutant.search)
缺实现红(未执行用例): 58(两文件全部)
行为红(断言失败): 2 ['tests/test_ppv1_profile.py::test_ppv1_identity_block_contract_versions', 'tests/test_ppv1_profile.py::test_ppv1_identity_block_default_switches']
基线绿(profile 其余): 21

## 环境与依赖
python 3.11.16
rdkit 2026.03.6
