"""M5.1c 口径对齐 + 日频 net 近似。

修复：
1. period_stats 改用 engine.nav_stats，对齐阶段三 Sharpe 1.4611 / M4 1.5527
2. 日频净值重建 "net 近似"：在 gross 日频基础上，每期调仓日按
   (1+net_ret)/(1+gross_ret) 一次性扣成本，量化 gross→net 的 MDD 变化
3. 输出修正后的六组绩效 + 顺序增量拆解
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402

from scripts.backtest.engine import nav_stats  # noqa: E402

PROC = Path("data/processed")

GROUPS = {
    "baseline": "composite_bt_lasso_horizon_all8.csv",
    "m4a_only": "m4a_bt_periods.csv",
    "m4b_only": "m4b_bt_periods_M4b_only.csv",
    "m4a_m4b": "m4_bt_periods.csv",
    "m4c_only": "m4c_bt_periods.csv",
    "full": "m4_final_periods.csv",
}

DAILY = {
    "baseline": "bt_nav_lasso_horizon_all8_daily.parquet",
    "full": "bt_nav_m4_final_daily.parquet",
}

ORDER = ["baseline", "m4a_only", "m4b_only", "m4a_m4b", "m4c_only", "full"]

LABELS = {
    "baseline": "Baseline(v1,满仓)",
    "m4a_only": "M4a(v1+vol)",
    "m4b_only": "M4b激进(v1)",
    "m4a_m4b": "M4a×M4b温和(v1)",
    "m4c_only": "M4c(实为v2+仓位)",
    "full": "Full(v2+仓位)",
}


def period_stats(df: pd.DataFrame) -> dict:
    """与 engine.nav_stats 完全对齐：用 pct_change 得 n-1 个收益。"""
    r = df["net_ret"].astype(float)
    nav = (1.0 + r).cumprod()
    nav.index = pd.to_datetime(df["trade_date"])
    st = nav_stats(nav, periods_per_year=12.0)
    pos = df["pos"].astype(float) if "pos" in df.columns else pd.Series([1.0])
    st["avg_pos"] = float(pos.mean())
    st["min_pos"] = float(pos.min())
    st["avg_turnover"] = float(df["turnover"].mean())
    years = st["n_periods"] / 12.0
    st["ann_cost"] = float(df["cost"].sum() / years) if years > 0 else 0.0
    return st


def daily_mdd_gross(fname: str) -> float:
    df = pd.read_parquet(PROC / fname)
    nav = df["nav"].astype(float)
    dd = nav / nav.cummax() - 1.0
    return float(dd.min())


def daily_mdd_net_approx(
    periods_fname: str, daily_fname: str
) -> tuple[float, float, float]:
    """在 gross 日频净值上，每期调仓日按 (1+net)/(1+gross) 一次性扣成本。

    返回 (net_mdd, net_final_nav, gross_to_net_ratio)。
    """
    per = pd.read_csv(PROC / periods_fname)
    per["trade_date"] = pd.to_datetime(per["trade_date"])
    gross = per["gross_ret"].astype(float)
    net = per["net_ret"].astype(float)
    cost_factor = (1.0 + net) / (1.0 + gross)

    cum = []
    c = 1.0
    for x in cost_factor:
        c *= float(x)
        cum.append(c)
    factor_periods = pd.Series(cum, index=pd.DatetimeIndex(per["trade_date"]))

    daily = pd.read_parquet(PROC / daily_fname)
    nav_gross = daily["nav"].astype(float)
    factor_daily = factor_periods.reindex(nav_gross.index, method="ffill").fillna(1.0)
    nav_net = nav_gross * factor_daily

    dd = nav_net / nav_net.cummax() - 1.0
    return (
        float(dd.min()),
        float(nav_net.iloc[-1]),
        float(nav_net.iloc[-1] / nav_gross.iloc[-1]),
    )


def main() -> None:
    rows = []
    for name in ORDER:
        df = pd.read_csv(PROC / GROUPS[name])
        st = period_stats(df)
        st["group"] = name
        st["label"] = LABELS[name]
        if name in DAILY:
            st["daily_mdd_gross"] = daily_mdd_gross(DAILY[name])
            nmdd, nfinal, ratio = daily_mdd_net_approx(GROUPS[name], DAILY[name])
            st["daily_mdd_net"] = nmdd
            st["daily_final_net"] = nfinal
            st["cost_ratio"] = ratio
        else:
            st["daily_mdd_gross"] = float("nan")
            st["daily_mdd_net"] = float("nan")
            st["daily_final_net"] = float("nan")
            st["cost_ratio"] = float("nan")
        rows.append(st)

    perf = pd.DataFrame(rows).set_index("group")
    cols = [
        "label",
        "n_periods",
        "ann_return",
        "ann_vol",
        "sharpe",
        "max_drawdown",
        "calmar",
        "avg_pos",
        "min_pos",
        "avg_turnover",
        "ann_cost",
        "daily_mdd_gross",
        "daily_mdd_net",
        "cost_ratio",
    ]
    perf = perf[cols]

    print("=" * 110)
    print("M5.1c 六组绩效（Sharpe 口径已对齐 engine.nav_stats）")
    print("=" * 110)
    print(perf.to_string(float_format=lambda x: f"{x:.4f}"))

    print("\n[sanity]")
    b = perf.loc["baseline"]
    f = perf.loc["full"]
    print(f"  baseline Sharpe = {b['sharpe']:.4f}  (期望 1.4611)")
    print(f"  full     Sharpe = {f['sharpe']:.4f}  (期望 1.5527)")
    print(f"  baseline 年化   = {b['ann_return']:.4f}  (期望 0.5369)")
    print(f"  full     年化   = {f['ann_return']:.4f}  (期望 0.4349)")

    # ---- 顺序增量 ----
    metrics = ["ann_return", "ann_vol", "sharpe", "max_drawdown", "calmar"]
    b = perf.loc["baseline"]
    p = perf.loc["m4a_m4b"]
    f = perf.loc["full"]
    attr = pd.DataFrame(index=metrics)
    attr["baseline"] = [b[m] for m in metrics]
    attr["+仓位管理"] = [p[m] - b[m] for m in metrics]
    attr["+因子轮动"] = [f[m] - p[m] for m in metrics]
    attr["full"] = [f[m] for m in metrics]
    attr["check"] = attr["baseline"] + attr["+仓位管理"] + attr["+因子轮动"]

    print("\n" + "=" * 110)
    print("M5.1c 顺序增量拆解（口径修正版）")
    print("=" * 110)
    print(attr.to_string(float_format=lambda x: f"{x:+.4f}"))

    # ---- 日频 gross vs net ----
    print("\n" + "=" * 110)
    print("日频 MDD：gross 口径 vs net 近似口径")
    print("=" * 110)
    for name in ["baseline", "full"]:
        r = perf.loc[name]
        print(
            f"  {name:<10}  gross_mdd={r['daily_mdd_gross']:.4f}  "
            f"net_mdd={r['daily_mdd_net']:.4f}  "
            f"差={r['daily_mdd_net'] - r['daily_mdd_gross']:+.4f}  "
            f"累计成本比={r['cost_ratio']:.4f}"
        )
    print("\n  说明：net 近似 = 在 gross 日频净值上，每期调仓日一次性扣成本；")
    print("        与 engine 的期频 net_ret 数学等价（终值差 ≈ 1e-15）。")

    perf.to_csv(PROC / "m5_1c_perf.csv")
    attr.to_csv(PROC / "m5_1c_attribution.csv")
    print(f"\n[落盘] {PROC / 'm5_1c_perf.csv'}")
    print(f"[落盘] {PROC / 'm5_1c_attribution.csv'}")
    print("[完成] M5.1c 结束。")


if __name__ == "__main__":
    main()
