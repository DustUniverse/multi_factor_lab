"""
M6 S3: 分板块 (主板/创业板/科创板) 计算 8 选中因子的 IC/IR/胜率

输入:
    data/processed/factor_panel_selected.parquet
    data/processed/daily_panel_tencent_clean.parquet
输出:
    data/processed/sector_ic_summary.csv

用法:
    # smoke
    python scripts/validation/run_sector_ic.py --factors turnover --periods 20
    # 全量
    python scripts/validation/run_sector_ic.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = PROJECT_ROOT / "data" / "processed"

SELECTED_PATH = PROCESSED / "factor_panel_selected.parquet"
PRICE_PATH = PROCESSED / "daily_panel_tencent_clean.parquet"
OUT_IC = PROCESSED / "sector_ic_summary.csv"

SECTORS = ("主板", "创业板", "科创板")


# ---------- I/O ----------


def load_selected_panel() -> pd.DataFrame:
    df = pd.read_parquet(SELECTED_PATH)
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    return df


def load_prices_and_board() -> tuple[pd.DataFrame, pd.DataFrame]:
    """返回 (wide_prices, board_long)。

    board_long: 每只股票一行 (symbol -> board)，因为同一股票 board 不随时间变。
    """
    df = pd.read_parquet(PRICE_PATH, columns=["symbol", "date", "close", "board"])
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)

    wide = df.pivot(index="date", columns="symbol", values="close")
    wide = wide.sort_index().sort_index(axis=1)

    board_long = (
        df[["symbol", "board"]].drop_duplicates("symbol").reset_index(drop=True)
    )
    # 简单断言：每只股票 board 唯一
    n_dup = df.groupby("symbol")["board"].nunique()
    if (n_dup > 1).any():
        bad = n_dup[n_dup > 1].index.tolist()[:5]
        print(f"      !! 警告：{len(n_dup[n_dup > 1])} 只股票 board 不唯一，示例 {bad}")
    return wide, board_long


def make_fwd_long(wide: pd.DataFrame, period: int) -> pd.DataFrame:
    fwd = wide.shift(-period) / wide - 1.0
    long = fwd.stack().rename("fwd_ret").reset_index()
    long.columns = ["date", "symbol", "fwd_ret"]
    long["symbol"] = long["symbol"].astype(str).str.zfill(6)
    return long


# ---------- IC ----------


def compute_ic_series(
    df: pd.DataFrame, factor: str, ret_col: str = "fwd_ret"
) -> pd.Series:
    d = df[["date", factor, ret_col]].dropna()
    if d.empty:
        return pd.Series(dtype=float)
    corr = d.groupby("date")[[factor, ret_col]].corr(method="spearman")
    ic = corr.xs(factor, level=1)[ret_col].dropna()
    ic.index = ic.index.get_level_values(0)
    ic.name = "IC"
    return ic


def ic_summary(ic: pd.Series) -> dict:
    n = len(ic)
    if n < 2:
        return {
            "n_days": n,
            "IC_mean": np.nan,
            "IC_std": np.nan,
            "ICIR": np.nan,
            "IC_win": np.nan,
            "t_stat": np.nan,
        }
    m = float(ic.mean())
    sd = float(ic.std())
    icir = m / sd if sd > 0 else np.nan
    win = float((ic > 0).mean())
    t = m / (sd / np.sqrt(n)) if sd > 0 else np.nan
    return {
        "n_days": n,
        "IC_mean": m,
        "IC_std": sd,
        "ICIR": icir,
        "IC_win": win,
        "t_stat": t,
    }


# ---------- 主流程 ----------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--factors", type=str, default=None)
    parser.add_argument("--periods", type=str, default="1,5,20")
    args = parser.parse_args()

    print(f"[1/4] 读取选中面板: {SELECTED_PATH}")
    panel = load_selected_panel()
    factor_cols = [c for c in panel.columns if c not in ("date", "symbol")]
    factors = (
        [f.strip() for f in args.factors.split(",")] if args.factors else factor_cols
    )
    for f in factors:
        if f not in factor_cols:
            raise ValueError(f"面板里没有 {f!r}，可选：{factor_cols}")
    panel = panel[["date", "symbol"] + factors].copy()
    periods = tuple(int(p) for p in args.periods.split(","))
    print(f"      shape={panel.shape}  factors={factors}  periods={periods}")

    print(f"[2/4] 读取价格 + 板块: {PRICE_PATH}")
    wide, board_long = load_prices_and_board()
    print(f"      wide shape={wide.shape}")
    print("      board 分布:")
    print(board_long["board"].value_counts().to_string())

    print("[3/4] 逐持有期计算 IC (按板块)")
    ic_rows = []
    for p in periods:
        print(f"\n  === 持有期 {p}D ===")
        fwd_long = make_fwd_long(wide, p)
        base = panel.merge(fwd_long, on=["date", "symbol"], how="inner")
        base = base.dropna(subset=["fwd_ret"]).merge(
            board_long, on="symbol", how="inner"
        )
        print(f"      merged shape={base.shape}")
        for f in factors:
            parts = []
            for sec in SECTORS:
                sub = base[base["board"] == sec]
                ic = compute_ic_series(sub, f)
                st = ic_summary(ic)
                st.update({"factor": f, "sector": sec, "period": f"{p}D"})
                ic_rows.append(st)
                if np.isnan(st["IC_mean"]):
                    parts.append(f"{sec}:n={st['n_days']}")
                else:
                    parts.append(
                        f"{sec}:IC={st['IC_mean']:+.3f}/ICIR={st['ICIR']:+.2f}"
                    )
            print(f"    {f:14s} {p}D  " + "  ".join(parts))

    ic_df = pd.DataFrame(ic_rows)[
        [
            "factor",
            "sector",
            "period",
            "n_days",
            "IC_mean",
            "IC_std",
            "ICIR",
            "IC_win",
            "t_stat",
        ]
    ]
    print(f"\n[4/4] 写入: {OUT_IC}")
    ic_df.to_csv(OUT_IC, index=False, encoding="utf-8-sig")

    print("\n=== IC 均值 (20D) 因子 × 板块 ===")
    sub = ic_df[ic_df["period"] == "20D"].pivot(
        index="factor", columns="sector", values="IC_mean"
    )
    print(sub.reindex(columns=list(SECTORS)).round(4).to_string())

    print("\n=== ICIR (20D) 因子 × 板块 ===")
    sub = ic_df[ic_df["period"] == "20D"].pivot(
        index="factor", columns="sector", values="ICIR"
    )
    print(sub.reindex(columns=list(SECTORS)).round(2).to_string())

    print("\n完成。")


if __name__ == "__main__":
    main()
