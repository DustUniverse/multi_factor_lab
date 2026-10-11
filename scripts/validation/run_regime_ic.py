"""
M6 S2: 分市场状态 (bull/flat/bear) 计算 8 选中因子的 IC/IR/胜率/多空夏普

输入:
    data/processed/factor_panel_selected.parquet   (MultiIndex: date, symbol; 8 因子)
    data/processed/daily_panel_tencent_clean.parquet (symbol, date, close, ...)
    data/processed/market_regime.csv                (date, nav, ret_120d, regime)

输出:
    data/processed/regime_ic_summary.csv
    data/processed/regime_ls_sharpe.csv

用法:
    # smoke: 单因子、仅 20D、跳过多空
    python scripts/validation/run_regime_ic.py --factors turnover --periods 20 --skip-ls
    # 全量
    python scripts/validation/run_regime_ic.py
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
REGIME_PATH = PROCESSED / "market_regime.csv"
OUT_IC = PROCESSED / "regime_ic_summary.csv"
OUT_LS = PROCESSED / "regime_ls_sharpe.csv"

HOLDING = 20
QUANTILES = 10
ANNUAL_FACTOR = float(np.sqrt(252 / HOLDING))
REGIMES = ("bull", "flat", "bear")


# ---------- I/O ----------


def load_selected_panel() -> pd.DataFrame:
    df = pd.read_parquet(SELECTED_PATH)
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    return df


def load_prices_wide() -> pd.DataFrame:
    df = pd.read_parquet(PRICE_PATH, columns=["symbol", "date", "close"])
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.zfill(6)
    wide = df.pivot(index="date", columns="symbol", values="close")
    return wide.sort_index().sort_index(axis=1)


def make_fwd_long(wide: pd.DataFrame, period: int) -> pd.DataFrame:
    fwd = wide.shift(-period) / wide - 1.0
    long = fwd.stack().rename("fwd_ret").reset_index()
    long.columns = ["date", "symbol", "fwd_ret"]
    long["symbol"] = long["symbol"].astype(str).str.zfill(6)
    return long


def load_regime() -> pd.DataFrame:
    r = pd.read_csv(REGIME_PATH, usecols=["date", "regime"])
    r["date"] = pd.to_datetime(r["date"])
    return r


# ---------- IC ----------


def compute_ic_series(
    df: pd.DataFrame, factor: str, ret_col: str = "fwd_ret"
) -> pd.Series:
    """按日 Spearman IC (因子 vs 前视收益)。向量化实现。"""
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


# ---------- 多空夏普 (Q10-Q1) ----------


def _qcut_labels(x: pd.Series, n_q: int) -> pd.Series:
    try:
        return pd.qcut(x, n_q, labels=False, duplicates="drop")
    except ValueError:
        return pd.Series(np.nan, index=x.index)


def compute_ls_series(
    df: pd.DataFrame, factor: str, ret_col: str = "fwd_ret", n_q: int = QUANTILES
) -> pd.Series:
    d = df[["date", factor, ret_col]].dropna()
    if d.empty:
        return pd.Series(dtype=float)
    d = d.copy()
    d["q"] = d.groupby("date")[factor].transform(lambda x: _qcut_labels(x, n_q))
    d = d.dropna(subset=["q"])
    g = d.groupby(["date", "q"])[ret_col].mean().unstack()
    if g.shape[1] < 2:
        return pd.Series(dtype=float)
    hi, lo = g.columns.max(), g.columns.min()
    ls = (g[hi] - g[lo]).dropna()
    ls.name = "LS"
    return ls


def ls_summary(ls: pd.Series) -> dict:
    n = len(ls)
    if n < 2:
        return {
            "n_days": n,
            "LS_mean": np.nan,
            "LS_std": np.nan,
            "LS_Sharpe_ann": np.nan,
        }
    m = float(ls.mean())
    sd = float(ls.std())
    sharpe = m / sd * ANNUAL_FACTOR if sd > 0 else np.nan
    return {"n_days": n, "LS_mean": m, "LS_std": sd, "LS_Sharpe_ann": sharpe}


# ---------- 主流程 ----------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--factors", type=str, default=None, help="逗号分隔的因子列表，默认全部"
    )
    parser.add_argument(
        "--periods", type=str, default="1,5,20", help="逗号分隔持有期，默认 1,5,20"
    )
    parser.add_argument("--skip-ls", action="store_true", help="跳过多空夏普计算")
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

    print(f"[3/5] 读取市场状态: {REGIME_PATH}")
    regime = load_regime()
    print(f"      regime 天数={len(regime)}")
    print(regime["regime"].value_counts().to_string())

    print("[4/5] 逐持有期计算 IC")
    ic_rows = []
    for p in periods:
        print(f"\n  === 持有期 {p}D ===")
        fwd_long = make_fwd_long(wide, p)
        base = panel.merge(fwd_long, on=["date", "symbol"], how="inner")
        base = base.dropna(subset=["fwd_ret"]).merge(regime, on="date", how="inner")
        print(f"      merged shape={base.shape}")
        for f in factors:
            ic = compute_ic_series(base, f)
            parts = []
            for reg in REGIMES:
                reg_dates = regime.loc[regime["regime"] == reg, "date"]
                ic_reg = ic[ic.index.isin(reg_dates)]
                st = ic_summary(ic_reg)
                st.update({"factor": f, "regime": reg, "period": f"{p}D"})
                ic_rows.append(st)
                if np.isnan(st["IC_mean"]):
                    parts.append(f"{reg}:n={st['n_days']}")
                else:
                    parts.append(
                        f"{reg}:IC={st['IC_mean']:+.3f}/ICIR={st['ICIR']:+.2f}"
                    )
            print(f"    {f:14s} {p}D  " + "  ".join(parts))

    ic_df = pd.DataFrame(ic_rows)[
        [
            "factor",
            "regime",
            "period",
            "n_days",
            "IC_mean",
            "IC_std",
            "ICIR",
            "IC_win",
            "t_stat",
        ]
    ]
    ic_df.to_csv(OUT_IC, index=False, encoding="utf-8-sig")
    print(f"\n      写入: {OUT_IC}")

    if not args.skip_ls:
        print(
            f"\n[5/5] 多空夏普 Q{QUANTILES}-Q1, 持有 {HOLDING}D, "
            f"年化因子={ANNUAL_FACTOR:.2f}"
        )
        fwd_h = make_fwd_long(wide, HOLDING)
        base_h = panel.merge(fwd_h, on=["date", "symbol"], how="inner")
        base_h = base_h.dropna(subset=["fwd_ret"]).merge(regime, on="date", how="inner")
        ls_rows = []
        for f in factors:
            ls = compute_ls_series(base_h, f)
            parts = []
            for reg in REGIMES:
                reg_dates = regime.loc[regime["regime"] == reg, "date"]
                ls_reg = ls[ls.index.isin(reg_dates)]
                st = ls_summary(ls_reg)
                st.update({"factor": f, "regime": reg})
                ls_rows.append(st)
                if np.isnan(st["LS_Sharpe_ann"]):
                    parts.append(f"{reg}:n={st['n_days']}")
                else:
                    parts.append(f"{reg}:Sharpe={st['LS_Sharpe_ann']:+.2f}")
            print(f"    {f:14s}  " + "  ".join(parts))
        ls_df = pd.DataFrame(ls_rows)[
            ["factor", "regime", "n_days", "LS_mean", "LS_std", "LS_Sharpe_ann"]
        ]
        ls_df.to_csv(OUT_LS, index=False, encoding="utf-8-sig")
        print(f"\n      写入: {OUT_LS}")

    print("\n完成。")
    if not ic_df.empty:
        print("\n=== IC 均值 (20D) 因子 × 状态 ===")
        sub = ic_df[ic_df["period"] == "20D"].pivot(
            index="factor", columns="regime", values="IC_mean"
        )
        print(sub.reindex(columns=list(REGIMES)).round(4).to_string())


if __name__ == "__main__":
    main()
