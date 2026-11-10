"""pathway_v43 — v4.3 反应资产接线包。

职责边界(见 TASK_ASSET_WIRING.md §2):
- 本仓 assets/ 清单校验(fail-closed,无旧仓回退);
- v3 冻结引擎只读适配器(资产根导入前注入);
- v4 两份类比最终索引的装载与校验;
- checkenv / probe CLI。

LangGraph 工作流后续直接调用 adapters 的稳定接口:
  from pathway_v43.config import resolve_config
  from pathway_v43.adapters.v3_engine import get_engine
  from pathway_v43.adapters.analog_index import AnalogAssets
"""

from pathway_v43.config import V43Config, resolve_config

__all__ = ["V43Config", "resolve_config"]
__version__ = "0.1.0"
