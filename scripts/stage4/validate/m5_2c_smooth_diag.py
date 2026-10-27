"""M5.2c M4c 平滑 K 的扩展诊断：判断 K=5 是"尖峰"还是"未收敛爬坡"。

对 K ∈ {2,3,4,5,6,7,8}，输出：
1. 全期 Sharpe / 年化 / MDD / 换手
2. 剔除 2021 后 Sharpe（复用否决 top_n=25 的同一标准）
3. 2021 年收益贡献占比

红线：
- K=5 若剔除 2021 后 Sharpe < 0.722（定稿 K=3 的剔除2021 Sharpe），判定为行情馈赠，否决。
- 若 K=6、7、8 继续单调上升，判定参数未收敛，K=3 不能称"最优"，只能称"保守选择"。
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
K_GRID = [2, 3, 4, 5, 6, 7, 8]
BASELINE_EX2021_SHARPE = 0.7223  # top_n=50 v1 的剔除2021 Sharpe（前情提要）


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


def build_pos_final(m4a: pd.Series, dd_sig: pd.Series) -> pd.Series:
    """定稿 M4a×M4b 温和版仓位，D=0.15, min_pos=0.70。"""
    pos_m4b = (1.0 - dd_sig.abs() / 0.15).clip(lower=0.70, upper=1.0).fillna(1.0)
    pos = pd.concat([m4a, pos_m4b], axis=1).min(axis=1)
    pos.name = "pos"
    pos.index.name = "trade_date"
    return pos


def stats_full_and_ex2021(periods: pd.DataFrame) -> dict:
    """全期与剔除2021 的绩效。"""
    p = periods.copy()
    p["trade_date"] = pd.to_datetime(p["trade_date"])

    # 全期
    nav_full = (1.0 + p["net_ret"].astype(float)).cumprod()
    st_full = nav_stats(nav_full, periods_per_year=12.0)

    # 剔除 2021
    mask_ex = p["trade_date"].dt.year != 2021
    p_ex = p[mask_ex].reset_index(drop=True)
    nav_ex = (1.0 + p_ex["net_ret"].astype(float)).cumprod()
    st_ex = nav_stats(nav_ex, periods_per_year=12.0)

    # 2021 收益贡献
    p_2021 = p[~mask_ex]
    ret_2021 = float((1.0 + p_2021["net_ret"]).prod() - 1.0)
    ret_all = float((1.0 + p["net_ret"]).prod() - 1.0)

    return {
        "sharpe_full": st_full["sharpe"],
        "ann_full": st_full["ann_return"],
        "mdd_full": st_full["max_drawdown"],
        "sharpe_ex2021": st_ex["sharpe"],
        "ann_ex2021": st_ex["ann_return"],
        "ret_2021": ret_2021,
        "ret_all": ret_all,
        "share_2021": ret_2021 / ret_all if abs(ret_all) > 1e-9 else float("nan"),
        "avg_turnover": float(p["turnover"].mean()),
        "n_full": len(p),
        "n_ex2021": len(p_ex),
    }


def main() -> None:
    print("[M5.2c] M4c 平滑 K 扩展诊断 ...")
    cal = load_calendar()
    prices = load_prices()
    scores_v2 = load_scores_v2()
    m4a = load_m4a()
    dd_sig = build_dd_sig()
    pos_final = build_pos_final(m4a, dd_sig)

    rows = []
    for K in K_GRID:
        scores_s = scores_v2.rolling(K, min_periods=1).mean()
        r = run_backtest(
            scores_s,
            cal,
            prices,
            top_n=TOP_N,
            buffer_n=BUFFER_N,
            position_series=pos_final,
        )
        st = stats_full_and_ex2021(r["periods"])
        st["K"] = K
        rows.append(st)
        print(
            f"  K={K}  Sharpe_full={st['sharpe_full']:.4f}  "
            f"Sharpe_ex2021={st['sharpe_ex2021']:.4f}  "
            f"ann_full={st['ann_full']:.4f}  "
            f"mdd_full={st['mdd_full']:.4f}  "
            f"2021占比={st['share_2021']:.2%}"
        )

    df = pd.DataFrame(rows)[
        [
            "K",
            "sharpe_full",
            "ann_full",
            "mdd_full",
            "sharpe_ex2021",
            "ann_ex2021",
            "ret_2021",
            "ret_all",
            "share_2021",
            "avg_turnover",
        ]
    ]
    out = PROC / "m5_2c_smooth_diag.csv"
    df.to_csv(out, index=False)
    print(f"\n[落盘] {out}")

    # ---- 判定 ----
    print("\n" + "=" * 100)
    print("判定")
    print("=" * 100)

    k3 = df[df["K"] == 3].iloc[0]
    k5 = df[df["K"] == 5].iloc[0]

    print(
        f"  定稿 K=3: Sharpe_full={k3['sharpe_full']:.4f}, "
        f"Sharpe_ex2021={k3['sharpe_ex2021']:.4f}"
    )
    print(
        f"  候选 K=5: Sharpe_full={k5['sharpe_full']:.4f}, "
        f"Sharpe_ex2021={k5['sharpe_ex2021']:.4f}"
    )

    print("\n  [判断1] K=5 是否行情馈赠：")
    if k5["sharpe_ex2021"] < k3["sharpe_ex2021"]:
        print(
            f"    → K=5 剔除2021 Sharpe ({k5['sharpe_ex2021']:.4f}) "
            f"低于 K=3 ({k3['sharpe_ex2021']:.4f})，"
            f"与 top_n=25 同罪，**应否决**"
        )
    else:
        print(
            f"    → K=5 剔除2021 Sharpe ({k5['sharpe_ex2021']:.4f}) "
            f"不低于 K=3 ({k3['sharpe_ex2021']:.4f})，"
            f"需结合收敛性进一步论证"
        )

    print("\n  [判断2] 参数是否收敛：")
    seq = df["sharpe_full"].tolist()
    is_monotone_up = all(b >= a - 0.01 for a, b in zip(seq, seq[1:]))
    print(f"    Sharpe_full 序列: {[round(x, 4) for x in seq]}")
    if is_monotone_up:
        print("    → 单调上升，**未收敛**，K=3 不能称'最优'，只能称'保守选择'")
    else:
        peak_k = df.loc[df["sharpe_full"].idxmax(), "K"]
        print(f"    → 非单调，峰值在 K={peak_k}，" f"需判断峰值是否为过拟合尖峰")

    print("\n  原则：无论诊断结果如何，K=5 不自动替换定稿 K=3。")
    print("        若报告需提及 K=5，必须同时披露收敛性和剔除2021 结论。")
    print("[完成] M5.2c 结束。")


if __name__ == "__main__":
    main()
