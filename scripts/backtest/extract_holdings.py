"""M7-a: 提取 ic_no_vol 策略每期持仓明细。

在 run_composite_backtest.py 里，持仓是用 engine.run_backtest 内部决定的，
没有落盘。本脚本重放同样的逻辑（含信号平滑 3 期 + 涨跌停过滤），
生成每期持仓的明细表，供 Backtrader 复现使用。

输出：
    data/processed/composite_holdings_ic_no_vol.csv
        trade_date, symbol, rank

用法（项目根目录、激活 .venv 后）：
    python scripts/backtest/extract_holdings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

PROCESSED = _ROOT / "data" / "processed"
SCORE_PATH = PROCESSED / "composite_scores_ic_no_vol.parquet"
PRICE_PATH = PROCESSED / "daily_panel_tencent_clean.parquet"
CAL_PATH = PROCESSED / "rebalance_calendar.csv"
OUT_PATH = PROCESSED / "composite_holdings_ic_no_vol.csv"

TOP_N = 50
SMOOTH_N = 3
PRICE_COLS = ["symbol", "date", "open", "is_limit_up", "is_suspended"]


def normalize_symbol(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.split(".").str[0]
    return s.str.zfill(6)


def main() -> None:
    print("[M7-a] 提取 ic_no_vol 持仓 ...")
    scores = pd.read_parquet(SCORE_PATH)
    scores.index = pd.to_datetime(scores.index)
    scores = scores.sort_index()
    print(f"  分数面板: {scores.shape}")

    # 信号平滑：3 期滚动均值
    scores_smooth = scores.rolling(SMOOTH_N, min_periods=1).mean()

    prices = pd.read_parquet(PRICE_PATH, columns=PRICE_COLS)
    prices["symbol"] = normalize_symbol(prices["symbol"])
    prices["date"] = pd.to_datetime(prices["date"])
    prices_by_date = {d: g.set_index("symbol") for d, g in prices.groupby("date")}

    cal = pd.read_csv(CAL_PATH, parse_dates=["signal_date", "trade_date"])
    print(f"  调仓点数: {len(cal)}")

    rows = []
    n_skipped = 0
    for _, r in cal.iterrows():
        sig = r["signal_date"]
        trade = r["trade_date"]
        if sig not in scores_smooth.index:
            n_skipped += 1
            continue
        s = scores_smooth.loc[sig].dropna()
        if len(s) < TOP_N:
            n_skipped += 1
            continue

        trade_prices = prices_by_date.get(trade)
        if trade_prices is None:
            n_skipped += 1
            continue

        # 候选池：top_n * 2
        candidates = s.nlargest(TOP_N * 2).index.tolist()
        valid = []
        for sym in candidates:
            if sym not in trade_prices.index:
                continue
            p = trade_prices.loc[sym]
            if p.get("is_limit_up", False) or p.get("is_suspended", False):
                continue
            valid.append(sym)
            if len(valid) == TOP_N:
                break

        if len(valid) < TOP_N // 2:
            n_skipped += 1
            continue

        for rank, sym in enumerate(valid):
            rows.append(
                {
                    "signal_date": sig,
                    "trade_date": trade,
                    "symbol": sym,
                    "rank": rank,
                }
            )

    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)
    print(f"  持仓明细行数: {len(out)}")
    print(f"  有效调仓期:   {out['trade_date'].nunique()}（跳过 {n_skipped}）")
    print(f"  涉及的股票数: {out['symbol'].nunique()}")
    print(f"  每期持仓数:   {out.groupby('trade_date').size().describe().to_dict()}")
    print(f"  保存到: {OUT_PATH}")


if __name__ == "__main__":
    main()
