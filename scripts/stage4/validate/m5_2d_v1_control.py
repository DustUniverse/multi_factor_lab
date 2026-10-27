"""M5.2d v1 对照扫描：v1 scores 做同样的 K 网格，判断单调上升是 v2 特有还是普遍现象。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402

from scripts.backtest.engine import nav_stats, run_backtest  # noqa: E402
from scripts.backtest.run_composite_backtest import (  # noqa: E402
    BUFFER_N,
    TOP_N,
    load_calendar,
    load_prices,
)

PROC = Path("data/processed")
K_GRID = [2, 3, 4, 5, 6, 7, 8]


def main() -> None:
    print("[M5.2d] v1 scores 对照 K 扫描 ...")
    cal = load_calendar()
    prices = load_prices()

    s_v1 = pd.read_parquet(PROC / "composite_scores_lasso_horizon_all8.parquet")
    s_v1.index = pd.to_datetime(s_v1.index)

    m4a = pd.read_parquet(PROC / "m4a_position_series.parquet")["pos"]
    m4a.index = pd.to_datetime(m4a.index)

    nav = pd.read_parquet(PROC / "bt_nav_lasso_horizon_all8_daily.parquet")["nav"]
    nav.index = pd.to_datetime(nav.index)
    dd = nav / nav.cummax() - 1.0
    cal_df = pd.read_csv(
        PROC / "rebalance_calendar.csv",
        parse_dates=["signal_date", "trade_date"],
    )
    dd_sig = dd.reindex(cal_df["signal_date"], method="ffill")
    dd_sig.index = pd.to_datetime(cal_df["trade_date"])

    pos_m4b = (1.0 - dd_sig.abs() / 0.15).clip(lower=0.70, upper=1.0).fillna(1.0)
    pos_final = pd.concat([m4a, pos_m4b], axis=1).min(axis=1)
    pos_final.name = "pos"
    pos_final.index.name = "trade_date"

    rows = []
    for K in K_GRID:
        s = s_v1.rolling(K, min_periods=1).mean()
        r = run_backtest(
            s,
            cal,
            prices,
            top_n=TOP_N,
            buffer_n=BUFFER_N,
            position_series=pos_final,
        )
        st = nav_stats(r["nav"], periods_per_year=12.0)
        rows.append(
            {
                "K": K,
                "sharpe_full": st["sharpe"],
                "ann_full": st["ann_return"],
                "mdd_full": st["max_drawdown"],
                "avg_turnover": float(r["periods"]["turnover"].mean()),
            }
        )
        print(
            f"  K={K}  sharpe={st['sharpe']:.4f}  ann={st['ann_return']:.4f}  "
            f"mdd={st['max_drawdown']:.4f}  turnover={rows[-1]['avg_turnover']:.4f}"
        )

    df = pd.DataFrame(rows)
    out = PROC / "m5_2d_v1_control.csv"
    df.to_csv(out, index=False)
    print(f"[落盘] {out}")

    print("\n" + "=" * 80)
    print("对照结论")
    print("=" * 80)
    seq = df["sharpe_full"].tolist()
    is_monotone_up = all(b >= a - 0.01 for a, b in zip(seq, seq[1:]))
    print(f"  v1 Sharpe 序列: {[round(x, 4) for x in seq]}")
    if is_monotone_up:
        print("  → v1 也单调上升 → 问题出在 M5.2 平滑或因子体系，不是 v2 特有")
    else:
        peak_k = df.loc[df["sharpe_full"].idxmax(), "K"]
        print(f"  → v1 不单调（峰值 K={peak_k}）→ 问题集中在 v2")


if __name__ == "__main__":
    main()
