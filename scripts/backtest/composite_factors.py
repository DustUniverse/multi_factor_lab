"""M2a: 滚动窗口多因子合成（IC / IR / 等权加权，含 volatility_20 对照组）。

在每个调仓日 t（signal_date）：
    1. 取过去 12 个月（≥120 个交易日）的因子 IC 序列
    2. 计算滚动权重：
        - IC 加权：w_i = |mean(IC_i)| / Σ|mean(IC_j)|
        - IR 加权：w_i = |mean(IC_i)/std(IC_i)| / Σ|...|
        - 等权：  w_i = 1/n
    3. 取 t 日各因子的横截面值，逐日 MAD 去极值 + z-score 标准化
    4. 合成分数 = Σ w_i * z(factor_i)

因子集：
    all8   = 全部 8 因子
    no_vol = 剔除 volatility_20 的 7 因子

输出（每组一个 parquet + 一个 csv）：
    data/processed/composite_scores_{method}_{set}.parquet
        index=signal_date, columns=symbol, values=score
    data/processed/composite_weights_{method}_{set}.csv
        index=signal_date, columns=因子名

用法（项目根目录、激活 .venv 后）：
    python scripts/backtest/composite_factors.py
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
IC_PATH = _ROOT / "data" / "processed" / "factor_ic_daily_1d.parquet"
CAL_PATH = _ROOT / "data" / "processed" / "rebalance_calendar.csv"
OUT_DIR = _ROOT / "data" / "processed"

ALL_FACTORS = [
    "turnover",
    "volatility_20",
    "amihud_20",
    "bp",
    "corr_pv_20",
    "reversal_20",
    "bias_20",
    "ep_ttm",
]
NO_VOL_FACTORS = [f for f in ALL_FACTORS if f != "volatility_20"]

WINDOW_MONTHS = 12
MIN_OBS = 120


def normalize_symbol(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.split(".").str[0]
    return s.str.zfill(6)


def load_factor_panel() -> pd.DataFrame:
    df = pd.read_parquet(FACTOR_PATH).reset_index()
    df["symbol"] = normalize_symbol(df["symbol"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_ic() -> pd.DataFrame:
    ic = pd.read_parquet(IC_PATH)
    ic.index = pd.to_datetime(ic.index)
    return ic


def load_calendar() -> pd.DataFrame:
    cal = pd.read_csv(CAL_PATH, parse_dates=["signal_date", "trade_date"])
    return cal


def robust_zscore(s: pd.Series) -> pd.Series:
    """MAD 去极值 + z-score，保持原索引（NaN 保留为 NaN）。"""
    valid = s.dropna()
    out = pd.Series(np.nan, index=s.index, dtype=float)
    if len(valid) < 5:
        return out
    med = valid.median()
    mad = (valid - med).abs().median()
    if mad == 0 or np.isnan(mad):
        z = (valid - valid.mean()) / (valid.std() + 1e-12)
    else:
        lo, hi = med - 3 * 1.4826 * mad, med + 3 * 1.4826 * mad
        v2 = valid.clip(lo, hi)
        z = (v2 - v2.mean()) / (v2.std() + 1e-12)
    out.loc[z.index] = z
    return out


def compute_weights(ic_window: pd.DataFrame, factors: list[str], method: str):
    """根据历史 IC 窗口计算权重。返回 None 表示暖机期跳过。"""
    sub = ic_window[factors].dropna()
    if len(sub) < MIN_OBS:
        return None

    ic_mean = sub.mean()
    if method == "ic":
        w = ic_mean.abs() / (ic_mean.abs().sum() + 1e-12)
    elif method == "ir":
        ic_std = sub.std()
        ir = ic_mean / (ic_std + 1e-12)
        w = ir.abs() / (ir.abs().sum() + 1e-12)
    elif method == "equal":
        w = pd.Series(1.0 / len(factors), index=factors)
    else:
        raise ValueError(f"unknown method: {method}")
    return w


def main() -> None:
    print("[M2a] 滚动窗口多因子合成 ...")
    factor_df = load_factor_panel()
    ic_df = load_ic()
    cal = load_calendar()

    print(f"  因子面板: {factor_df.shape}")
    print(f"  IC 序列:   {ic_df.shape}")
    print(f"  调仓点数: {len(cal)}")
    print(f"  窗口:      {WINDOW_MONTHS} 个月（最小 {MIN_OBS} 观测）")

    factor_sets = {"all8": ALL_FACTORS, "no_vol": NO_VOL_FACTORS}
    methods = ["ic", "ir", "equal"]

    factor_by_date = {d: g for d, g in factor_df.groupby("date")}

    for set_name, factors in factor_sets.items():
        for method in methods:
            tag = f"{method}_{set_name}"
            print(f"\n  === {tag} ===")
            scores_rows = []
            weights_rows = []
            n_skipped = 0

            for _, row in cal.iterrows():
                sig = row["signal_date"]
                w_start = sig - pd.DateOffset(months=WINDOW_MONTHS)
                ic_window = ic_df.loc[(ic_df.index >= w_start) & (ic_df.index <= sig)]
                w = compute_weights(ic_window, factors, method)
                if w is None:
                    n_skipped += 1
                    continue

                day_df = factor_by_date.get(sig)
                if day_df is None or day_df.empty:
                    n_skipped += 1
                    continue

                day_df = day_df.set_index("symbol")
                z = pd.DataFrame(index=day_df.index)
                for f in factors:
                    z[f] = robust_zscore(day_df[f])
                z["score"] = 0.0
                for f in factors:
                    z["score"] += w[f] * z[f].fillna(0.0)

                scores_rows.append(
                    pd.DataFrame(
                        {
                            "signal_date": sig,
                            "symbol": z.index,
                            "score": z["score"].values,
                        }
                    )
                )
                w_row = {"signal_date": sig}
                w_row.update(w.to_dict())
                weights_rows.append(w_row)

            if not scores_rows:
                print(f"    [{tag}] 无有效调仓日")
                continue

            scores_df = pd.concat(scores_rows, ignore_index=True)
            scores_df = scores_df.pivot(
                index="signal_date", columns="symbol", values="score"
            )
            weights_df = pd.DataFrame(weights_rows).set_index("signal_date")

            s_path = OUT_DIR / f"composite_scores_{tag}.parquet"
            w_path = OUT_DIR / f"composite_weights_{tag}.csv"
            scores_df.to_parquet(s_path)
            weights_df.to_csv(w_path)

            print(f"    有效调仓日: {scores_df.shape[0]}（跳过 {n_skipped}）")
            print(f"    分数落盘:   {s_path.name}  shape={scores_df.shape}")
            print(f"    权重落盘:   {w_path.name}  shape={weights_df.shape}")
            print(f"    最新权重:   {weights_df.iloc[-1].round(4).to_dict()}")


if __name__ == "__main__":
    main()
