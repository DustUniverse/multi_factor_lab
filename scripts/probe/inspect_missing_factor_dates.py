"""诊断 ep_ttm / bp / turnover 三个因子在哪些交易日整体缺失。

只读脚本，不修改任何数据。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FACTOR_PANEL_PATH = PROCESSED_DIR / "factor_panel.parquet"
PRICE_PANEL_PATH = PROCESSED_DIR / "daily_panel_tencent_clean.parquet"

# 让脚本能 import alphalens_io
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "validation"))
from alphalens_io import load_prices  # noqa: E402

TARGET_FACTORS = ["ep_ttm", "bp", "turnover"]


def main() -> None:
    print("读取 prices ...")
    prices = load_prices()
    price_dates = prices.index
    print(f"prices 交易日数：{len(price_dates)}")
    print(f"范围：{price_dates.min().date()} ~ {price_dates.max().date()}")
    print()

    print("读取 factor_panel（只读需要列）...")
    df = pd.read_parquet(
        FACTOR_PANEL_PATH,
        columns=["symbol", "date"] + TARGET_FACTORS,
    )
    df["date"] = pd.to_datetime(df["date"])
    print()

    price_date_set = set(price_dates)

    for factor in TARGET_FACTORS:
        print("=" * 78)
        print(f"因子：{factor}")
        sub = df[["date", factor]].dropna(subset=[factor])
        # 每个交易日有多少非空值
        counts = sub.groupby("date").size()
        factor_dates = counts.index

        missing_from_prices = price_date_set - set(factor_dates)
        extra_not_in_prices = set(factor_dates) - price_date_set

        print(f"  非空数据覆盖的交易日数：{len(factor_dates)}")
        print(f"  prices 里有、该因子完全没数据的交易日：{len(missing_from_prices)} 天")
        if missing_from_prices:
            sample = sorted(missing_from_prices)[:10]
            print(f"    前 10 天：{[d.date() for d in sample]}")

        if extra_not_in_prices:
            sample = sorted(extra_not_in_prices)[:5]
            print(
                f"  !! 因子有、但 prices 里没有的交易日（不应出现）：{len(extra_not_in_prices)} 天"
            )
            print(f"    前 5 天：{[d.date() for d in sample]}")

        # 每日覆盖股票数的分布
        print(
            f"  每日非空股票数：min={counts.min()},"
            f"median={int(counts.median())}, max={counts.max()}"
        )
        # 找覆盖率极低的日子
        low_cov = counts[counts < 100]
        print(f"  非空股票数 < 100 的交易日数：{len(low_cov)}")
        if len(low_cov) > 0:
            print("    前 10 天：")
            print(low_cov.head(10).to_string())
        print()


if __name__ == "__main__":
    main()
