"""M4 最终版：v2 scores + top_n=50 + M4a×M4b 仓位，落盘全部产物。

产物：
- data/processed/m4_final_periods.csv
- data/processed/m4_final_nav.parquet
- data/processed/m4_final_holdings.csv（供日频净值重建）
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402

from scripts.backtest.engine import nav_stats, run_backtest  # noqa: E402
from scripts.backtest.run_composite_backtest import (  # noqa: E402
    BUFFER_N,
    SMOOTH_N,
    TOP_N,
    load_calendar,
    load_prices,
)

PROC = Path("data/processed")


def main() -> None:
    print("[M4 最终版] v2 scores + top_n=50 + M4a×M4b ...")
    cal = load_calendar()
    prices = load_prices()

    scores_v2 = pd.read_parquet(PROC / "composite_scores_lasso_horizon_all8_v2.parquet")
    scores_v2.index = pd.to_datetime(scores_v2.index)
    scores_smooth = scores_v2.rolling(SMOOTH_N, min_periods=1).mean()

    ps = pd.read_parquet(PROC / "m4_position_series.parquet")["pos"]
    ps.index = pd.to_datetime(ps.index)

    r = run_backtest(
        scores_smooth,
        cal,
        prices,
        top_n=TOP_N,
        buffer_n=BUFFER_N,
        position_series=ps,
    )
    periods = r["periods"]
    nav = r["nav"]
    holdings = r["holdings"]

    st = nav_stats(nav, periods_per_year=12.0)
    print("\n=== M4 最终绩效 ===")
    for k, v in st.items():
        print(f"  {k:<14} {v}")

    # 落盘 periods / nav
    periods.to_csv(PROC / "m4_final_periods.csv", index=False)
    nav.to_frame("nav").to_parquet(PROC / "m4_final_nav.parquet")
    print(f"\n  → {PROC / 'm4_final_periods.csv'}")
    print(f"  → {PROC / 'm4_final_nav.parquet'}")

    # 落盘 holdings（供日频净值重建）
    rows = []
    for td, syms in holdings.items():
        for rank, s in enumerate(syms, start=1):
            rows.append({"trade_date": td, "rank": rank, "symbol": s})
    hdf = pd.DataFrame(rows).sort_values(["trade_date", "rank"]).reset_index(drop=True)
    hdf.to_csv(PROC / "m4_final_holdings.csv", index=False)
    print(f"  → {PROC / 'm4_final_holdings.csv'}")
    n_periods = hdf["trade_date"].nunique()
    n_per_period = len(hdf) / n_periods
    print(f"    holdings: {n_periods} 期 × {n_per_period:.0f} 只")

    # 验收
    base = {
        "ann_return": 0.5369,
        "ann_vol": 0.3675,
        "sharpe": 1.4611,
        "max_drawdown": -0.2184,
        "calmar": 2.4590,
    }
    print("\n=== vs 基线 ===")
    print(f"{'指标':<16}{'基线':>10}{'M4最终':>10}{'变化':>10}")
    for k in ["ann_return", "ann_vol", "sharpe", "max_drawdown", "calmar"]:
        b = base[k]
        print(f"{k:<16}{b:>10.4f}{st[k]:>10.4f}{st[k] - b:>+10.4f}")

    print("\n=== 验收 ===")
    print(
        f"  Sharpe >= 1.680: "
        f"{'PASS' if st['sharpe'] >= 1.680 else 'FAIL'} "
        f"({st['sharpe']:.4f})"
    )
    print(
        f"  |MDD| <= 25%:    "
        f"{'PASS' if abs(st['max_drawdown']) <= 0.25 else 'FAIL'} "
        f"({st['max_drawdown']:.4f})"
    )


if __name__ == "__main__":
    main()
