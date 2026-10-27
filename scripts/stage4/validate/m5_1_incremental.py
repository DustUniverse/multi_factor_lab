"""M5.1 增量分析：baseline vs M4a/M4b/M4c/合成 的绩效对比与增量拆解。

口径说明：
- m4b_only 为早期激进版（pos 下界 0，可清仓），仅作敏感性对照；
- m4a_m4b 为定稿温和版（pos 下界 0.70），作为“仓位管理增量”；
- 增量拆解：Δ_factor = m4c_only - baseline
            Δ_position = m4a_m4b - baseline
            interaction = full - m4c_only - m4a_m4b + baseline
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

matplotlib.use("Agg")
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

PROC = Path("data/processed")
FIG = Path("reports/figures")
FIG.mkdir(parents=True, exist_ok=True)

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
    "m4c_only": "M4c(v2,满仓)",
    "full": "Full(v2+M4a×b)",
}


def period_stats(df: pd.DataFrame, ppy: float = 12.0) -> dict:
    """基于 periods 的 net_ret 计算期频指标。"""
    r = df["net_ret"].astype(float)
    nav = (1.0 + r).cumprod()
    n = len(r)
    total = float(nav.iloc[-1] - 1.0)
    ann = float(nav.iloc[-1] ** (ppy / n) - 1.0)
    vol = float(r.std(ddof=1) * (ppy**0.5))
    sharpe = ann / vol if vol > 0 else float("nan")
    dd = nav / nav.cummax() - 1.0
    mdd = float(dd.min())
    calmar = ann / abs(mdd) if mdd < 0 else float("nan")
    pos = df["pos"].astype(float) if "pos" in df.columns else pd.Series([1.0])
    avg_pos = float(pos.mean())
    min_pos = float(pos.min())
    avg_to = float(df["turnover"].mean())
    ann_cost = float(df["cost"].sum() * ppy / n)
    return {
        "n_periods": n,
        "total_ret": total,
        "ann_return": ann,
        "ann_vol": vol,
        "sharpe": sharpe,
        "mdd_period": mdd,
        "calmar": calmar,
        "avg_pos": avg_pos,
        "min_pos": min_pos,
        "avg_turnover": avg_to,
        "ann_cost": ann_cost,
    }


def daily_mdd(fname: str) -> float:
    df = pd.read_parquet(PROC / fname)
    nav = df["nav"].astype(float)
    dd = nav / nav.cummax() - 1.0
    return float(dd.min())


def main() -> None:
    rows = []
    for name in ORDER:
        df = pd.read_csv(PROC / GROUPS[name])
        st = period_stats(df)
        st["group"] = name
        st["label"] = LABELS[name]
        st["daily_mdd"] = float("nan")
        if name in DAILY:
            st["daily_mdd"] = daily_mdd(DAILY[name])
        rows.append(st)

    perf = pd.DataFrame(rows).set_index("group")
    cols = [
        "label",
        "ann_return",
        "ann_vol",
        "sharpe",
        "mdd_period",
        "daily_mdd",
        "calmar",
        "avg_pos",
        "min_pos",
        "avg_turnover",
        "ann_cost",
    ]
    perf = perf[cols]

    print("=" * 100)
    print("M5.1 六组绩效对比")
    print("=" * 100)
    print(perf.to_string(float_format=lambda x: f"{x:.4f}"))

    print(
        "\n[sanity] baseline Sharpe vs 阶段三 1.4611: "
        f"{perf.loc['baseline', 'sharpe']:.4f}"
    )
    print(
        f"[sanity] full     Sharpe vs M4 定稿 1.5527: "
        f"{perf.loc['full', 'sharpe']:.4f}"
    )
    print(
        f"[sanity] m4b_only Sharpe vs 笔记 1.4755:   "
        f"{perf.loc['m4b_only', 'sharpe']:.4f}"
    )
    print("  （若 m4b_only 明显偏离 1.4755，说明该文件为早期激进版，仅作对照）")

    # 增量拆解（用 m4a_m4b 温和版作为仓位管理增量）
    metrics = ["ann_return", "sharpe", "mdd_period", "calmar", "ann_vol"]
    b = perf.loc["baseline"]
    f = perf.loc["full"]
    fac = perf.loc["m4c_only"]
    pos = perf.loc["m4a_m4b"]

    attr = pd.DataFrame(index=metrics)
    attr["baseline"] = [b[m] for m in metrics]
    attr["full"] = [f[m] for m in metrics]
    attr["d_total"] = [f[m] - b[m] for m in metrics]
    attr["d_factor_v2"] = [fac[m] - b[m] for m in metrics]
    attr["d_position_warm"] = [pos[m] - b[m] for m in metrics]
    attr["interaction"] = [
        attr.loc[m, "d_total"]
        - attr.loc[m, "d_factor_v2"]
        - attr.loc[m, "d_position_warm"]
        for m in metrics
    ]

    print("\n" + "=" * 100)
    print("M5.1 增量拆解（仓位用 M4a×M4b 温和版，m4b激进版不参与相加）")
    print("=" * 100)
    print(attr.to_string(float_format=lambda x: f"{x:+.4f}"))

    perf.to_csv(PROC / "m5_1_incremental.csv")
    attr.to_csv(PROC / "m5_1_attribution.csv")
    print(f"\n[落盘] {PROC / 'm5_1_incremental.csv'}")
    print(f"[落盘] {PROC / 'm5_1_attribution.csv'}")

    # ---- 图 ----
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    x = list(range(len(perf)))

    axes[0].bar(x, perf["sharpe"], color="steelblue")
    axes[0].axhline(1.4611, color="gray", ls="--", label="baseline 1.461")
    axes[0].axhline(1.680, color="red", ls="--", label="target 1.680")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(perf["label"], rotation=20, ha="right", fontsize=9)
    axes[0].set_ylabel("Sharpe")
    axes[0].set_title("M5.1 期频 Sharpe 对比")
    axes[0].legend(fontsize=8)

    w = 0.38
    axes[1].bar(
        [i - w / 2 for i in x],
        perf["mdd_period"],
        width=w,
        label="期频MDD",
        color="darkorange",
    )
    dm = perf["daily_mdd"]
    mask = dm.notna()
    axes[1].bar(
        [i + w / 2 for i, ok in zip(x, mask) if ok],
        dm[mask],
        width=w,
        label="日频MDD(仅baseline/full)",
        color="crimson",
    )
    axes[1].axhline(-0.25, color="red", ls="--", label="-25% 约束")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(perf["label"], rotation=20, ha="right", fontsize=9)
    axes[1].set_ylabel("MDD")
    axes[1].set_title("M5.1 MDD 对比")
    axes[1].legend(fontsize=8)

    fig.tight_layout()
    out = FIG / "m5_1_incremental.png"
    fig.savefig(out, dpi=150)
    print(f"[图] {out}")
    print("[完成] M5.1 增量分析结束。")


if __name__ == "__main__":
    main()
