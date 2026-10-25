"""M3 图表：行业 MCTR / 因子 MCTR / 滚动波动 / MDD 区间净值。

产出（reports/figures/）：
- m3_mctr_industry.png     行业 MCTR 横向条形图（Top 15 + 其余合并）
- m3_mctr_factor.png       因子 MCTR 条形图（含 alpha，正负着色）
- m3_rolling_vol.png       滚动 60 日年化波动曲线
- m3_mdd_nav.png           净值 + 回撤子图，标注 Top 3 回撤区间
"""

import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")
FIG = os.path.join(ROOT, "reports", "figures")
os.makedirs(FIG, exist_ok=True)

IND_MCTR = os.path.join(PROC, "m3_mctr_industry.csv")
FAC_MCTR = os.path.join(PROC, "m3_factor_risk.csv")
NAV_FILE = os.path.join(PROC, "bt_nav_lasso_horizon_all8_daily.parquet")
DD_FILE = os.path.join(PROC, "m3_mdd_periods.csv")
ROLL_FILE = os.path.join(PROC, "m3_rolling_vol.csv")

TOP_IND = 15


def fig_industry():
    df = pd.read_csv(IND_MCTR, index_col=0)
    df = df.sort_values("mctr_ann", ascending=True)
    top = df.tail(TOP_IND).copy()
    rest = df.head(len(df) - TOP_IND)
    if len(rest) > 0:
        merged = pd.DataFrame(
            {
                "mctr_ann": [rest["mctr_ann"].sum()],
                "mctr_pct": [rest["mctr_pct"].sum()],
            },
            index=[f"其余 {len(rest)} 个行业"],
        )
        top = pd.concat([merged, top])

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["#d62728" if v < 0 else "#1f77b4" for v in top["mctr_ann"]]
    ax.barh(top.index, top["mctr_ann"] * 100, color=colors)
    for i, (v, pct) in enumerate(zip(top["mctr_ann"], top["mctr_pct"])):
        ax.text(
            v * 100 + (0.05 if v >= 0 else -0.05),
            i,
            f"{v * 100:.2f}% ({pct * 100:.1f}%)",
            va="center",
            ha="left" if v >= 0 else "right",
            fontsize=8,
        )
    ax.axvline(0, color="black", lw=0.5)
    ax.margins(x=0.15)  # 右侧多留 15% 空间，防止“其余 17 个行业”数值超出
    ax.set_xlim(left=0)  # 行业 MCTR 全为正，强制 x 轴从 0 开始，更美观
    ax.set_xlabel("年化 MCTR（%）")
    ax.set_title(f"行业风险贡献 MCTR（Top {TOP_IND} + 其余合并，Σ = 年化波动）")
    plt.tight_layout()
    out = os.path.join(FIG, "m3_mctr_industry.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  saved: {out}")


def fig_factor():
    df = pd.read_csv(FAC_MCTR, index_col=0)
    alpha_pct = float(df.loc["alpha", "mctr_pct"]) if "alpha" in df.index else 0.0
    df = df.drop(index="alpha", errors="ignore")  # 剔除 alpha，只画 8 因子
    df = df.sort_values("mctr_pct", ascending=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = ["#d62728" if v < 0 else "#1f77b4" for v in df["mctr_pct"]]
    ax.barh(df.index, df["mctr_pct"] * 100, color=colors)
    for i, v in enumerate(df["mctr_pct"] * 100):
        ax.text(
            v + (0.05 if v >= 0 else -0.05),
            i,
            f"{v:+.2f}%",
            va="center",
            ha="left" if v >= 0 else "right",
            fontsize=9,
        )
    ax.axvline(0, color="black", lw=0.5)
    ax.margins(x=0.15)  # 左右两侧各多留 15% 空间，防止 amihud 负值遮挡 y 轴标签
    ax.set_xlabel("波动占比 MCTR_pct（%）")
    ax.set_title(
        f"8 因子波动 MCTR（51 期月频；alpha 因子外波动占比 {alpha_pct * 100:.1f}%，未显示）"
    )
    plt.tight_layout()
    out = os.path.join(FIG, "m3_mctr_factor.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  saved: {out}")


def fig_rolling():
    roll = pd.read_csv(ROLL_FILE, index_col=0, parse_dates=True)
    s = roll["vol_ann_60d"] * 100
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(s.index, s.values, color="#1f77b4", lw=1.0)
    ax.axhline(s.mean(), color="gray", ls="--", lw=0.8, label=f"均值 {s.mean():.1f}%")
    peak_idx = s.idxmax()
    ax.scatter([peak_idx], [s.max()], color="#d62728", zorder=5)
    ax.annotate(
        f"峰值 {s.max():.1f}%\n{peak_idx.date()}",
        xy=(peak_idx, s.max()),
        xytext=(10, -25),
        textcoords="offset points",
        fontsize=8,
        color="#d62728",
        arrowprops=dict(arrowstyle="->", color="#d62728", lw=0.6),
    )
    ax.set_ylabel("年化波动（%）")
    ax.set_title("滚动 60 日年化波动（日频）")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    out = os.path.join(FIG, "m3_rolling_vol.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  saved: {out}")


def fig_mdd():
    nav_df = pd.read_parquet(NAV_FILE)
    nav = nav_df["nav"]
    dd = nav / nav.cummax() - 1.0

    periods = pd.read_csv(DD_FILE, parse_dates=["peak", "trough", "recovery"])

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6.5), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
    )
    ax1.plot(nav.index, nav.values, color="#1f77b4", lw=1.2)
    ax1.set_ylabel("净值")
    ax1.set_title("lasso_horizon_all8 日频净值与回撤（标注 Top 3 回撤区间）")
    ax1.grid(alpha=0.3)

    ax2.fill_between(dd.index, dd.values * 100, 0, color="#d62728", alpha=0.4)
    ax2.set_ylabel("回撤（%）")
    ax2.set_xlabel("日期")
    ax2.grid(alpha=0.3)

    top3 = periods.sort_values("depth").head(3)
    colors = ["#8c564b", "#e377c2", "#17becf"]
    for (_, row), c in zip(top3.iterrows(), colors):
        peak, trough, depth = row["peak"], row["trough"], row["depth"]
        ax1.axvspan(peak, trough, color=c, alpha=0.15)
        ax2.axvspan(peak, trough, color=c, alpha=0.15)
        mid = peak + (trough - peak) / 2
        ax1.annotate(
            f"{depth * 100:.1f}%",
            xy=(mid, nav.loc[trough]),
            xytext=(0, -18),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=c,
            fontweight="bold",
        )

    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    plt.tight_layout()
    out = os.path.join(FIG, "m3_mdd_nav.png")
    plt.savefig(out, dpi=150)
    plt.close()
    print(f"  saved: {out}")


def main():
    print("[M3 figures] 生成 4 张图...")
    fig_industry()
    fig_factor()
    fig_rolling()
    fig_mdd()
    print("  完成")


if __name__ == "__main__":
    main()
