# tests/conftest.py
"""pytest 公共引导。

src/ 与 config/ 都是位于项目根的包（源码内部使用 `from src...` / `from config...` 绝对导入）。
这里把项目根注入 sys.path，确保任意工作目录下 pytest 都能解析这两个包。
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))