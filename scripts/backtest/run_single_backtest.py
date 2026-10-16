"""M5a: 单因子十分位多头组合对账（阶段三 vs 阶段二）。

对指定的单因子，取 signal_date 上 top_n 只（Q10 近似），用自研引擎跑月频回测，
与阶段二 M3 的 Q10 净值做方向一致性对比。

用法（项目根目录、激活 .venv 后）：
    python scripts/backtest/run_single_backtest.py
    python scripts/backtest/run_single_backtest.py --factor turnover --top_n 480
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_THIS.parent))

from engine import nav_stats, run_backtest  # noqa: E402

FACTOR_PATH = _ROOT / "data" / "processed" / "factor_panel_final.parquet"
PRICE_PATH = _ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"
CAL_PATH = _ROOT / "data" / "processed" / "rebalance_calendar.csv"
STAGE2_QDIR = _ROOT / "data" / "processed"

PRICE_COLS = ["symbol", "date", "open", "close", "is_limit_up", "is_suspended"]


def normalize_symbol(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.split(".").str[0]
    return s.str.zfill(6)


def load_scores_for_factor(factor: str) -> pd.DataFrame:
    """把因子面板转成 signal_date × symbol 的宽表（单因子分数）。"""
    df = pd.read_parquet(FACTOR_PATH)
    df = df.reset_index()  # MultiIndex(date, symbol) → 普通列
    df["symbol"] = normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot(index="date", columns="symbol", values=factor)
    wide.index.name = "signal_date"
    return wide


def load_prices() -> pd.DataFrame:
    df = pd.read_parquet(PRICE_PATH, columns=PRICE_COLS)
    df["symbol"] = normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_calendar() -> pd.DataFrame:
    cal = pd.read_csv(CAL_PATH, parse_dates=["signal_date", "trade_date"])
    return cal


def load_stage2_q10_nav(factor: str) -> pd.Series:
    """阶段二 Q10 净值：把 20D forward return 日化后累乘。"""
    path = STAGE2_QDIR / f"quantile_returns_{factor}.csv"
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    q10 = df.iloc[:, -1]  # 最后一列是 Q9（即 Q10 组，0-indexed）
    daily = (1.0 + q10) ** (1.0 / 20) - 1.0
    nav = (1.0 + daily).cumprod()
    return nav


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", default="turnover")
    ap.add_argument("--top_n", type=int, default=480)
    args = ap.parse_args()

    print(f"[M5a] 单因子对账：factor={args.factor}, top_n={args.top_n}")

    scores = load_scores_for_factor(args.factor)
    print(
        f"  分数面板: {scores.shape}, "
        f"  日期 {scores.index.min().date()} ~ {scores.index.max().date()}"
    )

    prices = load_prices()
    print(f"  价格面板: {prices.shape}")

    cal = load_calendar()
    print(f"  调仓点数: {len(cal)}")

    result = run_backtest(scores, cal, prices, top_n=args.top_n)
    periods = result["periods"]
    nav3 = result["nav"]

    if periods.empty:
        print("  [ERROR] 无有效回测期")
        return

    stats3 = nav_stats(nav3, periods_per_year=12.0)
    print("\n  === 阶段三（自研引擎，月频调仓，含交易成本）===")
    print(f"  有效期数:  {stats3['n_periods']}")
    print(f"  年化收益:  {stats3['ann_return']:+.2%}")
    print(f"  年化波动:  {stats3['ann_vol']:.2%}")
    print(f"  Sharpe:    {stats3['sharpe']:.3f}")
    print(f"  最大回撤:  {stats3['max_drawdown']:.2%}")
    print(f"  Calmar:    {stats3['calmar']:.3f}")
    print(f"  胜率:      {stats3['win_rate']:.2%}")
    print(f"  盈亏比:    {stats3['pnl_ratio']:.3f}")
    print(f"  净值终值:  {nav3.iloc[-1]:.4f}")
    print(f"  平均换手:  {periods['turnover'].mean():.2%}")
    print(f"  平均成本:  {periods['cost'].mean():.4%}")

    # 阶段二 Q10 对照
    nav2 = load_stage2_q10_nav(args.factor)
    daily2 = nav2.pct_change().dropna()
    n_days = len(daily2)
    years2 = n_days / 242.0
    ann2 = nav2.iloc[-1] ** (1.0 / years2) - 1.0
    vol2 = daily2.std() * np.sqrt(242.0)
    sharpe2 = ann2 / vol2 if vol2 > 0 else np.nan
    dd2 = (nav2 / nav2.cummax() - 1.0).min()

    print("\n  === 阶段二（Q10 多头，日频滚动 20D，无成本）===")
    print(f"  年化收益:  {ann2:+.2%}")
    print(f"  年化波动:  {vol2:.2%}")
    print(f"  Sharpe:    {sharpe2:.3f}")
    print(f"  最大回撤:  {dd2:.2%}")
    print(f"  净值终值:  {nav2.iloc[-1]:.4f}")

    # 对账
    print("\n  === 对账 ===")
    print(f"  Sharpe 差异（阶段三 - 阶段二）: {stats3['sharpe'] - sharpe2:+.3f}")
    print(f"  年化收益差异:                  {stats3['ann_return'] - ann2:+.2%}")

    # 保存
    out = _ROOT / "data" / "processed" / f"single_bt_{args.factor}.csv"
    periods.to_csv(out, index=False)
    print(f"\n  期频结果已保存: {out}")


if __name__ == "__main__":
    main()
