"""M5.1b 修正版：顺序增量拆解 + sanity 诊断。

背景：m4c_bt_periods 已是 v2 scores + 仓位管理的结果（与 full 逐行一致），
      正交拆解失效，改为"叠加顺序"拆解：
      Step 0: baseline (v1 满仓)
      Step 1: baseline -> m4a_m4b = 仓位管理增量
      Step 2: m4a_m4b  -> full    = 因子轮动增量（在仓位之上叠加 v2 scores）
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
    "m4c_only": "M4c(实为v2+仓位)",
    "full": "Full(v2+仓位)",
}


def period_stats(df: pd.DataFrame, ppy: float = 12.0) -> dict:
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
    return {
        "n_periods": n,
        "total_ret": total,
        "ann_return": ann,
        "ann_vol": vol,
        "sharpe": sharpe,
        "mdd_period": mdd,
        "calmar": calmar,
        "avg_pos": float(pos.mean()),
        "min_pos": float(pos.min()),
        "avg_turnover": float(df["turnover"].mean()),
        "ann_cost": float(df["cost"].sum() * ppy / n),
    }


def daily_mdd(fname: str) -> float:
    df = pd.read_parquet(PROC / fname)
    nav = df["nav"].astype(float)
    dd = nav / nav.cummax() - 1.0
    return float(dd.min())


def diff_two_periods(a_name: str, b_name: str) -> None:
    print("=" * 80)
    print(f"[诊断1] {a_name} vs {b_name} 逐列对比")
    print("=" * 80)
    a = pd.read_csv(PROC / GROUPS[a_name])
    b = pd.read_csv(PROC / GROUPS[b_name])
    if len(a) != len(b):
        print(f"  行数不同: {len(a)} vs {len(b)}")
        return
    for c in a.columns:
        if c not in b.columns:
            print(f"  {c}: 只在 {a_name}")
            continue
        if a[c].dtype == object:
            md = (a[c].astype(str) != b[c].astype(str)).sum()
            print(f"  {c:<16} 不一致行数={md}")
        else:
            md = float((a[c] - b[c]).abs().max())
            print(f"  {c:<16} max_abs_diff={md:.6e}")


def reconcile_nav() -> None:
    print("\n" + "=" * 80)
    print("[诊断2] periods 复利 vs 日频净值 对账")
    print("=" * 80)
    for name in ["baseline", "full"]:
        per = pd.read_csv(PROC / GROUPS[name])
        nav_per = (1.0 + per["net_ret"]).cumprod()
        daily = pd.read_parquet(PROC / DAILY[name])["nav"]
        print(f"  {name}:")
        print(f"    periods final_nav = {nav_per.iloc[-1]:.6f}  (n={len(per)})")
        print(f"    daily   final_nav = {daily.iloc[-1]:.6f}  (n={len(daily)})")
        print(f"    终值差 = {abs(nav_per.iloc[-1] - daily.iloc[-1]):.3e}")

    print("\n  说明：若终值差 < 1e-10 但 Sharpe 与笔记不符，")
    print("       则差异来自 nav_stats 的年化口径（如算术 vs 几何），非数据问题。")


def main() -> None:
    rows = []
    for name in ORDER:
        df = pd.read_csv(PROC / GROUPS[name])
        st = period_stats(df)
        st["group"] = name
        st["label"] = LABELS[name]
        st["daily_mdd"] = daily_mdd(DAILY[name]) if name in DAILY else float("nan")
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
    print("M5.1b 六组绩效对比（顺序增量版）")
    print("=" * 100)
    print(perf.to_string(float_format=lambda x: f"{x:.4f}"))

    # ---- 顺序增量拆解 ----
    metrics = ["ann_return", "ann_vol", "sharpe", "mdd_period", "calmar"]
    b = perf.loc["baseline"]
    p = perf.loc["m4a_m4b"]
    f = perf.loc["full"]

    attr = pd.DataFrame(index=metrics)
    attr["baseline"] = [b[m] for m in metrics]
    attr["+仓位管理"] = [p[m] - b[m] for m in metrics]
    attr["+因子轮动"] = [f[m] - p[m] for m in metrics]
    attr["full"] = [f[m] for m in metrics]
    attr["check_sum"] = attr["baseline"] + attr["+仓位管理"] + attr["+因子轮动"]

    print("\n" + "=" * 100)
    print("M5.1b 顺序增量拆解")
    print("=" * 100)
    print(attr.to_string(float_format=lambda x: f"{x:+.4f}"))
    print("\n  说明：Step1 = m4a_m4b - baseline（仓位管理，v1 scores 下）")
    print("        Step2 = full - m4a_m4b（因子轮动，在仓位之上叠加 v2 scores）")
    print("        两步骤按回测实际叠加顺序拆解，未做正交分离；")
    print("        交互项不可分离，报告如实说明。")

    perf.to_csv(PROC / "m5_1b_incremental.csv")
    attr.to_csv(PROC / "m5_1b_attribution.csv")
    print(f"\n[落盘] {PROC / 'm5_1b_incremental.csv'}")
    print(f"[落盘] {PROC / 'm5_1b_attribution.csv'}")

    # ---- 诊断 ----
    diff_two_periods("m4c_only", "full")
    reconcile_nav()

    # ---- 图 ----
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    x = list(range(len(perf)))

    axes[0].bar(x, perf["sharpe"], color="steelblue")
    axes[0].axhline(1.4611, color="gray", ls="--", label="阶段三 1.461")
    axes[0].axhline(1.680, color="red", ls="--", label="target 1.680")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(perf["label"], rotation=20, ha="right", fontsize=9)
    axes[0].set_ylabel("Sharpe")
    axes[0].set_title("M5.1b 六组期频 Sharpe")
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
    xs = [x[i] for i in range(len(x)) if mask.iloc[i]]
    axes[1].bar(
        [i + w / 2 for i in xs],
        dm[mask],
        width=w,
        label="日频MDD(仅baseline/full)",
        color="crimson",
    )
    axes[1].axhline(-0.25, color="red", ls="--", label="-25% 约束")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(perf["label"], rotation=20, ha="right", fontsize=9)
    axes[1].set_ylabel("MDD")
    axes[1].set_title("M5.1b MDD 对比")
    axes[1].legend(fontsize=8)

    fig.tight_layout()
    out = FIG / "m5_1b_incremental.png"
    fig.savefig(out, dpi=150)
    print(f"[图] {out}")
    print("[完成] M5.1b 结束。")


if __name__ == "__main__":
    main()
