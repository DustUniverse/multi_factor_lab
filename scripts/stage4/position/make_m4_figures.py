"""M4 三张图：期频净值对比、仓位时序、2024 日频放大。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from scripts.backtest.run_composite_backtest import (  # noqa: E402
    load_benchmark_monthly,
    load_calendar,
)

PROC = Path("data/processed")
FIG = Path("reports/figures")
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def fig1_nav_compare() -> None:
    """期频净值：基线 vs M4 最终 vs 沪深300。"""
    bt = (
        pd.read_csv(
            PROC / "composite_bt_lasso_horizon_all8.csv",
            parse_dates=["trade_date"],
        )
        .sort_values("trade_date")
        .set_index("trade_date")
    )
    base_nav = (1 + bt["net_ret"]).cumprod()

    m4_nav = pd.read_parquet(PROC / "m4_final_nav.parquet")["nav"]
    m4_nav.index = pd.to_datetime(m4_nav.index)

    cal = load_calendar()
    bench_ret = load_benchmark_monthly(cal)
    bench_nav = (1 + bench_ret).cumprod()

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(
        base_nav.index,
        base_nav.values,
        label="基线 lasso_horizon_all8",
        linewidth=1.4,
        color="#888888",
    )
    ax.plot(
        m4_nav.index,
        m4_nav.values,
        label="M4 最终（v2 + M4a×M4b）",
        linewidth=1.8,
        color="#c0392b",
    )
    ax.plot(
        bench_nav.index,
        bench_nav.values,
        label="沪深300",
        linewidth=1.2,
        color="#2980b9",
        linestyle="--",
    )
    ax.set_title("M4 期频净值对比（top_n=50，含交易成本）")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative NAV")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10)
    out = FIG / "m4_nav_compare.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  → {out}")


def fig2_position() -> None:
    """仓位时序：pos_m4a / pos_m4b / pos_final。"""
    m4a = pd.read_parquet(PROC / "m4a_position_series.parquet")["pos"]
    m4a.index = pd.to_datetime(m4a.index)
    m4b = pd.read_parquet(PROC / "m4b_pos_m4b_only.parquet")["pos_m4b"]
    m4b.index = pd.to_datetime(m4b.index)
    final = pd.read_parquet(PROC / "m4_position_series.parquet")["pos"]
    final.index = pd.to_datetime(final.index)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(
        m4a.index,
        m4a.values,
        label="pos_m4a（波动率目标）",
        linewidth=1.2,
        color="#3498db",
        alpha=0.8,
    )
    ax.plot(
        m4b.index,
        m4b.values,
        label="pos_m4b（回撤止损）",
        linewidth=1.2,
        color="#e67e22",
        alpha=0.8,
    )
    ax.plot(
        final.index,
        final.values,
        label="pos_final = min(m4a, m4b)",
        linewidth=2.0,
        color="#c0392b",
    )
    ax.set_title("M4 仓位时序")
    ax.set_xlabel("Trade Date")
    ax.set_ylabel("Position")
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10)
    out = FIG / "m4_position_ts.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  → {out}")


def fig3_2024_zoom() -> None:
    """2024 日频净值放大：基线 vs M4，标谷底。"""
    base_d = pd.read_parquet(PROC / "bt_nav_lasso_horizon_all8_daily.parquet")["nav"]
    base_d.index = pd.to_datetime(base_d.index)
    m4_d = pd.read_parquet(PROC / "bt_nav_m4_final_daily.parquet")["nav"]
    m4_d.index = pd.to_datetime(m4_d.index)

    mask_b = base_d.index >= "2023-11-01"
    mask_m = m4_d.index >= "2023-11-01"

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(
        base_d.index[mask_b],
        base_d.values[mask_b],
        label="基线日频（满仓，gross）",
        linewidth=1.2,
        color="#888888",
    )
    ax.plot(
        m4_d.index[mask_m],
        m4_d.values[mask_m],
        label="M4 日频（pos 缩放，gross）",
        linewidth=1.8,
        color="#c0392b",
    )

    trough = pd.Timestamp("2024-02-05")
    if trough in base_d.index:
        ax.axvline(trough, color="black", linestyle=":", alpha=0.5)
        ax.annotate(
            "2024-02-05\n基线日频 MDD -36.32%\nM4 日频 MDD -27.56%",
            xy=(trough, base_d.loc[trough]),
            xytext=(trough, base_d.loc[trough] * 1.15),
            fontsize=9,
            ha="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
        )
    ax.set_title("2024 年日频净值放大（gross 口径，未扣成本）")
    ax.set_xlabel("Date")
    ax.set_ylabel("NAV")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10)
    out = FIG / "m4_2024_zoom.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  → {out}")


def main() -> None:
    print("[M4 图表] ...")
    fig1_nav_compare()
    fig2_position()
    fig3_2024_zoom()
    print("全部完成。")


if __name__ == "__main__":
    main()
