"""M4c 稳健性：top_n 对 2021 依赖度 + 参数敏感性。"""

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
    load_calendar,
    load_prices,
)

PROC = Path("data/processed")


def sharpe_ex2021(nav: pd.Series) -> float:
    """剔除 2021 年后的期频 Sharpe。"""
    mask = nav.index.year != 2021
    nav2 = nav[mask]
    if len(nav2) < 5:
        return np.nan
    r = nav2.pct_change().dropna()
    return r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else np.nan


def main() -> None:
    print("[M4c] 稳健性检验 ...")
    cal = load_calendar()
    prices = load_prices()
    scores_v2 = pd.read_parquet(PROC / "composite_scores_lasso_horizon_all8_v2.parquet")
    scores_v2.index = pd.to_datetime(scores_v2.index)
    scores_smooth = scores_v2.rolling(SMOOTH_N, min_periods=1).mean()
    ps = pd.read_parquet(PROC / "m4_position_series.parquet")["pos"]
    ps.index = pd.to_datetime(ps.index)

    print(f"\n{'top_n':>8}{'全期Sharpe':>12}{'剔除2021':>12}{'降幅':>10}{'MDD':>10}")
    for top_n in [20, 24, 25, 26, 30, 50]:
        r = run_backtest(
            scores_smooth,
            cal,
            prices,
            top_n=top_n,
            buffer_n=BUFFER_N,
            position_series=ps,
        )
        st = nav_stats(r["nav"], periods_per_year=12.0)
        s_ex = sharpe_ex2021(r["nav"])
        drop = (s_ex - st["sharpe"]) / st["sharpe"] * 100
        print(
            f"{top_n:>8d}{st['sharpe']:>12.4f}{s_ex:>12.4f}"
            f"{drop:>9.1f}%{st['max_drawdown']:>10.4f}"
        )


if __name__ == "__main__":
    main()
