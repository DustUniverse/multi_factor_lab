"""M4b 诊断：平滑线性止损参数扫描 + 原滞回规则放宽版。"""

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
BASE_SHARPE = 1.4611
BASE_MDD = -0.2184


def make_pos_linear(dd_sig: pd.Series, D: float, min_pos: float) -> pd.Series:
    pos = 1.0 - dd_sig.abs() / D
    return pos.clip(lower=min_pos, upper=1.0).fillna(1.0)


def run_one(pos: pd.Series, scores, cal, prices) -> dict:
    r = run_backtest(
        scores, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N, position_series=pos
    )
    st = nav_stats(r["nav"], periods_per_year=12.0)
    return st, pos.mean()


def main() -> None:
    cal = load_calendar()
    scores = load_scores(TAG).rolling(SMOOTH_N, min_periods=1).mean()
    prices = load_prices()

    nav = pd.read_parquet(PROC / "bt_nav_lasso_horizon_all8_daily.parquet")
    nav.index = pd.to_datetime(nav.index)
    dd = nav["nav"] / nav["nav"].cummax() - 1.0
    dd_sig = dd.reindex(cal["signal_date"], method="ffill")
    dd_sig.index = pd.to_datetime(cal["trade_date"])

    print(f"基线: Sharpe {BASE_SHARPE:.4f}, MDD {BASE_MDD:.4f}")
    print(
        f"dd 分布: min={dd_sig.min():.4f}, median={dd_sig.median():.4f}, "
        f"p25={dd_sig.quantile(0.25):.4f}"
    )

    print("\n[扫描 1] 线性止损 pos = clip(1-|dd|/D, min_pos, 1.0)")
    print(
        f"{'D':>6}{'min_pos':>10}{'sharpe':>10}{'ann_ret':>10}"
        f"{'ann_vol':>10}{'MDD':>10}{'avg_pos':>10}"
    )
    best = (None, -999)
    for D in [0.15, 0.20, 0.25, 0.30, 0.40, 0.50]:
        for mp in [0.0, 0.3, 0.5, 0.7]:
            ps = make_pos_linear(dd_sig, D, mp)
            ps.index = pd.to_datetime(cal["trade_date"])
            st, avg = run_one(ps, scores, cal, prices)
            print(
                f"{D:>6.2f}{mp:>10.1f}{st['sharpe']:>10.3f}{st['ann_return']:>10.4f}"
                f"{st['ann_vol']:>10.4f}{st['max_drawdown']:>10.4f}{avg:>10.3f}"
            )
            if st["sharpe"] > best[1]:
                best = ((D, mp, st), st["sharpe"])

    print(
        f"\n最优: D={best[0][0]}, min_pos={best[0][1]}, "
        f"Sharpe={best[0][2]['sharpe']:.4f}, "
        f"MDD={best[0][2]['max_drawdown']:.4f}"
    )

    # 对比：最优组合与 M4a 取 min
    m4a = pd.read_parquet(PROC / "m4a_position_series.parquet")["pos"]
    m4a.index = pd.to_datetime(m4a.index)
    ps_best = make_pos_linear(dd_sig, best[0][0], best[0][1])
    ps_best.index = pd.to_datetime(cal["trade_date"])
    combo = pd.concat([m4a, ps_best], axis=1).min(axis=1)
    st_c, avg_c = run_one(combo, scores, cal, prices)
    print(
        f"\n[最优 × M4a 合成] Sharpe={st_c['sharpe']:.4f}, "
        f"MDD={st_c['max_drawdown']:.4f}, avg_pos={avg_c:.3f}"
    )

    if best[1] < BASE_SHARPE:
        print(f"\n结论: 最优线性止损 Sharpe {best[1]:.4f} < 基线 {BASE_SHARPE:.4f}")
        print("      → 止损在平滑口径下仍无法提升 Sharpe，M4b 应降级为尾部保护")
    else:
        print(f"\n结论: 存在有效参数（Sharpe {best[1]:.4f} > 基线）")


if __name__ == "__main__":
    main()
