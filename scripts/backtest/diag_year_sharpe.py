"""重算分年度收益与剔除 2021 后的 Sharpe（与 summary 完全同口径）。"""

import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(r"C:\Users\16075\code\multi_factor_lab")
sys.path.insert(0, str(_ROOT / "scripts" / "backtest"))

from engine import nav_stats  # noqa: E402

PROC = _ROOT / "data" / "processed"


def load(tag):
    return (
        pd.read_csv(PROC / f"composite_bt_{tag}.csv", parse_dates=["trade_date"])
        .sort_values("trade_date")
        .reset_index(drop=True)
    )


def build_nav(net_ret):
    """与 run_backtest 完全一致：nav.iloc[0] = 1+r0，不前置 1.0。"""
    return pd.Series((1.0 + net_ret).cumprod().to_numpy())


for tag in ["lasso_all8", "ic_no_vol", "lasso_horizon_all8"]:
    df = load(tag)
    print(f"\n=== {tag} ===")

    df_y = df.copy()
    df_y["year"] = df_y["trade_date"].dt.year
    for y, g in df_y.groupby("year"):
        print(f"  {y}: {(1 + g['net_ret']).prod() - 1:+.2%}")

    full = nav_stats(build_nav(df["net_ret"]), periods_per_year=12.0)
    print(
        f"  全周期 Sharpe: {full['sharpe']:.3f}   全周期 ann: {full['ann_return']:+.2%}"
    )

    df_ex = df[df["trade_date"].dt.year != 2021].reset_index(drop=True)
    ex = nav_stats(build_nav(df_ex["net_ret"]), periods_per_year=12.0)
    print(
        f"  剔除 2021 Sharpe: {ex['sharpe']:.3f}   剔除 2021 ann: {ex['ann_return']:+.2%}"
    )
