"""M2-prep: 重算 8 因子逐日 1D IC 序列。

用途：
    滚动窗口加权（M2a）需要逐日 IC 序列，而阶段二只落盘了汇总表。
    本脚本用纯 pandas 重算 8 因子在每天的横截面 Spearman Rank IC。

    1D 前瞻收益定义：
        forward_ret(t) = close(t+1) / close(t) - 1
    使用 t 日因子值 vs t+1 日收益，t 日盘后即知，无未来函数。

输出：
    data/processed/factor_ic_daily_1d.parquet
        index: date
        columns: 8 个因子（每个因子对应一天一个 IC 值）

用法（项目根目录、激活 .venv 后）：
    python scripts/backtest/compute_daily_ic.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

FACTOR_PATH = _ROOT / "data" / "processed" / "factor_panel_final.parquet"
PRICE_PATH = _ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"
OUT_PATH = _ROOT / "data" / "processed" / "factor_ic_daily_1d.parquet"


def normalize_symbol(s: pd.Series) -> pd.Series:
    """000001.SZ -> 000001；000001 -> 000001。"""
    s = s.astype(str).str.strip().str.split(".").str[0]
    return s.str.zfill(6)


def load_factor_panel() -> pd.DataFrame:
    """读 MultiIndex 因子面板，返回 date/symbol 为普通列的 long 表。"""
    df = pd.read_parquet(FACTOR_PATH)
    df = df.reset_index()
    df["symbol"] = normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_close() -> pd.DataFrame:
    """读价格面板，只保留 symbol/date/close。"""
    df = pd.read_parquet(PRICE_PATH, columns=["symbol", "date", "close"])
    df["symbol"] = normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def compute_forward_ret(close_df: pd.DataFrame) -> pd.DataFrame:
    """每只股票的 1D 前瞻收益：close(t+1) / close(t) - 1。"""
    df = close_df.sort_values(["symbol", "date"]).copy()
    df["fwd_ret_1d"] = df.groupby("symbol")["close"].shift(-1) / df["close"] - 1
    return df[["symbol", "date", "fwd_ret_1d"]]


def compute_daily_ic(
    factor_df: pd.DataFrame,
    ret_df: pd.DataFrame,
    factors: list[str],
) -> pd.DataFrame:
    """逐日横截面 Spearman Rank IC，返回 index=date，columns=factors 的宽表。"""
    merged = factor_df.merge(ret_df, on=["symbol", "date"], how="inner")
    merged = merged.dropna(subset=["fwd_ret_1d"])

    out: dict[str, pd.Series] = {}
    for f in factors:
        sub = merged[["date", f, "fwd_ret_1d"]].dropna()
        ic_series = sub.groupby("date").apply(
            lambda g: (
                g[f].corr(g["fwd_ret_1d"], method="spearman")
                if len(g) >= 10
                else np.nan
            )
        )
        out[f] = ic_series

    ic_df = pd.DataFrame(out)
    ic_df.index = pd.to_datetime(ic_df.index)
    ic_df = ic_df.sort_index()
    return ic_df


def main() -> None:
    print("[M2-prep] 重算 8 因子逐日 1D IC ...")

    factor_df = load_factor_panel()
    print(
        f"  因子面板: {factor_df.shape}, "
        f"日期 {factor_df['date'].min().date()} ~ {factor_df['date'].max().date()}"
    )
    factors = [c for c in factor_df.columns if c not in ("date", "symbol")]
    print(f"  因子列表: {factors}")

    close_df = load_close()
    print(f"  价格面板: {close_df.shape}")

    ret_df = compute_forward_ret(close_df)
    print(f"  前瞻收益非空: {ret_df['fwd_ret_1d'].notna().sum():,}")

    ic_df = compute_daily_ic(factor_df, ret_df, factors)
    print(f"  IC 序列形状: {ic_df.shape}")
    print(f"  覆盖日期: {ic_df.index.min().date()} ~ {ic_df.index.max().date()}")
    print("  各因子有效天数 / 均值 / 标准差:")
    for f in factors:
        s = ic_df[f].dropna()
        print(f"    {f:>15s}: n={len(s):4d}, mean={s.mean():+.4f}, std={s.std():.4f}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ic_df.to_parquet(OUT_PATH)
    print(f"  保存到: {OUT_PATH}")


if __name__ == "__main__":
    main()
