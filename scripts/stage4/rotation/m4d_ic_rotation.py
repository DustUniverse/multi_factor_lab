"""M4d: 滚动 IC 因子轮动对比实验（不碰主线，只生成对比组分数）。

规则：
- 每个调仓日 sig，取过去 LOOKBACK=6 期各因子与下期收益的截面 Spearman IC；
- 权重 = 过去 6 期 IC 均值（仅保留非 NaN 因子，权重按绝对值归一）；
- 用权重对当期标准化因子加权求和，得到 score；
- 输出 composite_scores_ic_rotation_all8.parquet，格式与 load_scores 兼容。
"""

import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.stdout.reconfigure(encoding="utf-8")

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

FACTOR_FILE = os.path.join(PROC, "factor_panel_final.parquet")
PRICE_FILE = os.path.join(PROC, "daily_panel_tencent_clean.parquet")
CAL_FILE = os.path.join(PROC, "rebalance_calendar.csv")

ALL8 = [
    "turnover",
    "volatility_20",
    "amihud_20",
    "bp",
    "corr_pv_20",
    "reversal_20",
    "bias_20",
    "ep_ttm",
]
LOOKBACK = 6
MIN_PERIODS = 3
MIN_STOCKS = 30


def cs_standardize(df, factor_cols):
    out = df.copy()
    dates = df["date"]
    for c in factor_cols:
        med = df.groupby("date")[c].transform("median")
        abs_dev = (df[c] - med).abs()
        mad = abs_dev.groupby(dates).transform("median")
        k = 1.4826
        lo = med - 3 * k * mad
        hi = med + 3 * k * mad
        x = df[c].clip(lo, hi)
        m = x.groupby(dates).transform("mean")
        s = x.groupby(dates).transform("std").replace(0, 1)
        out[c] = (x - m) / s
    return out


def main() -> None:
    print("[M4d] 读取因子...")
    fp = pd.read_parquet(FACTOR_FILE).reset_index()
    fp["symbol"] = fp["symbol"].astype(str).str.zfill(6)
    fp["date"] = pd.to_datetime(fp["date"])
    fp = cs_standardize(fp, ALL8)
    fp = fp.set_index(["date", "symbol"])

    print("[M4d] 读取价格...")
    px = pd.read_parquet(PRICE_FILE, columns=["symbol", "date", "open"])
    px["symbol"] = px["symbol"].astype(str).str.zfill(6)
    px["date"] = pd.to_datetime(px["date"])
    open_mat = px.pivot(index="date", columns="symbol", values="open").sort_index()

    cal = (
        pd.read_csv(CAL_FILE, parse_dates=["signal_date", "trade_date"])
        .sort_values("signal_date")
        .reset_index(drop=True)
    )

    # 每期下期收益：trade_date -> next trade_date，open-to-open
    rets = {}
    for i in range(len(cal) - 1):
        sig = cal.loc[i, "signal_date"]
        t0 = cal.loc[i, "trade_date"]
        t1 = cal.loc[i + 1, "trade_date"]
        if t0 not in open_mat.index or t1 not in open_mat.index:
            continue
        r = open_mat.loc[t1] / open_mat.loc[t0] - 1
        r.name = sig
        rets[sig] = r
    ret_df = pd.DataFrame(rets).T

    print("[M4d] 计算每期截面 IC...")
    ic_records = []
    factor_dates = fp.index.get_level_values("date")
    for sig in ret_df.index:
        if sig not in factor_dates:
            continue
        try:
            f_sig = fp.xs(sig, level="date")
        except KeyError:
            continue
        r_sig = ret_df.loc[sig].dropna()
        common = f_sig.index.intersection(r_sig.index)
        if len(common) < MIN_STOCKS:
            continue
        f_common = f_sig.loc[common]
        r_common = r_sig.loc[common]
        row = {"signal_date": sig}
        for c in ALL8:
            x = f_common[c]
            valid = x.notna() & r_common.notna()
            if valid.sum() < MIN_STOCKS:
                row[c] = np.nan
            else:
                row[c] = spearmanr(x[valid], r_common[valid]).correlation
        ic_records.append(row)
    ic_df = pd.DataFrame(ic_records).set_index("signal_date").sort_index()
    ic_df.to_csv(os.path.join(PROC, "m4d_ic_rotation_raw_ic.csv"), encoding="utf-8-sig")
    print(f"[M4d] IC 表：{ic_df.shape}，已写 m4d_ic_rotation_raw_ic.csv")

    # 滚动 IC 均值作权重
    ic_mean = ic_df.rolling(LOOKBACK, min_periods=MIN_PERIODS).mean()

    print("[M4d] 生成轮动分数...")
    scores = {}
    for sig in cal["signal_date"]:
        if sig not in factor_dates:
            continue
        if sig not in ic_mean.index:
            continue
        w = ic_mean.loc[sig].dropna()
        if len(w) < 3:
            continue
        w = w / w.abs().sum()
        f_sig = fp.xs(sig, level="date")
        score = (f_sig[w.index] * w).sum(axis=1)
        score.name = sig
        scores[sig] = score
    score_df = pd.DataFrame(scores).T
    score_df.index = pd.to_datetime(score_df.index)
    score_df.index.name = "date"

    out_path = os.path.join(PROC, "composite_scores_ic_rotation_all8.parquet")
    score_df.to_parquet(out_path)
    print(f"[M4d] 输出：{out_path}")
    print(f"[M4d] shape={score_df.shape}，覆盖 {score_df.shape[0]} 期")
    print(f"[M4d] 平均每期有效股票数：{score_df.notna().sum(axis=1).mean():.0f}")


if __name__ == "__main__":
    main()
