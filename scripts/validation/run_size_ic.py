"""
M7 S3: 分市值 (大/中/小盘) 计算 8 选中因子的 IC/IR/胜率

方法:
    每个交易日按流通市值 qcut 分 3 档: 前30% / 中40% / 后30%
    分别计算各档内 8 因子的 逐日 Spearman IC / ICIR / 胜率 / t

输入:
    data/processed/factor_panel_selected.parquet
    data/processed/daily_panel_tencent_clean.parquet
    data/processed/mktcap_panel.parquet
输出:
    data/processed/size_ic_summary.csv

用法:
    python scripts/validation/run_size_ic.py --factors turnover --periods 20
    python scripts/validation/run_size_ic.py
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
MKTCAP_PATH = PROCESSED / "mktcap_panel.parquet"
OUT_IC = PROCESSED / "size_ic_summary.csv"

SIZE_GROUPS = ("small", "mid", "large")
Q_CUTS = [0.0, 0.3, 0.7, 1.0]  # 30% / 40% / 30%


def _norm_symbol(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.split(".").str[0].str.zfill(6)


def load_selected_panel() -> pd.DataFrame:
    df = pd.read_parquet(SELECTED_PATH)
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = _norm_symbol(df["symbol"])
    return df


def load_prices_wide() -> pd.DataFrame:
    df = pd.read_parquet(PRICE_PATH, columns=["symbol", "date", "close"])
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = _norm_symbol(df["symbol"])
    wide = df.pivot(index="date", columns="symbol", values="close")
    return wide.sort_index().sort_index(axis=1)


def load_mktcap_long() -> pd.DataFrame:
    wide = pd.read_parquet(MKTCAP_PATH)
    wide.index = pd.to_datetime(wide.index)
    wide.columns = _norm_symbol(pd.Series(wide.columns)).values
    long = wide.stack().rename("mktcap").reset_index()
    long.columns = ["date", "symbol", "mktcap"]
    long["symbol"] = _norm_symbol(long["symbol"])
    long = long[long["mktcap"] > 0]
    return long[["date", "symbol", "mktcap"]]


def make_fwd_long(wide: pd.DataFrame, period: int) -> pd.DataFrame:
    fwd = wide.shift(-period) / wide - 1.0
    long = fwd.stack().rename("fwd_ret").reset_index()
    long.columns = ["date", "symbol", "fwd_ret"]
    long["symbol"] = _norm_symbol(long["symbol"])
    return long


def add_size_group(df: pd.DataFrame) -> pd.DataFrame:
    """按日 qcut 分 3 档。"""

    def _label(x: pd.Series) -> pd.Series:
        try:
            # qcut 返回区间；用 labels=False 得 0/1/2
            lab = pd.qcut(x, q=Q_CUTS, labels=False, duplicates="drop")
            # 0->small, 1->mid, 2->large
            mapping = {0: "small", 1: "mid", 2: "large"}
            return lab.map(mapping)
        except ValueError:
            return pd.Series(np.nan, index=x.index)

    df = df.copy()
    df["size_group"] = df.groupby("date")["mktcap"].transform(_label)
    return df


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--factors", type=str, default=None)
    parser.add_argument("--periods", type=str, default="1,5,20")
    args = parser.parse_args()

    print(f"[1/5] 读取选中面板: {SELECTED_PATH}")
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

    print(f"[2/5] 读取价格宽表: {PRICE_PATH}")
    wide = load_prices_wide()
    print(f"      wide shape={wide.shape}")

    print(f"[3/5] 读取市值: {MKTCAP_PATH}")
    mkt = load_mktcap_long()
    print(f"      mktcap long shape={mkt.shape}")

    print("[4/5] 逐持有期计算 IC (按市值分档)")
    ic_rows = []
    for p in periods:
        print(f"\n  === 持有期 {p}D ===")
        fwd_long = make_fwd_long(wide, p)
        base = panel.merge(fwd_long, on=["date", "symbol"], how="inner")
        base = base.dropna(subset=["fwd_ret"]).merge(
            mkt, on=["date", "symbol"], how="inner"
        )
        base = add_size_group(base)
        base = base.dropna(subset=["size_group"])
        # 检查每档样本量（第一天）
        first_day = base[base["date"] == base["date"].min()]
        cnt = first_day["size_group"].value_counts().to_dict()
        print(f"      merged shape={base.shape}  首日分档={cnt}")
        for f in factors:
            parts = []
            for g in SIZE_GROUPS:
                sub = base[base["size_group"] == g]
                ic = compute_ic_series(sub, f)
                st = ic_summary(ic)
                st.update({"factor": f, "size_group": g, "period": f"{p}D"})
                ic_rows.append(st)
                if np.isnan(st["IC_mean"]):
                    parts.append(f"{g}:n={st['n_days']}")
                else:
                    parts.append(f"{g}:IC={st['IC_mean']:+.3f}/ICIR={st['ICIR']:+.2f}")
            print(f"    {f:14s} {p}D  " + "  ".join(parts))

    ic_df = pd.DataFrame(ic_rows)[
        [
            "factor",
            "size_group",
            "period",
            "n_days",
            "IC_mean",
            "IC_std",
            "ICIR",
            "IC_win",
            "t_stat",
        ]
    ]
    print(f"\n[5/5] 写入: {OUT_IC}")
    ic_df.to_csv(OUT_IC, index=False, encoding="utf-8-sig")

    print("\n=== IC 均值 (20D) 因子 × 市值档 ===")
    sub = ic_df[ic_df["period"] == "20D"].pivot(
        index="factor", columns="size_group", values="IC_mean"
    )
    print(sub.reindex(columns=list(SIZE_GROUPS)).round(4).to_string())

    print("\n=== ICIR (20D) 因子 × 市值档 ===")
    sub = ic_df[ic_df["period"] == "20D"].pivot(
        index="factor", columns="size_group", values="ICIR"
    )
    print(sub.reindex(columns=list(SIZE_GROUPS)).round(2).to_string())

    print("\n完成。")


if __name__ == "__main__":
    main()
