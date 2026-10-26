"""M4a 诊断：pos vs 收益关系 + TARGET_VOL 扫描。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np  # noqa: E402
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


def make_pos(vol_sig: pd.Series, target: float, floor: float = 0.0) -> pd.Series:
    pos = np.minimum(1.0, target / vol_sig)
    pos = pos.clip(lower=floor)
    return pos.fillna(1.0)


def main() -> None:
    cal = load_calendar()
    scores = load_scores(TAG).rolling(SMOOTH_N, min_periods=1).mean()
    prices = load_prices()

    nav_d = pd.read_parquet(PROC / "bt_nav_lasso_horizon_all8_daily.parquet")
    vol = nav_d["daily_ret"].rolling(60, min_periods=60).std() * np.sqrt(252)
    vol_sig = vol.reindex(cal["signal_date"], method="ffill")
    vol_sig.index = cal.index

    # ---- 诊断 1：vol60 vs 当期 gross_ret 的相关性 ----
    base = run_backtest(scores, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N)
    p = base["periods"]
    v = vol_sig.reindex(range(len(p))).values
    mask = ~np.isnan(v)
    corr = np.corrcoef(v[mask], p["gross_ret"].values[mask])[0, 1]
    print(f"[诊断] vol60 vs gross_ret 相关系数 = {corr:+.3f}  (n={mask.sum()})")

    # 按 vol 分档看 gross_ret
    df = pd.DataFrame({"vol": v, "gross": p["gross_ret"].values}).dropna()
    df["vol_q"] = pd.qcut(df["vol"], 4, labels=["Q1低", "Q2", "Q3", "Q4高"])
    print("\n[诊断] 按 vol60 分档的 gross_ret 均值:")
    print(
        df.groupby("vol_q", observed=True)["gross"]
        .agg(["mean", "std", "count"])
        .to_string()
    )

    # ---- 诊断 2：TARGET_VOL 扫描 ----
    print("\n[扫描] TARGET_VOL 敏感性（floor=0）:")
    print(
        f"{'target':>8}{'sharpe':>10}{'ann_ret':>10}{'ann_vol':>10}"
        f"{'MDD':>10}{'calmar':>10}{'avg_pos':>10}"
    )
    results = {}
    for tgt in [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
        ps = make_pos(vol_sig, tgt)
        ps.index = pd.to_datetime(cal["trade_date"])
        r = run_backtest(
            scores, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N, position_series=ps
        )
        st = nav_stats(r["nav"], periods_per_year=12.0)
        results[tgt] = (st, ps.mean())
        print(
            f"{tgt:>8.2f}{st['sharpe']:>10.3f}{st['ann_return']:>10.4f}"
            f"{st['ann_vol']:>10.4f}{st['max_drawdown']:>10.4f}"
            f"{st['calmar']:>10.3f}{ps.mean():>10.3f}"
        )

    # ---- 诊断 3：压仓下限（防过度压仓） ----
    print("\n[扫描] TARGET_VOL=0.25, floor 敏感性:")
    print(
        f"{'floor':>8}{'sharpe':>10}{'ann_ret':>10}{'ann_vol':>10}"
        f"{'MDD':>10}{'calmar':>10}"
    )
    for fl in [0.0, 0.3, 0.4, 0.5, 0.6, 0.7]:
        ps = make_pos(vol_sig, 0.25, floor=fl)
        ps.index = pd.to_datetime(cal["trade_date"])
        r = run_backtest(
            scores, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N, position_series=ps
        )
        st = nav_stats(r["nav"], periods_per_year=12.0)
        print(
            f"{fl:>8.1f}{st['sharpe']:>10.3f}{st['ann_return']:>10.4f}"
            f"{st['ann_vol']:>10.4f}{st['max_drawdown']:>10.4f}{st['calmar']:>10.3f}"
        )

    print(f"\n基线: Sharpe {BASE_SHARPE:.4f}, MDD {BASE_MDD:.4f}")


if __name__ == "__main__":
    main()
