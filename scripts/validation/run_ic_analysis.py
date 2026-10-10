"""M2: 批量对 18 个基础因子做 IC / IR / 胜率 / t 统计量分析。

对每个因子计算：
- Spearman Rank IC（逐日）
- IC 均值、IC 标准差、ICIR、IC 胜率
- t 统计量、双侧 p 值

输出：
- data/processed/factor_ic_summary.csv：因子 × 持有期的汇总表
- docs/figures/stage2/ic_ts/<factor>.png：每个因子的 IC 时序图

用法：
    python scripts/validation/run_ic_analysis.py
    python scripts/validation/run_ic_analysis.py --limit 2
    python scripts/validation/run_ic_analysis.py --factors momentum_20,reversal_20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

# 让脚本能 import 同目录的 alphalens_io
sys.path.insert(0, str(Path(__file__).resolve().parent))

from alphalens.performance import factor_information_coefficient  # noqa: E402
from alphalens.utils import get_clean_factor_and_forward_returns  # noqa: E402
from alphalens_io import (  # noqa: E402
    FACTOR_COLUMNS,
    FACTOR_PANEL_PATH,
    PROJECT_ROOT,
    load_prices,
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

PERIODS = (1, 5, 20)
QUANTILES = 10

FIG_DIR = PROJECT_ROOT / "docs" / "figures" / "stage2" / "ic_ts"
FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = PROJECT_ROOT / "data" / "processed" / "factor_ic_summary.csv"


def normalize_symbol(s: pd.Series) -> pd.Series:
    """000001.SZ -> 000001；000001 -> 000001。"""
    s = s.astype(str).str.strip().str.split(".").str[0]
    return s.str.zfill(6)


def load_factor_panel_subset(factors: list[str]) -> pd.DataFrame:
    """只读 symbol / date / 指定因子列，省内存。"""
    df = pd.read_parquet(
        FACTOR_PANEL_PATH,
        columns=["symbol", "date"] + factors,
    )
    df["symbol"] = normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def compute_ic_stats(ic: pd.DataFrame) -> pd.DataFrame:
    """ic: index=date, columns=period；返回每个 period 一行的汇总表。"""
    rows = []
    for period in ic.columns:
        s = ic[period].dropna()
        n = len(s)
        if n < 2:
            continue
        ic_mean = s.mean()
        ic_std = s.std()
        icir = ic_mean / ic_std if ic_std > 0 else np.nan
        ic_win = (s > 0).mean()
        t_stat = ic_mean / (ic_std / np.sqrt(n)) if ic_std > 0 else np.nan
        p_value = (
            2 * stats.t.sf(abs(t_stat), df=n - 1) if not np.isnan(t_stat) else np.nan
        )
        rows.append(
            {
                "period": period,
                "n_periods": n,
                "IC_mean": ic_mean,
                "IC_std": ic_std,
                "ICIR": icir,
                "IC_win": ic_win,
                "t_stat": t_stat,
                "p_value": p_value,
            }
        )
    return pd.DataFrame(rows)


def plot_ic(ic: pd.DataFrame, factor_name: str, out_path: Path) -> None:
    n = len(ic.columns)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4), sharey=True)
    if n == 1:
        axes = [axes]
    for ax, col in zip(axes, ic.columns):
        ax.bar(ic.index, ic[col], width=1.0, color="steelblue", alpha=0.7)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title(f"IC - {col}")
        ax.set_xlabel("date")
        ax.set_ylabel("IC")
    fig.suptitle(f"{factor_name} IC 时序")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--factors",
        type=str,
        default=None,
        help="逗号分隔的因子列表，默认全部 18 个",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只跑前 N 个因子（快速验证用）",
    )
    args = parser.parse_args()

    if args.factors:
        factors = [f.strip() for f in args.factors.split(",") if f.strip()]
    else:
        factors = list(FACTOR_COLUMNS)
    if args.limit:
        factors = factors[: args.limit]

    print(f"待分析因子（{len(factors)} 个）：{factors}")

    print("[1/3] 读取 prices ...")
    prices = load_prices()
    print(f"      prices: {prices.shape}")

    print("[2/3] 读取 factor_panel（只读需要的列）...")
    factor_df = load_factor_panel_subset(factors)
    print(f"      factor_df: {factor_df.shape}")

    print("[3/3] 逐个因子计算 IC ...")
    all_rows = []
    for i, factor_name in enumerate(factors, 1):
        print(f"  ({i}/{len(factors)}) {factor_name} ...")
        try:
            sub = factor_df[["date", "symbol", factor_name]]
            series = sub.set_index(["date", "symbol"])[factor_name].sort_index()
            series.name = factor_name
            # 补齐缺失日期：让 date level 覆盖完整 prices.index，
            # 避免 alphalens 因日期不连续而无法推断频率
            full_index = pd.MultiIndex.from_product(
                [prices.index, prices.columns],
                names=["date", "symbol"],
            )
            series = series.reindex(full_index)

            factor_data = get_clean_factor_and_forward_returns(
                factor=series,
                prices=prices,
                quantiles=QUANTILES,
                periods=PERIODS,
                max_loss=0.5,
            )
            ic = factor_information_coefficient(factor_data)
            stats_df = compute_ic_stats(ic)
            stats_df.insert(0, "factor", factor_name)
            all_rows.append(stats_df)

            fig_path = FIG_DIR / f"{factor_name}.png"
            plot_ic(ic, factor_name, fig_path)

            row20 = stats_df[stats_df["period"] == "20D"].iloc[0]
            print(
                f"      20D: IC_mean={row20['IC_mean']:.4f}, "
                f"ICIR={row20['ICIR']:.4f}, IC_win={row20['IC_win']:.3f}"
            )
        except Exception as e:  # noqa: BLE001
            print(f"      !! {factor_name} 失败：{type(e).__name__}: {e}")
            continue

    if not all_rows:
        print("没有任何因子成功，退出。")
        return

    summary = pd.concat(all_rows, ignore_index=True)
    summary = summary.sort_values(
        ["period", "IC_mean"], ascending=[True, False]
    ).reset_index(drop=True)
    summary.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n已保存汇总表：{OUT_CSV}")
    print(f"共 {summary['factor'].nunique()} 个因子，{len(summary)} 行。")

    # 打印 20D 排名，最直观
    print("\n=== 20D IC 排名（按 |IC_mean| 降序）===")
    sub = summary[summary["period"] == "20D"].copy()
    sub["abs_IC"] = sub["IC_mean"].abs()
    sub = sub.sort_values("abs_IC", ascending=False)
    cols = ["factor", "IC_mean", "ICIR", "IC_win", "t_stat", "p_value"]
    print(sub[cols].to_string(index=False))


if __name__ == "__main__":
    main()
