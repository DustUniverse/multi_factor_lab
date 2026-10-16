"""M1-B: 构建月度调仓日历。

从交易日列表出发，取每个自然月最后一个交易日作为信号日（signal_date），
其下一个交易日作为成交日（trade_date）。

设计原则：
    T 日盘后生成信号（用 T 日可见因子值），T+1 开盘成交
    → 严格无未来函数

落盘：
    data/processed/rebalance_calendar.csv

用法（项目根目录、激活 .venv 后）：
    python scripts/backtest/build_rebalance_calendar.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

PRICE_PATH = _ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"
OUT_PATH = _ROOT / "data" / "processed" / "rebalance_calendar.csv"


def load_trading_days() -> pd.DatetimeIndex:
    """从价格面板提取所有交易日（去重、排序）。"""
    df = pd.read_parquet(PRICE_PATH, columns=["date"])
    days = pd.to_datetime(df["date"].unique())
    days = pd.DatetimeIndex(sorted(days))
    return days


def build_calendar(days: pd.DatetimeIndex) -> pd.DataFrame:
    """按自然月分组，取每月最后一个交易日为 signal_date。"""
    s = pd.Series(days, index=days)
    # groupby 年月，取每月最后一天
    monthly_last = s.groupby([s.index.year, s.index.month]).max()
    signal_dates = pd.DatetimeIndex(sorted(monthly_last.values))

    # 对每个 signal_date，找到它在 days 里的位置，取下一个交易日
    day_to_idx = {d: i for i, d in enumerate(days)}
    rows = []
    for sig in signal_dates:
        idx = day_to_idx[sig]
        if idx + 1 < len(days):
            trade = days[idx + 1]
            rows.append({"signal_date": sig, "trade_date": trade})

    cal = pd.DataFrame(rows)
    return cal


def main() -> None:
    print("[M1-B] 构建月度调仓日历 ...")
    days = load_trading_days()
    print(f"  交易日总数: {len(days)}")
    print(f"  区间:       {days[0].date()} ~ {days[-1].date()}")

    cal = build_calendar(days)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cal.to_csv(OUT_PATH, index=False)

    print(f"  保存到:   {OUT_PATH}")
    print(f"  调仓点数: {len(cal)}")
    print(
        f"  首行:     signal={cal.iloc[0]['signal_date'].date()}  "
        f"trade={cal.iloc[0]['trade_date'].date()}"
    )
    print(
        f"  末行:     signal={cal.iloc[-1]['signal_date'].date()}  "
        f"trade={cal.iloc[-1]['trade_date'].date()}"
    )
    print()
    print("  前 5 行:")
    print(cal.head(5).to_string(index=False))
    print()
    print("  后 5 行:")
    print(cal.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
