"""M4c: top_n 细化扫描（20-40），找 Sharpe 峰值。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402

from scripts.backtest.engine import nav_stats, run_backtest  # noqa: E402
from scripts.backtest.run_composite_backtest import (  # noqa: E402
    BUFFER_N,
    SMOOTH_N,
    load_calendar,
    load_prices,
)

PROC = Path("data/processed")


def main() -> None:
    print("[M4c] top_n 细化扫描 ...")
    cal = load_calendar()
    prices = load_prices()

    scores_v2 = pd.read_parquet(PROC / "composite_scores_lasso_horizon_all8_v2.parquet")
    scores_v2.index = pd.to_datetime(scores_v2.index)
    scores_smooth = scores_v2.rolling(SMOOTH_N, min_periods=1).mean()

    ps = pd.read_parquet(PROC / "m4_position_series.parquet")["pos"]
    ps.index = pd.to_datetime(ps.index)

    print(
        f"\n{'top_n':>8}{'sharpe':>10}{'ann_ret':>10}{'ann_vol':>10}"
        f"{'MDD':>10}{'calmar':>10}{'turnover':>10}{'cost':>8}"
    )
    best = (None, -999, None)
    for top_n in [20, 25, 30, 35, 40]:
        r = run_backtest(
            scores_smooth,
            cal,
            prices,
            top_n=top_n,
            buffer_n=BUFFER_N,
            position_series=ps,
        )
        st = nav_stats(r["nav"], periods_per_year=12.0)
        p = r["periods"]
        print(
            f"{top_n:>8d}{st['sharpe']:>10.4f}{st['ann_return']:>10.4f}"
            f"{st['ann_vol']:>10.4f}{st['max_drawdown']:>10.4f}"
            f"{st['calmar']:>10.4f}"
            f"{p['turnover'].mean()*12*100:>9.1f}%"
            f"{p['cost'].mean()*12*100:>7.2f}%"
        )
        if st["sharpe"] > best[1]:
            best = (top_n, st["sharpe"], st)

    print(
        f"\n最优: top_n={best[0]}, Sharpe={best[1]:.4f}, "
        f"MDD={best[2]['max_drawdown']:.4f}, ann_ret={best[2]['ann_return']:.4f}"
    )
    ok = "PASS" if best[1] >= 1.680 else "FAIL"
    print(f"验收: Sharpe>=1.680 {ok}")


if __name__ == "__main__":
    main()
