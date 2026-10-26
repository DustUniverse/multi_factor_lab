"""M4c: v2 scores 回测（前视修正 + 权重平滑），叠加 M4a+M4b 仓位。"""

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
)

PROC = Path("data/processed")


def load_scores_v2(tag: str) -> pd.DataFrame:
    p = PROC / f"composite_scores_{tag}_v2.parquet"
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index)
    return df


def main() -> None:
    print("[M4c] v2 scores 回测 ...")
    cal = load_calendar()
    prices = load_prices()

    # 1) v2 scores（前视修正 + 权重平滑）
    scores_v2 = load_scores_v2("lasso_horizon_all8")
    # 2) 信号平滑：与基线一致（SMOOTH_N=3），保证可比
    scores_v2_smooth = scores_v2.rolling(SMOOTH_N, min_periods=1).mean()
    print(f"  v2 scores: {scores_v2.shape}, 平滑后: {scores_v2_smooth.shape}")

    # 3) 仓位：M4a×M4b 合成
    ps = pd.read_parquet(PROC / "m4_position_series.parquet")["pos"]
    ps.index = pd.to_datetime(ps.index)

    # 4) 回测
    r = run_backtest(
        scores_v2_smooth,
        cal,
        prices,
        top_n=TOP_N,
        buffer_n=BUFFER_N,
        position_series=ps,
    )
    st = nav_stats(r["nav"], periods_per_year=12.0)

    print("\n=== M4c 最终绩效（v2 scores + M4a×M4b 仓位） ===")
    for k, v in st.items():
        print(f"  {k:<14} {v}")

    r["periods"].to_csv(PROC / "m4c_bt_periods.csv", index=False)
    r["nav"].to_frame("nav").to_parquet(PROC / "m4c_bt_nav.parquet")

    # 5) 三方对比
    base = {
        "ann_return": 0.5369,
        "ann_vol": 0.3675,
        "sharpe": 1.4611,
        "max_drawdown": -0.2184,
        "calmar": 2.4590,
    }
    m4ab = {
        "ann_return": 0.4255,
        "ann_vol": 0.2875,
        "sharpe": 1.4801,
        "max_drawdown": -0.1826,
        "calmar": 2.3306,
    }
    print("\n=== 三方对比 ===")
    print(f"{'指标':<16}{'基线':>10}{'M4a×M4b':>10}{'M4c最终':>10}{'vs基线':>10}")
    for k in ["ann_return", "ann_vol", "sharpe", "max_drawdown", "calmar"]:
        b = base[k]
        m = m4ab[k]
        f = st[k]
        print(f"{k:<16}{b:>10.4f}{m:>10.4f}{f:>10.4f}{f - b:>+10.4f}")

    print("\n=== 验收（M4 全量合并） ===")
    print(
        f"  Sharpe >= 1.680: "
        f"{'PASS' if st['sharpe'] >= 1.680 else 'FAIL'} ({st['sharpe']:.3f})"
    )
    print(
        f"  |MDD| <= 25%:    "
        f"{'PASS' if abs(st['max_drawdown']) <= 0.25 else 'FAIL'} "
        f"({st['max_drawdown']:.4f})"
    )

    # 6) v2 scores 换手诊断（与基线 periods 对比）
    p = r["periods"]
    print(f"\n  年化成本: {p['cost'].mean() * 12 * 100:.2f}%")
    print(f"  年化换手: {p['turnover'].mean() * 12 * 100:.2f}%")


if __name__ == "__main__":
    main()
