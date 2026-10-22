"""临时对比脚本：engine 内部 holdings vs extract_holdings 产出 CSV。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]  # 项目根
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_THIS.parent))  # scripts/backtest

from engine import run_backtest  # noqa: E402

PROCESSED = _ROOT / "data" / "processed"
PRICE_PATH = PROCESSED / "daily_panel_tencent_clean.parquet"
CAL_PATH = PROCESSED / "rebalance_calendar.csv"
GROUP = "lasso_all8"
TOP_N = 50
BUFFER_N = 0
SMOOTH_N = 3
PRICE_COLS = ["symbol", "date", "open", "close", "is_limit_up", "is_suspended"]


def normalize_symbol(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.split(".").str[0]
    return s.str.zfill(6)


def main() -> None:
    cal = pd.read_csv(CAL_PATH, parse_dates=["signal_date", "trade_date"])
    prices = pd.read_parquet(PRICE_PATH, columns=PRICE_COLS)
    prices["symbol"] = normalize_symbol(prices["symbol"])
    prices["date"] = pd.to_datetime(prices["date"])

    scores = pd.read_parquet(PROCESSED / f"composite_scores_{GROUP}.parquet")
    scores.index = pd.to_datetime(scores.index)
    scores_smooth = scores.rolling(SMOOTH_N, min_periods=1).mean()

    res = run_backtest(scores_smooth, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N)
    eng_hold: dict = res["holdings"]  # trade_date(Timestamp) -> list[symbol]

    csv = pd.read_csv(
        PROCESSED / f"composite_holdings_{GROUP}.csv",
        parse_dates=["signal_date", "trade_date"],
        dtype={"symbol": str},
    )
    csv["symbol"] = csv["symbol"].str.zfill(6)
    csv_hold = {d: g["symbol"].tolist() for d, g in csv.groupby("trade_date")}

    eng_dates = set(eng_hold.keys())
    csv_dates = set(csv_hold.keys())
    print(f"engine 期数: {len(eng_dates)}")
    print(f"csv    期数: {len(csv_dates)}")
    eng_only = sorted(eng_dates - csv_dates)[:5]
    print(f"仅 engine : {eng_only}")
    print(f"仅 csv    : {sorted(csv_dates - eng_dates)[:5]}")

    common = sorted(eng_dates & csv_dates)
    print(f"共同期数: {len(common)}\n")

    n_diff = 0
    first_diff = None
    for d in common:
        a = set(eng_hold[d])
        b = set(csv_hold[d])
        if a != b:
            n_diff += 1
            if first_diff is None:
                first_diff = (d, a, b)
            if n_diff <= 5:
                print(
                    f"[差异] {d.date()}: engine {len(a)} / csv {len(b)}, "
                    f"交集 {len(a & b)}, eng-only {sorted(a - b)}, "
                    f"csv-only {sorted(b - a)}"
                )

    print(f"\n不一致期数: {n_diff} / {len(common)}")
    if first_diff is not None:
        d, a, b = first_diff
        print(f"\n首个不一致: {d}")
        print(f"  engine  ({len(a)}): {sorted(a)}")
        print(f"  csv     ({len(b)}): {sorted(b)}")
        print(f"  eng-only: {sorted(a - b)}")
        print(f"  csv-only: {sorted(b - a)}")
    else:
        print("全部一致 ✅（集合层面）")


if __name__ == "__main__":
    main()
