"""pathway_v43.vendor — 随仓第三方源码(vendored)命名空间。

本目录只放带完整来源/许可记录的第三方代码。当前内容:

- ``molecode/``:AtomFlow-AI/MoleCode 的 **molecule + prompts 子集**
  (上游 commit ``a4df3b04552b829ff816467b9620757a5dad765b``,MIT 许可,
  见 ``molecode/PROVENANCE.md`` 与 ``molecode/LICENSE``)。

与上游的差异(全部记录在 PROVENANCE.md,不隐瞒):

1. 未 vendored ``markush/``、``polymer/``、``llm.py`` 与上游顶层
   ``__init__.py``——本仓只用小分子转换;markush 需要 networkx(运行环境
   未安装),llm.py 是本仓不使用的 OpenAI 客户端。
2. 顶层 ``molecode/__init__.py`` 为本仓自写(只 re-export molecule 与
   prompts),保持 ``pathway_v43.vendor.molecode.molecule`` 导入路径可用;
   上游 __init__ 原文在 PROVENANCE.md 引用。
3. ``molecule/``、``prompts/`` 六个文件为上游逐字节拷贝,
   ``MANIFEST.sha256`` 可复核。
"""
