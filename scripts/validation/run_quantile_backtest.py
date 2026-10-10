"""M3 smoke：对单因子做十分位分层回测，验证分层逻辑与出图流程。

为什么不用 alphalens 的 mean_return_by_quantile：
    前情提要记录 alphalens-reloaded 与本机 pandas 版本不兼容，
    mean_information_coefficient、plot_ic_ts 均已报错。
    分层收益本质是 qcut + groupby，自实现更透明可控。

处理 20 日持有期重叠的方式：
    每日计算 20 日 forward return，日化为 (1+r)^(1/20)-1 后累乘。
    数学上等价于"每天都调仓、持有 20 日、日频复利"，
    累乘 242 天 ≈ (1+r)^(242/20) ≈ 12 个周期的复利。

用法（项目根目录、激活 .venv 后）：
    python scripts/validation/run_quantile_backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# ---------- 路径处理：兼容两种运行方式 ----------
_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
_THIS_DIR = _THIS.parent
for _p in (str(_ROOT), str(_THIS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from scripts.validation.alphalens_io import (  # type: ignore
        load_factor_series,
        load_prices,
    )
except ImportError:
    from alphalens_io import load_factor_series, load_prices  # type: ignore

# ---------------- 配置 ----------------
PERIOD = 20  # 持有期（交易日）
N_QUANTILES = 10  # 分层数
SMOKE_FACTOR = "turnover"  # 先用这个因子验证
MIN_STOCKS_PER_DAY = 100  # 某日有效股票少于这个数就跳过该日

# 12 个通过初筛因子的方向：+1 表示因子值越大越好，-1 表示越小越好
FACTOR_DIRECTIONS = {
    "turnover": -1,
    "amplitude_20": -1,
    "volatility_20": -1,
    "amihud_20": +1,
    "bp": +1,
    "corr_pv_20": -1,
    "reversal_20": +1,
    "momentum_20": -1,
    "rsi_14": -1,
    "bias_20": -1,
    "ep_ttm": +1,
    "boll_dev_20": -1,
}

FIG_DIR = _ROOT / "docs" / "figures" / "stage2" / "quantile"
OUT_DIR = _ROOT / "data" / "processed"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# ---------------- 核心函数 ----------------
def compute_forward_returns(prices: pd.DataFrame, period: int) -> pd.DataFrame:
    """计算 forward return：第 t 日买入、第 t+period 日卖出的收益。"""
    return prices.shift(-period) / prices - 1.0


def daily_quantile_returns(
    factor_wide: pd.DataFrame,
    fwd_ret: pd.DataFrame,
    n_quantiles: int,
    min_stocks: int,
) -> pd.DataFrame:
    """逐日分层，返回 date × quantile 的平均 forward return。"""
    rows = []
    skipped = 0
    for dt in factor_wide.index:
        if dt not in fwd_ret.index:
            skipped += 1
            continue
        f = factor_wide.loc[dt]
        r = fwd_ret.loc[dt]
        valid = f.notna() & r.notna() & np.isfinite(f) & np.isfinite(r)
        if valid.sum() < min_stocks:
            skipped += 1
            continue
        f_valid = f[valid]
        r_valid = r[valid]
        try:
            q = pd.qcut(f_valid, n_quantiles, labels=False, duplicates="drop")
        except ValueError:
            skipped += 1
            continue
        if q.nunique() < n_quantiles:
            skipped += 1
            continue
        grp = r_valid.groupby(q).mean()
        grp.name = dt
        rows.append(grp)
    print(f"    有效交易日：{len(rows)}，跳过：{skipped}")
    return pd.DataFrame(rows)


def to_daily_nav(qret: pd.DataFrame, period: int) -> pd.DataFrame:
    """把 period 日 forward return 日化后累乘成净值。"""
    r = qret.clip(lower=-0.999)
    daily = (1.0 + r) ** (1.0 / period) - 1.0
    return (1.0 + daily).cumprod()


def nav_stats(nav: pd.DataFrame) -> pd.DataFrame:
    """基于净值序列计算年化收益、波动、夏普、最大回撤、日胜率。"""
    daily = nav.pct_change().dropna(how="all")
    years = len(daily) / 242.0
    ann_ret = nav.iloc[-1] ** (1.0 / years) - 1.0
    ann_vol = daily.std() * np.sqrt(242.0)
    sharpe = ann_ret / ann_vol
    running_max = nav.cummax()
    dd = nav / running_max - 1.0
    max_dd = dd.min()
    win = (daily > 0).mean()
    return pd.DataFrame(
        {
            "ann_return": ann_ret,
            "ann_vol": ann_vol,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win,
        }
    )


def plot_nav(
    nav: pd.DataFrame, benchmark: pd.Series, factor: str, out_path: Path
) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    cmap = plt.get_cmap("coolwarm")
    colors = [cmap(i / (N_QUANTILES - 1)) for i in range(N_QUANTILES)]
    for q in nav.columns:
        ax.plot(
            nav.index,
            nav[q],
            color=colors[int(q)],
            linewidth=1.3,
            label=f"Q{int(q) + 1}",
        )
    ax.plot(
        benchmark.index,
        benchmark.values,
        color="black",
        linewidth=1.8,
        linestyle="--",
        label="All (benchmark)",
    )
    ax.set_title(f"{factor}  |  {N_QUANTILES}-quantile NAV  (holding={PERIOD}D)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative NAV (log scale)")
    ax.set_yscale("log")
    ax.legend(ncol=2, fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"    图已保存：{out_path}")


# ---------------- 主流程 ----------------
def main() -> None:
    factor_name = SMOKE_FACTOR
    print(f"[M3 smoke] 因子：{factor_name}")

    print("  1) 加载价格矩阵 ...")
    prices = load_prices()
    print(f"     prices shape = {prices.shape}")

    print("  2) 加载因子序列 ...")
    factor = load_factor_series(factor_name)
    print(f"     factor 长度 = {len(factor)}，index.names = {factor.index.names}")

    sign = FACTOR_DIRECTIONS[factor_name]
    factor = factor * sign
    print(f"     方向调整：sign = {sign}（调整后因子值越大越好）")

    # 宽表对齐：factor_wide 与 fwd_ret 同形
    factor_wide = factor.unstack(level=-1)
    factor_wide = factor_wide.reindex(index=prices.index, columns=prices.columns)

    print(f"  3) 计算 {PERIOD} 日 forward return ...")
    fwd_ret = compute_forward_returns(prices, PERIOD)

    print("  4) 逐日分层 ...")
    qret = daily_quantile_returns(factor_wide, fwd_ret, N_QUANTILES, MIN_STOCKS_PER_DAY)
    print(f"     qret shape = {qret.shape}（应为 有效日 × {N_QUANTILES}）")
    print("     qret 前 3 行：")
    print(qret.head(3).round(5).to_string())

    # 基准：当日全市场等权 forward return（与分层日期对齐）
    bench_ret = fwd_ret.mean(axis=1).reindex(qret.index)
    bench_daily = (1.0 + bench_ret.clip(lower=-0.999)) ** (1.0 / PERIOD) - 1.0
    bench_nav = (1.0 + bench_daily).cumprod()

    print("  5) 合成净值 ...")
    nav = to_daily_nav(qret, PERIOD)

    print("\n  分层统计：")
    stats = nav_stats(nav)
    print(stats.round(4).to_string())

    long_col = nav.columns.max()
    long_nav = nav[long_col]
    excess = long_nav / bench_nav
    print(f"\n  Q{int(long_col) + 1} 多头净值终值 = {long_nav.iloc[-1]:.3f}")
    print(f"  基准净值终值         = {bench_nav.iloc[-1]:.3f}")
    print(f"  多头累计超额         = {excess.iloc[-1]:.3f}")

    print("  6) 出图 ...")
    plot_nav(nav, bench_nav, factor_name, FIG_DIR / f"{factor_name}_nav.png")

    out_qret = OUT_DIR / f"quantile_returns_{factor_name}.csv"
    qret.to_csv(out_qret)
    print(f"    分层收益已保存：{out_qret}")

    out_stats = OUT_DIR / f"quantile_stats_{factor_name}.csv"
    stats.to_csv(out_stats)
    print(f"    分层统计已保存：{out_stats}")

    print("\n[M3 smoke] 完成。")


if __name__ == "__main__":
    main()
