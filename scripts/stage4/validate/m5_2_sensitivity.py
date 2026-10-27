"""M5.2 参数敏感性：只扫合理邻域，只作稳健性证据，不替换定稿基线。

扫描：
- M4b 止损阈值 D ∈ {0.10, 0.15, 0.20} × min_pos ∈ {0.60, 0.70, 0.80}
- M4c 平滑期数 K ∈ {1, 3, 5}
- 固定：v2 scores、top_n=50、M4a 仓位不变
- 红线：不扫 top_n，不改训练标签
"""

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

D_GRID = [0.10, 0.15, 0.20]
MINPOS_GRID = [0.60, 0.70, 0.80]
SMOOTH_GRID = [1, 3, 5]
SMOOTH_BASE = 3


def load_scores_v2() -> pd.DataFrame:
    s = pd.read_parquet(PROC / "composite_scores_lasso_horizon_all8_v2.parquet")
    s.index = pd.to_datetime(s.index)
    return s


def load_m4a() -> pd.Series:
    p = pd.read_parquet(PROC / "m4a_position_series.parquet")["pos"]
    p.index = pd.to_datetime(p.index)
    return p


def build_dd_sig() -> pd.Series:
    nav = pd.read_parquet(PROC / "bt_nav_lasso_horizon_all8_daily.parquet")["nav"]
    nav.index = pd.to_datetime(nav.index)
    dd = nav / nav.cummax() - 1.0
    cal = pd.read_csv(
        PROC / "rebalance_calendar.csv",
        parse_dates=["signal_date", "trade_date"],
    )
    dd_sig = dd.reindex(cal["signal_date"], method="ffill")
    dd_sig.index = pd.to_datetime(cal["trade_date"])
    return dd_sig


def stats_from_backtest(r: dict) -> dict:
    st = nav_stats(r["nav"], periods_per_year=12.0)
    pos = r["periods"]["pos"].astype(float)
    st["avg_pos"] = float(pos.mean())
    st["min_pos"] = float(pos.min())
    return st


def scan_m4b(cal, prices, scores, m4a, dd_sig) -> pd.DataFrame:
    print("\n" + "=" * 100)
    print("[M5.2a] M4b 参数扫描（D × min_pos），smooth=3，v2 scores")
    print("=" * 100)
    rows = []
    for D in D_GRID:
        for mp in MINPOS_GRID:
            pos_m4b = (1.0 - dd_sig.abs() / D).clip(lower=mp, upper=1.0).fillna(1.0)
            pos_final = pd.concat([m4a, pos_m4b], axis=1).min(axis=1)
            pos_final.name = "pos"
            pos_final.index.name = "trade_date"
            r = run_backtest(
                scores,
                cal,
                prices,
                top_n=TOP_N,
                buffer_n=BUFFER_N,
                position_series=pos_final,
            )
            st = stats_from_backtest(r)
            st["D"] = D
            st["min_pos"] = mp
            rows.append(st)
            print(
                f"  D={D:.2f} min_pos={mp:.2f}  "
                f"sharpe={st['sharpe']:.4f}  ann={st['ann_return']:.4f}  "
                f"mdd={st['max_drawdown']:.4f}  avg_pos={st['avg_pos']:.4f}"
            )
    df = pd.DataFrame(rows)

    # 重命名冲突列
    df = df.rename(columns={"min_pos": "min_pos_cfg"})
    if "min_pos" in df.columns and "min_pos_cfg" in df.columns:
        pass
    return df


def scan_smooth(cal, prices, scores_v2, m4a, dd_sig) -> pd.DataFrame:
    print("\n" + "=" * 100)
    print("[M5.2b] M4c 平滑期数扫描，D=0.15 min_pos=0.70，v2 scores")
    print("=" * 100)
    pos_m4b = (1.0 - dd_sig.abs() / 0.15).clip(lower=0.70, upper=1.0).fillna(1.0)
    pos_final = pd.concat([m4a, pos_m4b], axis=1).min(axis=1)
    pos_final.name = "pos"
    pos_final.index.name = "trade_date"

    rows = []
    for K in SMOOTH_GRID:
        scores_s = scores_v2.rolling(K, min_periods=1).mean()
        r = run_backtest(
            scores_s,
            cal,
            prices,
            top_n=TOP_N,
            buffer_n=BUFFER_N,
            position_series=pos_final,
        )
        st = stats_from_backtest(r)
        st["smooth_K"] = K
        rows.append(st)
        print(
            f"  K={K}  sharpe={st['sharpe']:.4f}  ann={st['ann_return']:.4f}  "
            f"mdd={st['max_drawdown']:.4f}"
        )
    return pd.DataFrame(rows)


def main() -> None:
    print("[M5.2] 参数敏感性扫描开始 ...")
    cal = load_calendar()
    prices = load_prices()
    scores_v2 = load_scores_v2()
    m4a = load_m4a()
    dd_sig = build_dd_sig()

    scores_smooth_base = scores_v2.rolling(SMOOTH_BASE, min_periods=1).mean()

    df_m4b = scan_m4b(cal, prices, scores_smooth_base, m4a, dd_sig)
    df_m4c = scan_smooth(cal, prices, scores_v2, m4a, dd_sig)

    # 落盘
    out1 = PROC / "m5_2a_m4b_scan.csv"
    out2 = PROC / "m5_2b_smooth_scan.csv"
    df_m4b.to_csv(out1, index=False)
    df_m4c.to_csv(out2, index=False)
    print(f"\n[落盘] {out1}")
    print(f"[落盘] {out2}")

    # 对照定稿基线
    base = pd.read_csv(PROC / "m5_1c_perf.csv", index_col=0)
    print("\n" + "=" * 100)
    print(
        "[对照] 定稿基线 full: Sharpe=%.4f ann=%.4f mdd=%.4f"
        % (
            base.loc["full", "sharpe"],
            base.loc["full", "ann_return"],
            base.loc["full", "max_drawdown"],
        )
    )
    print("  M4b 扫描最优: 见 m5_2a_m4b_scan.csv")
    print("  M4c 扫描: 见 m5_2b_smooth_scan.csv")
    print("  原则：扫描结果只作稳健性证据，不替换定稿基线。")
    print("[完成] M5.2 结束。")


if __name__ == "__main__":
    main()
