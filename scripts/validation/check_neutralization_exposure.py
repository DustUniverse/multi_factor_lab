"""
M7 S1: 中性化前后 市值/行业 暴露检查

对每个交易日、每个因子做横截面 OLS:
    f ~ 1 + log(mktcap) + industry_dummies

分别对 raw (未中性化) 和 neutralized (已中性化) 面板跑，
对比 beta_mktcap 和 R² 是否降到 0 附近。

用法:
    python scripts/validation/check_neutralization_exposure.py --smoke
    python scripts/validation/check_neutralization_exposure.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = PROJECT_ROOT / "data" / "processed"

RAW_PATH = PROCESSED / "factor_panel.parquet"
NEUT_PATH = PROCESSED / "factor_panel_selected.parquet"
MKTCAP_PATH = PROCESSED / "mktcap_panel.parquet"
BASIC_PATH = PROCESSED / "stock_basic.parquet"
OUT_PATH = PROCESSED / "neutralization_exposure_check.csv"

SELECTED_FACTORS = [
    "turnover",
    "volatility_20",
    "amihud_20",
    "bp",
    "corr_pv_20",
    "reversal_20",
    "bias_20",
    "ep_ttm",
]


def _norm_symbol(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.split(".").str[0].str.zfill(6)


def load_raw_panel() -> pd.DataFrame:
    df = pd.read_parquet(RAW_PATH, columns=["symbol", "date"] + SELECTED_FACTORS)
    df["symbol"] = _norm_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_neut_panel() -> pd.DataFrame:
    df = pd.read_parquet(NEUT_PATH)
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()
    df["symbol"] = _norm_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "symbol"] + SELECTED_FACTORS]


def load_mktcap_long() -> pd.DataFrame:
    wide = pd.read_parquet(MKTCAP_PATH)
    wide.index = pd.to_datetime(wide.index)
    wide.columns = _norm_symbol(pd.Series(wide.columns)).values
    long = wide.stack().rename("mktcap").reset_index()
    long.columns = ["date", "symbol", "mktcap"]
    long["symbol"] = _norm_symbol(long["symbol"])
    long["log_mktcap"] = np.log(long["mktcap"].where(long["mktcap"] > 0))
    return long[["date", "symbol", "mktcap", "log_mktcap"]]


def load_industry() -> pd.DataFrame:
    df = pd.read_parquet(BASIC_PATH, columns=["symbol", "industry"])
    df["symbol"] = _norm_symbol(df["symbol"])
    df = df.dropna(subset=["industry"]).drop_duplicates("symbol")
    return df


def daily_regression(
    day: pd.DataFrame,
    factor_cols: list[str],
    mktcap_col: str = "log_mktcap",
    min_n: int = 50,
) -> pd.DataFrame | None:
    d = day.dropna(subset=[mktcap_col, "industry"] + factor_cols)
    if len(d) < min_n:
        return None

    ind_dummies = pd.get_dummies(d["industry"], prefix="ind", drop_first=False)
    X = np.column_stack(
        [
            np.ones(len(d), dtype=np.float64),
            d[mktcap_col].to_numpy(dtype=np.float64),
            ind_dummies.to_numpy(dtype=np.float64),
        ]
    )
    Y = d[factor_cols].to_numpy(dtype=np.float64)

    beta, _, _, _ = np.linalg.lstsq(X, Y, rcond=None)
    Y_pred = X @ beta
    ss_res = ((Y - Y_pred) ** 2).sum(axis=0)
    ss_tot = ((Y - Y.mean(axis=0)) ** 2).sum(axis=0)
    r2_full = 1.0 - ss_res / np.where(ss_tot > 0, ss_tot, np.nan)

    # 对照：只含 log(mktcap) 的回归
    X1 = np.column_stack(
        [
            np.ones(len(d), dtype=np.float64),
            d[mktcap_col].to_numpy(dtype=np.float64),
        ]
    )
    beta1, _, _, _ = np.linalg.lstsq(X1, Y, rcond=None)
    Y_pred1 = X1 @ beta1
    ss_res1 = ((Y - Y_pred1) ** 2).sum(axis=0)
    r2_mkt = 1.0 - ss_res1 / np.where(ss_tot > 0, ss_tot, np.nan)

    return pd.DataFrame(
        {
            "factor": factor_cols,
            "n": len(d),
            "beta_mktcap": beta[1, :],
            "r2_full": r2_full,
            "r2_mktcap_only": r2_mkt,
        }
    )


def run_panel(
    panel: pd.DataFrame,
    mktcap_long: pd.DataFrame,
    industry_df: pd.DataFrame,
    panel_name: str,
) -> pd.DataFrame:
    merged = panel.merge(mktcap_long, on=["date", "symbol"], how="inner")
    merged = merged.merge(industry_df, on="symbol", how="inner")
    dates = sorted(merged["date"].unique())
    print(f"      [{panel_name}] merged shape={merged.shape}, 交易日={len(dates)}")

    frames = []
    for mkt_col in ("mktcap", "log_mktcap"):
        print(f"      [{panel_name}] 市值变量 = {mkt_col}")
        results = []
        for i, dt in enumerate(dates):
            if i % 200 == 0:
                print(f"        {i + 1}/{len(dates)} {pd.Timestamp(dt).date()}")
            day = merged[merged["date"] == dt]
            r = daily_regression(day, SELECTED_FACTORS, mktcap_col=mkt_col)
            if r is not None:
                r["date"] = dt
                results.append(r)
        if not results:
            print(f"        !! [{panel_name}/{mkt_col}] 无有效回归结果")
            continue
        res = pd.concat(results, ignore_index=True)
        agg = (
            res.groupby("factor")
            .agg(
                n_days=("n", "size"),
                beta_mktcap_mean=("beta_mktcap", "mean"),
                beta_mktcap_median=("beta_mktcap", "median"),
                beta_mktcap_std=("beta_mktcap", "std"),
                r2_full_mean=("r2_full", "mean"),
                r2_full_median=("r2_full", "median"),
                r2_mktcap_only_mean=("r2_mktcap_only", "mean"),
            )
            .reset_index()
        )
        agg["panel"] = panel_name
        agg["mktcap_var"] = mkt_col
        frames.append(agg)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    print(f"[1/4] 读取原始面板: {RAW_PATH}")
    raw = load_raw_panel()
    print(f"      shape={raw.shape}")

    print(f"[2/4] 读取中性化面板: {NEUT_PATH}")
    neut = load_neut_panel()
    print(f"      shape={neut.shape}")

    print("[3/4] 读取市值 / 行业")
    mktcap_long = load_mktcap_long()
    industry_df = load_industry()
    print(f"      市值 long: {mktcap_long.shape}")
    print(
        f"      行业映射: {industry_df.shape}, 行业数={industry_df['industry'].nunique()}"
    )

    if args.smoke:
        cutoff = pd.Timestamp("2021-06-01")
        dates = [d for d in sorted(raw["date"].unique()) if pd.Timestamp(d) >= cutoff][
            :20
        ]
        raw = raw[raw["date"].isin(dates)]
        neut = neut[neut["date"].isin(dates)]
        d0 = pd.Timestamp(dates[0]).date()
        d1 = pd.Timestamp(dates[-1]).date()
        print(f"      [smoke] 截取 {len(dates)} 天（{d0} ~ {d1}）")

    print("[4/4] 逐日回归")
    print("  --- raw (未中性化) ---")
    agg_raw = run_panel(raw, mktcap_long, industry_df, "raw")
    print("  --- neutralized (已中性化) ---")
    agg_neut = run_panel(neut, mktcap_long, industry_df, "neutralized")

    if agg_raw.empty and agg_neut.empty:
        print("\n!! 两组回归都没有有效结果，请检查数据 / min_n 设置。")
        return

    if agg_raw.empty and agg_neut.empty:
        print("\n!! 两组回归都没有有效结果，请检查数据 / min_n 设置。")
        return

    out = pd.concat([agg_raw, agg_neut], ignore_index=True)
    out = out.sort_values(["mktcap_var", "factor", "panel"]).reset_index(drop=True)
    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n      写入: {OUT_PATH}")

    for mv in ("mktcap", "log_mktcap"):
        sub = out[out["mktcap_var"] == mv]
        if sub.empty:
            continue
        print(f"\n=== 市值变量 = {mv} ===")

        print("  beta_mktcap (mean) —— 行=因子, 列=panel:")
        piv = sub.pivot(index="factor", columns="panel", values="beta_mktcap_mean")
        print(piv.round(4).to_string())

        print("  R²(full) (mean) —— 行=因子, 列=panel:")
        piv = sub.pivot(index="factor", columns="panel", values="r2_full_mean")
        print(piv.round(4).to_string())

    print("\n完成。")


if __name__ == "__main__":
    main()
