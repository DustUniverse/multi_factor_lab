"""M5b: 6 组合成策略回测 + 沪深 300 对照。

对 6 组（3 加权 × 2 因子集）合成分数，用同一引擎跑 top_n=50 月频回测，
与沪深 300 对比，输出绩效汇总表与净值曲线。

用法（项目根目录、激活 .venv 后）：
    python scripts/backtest/run_composite_backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_THIS.parent))

from engine import nav_stats, run_backtest  # noqa: E402

PROCESSED = _ROOT / "data" / "processed"
FIG_DIR = _ROOT / "docs" / "figures" / "stage3"
FIG_DIR.mkdir(parents=True, exist_ok=True)

PRICE_PATH = PROCESSED / "daily_panel_tencent_clean.parquet"
BENCH_PATH = PROCESSED / "hs300_benchmark.parquet"
CAL_PATH = PROCESSED / "rebalance_calendar.csv"

GROUPS = [
    ("ic_all8", "IC加权 · 8因子"),
    ("ir_all8", "IR加权 · 8因子"),
    ("equal_all8", "等权 · 8因子"),
    ("ic_no_vol", "IC加权 · 剔vol"),
    ("ir_no_vol", "IR加权 · 剔vol"),
    ("equal_no_vol", "等权 · 剔vol"),
    ("lasso_all8", "Lasso · 8因子"),
    ("lasso_no_vol", "Lasso · 剔vol"),
]

TOP_N = 50
BUFFER_N = 0
SMOOTH_N = 3  # 信号平滑：用过去 3 期合成分数的均值
PRICE_COLS = ["symbol", "date", "open", "close", "is_limit_up", "is_suspended"]


def normalize_symbol(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.split(".").str[0]
    return s.str.zfill(6)


def load_prices() -> pd.DataFrame:
    df = pd.read_parquet(PRICE_PATH, columns=PRICE_COLS)
    df["symbol"] = normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_calendar() -> pd.DataFrame:
    return pd.read_csv(CAL_PATH, parse_dates=["signal_date", "trade_date"])


def load_scores(tag: str) -> pd.DataFrame:
    p = PROCESSED / f"composite_scores_{tag}.parquet"
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index)
    return df


def load_benchmark_monthly(cal: pd.DataFrame) -> pd.Series:
    """沪深300 月频 open-to-open 收益（index=trade_date）。"""
    b = pd.read_parquet(BENCH_PATH)
    b["trade_date"] = pd.to_datetime(b["trade_date"])
    b = b.set_index("trade_date")["open"]

    rows = []
    for i in range(len(cal) - 1):
        t0 = cal.iloc[i]["trade_date"]
        t1 = cal.iloc[i + 1]["trade_date"]
        p0 = b.get(t0, pd.NA)
        p1 = b.get(t1, pd.NA)
        if pd.notna(p0) and pd.notna(p1):
            rows.append({"trade_date": t0, "ret": p1 / p0 - 1.0})
    s = pd.DataFrame(rows).set_index("trade_date")["ret"]
    s.index = pd.to_datetime(s.index)
    return s


def plot_navs(navs: dict[str, pd.Series], bench_nav: pd.Series) -> Path:
    fig, ax = plt.subplots(figsize=(11, 6))
    for label, nav in navs.items():
        ax.plot(nav.index, nav.values, label=label, linewidth=1.4)
    ax.plot(
        bench_nav.index,
        bench_nav.values,
        label="沪深300",
        linestyle="--",
        color="black",
        linewidth=1.6,
    )
    ax.set_title("阶段三：6 组合成策略 净值对比（top_n=50, 月频）")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative NAV")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    out = FIG_DIR / "composite_navs.png"
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def main() -> None:
    print("[M5b] 6 组合成策略回测 ...")
    cal = load_calendar()
    print(f"  调仓点数: {len(cal)}")

    prices = load_prices()
    print(f"  价格面板: {prices.shape}")

    # 基准
    bench_ret = load_benchmark_monthly(cal)
    bench_nav = (1.0 + bench_ret).cumprod()
    bench_nav.name = "hs300"
    print(f"  基准月频: {len(bench_ret)} 期, 终值 {bench_nav.iloc[-1]:.4f}")

    summary_rows = []
    navs = {}

    for tag, label in GROUPS:
        scores = load_scores(tag)
        scores_smooth = scores.rolling(SMOOTH_N, min_periods=1).mean()
        result = run_backtest(
            scores_smooth, cal, prices, top_n=TOP_N, buffer_n=BUFFER_N
        )
        periods = result["periods"]
        nav = result["nav"]
        if nav.empty:
            print(f"  [{tag}] 无结果，跳过")
            continue

        st = nav_stats(nav, periods_per_year=12.0)
        # 超额（几何）
        bench_aligned = bench_nav.reindex(nav.index).ffill()
        excess_cum = nav.iloc[-1] / bench_aligned.iloc[-1] - 1.0
        # 超额年化 ≈ 策略年化 - 基准年化
        n = len(nav)
        years = n / 12.0
        bench_ann = bench_aligned.iloc[-1] ** (1.0 / years) - 1.0

        row = {
            "tag": tag,
            "label": label,
            "n_periods": st["n_periods"],
            "ann_return": st["ann_return"],
            "ann_vol": st["ann_vol"],
            "sharpe": st["sharpe"],
            "max_drawdown": st["max_drawdown"],
            "calmar": st["calmar"],
            "win_rate": st["win_rate"],
            "pnl_ratio": st["pnl_ratio"],
            "avg_turnover": periods["turnover"].mean(),
            "bench_ann": bench_ann,
            "excess_ann": st["ann_return"] - bench_ann,
            "excess_cum": excess_cum,
            "nav_final": nav.iloc[-1],
        }
        summary_rows.append(row)
        navs[label] = nav
        print(
            f"  [{tag:14s}] ann {st['ann_return']:+.2%}  "
            f"Sharpe {st['sharpe']:.3f}  MDD {st['max_drawdown']:.2%}  "
            f"超额 {row['excess_ann']:+.2%}"
        )

        # 落盘 periods
        periods.to_csv(PROCESSED / f"composite_bt_{tag}.csv", index=False)

    # 汇总
    summary = pd.DataFrame(summary_rows)
    summary_path = PROCESSED / "composite_bt_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\n  汇总表保存: {summary_path}")

    # 基准年化
    n_bench = len(bench_ret)
    bench_ann_full = bench_nav.iloc[-1] ** (12.0 / n_bench) - 1.0
    print(f"\n  沪深300 年化: {bench_ann_full:+.2%}, 终值 {bench_nav.iloc[-1]:.4f}")

    # 出图
    fig_path = plot_navs(navs, bench_nav)
    print(f"  净值曲线保存: {fig_path}")

    # 打印完整表
    print("\n  === 6 组完整绩效 ===")
    cols = [
        "label",
        "ann_return",
        "ann_vol",
        "sharpe",
        "max_drawdown",
        "calmar",
        "win_rate",
        "pnl_ratio",
        "avg_turnover",
        "excess_ann",
    ]
    print(summary[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
