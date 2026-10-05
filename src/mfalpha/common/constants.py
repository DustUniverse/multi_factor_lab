# src/mfalpha/common/constants.py
"""项目全局常量。

集中管理路径与固定配置，避免各模块硬编码。
"""

from pathlib import Path

# 说明：本文件位于 src/mfalpha/common/，
# 向上 3 层即项目根 multi_factor_lab/。
# 用 __file__ 定位，保证在任何工作目录下运行都指向同一处。
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

DATA_DIR: Path = PROJECT_ROOT / "data" / "raw"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
FIGURES_DIR: Path = DOCS_DIR / "figures"
