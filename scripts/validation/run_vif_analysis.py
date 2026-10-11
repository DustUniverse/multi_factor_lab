"""M5: VIF 共线性检验（逐日横截面）。

对 12 个中性化因子，每个交易日做横截面回归：
    f_i = a + sum_j (b_j * f_j) + e   (j != i)
    VIF_i = 1 / (1 - R^2)

再对 1213 天取均值 / 中位数 / P90 / 最大值。

用法（在已激活 .venv 的 PowerShell 里）：
    python scripts/validation/run_vif_analysis.py --smoke   # 只跑前 5 天
    python scripts/validation/run_vif_analysis.py           # 全量 1213 天
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

NEUTRALIZED_PATH = DATA_PROCESSED / "factor_panel_neutralized.parquet"
VIF_SUMMARY_PATH = DATA_PROCESSED / "vif_summary.csv"

# 每日至少多少只有效股票才计算 VIF
MIN_STOCKS_PER_DAY = 100

# VIF 达到 1e12 视为完全共线（如镜像对），截断为 inf
VIF_INF_CUTOFF = 1e12


def load_neutralized_panel() -> pd.DataFrame:
    """读入中性化面板，兼容 MultiIndex / 列存储两种格式。"""
    df = pd.read_parquet(NEUTRALIZED_PATH)

    if not isinstance(df.index, pd.MultiIndex):
        # 兼容 date/symbol 存为列的格式
        if "date" in df.columns and "symbol" in df.columns:
            df = df.set_index(["date", "symbol"])
        else:
            raise ValueError(
                "无法识别面板索引，既不是 MultiIndex 也没有 date/symbol 列。"
            )

    df = df.sort_index()
    return df


def vif_one_day(cross: pd.DataFrame) -> dict[str, float]:
    """对单个交易日截面，返回 {factor: VIF}。

    cross: index = symbol, columns = factor（已 dropna）
    """
    factors = list(cross.columns)
    n = len(cross)
    out: dict[str, float] = {}

    # 预先把整块数据转成 numpy，供每次回归复用
    arr = cross.to_numpy(dtype=float)
    col_idx = {f: i for i, f in enumerate(factors)}

    for f in factors:
        i = col_idx[f]
        y = arr[:, i]
        others_idx = [col_idx[g] for g in factors if g != f]
        X = arr[:, others_idx]

        # 加截距项
        X = np.column_stack([np.ones(n), X])

        # lstsq 对秩亏稳健
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        y_hat = X @ coef

        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))

        if ss_tot <= 0:
            out[f] = np.nan
            continue

        r2 = 1.0 - ss_res / ss_tot
        # 数值噪声修正
        r2 = min(max(r2, 0.0), 1.0 - 1e-15)

        vif = 1.0 / (1.0 - r2)
        if vif >= VIF_INF_CUTOFF:
            vif = np.inf
        out[f] = vif

    return out


def run_vif(panel: pd.DataFrame, max_valid_days: int | None = None) -> pd.DataFrame:
    """逐日计算 VIF。

    max_valid_days: 仅用于 smoke，收集够这么多"有效日"后就停止扫描。
                    有效日 = 该日 dropna 后股票数 >= MIN_STOCKS_PER_DAY。

    返回 DataFrame: index = 交易日, columns = 因子。
    """
    all_dates = panel.index.get_level_values(0).unique().sort_values()

    records = []
    used_dates = []
    skipped = 0
    scanned = 0

    for d in all_dates:
        scanned += 1
        cross = panel.xs(d, level=0)
        cross = cross.dropna(how="any")
        if len(cross) < MIN_STOCKS_PER_DAY:
            skipped += 1
            continue
        records.append(vif_one_day(cross))
        used_dates.append(d)
        if max_valid_days is not None and len(records) >= max_valid_days:
            break

    if not records:
        raise RuntimeError(
            f"扫描了 {scanned} 天仍无有效交易日；"
            f"检查 MIN_STOCKS_PER_DAY={MIN_STOCKS_PER_DAY} 是否过高，或数据是否为空。"
        )

    print(
        f"扫描 {scanned} 天，跳过 {skipped} 天（有效股票不足），"
        f"实际计算 {len(records)} 天"
    )
    print(f"使用日期范围: {used_dates[0]} ~ {used_dates[-1]}")

    vif_df = pd.DataFrame(records, index=pd.Index(used_dates, name="date"))
    return vif_df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="只跑前 5 个交易日，用于快速验证逻辑",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="",
        help="逗号分隔的因子名，在计算 VIF 前先剔除（例如 momentum_20）",
    )
    args = parser.parse_args()

    panel = load_neutralized_panel()
    exclude = [x.strip() for x in args.exclude.split(",") if x.strip()]
    if exclude:
        missing = [c for c in exclude if c not in panel.columns]
        if missing:
            raise ValueError(f"--exclude 中有不存在的列: {missing}")
        panel = panel.drop(columns=exclude)
    print("=== 面板基本信息 ===")
    print(f"shape        : {panel.shape}")
    print(f"index 类型   : {type(panel.index).__name__}")
    print(f"因子列       : {list(panel.columns)}")
    if exclude:
        print(f"已剔除列     : {exclude}")
    dates = panel.index.get_level_values(0).unique()
    print(f"交易日数     : {len(dates)}")
    print(f"日期范围     : {dates.min()} ~ {dates.max()}")

    if args.smoke:
        vif_df = run_vif(panel, max_valid_days=5)
        print("\n=== smoke: 前 5 日 VIF ===")
        with pd.option_context("display.width", 200, "display.max_columns", 20):
            print(vif_df.round(2))
        return

    vif_df = run_vif(panel)

    summary = pd.DataFrame(
        {
            "vif_mean": vif_df.mean(),
            "vif_median": vif_df.median(),
            "vif_p90": vif_df.quantile(0.90),
            "vif_max": vif_df.max(),
        }
    ).sort_values("vif_mean", ascending=False)

    summary.to_csv(VIF_SUMMARY_PATH, encoding="utf-8-sig")

    print("\n=== VIF 汇总（按均值降序）===")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary.round(2))
    print(f"\n已保存: {VIF_SUMMARY_PATH}")


if __name__ == "__main__":
    main()
