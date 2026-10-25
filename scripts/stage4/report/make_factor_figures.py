"""M2 因子归因图表。

输出到 reports/figures/：
- factor_contrib_bar.png       8 因子累计贡献条形
- factor_contrib_yearly.png    分年度因子贡献堆叠

运行：
    python scripts/stage4/report/make_factor_figures.py
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
    fa = pd.read_csv(PROCESSED / f"factor_attr_{GROUP}.csv")
    fa["trade_date"] = pd.to_datetime(fa["trade_date"])
    fa["year"] = fa["trade_date"].dt.year

    total = fa.groupby("factor")["contrib"].sum().sort_values()
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["tab:red" if v < 0 else "tab:green" for v in total.values]
    ax.barh(total.index, total.values, color=colors)
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_title("8 因子累计贡献（Σ expo × β）")
    ax.set_xlabel("累计贡献（逐期算术和）")
    fig.tight_layout()
    fig.savefig(FIG / "factor_contrib_bar.png", dpi=150)
    plt.close(fig)

    yearly = fa.pivot_table(
        index="year", columns="factor", values="contrib", aggfunc="sum"
    ).fillna(0.0)
    fig, ax = plt.subplots(figsize=(11, 5))
    yearly.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_title("分年度因子贡献（堆叠）")
    ax.set_ylabel("贡献（逐期算术和）")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "factor_contrib_yearly.png", dpi=150)
    plt.close(fig)

    print(f"[OK] 2 张图 -> {FIG}")
    print("分年度因子贡献:\n", yearly.round(3).to_string())


if __name__ == "__main__":
    main()
