"""M4a: 目标波动仓位回测（lasso_horizon_all8），对比基线。"""

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
POS_FILE = PROC / "m4a_position_series.parquet"
TAG = "lasso_horizon_all8"

# 阶段三基线（verify_baseline 已验证，直接引用）
BASE = {
    "ann_return": 0.5369,
    "ann_vol": 0.3675,
    "sharpe": 1.4611,
    "max_drawdown": -0.2184,
    "calmar": 2.4590,
}


def main() -> None:
    print("[M4a] 目标波动仓位回测 ...")
    cal = load_calendar()
    scores = load_scores(TAG)
    scores_smooth = scores.rolling(SMOOTH_N, min_periods=1).mean()
    prices = load_prices()
    ps = pd.read_parquet(POS_FILE)["pos"]
    ps.index = pd.to_datetime(ps.index)
    print(f"  calendar {len(cal)} 期, scores {scores.shape}, prices {prices.shape}")
    print(f"  position_series {len(ps)} 期, mean {ps.mean():.4f}, min {ps.min():.4f}")

    res = run_backtest(
        scores_smooth,
        cal,
        prices,
        top_n=TOP_N,
        buffer_n=BUFFER_N,
        position_series=ps,
    )
    periods = res["periods"]
    nav = res["nav"]
    st = nav_stats(nav, periods_per_year=12.0)

    print("\n=== M4a 绩效 ===")
    for k, v in st.items():
        print(f"  {k:<14} {v}")

    periods.to_csv(PROC / "m4a_bt_periods.csv", index=False)
    nav.to_frame("nav").to_parquet(PROC / "m4a_bt_nav.parquet")

    print("\n=== M4a vs 基线 ===")
    print(f"{'指标':<16}{'基线':>10}{'M4a':>10}{'变化':>12}")
    for k in ["ann_return", "ann_vol", "sharpe", "max_drawdown", "calmar"]:
        b, m = BASE[k], st[k]
        print(f"{k:<16}{b:>10.4f}{m:>10.4f}{m - b:>+12.4f}")

    print("\n=== 验收 ===")
    print(f"  calendar {len(cal)} 期, scores {scores.shape}, " f"prices {prices.shape}")
    print(
        f"  position_series {len(ps)} 期, " f"mean {ps.mean():.4f}, min {ps.min():.4f}"
    )
    print("\n=== 2024 年逐期 pos / gross / net ===")
    p24 = periods[periods["trade_date"] >= "2024-01-01"][
        ["trade_date", "pos", "gross_ret", "cost", "net_ret"]
    ]
    print(p24.to_string(index=False))


if __name__ == "__main__":
    main()
