"""对日线面板做最小化清洗：只加标记，不删行。

输入：data/processed/daily_panel.parquet
输出：data/processed/daily_panel_clean.parquet

处理内容：
1. symbol 统一为 6 位字符串
2. 加 is_suspended（成交量为 0）
3. 加 is_limit_up / is_limit_down（按板块判断涨跌幅限制）
4. 加 board（主板/创业板/科创板）
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mfalpha.common.constants import DATA_DIR  # noqa: E402

PROCESSED_DIR = DATA_DIR.parent / "processed"


def classify_board(symbol: str) -> str:
    """按代码前缀判断板块。"""
    if symbol.startswith("688"):
        return "科创板"  # 20% 涨跌幅
    if symbol.startswith("3"):
        return "创业板"  # 20% 涨跌幅
    if symbol.startswith(("0", "6")):
        return "主板"  # 10% 涨跌幅
    return "其他"


def get_limit(board: str) -> float:
    """不同板块涨跌幅限制。"""
    if board in ("科创板", "创业板"):
        return 20.0
    return 10.0


def main() -> None:
    src = PROCESSED_DIR / "daily_panel.parquet"
    df = pd.read_parquet(src)
    print(f"读取面板: {df.shape}")

    # 1. symbol 统一为 6 位字符串
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)

    # 2. 板块
    df["board"] = df["symbol"].map(classify_board)

    # 3. 停牌标记
    df["is_suspended"] = df["volume"] == 0

    # 4. 涨跌停标记（用涨跌幅阈值判断，留 0.5% 余量避免精度问题）
    limit = df["board"].map(get_limit)
    df["is_limit_up"] = df["pct_chg"] >= (limit - 0.5)
    df["is_limit_down"] = df["pct_chg"] <= -(limit - 0.5)

    print(f"处理后形状: {df.shape}")
    print("\n板块分布：")
    print(df["board"].value_counts())
    print(f"\n停牌行数: {df['is_suspended'].sum()}")
    print(f"涨停行数: {df['is_limit_up'].sum()}")
    print(f"跌停行数: {df['is_limit_down'].sum()}")

    out_path = PROCESSED_DIR / "daily_panel_clean.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\n已保存到: {out_path}")


if __name__ == "__main__":
    main()
