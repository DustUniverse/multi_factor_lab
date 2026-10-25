"""M1 Brinson 归因图表。

输出到 reports/figures/：
- brinson_cum_A_S_I.png        累计 A/S/I 曲线
- brinson_yearly_bar.png       分年度 A/S/I 柱状
- brinson_industry_A.png       行业配置贡献 Top/Bottom

运行：
    python scripts/stage4/report/make_brinson_figures.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROCESSED = Path("data/processed")
FIG = Path("reports/figures")
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

GROUP = "lasso_horizon_all8"


def main():
    detail = pd.read_csv(PROCESSED / f"brinson_detail_{GROUP}.csv")
    detail["trade_date"] = pd.to_datetime(detail["trade_date"])

    # 1. 累计 A/S/I 曲线
    per_period = detail.groupby("trade_date")[["A", "S", "I"]].sum().sort_index()
    cum = per_period.cumsum()

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(cum.index, cum["A"], label="配置 A", color="tab:blue")
    ax.plot(cum.index, cum["S"], label="选择 S", color="tab:green")
    ax.plot(cum.index, cum["I"], label="交互 I", color="tab:orange")
    ax.axhline(0, color="gray", lw=0.8, ls="--")
    ax.set_title(f"Brinson 累计收益分解（{GROUP}）")
    ax.set_ylabel("累计贡献（逐期算术和）")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "brinson_cum_A_S_I.png", dpi=150)
    plt.close(fig)

    # 2. 分年度柱状
    detail["year"] = detail["trade_date"].dt.year
    yearly = detail.groupby("year")[["A", "S", "I"]].sum()
    fig, ax = plt.subplots(figsize=(10, 5))
    yearly.plot(kind="bar", ax=ax, color=["tab:blue", "tab:green", "tab:orange"])
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_title("分年度 Brinson 分解")
    ax.set_ylabel("贡献（逐期算术和）")
    ax.legend(["配置 A", "选择 S", "交互 I"])
    fig.tight_layout()
    fig.savefig(FIG / "brinson_yearly_bar.png", dpi=150)
    plt.close(fig)

    # 3. 行业配置贡献 Top/Bottom
    by_ind = detail.groupby("industry")["A"].sum().sort_values()
    sel = pd.concat([by_ind.head(6), by_ind.tail(6)])

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["tab:red" if v < 0 else "tab:green" for v in sel.values]
    ax.barh(sel.index, sel.values, color=colors)
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_title("行业配置贡献 A：Top6 / Bottom6")
    ax.set_xlabel("累计 A（逐期算术和）")
    fig.tight_layout()
    fig.savefig(FIG / "brinson_industry_A.png", dpi=150)
    plt.close(fig)

    print(f"[OK] 3 张图 -> {FIG}")
    print("yearly:\n", yearly.round(4).to_string())


if __name__ == "__main__":
    main()
