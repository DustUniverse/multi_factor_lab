"""M5a-补充：把阶段二 Q10 净值按"月频不重叠"口径重算，用于对账。

阶段二原脚本用重叠 20D 窗口日频累乘，导致波动被严重低估。
本脚本按 rebalance_calendar 的 signal_date 采样（每期只取一个 20D 收益），
得到与阶段三可比的月频序列。

用法（项目根目录、激活 .venv 后）：
    python scripts/backtest/stage2_recompute_monthly.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

QD = _ROOT / "data" / "processed"
CAL_PATH = QD / "rebalance_calendar.csv"
FACTORS = ["turnover", "amihud_20", "bp"]

OUT_PATH = QD / "stage2_monthly_recompute.csv"


def compute_monthly_stats(factor: str, cal: pd.DataFrame) -> dict | None:
    """按 signal_date 采样 Q10 20D 收益，做月频不重叠统计。"""
    path = QD / f"quantile_returns_{factor}.csv"
    if not path.exists():
        print(f"  [跳过] 缺 {path.name}")
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    q10 = df.iloc[:, -1]  # 最后一列是 Q9（0-indexed，即 Q10）

    rows = []
    for sig in cal["signal_date"]:
        if sig in q10.index:
            r = q10.loc[sig]
            if pd.notna(r):
                rows.append({"signal_date": sig, "ret_20d": r})
    if len(rows) < 10:
        print(f"  [跳过] {factor} 有效月频样本 {len(rows)} 不足")
        return None

    out = pd.DataFrame(rows).sort_values("signal_date").reset_index(drop=True)
    # 近似把 20D 收益当日→次月，直接当周期收益累乘
    nav = (1.0 + out["ret_20d"]).cumprod()

    periods_per_year = 12.0
    rets = out["ret_20d"]
    n = len(rets)
    years = n / periods_per_year
    ann = nav.iloc[-1] ** (1.0 / years) - 1.0
    vol = rets.std() * np.sqrt(periods_per_year)
    sharpe = ann / vol if vol > 0 else np.nan
    dd = (nav / nav.cummax() - 1.0).min()
    calmar = ann / abs(dd) if dd < 0 else np.nan
    win = (rets > 0).mean()
    avg_win = rets[rets > 0].mean() if (rets > 0).any() else 0.0
    avg_loss = rets[rets < 0].mean() if (rets < 0).any() else 0.0
    pl = abs(avg_win / avg_loss) if avg_loss < 0 else np.nan

    return {
        "factor": factor,
        "n_periods": n,
        "ann_return": ann,
        "ann_vol": vol,
        "sharpe": sharpe,
        "max_drawdown": dd,
        "calmar": calmar,
        "win_rate": win,
        "pnl_ratio": pl,
        "nav_final": nav.iloc[-1],
    }


def main() -> None:
    print("[M5a-补充] 阶段二月频不重叠重算 ...")
    cal = pd.read_csv(CAL_PATH, parse_dates=["signal_date", "trade_date"])
    print(f"  调仓点数: {len(cal)}")

    rows = []
    for f in FACTORS:
        st = compute_monthly_stats(f, cal)
        if st is not None:
            rows.append(st)
            print(f"\n  === {f} 阶段二月频版 ===")
            print(f"  有效期数:  {st['n_periods']}")
            print(f"  年化收益:  {st['ann_return']:+.2%}")
            print(f"  年化波动:  {st['ann_vol']:.2%}")
            print(f"  Sharpe:    {st['sharpe']:.3f}")
            print(f"  最大回撤:  {st['max_drawdown']:.2%}")
            print(f"  Calmar:    {st['calmar']:.3f}")
            print(f"  净值终值:  {st['nav_final']:.4f}")

    if rows:
        out = pd.DataFrame(rows)
        out.to_csv(OUT_PATH, index=False)
        print(f"\n  已保存: {OUT_PATH}")


if __name__ == "__main__":
    main()
