"""M3 batch：对 12 个通过初筛的因子批量做十分位分层回测。

复用 run_quantile_backtest.py 里已跑通的函数，避免重复代码。

输出：
    - docs/figures/stage2/quantile/<factor>_nav.png        × 12
    - data/processed/quantile_returns_<factor>.csv          × 12
    - data/processed/quantile_stats_<factor>.csv            × 12
    - data/processed/quantile_summary.csv                   （汇总表，M3 的核心产出）
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_THIS.parent))

from run_quantile_backtest import (  # noqa: E402
    FACTOR_DIRECTIONS,
    MIN_STOCKS_PER_DAY,
    N_QUANTILES,
    PERIOD,
    compute_forward_returns,
    daily_quantile_returns,
    load_factor_series,
    load_prices,
    nav_stats,
    plot_nav,
    to_daily_nav,
)

FIG_DIR = _ROOT / "docs" / "figures" / "stage2" / "quantile"
OUT_DIR = _ROOT / "data" / "processed"


def run_one(factor_name: str, prices: pd.DataFrame, fwd_ret: pd.DataFrame) -> dict:
    """对单因子做完整分层回测，返回汇总指标（同时落盘图/CSV）。"""
    sign = FACTOR_DIRECTIONS[factor_name]
    factor = load_factor_series(factor_name) * sign
    factor_wide = factor.unstack(level=-1).reindex(
        index=prices.index, columns=prices.columns
    )

    qret = daily_quantile_returns(factor_wide, fwd_ret, N_QUANTILES, MIN_STOCKS_PER_DAY)
    nav = to_daily_nav(qret, PERIOD)
    stats = nav_stats(nav)

    # 基准：与分层日期对齐
    bench_ret = fwd_ret.mean(axis=1).reindex(qret.index)
    bench_daily = (1.0 + bench_ret.clip(lower=-0.999)) ** (1.0 / PERIOD) - 1.0
    bench_nav = (1.0 + bench_daily).cumprod()

    long_col = nav.columns.max()
    short_col = nav.columns.min()
    long_nav = nav[long_col]

    # 多空组合：日频（Q10 - Q1）净值
    daily = nav.pct_change().dropna(how="all")
    ls_daily = daily[long_col] - daily[short_col]
    ls_nav = (1.0 + ls_daily).cumprod()
    years = len(ls_daily) / 242.0
    ls_ann_ret = ls_nav.iloc[-1] ** (1.0 / years) - 1.0
    ls_sharpe = ls_daily.mean() / ls_daily.std() * np.sqrt(242.0)

    # 单调性：各层平均 forward return 与层号 1..10 的 Spearman 秩相关
    mean_qret = qret.mean()
    rho, _ = spearmanr(mean_qret.index.values, mean_qret.values)

    # 落盘
    plot_nav(nav, bench_nav, factor_name, FIG_DIR / f"{factor_name}_nav.png")
    qret.to_csv(OUT_DIR / f"quantile_returns_{factor_name}.csv")
    stats.to_csv(OUT_DIR / f"quantile_stats_{factor_name}.csv")

    return {
        "factor": factor_name,
        "sign": sign,
        "Q1_ann_ret": stats.loc[short_col, "ann_return"],
        "Q10_ann_ret": stats.loc[long_col, "ann_return"],
        "Q10_sharpe": stats.loc[long_col, "sharpe"],
        "Q10_max_dd": stats.loc[long_col, "max_drawdown"],
        "Q10_win_rate": stats.loc[long_col, "win_rate"],
        "spread_Q10_Q1": stats.loc[long_col, "ann_return"]
        - stats.loc[short_col, "ann_return"],
        "ls_ann_ret": ls_ann_ret,
        "ls_sharpe": ls_sharpe,
        "monotonicity_rho": rho,
        "long_nav_end": long_nav.iloc[-1],
        "bench_nav_end": bench_nav.iloc[-1],
        "long_excess_end": long_nav.iloc[-1] / bench_nav.iloc[-1],
    }


def main() -> None:
    print("[M3 batch] 12 因子批量分层回测")
    print("  1) 加载价格矩阵 ...")
    prices = load_prices()
    print(f"     prices shape = {prices.shape}")

    print(f"  2) 计算 {PERIOD} 日 forward return ...")
    fwd_ret = compute_forward_returns(prices, PERIOD)

    factors = list(FACTOR_DIRECTIONS.keys())
    results = []
    for i, fname in enumerate(factors, 1):
        print(f"\n  [{i}/{len(factors)}] {fname} ...")
        try:
            r = run_one(fname, prices, fwd_ret)
            results.append(r)
            print(
                f"     Q10 ann={r['Q10_ann_ret']:+.3f}  "
                f"Sharpe={r['Q10_sharpe']:+.2f}  "
                f"maxDD={r['Q10_max_dd']:+.3f}  "
                f"spread={r['spread_Q10_Q1']:+.3f}  "
                f"mono_rho={r['monotonicity_rho']:+.2f}  "
                f"long_excess={r['long_excess_end']:.2f}x"
            )
        except Exception as e:  # noqa: BLE001
            print(f"     FAILED: {type(e).__name__}: {e}")

    df = pd.DataFrame(results)
    # 按多空夏普排序（衡量因子区分能力最直观）
    df = df.sort_values("ls_sharpe", ascending=False).reset_index(drop=True)
    out = OUT_DIR / "quantile_summary.csv"
    df.to_csv(out, index=False, float_format="%.4f")
    print(f"\n[M3 batch] 汇总表已保存：{out}")
    print("\n  汇总（按多空夏普排序）：")
    cols = [
        "factor",
        "Q10_ann_ret",
        "Q10_sharpe",
        "Q10_max_dd",
        "spread_Q10_Q1",
        "ls_ann_ret",
        "ls_sharpe",
        "monotonicity_rho",
        "long_excess_end",
    ]
    print(df[cols].round(3).to_string(index=False))
    print("\n[M3 batch] 完成。")


if __name__ == "__main__":
    main()
