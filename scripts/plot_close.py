"""读取 600519 日行情 parquet 并画出收盘价走势图。

Usage:
    python scripts/plot_close.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无 GUI 环境也能出图，必须在 pyplot 之前设置
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR, FIGURES_DIR  # noqa: E402


def main() -> None:
    """读 parquet、画收盘价、保存到 docs/figures/。"""
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False  # 修复负号显示为方框

    df = pd.read_parquet(DATA_DIR / "daily_600519.parquet")

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df["close"], linewidth=1.2)
    ax.set_title("贵州茅台（600519）前复权收盘价 · 2019-2024")
    ax.set_xlabel("日期")
    ax.set_ylabel("收盘价（元）")
    ax.grid(alpha=0.3)
    fig.tight_layout()

    out = FIGURES_DIR / "close_600519.png"
    fig.savefig(out, dpi=150)
    print(f"图已保存 → {out}")


if __name__ == "__main__":
    main()
