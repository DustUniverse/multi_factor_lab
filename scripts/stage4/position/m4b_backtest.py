"""M4b: 回撤止损回测（M4b only + M4a×M4b 合成），对比基线。"""

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


def run_one(label: str, pos: pd.Series, scores, cal, prices) -> dict:
    r = run_backtest(
        scores, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N, position_series=pos
    )
    st = nav_stats(r["nav"], periods_per_year=12.0)
    print(f"\n=== {label} ===")
    for k in ["ann_return", "ann_vol", "sharpe", "max_drawdown", "calmar", "win_rate"]:
        print(f"  {k:<14} {st[k]:.4f}")
    r["periods"].to_csv(PROC / f"m4b_bt_periods_{label}.csv", index=False)
    return st


def main() -> None:
    print("[M4b] 回撤止损回测 ...")
    cal = load_calendar()
    scores = load_scores(TAG).rolling(SMOOTH_N, min_periods=1).mean()
    prices = load_prices()

    m4a = pd.read_parquet(PROC / "m4a_position_series.parquet")["pos"]
    m4a.index = pd.to_datetime(m4a.index)
    m4b = pd.read_parquet(PROC / "m4b_pos_m4b_only.parquet")["pos_m4b"]
    m4b.index = pd.to_datetime(m4b.index)
    combo = pd.read_parquet(PROC / "m4b_position_series.parquet")["pos"]
    combo.index = pd.to_datetime(combo.index)

    st_m4b = run_one("M4b_only", m4b, scores, cal, prices)
    st_combo = run_one("M4a_M4b", combo, scores, cal, prices)

    print("\n=== 三方对比（期频） ===")
    print(f"{'指标':<16}{'基线':>10}{'M4a':>10}{'M4b_only':>10}{'合成':>10}")
    for k in ["ann_return", "ann_vol", "sharpe", "max_drawdown", "calmar"]:
        b = BASE[k]
        m4a_val = (
            0.4992
            if k == "ann_return"
            else (
                0.3595
                if k == "ann_vol"
                else (
                    1.3885
                    if k == "sharpe"
                    else (-0.2418 if k == "max_drawdown" else 2.0643)
                )
            )
        )
        print(
            f"{k:<16}{b:>10.4f}{m4a_val:>10.4f}{st_m4b[k]:>10.4f}{st_combo[k]:>10.4f}"
        )

    print("\n=== 验收（合成） ===")
    print(
        f"  Sharpe >= 1.680: "
        f"{'PASS' if st_combo['sharpe'] >= 1.680 else 'FAIL'} "
        f"({st_combo['sharpe']:.3f})"
    )
    print(
        f"  |MDD| <= 25%:    "
        f"{'PASS' if abs(st_combo['max_drawdown']) <= 0.25 else 'FAIL'} "
        f"({st_combo['max_drawdown']:.4f})"
    )


if __name__ == "__main__":
    main()
