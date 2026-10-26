"""M4c-v3: 流动性过滤（极端低流动性剔除）+ 阈值扫描。

逻辑：
- Lasso 正系数偏好低流动性股（amihud 高），这是 alpha 来源
- 只剔除截面 amihud 最高的 top_pct，保留大部分低流动性 alpha
- 过滤在「v2 scores 平滑后」进行：把极端低流动性股的 score 设为 -inf
- 扫描 top_pct ∈ {5%, 10%, 15%, 20%, 30%}

无前视：
- 每期用当期（signal_date）的 amihud_20 截面，不用未来数据
"""

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
)

PROC = Path("data/processed")
FACTOR_FILE = PROC / "factor_panel_final.parquet"


def load_amihud() -> pd.Series:
    """读 amihud_20，index=(date, symbol)。"""
    print("  读 amihud_20 ...")
    fp = pd.read_parquet(FACTOR_FILE, columns=["amihud_20"])
    fp = fp.reset_index()
    fp["symbol"] = fp["symbol"].astype(str).str.zfill(6)
    fp["date"] = pd.to_datetime(fp["date"])
    s = fp.set_index(["date", "symbol"])["amihud_20"].dropna()
    print(f"    amihud 有效行: {len(s)}")
    return s


def apply_filter(
    scores_smooth: pd.DataFrame, amihud: pd.Series, top_pct: float
) -> pd.DataFrame:
    """每期把 amihud 截面 top_pct 的股票 score 设为 -inf。"""
    out = scores_smooth.copy()
    n_filtered = []
    for d in out.index:
        try:
            am_d = amihud.loc[d]
        except KeyError:
            n_filtered.append(0)
            continue
        if len(am_d) == 0:
            n_filtered.append(0)
            continue
        thr = am_d.quantile(1.0 - top_pct)
        bad = am_d[am_d >= thr].index
        common = out.columns.intersection(bad)
        out.loc[d, common] = -np.inf
        n_filtered.append(len(common))
    print(f"    top_pct={top_pct:.0%}: 每期平均过滤 {np.mean(n_filtered):.0f} 只")
    return out


def main() -> None:
    print("[M4c-v3] 流动性过滤扫描 ...")
    cal = load_calendar()
    prices = load_prices()

    scores_v2 = pd.read_parquet(PROC / "composite_scores_lasso_horizon_all8_v2.parquet")
    scores_v2.index = pd.to_datetime(scores_v2.index)
    scores_smooth = scores_v2.rolling(SMOOTH_N, min_periods=1).mean()
    scores_smooth.columns = scores_smooth.columns.astype(str).str.zfill(6)

    amihud = load_amihud()
    ps = pd.read_parquet(PROC / "m4_position_series.parquet")["pos"]
    ps.index = pd.to_datetime(ps.index)

    # 基线：v2 不过滤（已知 1.5527）
    print("\n[基线] v2 scores 不过滤 ...")
    r0 = run_backtest(
        scores_smooth, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N, position_series=ps
    )
    st0 = nav_stats(r0["nav"], periods_per_year=12.0)
    print(
        f"  Sharpe={st0['sharpe']:.4f}  ann_ret={st0['ann_return']:.4f}  "
        f"MDD={st0['max_drawdown']:.4f}  "
        f"cost={r0['periods']['cost'].mean()*12*100:.2f}%"
    )

    print("\n[扫描] top_pct ∈ {5%, 10%, 15%, 20%, 30%}")
    print(
        f"{'top_pct':>8}{'sharpe':>10}{'ann_ret':>10}{'ann_vol':>10}"
        f"{'MDD':>10}{'calmar':>10}"
    )
    best = (None, -999)
    for pct in [0.05, 0.10, 0.15, 0.20, 0.30]:
        print(f"\n  --- top_pct={pct:.0%} ---")
        sc = apply_filter(scores_smooth, amihud, pct)
        r = run_backtest(
            sc, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N, position_series=ps
        )
        st = nav_stats(r["nav"], periods_per_year=12.0)
        print(
            f"{pct:>8.2f}{st['sharpe']:>10.4f}{st['ann_return']:>10.4f}"
            f"{st['ann_vol']:>10.4f}{st['max_drawdown']:>10.4f}"
            f"{st['calmar']:>10.4f}"
        )
        if st["sharpe"] > best[1]:
            best = (pct, st["sharpe"], r)

    print(f"\n最优: top_pct={best[0]:.0%}, Sharpe={best[1]:.4f}")
    ok = "PASS" if best[1] >= 1.680 else "FAIL"
    print(f"验收: Sharpe>=1.680 {ok}")


if __name__ == "__main__":
    main()
