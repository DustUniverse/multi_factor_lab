"""M4a+M4b 合并回测：最终 position_series 完整绩效。"""

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
    load_scores,
)

PROC = Path("data/processed")
TAG = "lasso_horizon_all8"
BASE = {
    "ann_return": 0.5369,
    "ann_vol": 0.3675,
    "sharpe": 1.4611,
    "max_drawdown": -0.2184,
    "calmar": 2.4590,
}


def main() -> None:
    print("[M4] M4a+M4b 合并回测 ...")
    cal = load_calendar()
    scores = load_scores(TAG).rolling(SMOOTH_N, min_periods=1).mean()
    prices = load_prices()
    ps = pd.read_parquet(PROC / "m4_position_series.parquet")["pos"]
    ps.index = pd.to_datetime(ps.index)

    r = run_backtest(
        scores, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N, position_series=ps
    )
    st = nav_stats(r["nav"], periods_per_year=12.0)

    print("\n=== M4a+M4b 最终绩效 ===")
    for k, v in st.items():
        print(f"  {k:<14} {v}")

    r["periods"].to_csv(PROC / "m4_bt_periods.csv", index=False)
    r["nav"].to_frame("nav").to_parquet(PROC / "m4_bt_nav.parquet")

    print("\n=== vs 基线 ===")
    print(f"{'指标':<16}{'基线':>10}{'M4a':>10}{'M4b':>10}{'合成':>10}")
    m4a_val = {
        "ann_return": 0.4992,
        "ann_vol": 0.3595,
        "sharpe": 1.3885,
        "max_drawdown": -0.2418,
        "calmar": 2.0643,
    }
    m4b_val = {
        "ann_return": 0.4296,
        "ann_vol": 0.2911,
        "sharpe": 1.4755,
        "max_drawdown": -0.1766,
        "calmar": 2.4320,
    }
    for k in ["ann_return", "ann_vol", "sharpe", "max_drawdown", "calmar"]:
        print(
            f"{k:<16}{BASE[k]:>10.4f}{m4a_val[k]:>10.4f}"
            f"{m4b_val[k]:>10.4f}{st[k]:>10.4f}"
        )

    print("\n=== 验收（合并） ===")
    print(
        f"  Sharpe >= 1.680: "
        f"{'PASS' if st['sharpe'] >= 1.680 else 'FAIL'} ({st['sharpe']:.3f})"
    )
    print(
        f"  |MDD| <= 25%:   "
        f"{'PASS' if abs(st['max_drawdown']) <= 0.25 else 'FAIL'} "
        f"({st['max_drawdown']:.4f})"
    )


if __name__ == "__main__":
    main()
