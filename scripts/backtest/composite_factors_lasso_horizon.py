"""
M3-horizon: Lasso 标签改为调仓周期持有期收益，重训对照组。

与 composite_factors_lasso.py 的区别：
- 训练样本只取调仓 signal_date 当天的截面（每个调仓期一个截面）
- 标签 = 从该调仓的 trade_date 到下一个 trade_date 的持有期收益
- 预测目标与策略持仓周期一致，避免日度噪声过拟合

输出：
    composite_scores_lasso_horizon_all8.parquet
    composite_scores_lasso_horizon_no_vol.parquet
    composite_weights_lasso_horizon_all8.csv
    composite_weights_lasso_horizon_no_vol.csv
"""

import os

import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso

# ---------- 路径 ----------
ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

FACTOR_FILE = os.path.join(PROC, "factor_panel_final.parquet")
PRICE_FILE = os.path.join(PROC, "daily_panel_tencent_clean.parquet")
CAL_FILE = os.path.join(PROC, "rebalance_calendar.csv")

# ---------- 因子清单 ----------
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
NO_VOL = [f for f in ALL8 if f != "volatility_20"]

# ---------- 参数 ----------
WINDOW_MONTHS = 12
MIN_PERIODS = 6  # 训练窗口内最少调仓期数（12 个月约 12 期，留余量）
MIN_ROWS = 10000  # 训练集最少样本行数
ALPHA = 1e-4


# ============================================================
# 逐日横截面 MAD 去极值 + z-score（与原脚本一致）
# ============================================================
def cs_standardize(df, factor_cols):
    out = df.copy()
    for c in factor_cols:
        med = df.groupby("date")[c].transform("median")
        abs_dev = (df[c] - med).abs()
        mad = abs_dev.groupby(df["date"]).transform("median")
        k = 1.4826
        lo = med - 3 * k * mad
        hi = med + 3 * k * mad
        x = df[c].clip(lo, hi)
        m = x.groupby(df["date"]).transform("mean")
        s = x.groupby(df["date"]).transform("std").replace(0, 1)
        out[c] = (x - m) / s
    return out


# ============================================================
# 主流程
# ============================================================
def main():
    # ---------- 加载因子面板 ----------
    print("[Lasso-horizon] 加载因子面板 ...")
    fp = pd.read_parquet(FACTOR_FILE).reset_index()
    fp["symbol"] = fp["symbol"].astype(str).str.zfill(6)
    fp["date"] = pd.to_datetime(fp["date"])
    print(f"  shape: {fp.shape}")

    # ---------- 加载价格 ----------
    print("[Lasso-horizon] 加载价格 ...")
    panel = pd.read_parquet(PRICE_FILE)
    if "date" in panel.columns and "trade_date" not in panel.columns:
        panel = panel.rename(columns={"date": "trade_date"})
    panel["symbol"] = panel["symbol"].astype(str).str.zfill(6)
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel = panel[["trade_date", "symbol", "close"]].dropna()

    # ---------- 读调仓日历 ----------
    print("[Lasso-horizon] 加载调仓日历 ...")
    cal = pd.read_csv(CAL_FILE, parse_dates=["signal_date", "trade_date"])
    cal = cal.sort_values("trade_date").reset_index(drop=True)
    cal["next_trade_date"] = cal["trade_date"].shift(-1)
    print(f"  调仓期数: {len(cal)}")

    # ---------- 计算每个调仓期的持有期收益 ----------
    print("[Lasso-horizon] 计算持有期收益 ...")
    ret_by_trade_date = {}  # trade_date -> Series(symbol -> ret)
    for _, row in cal.iterrows():
        td = row["trade_date"]
        ntd = row["next_trade_date"]
        if pd.isna(ntd):
            continue
        p0 = panel[panel["trade_date"] == td].set_index("symbol")["close"]
        p1 = panel[panel["trade_date"] == ntd].set_index("symbol")["close"]
        ret = (p1 / p0 - 1.0).dropna()
        ret_by_trade_date[td] = ret
    print(f"  有效收益期数: {len(ret_by_trade_date)}")

    # ---------- 调仓 signal_date 对齐线性组 ----------
    linear_file = os.path.join(PROC, "composite_scores_ic_no_vol.parquet")
    linear_index = pd.read_parquet(linear_file).index
    signal_dates = sorted(pd.to_datetime(linear_index).normalize())
    print(f"  调仓日数: {len(signal_dates)}（对齐线性组）")

    # ---------- 逐个 set 合成 ----------
    for set_name, factor_cols in [("all8", ALL8), ("no_vol", NO_VOL)]:
        print(f"\n{'=' * 60}")
        print(f"[Lasso-horizon] set = {set_name}")
        print("=" * 60)

        scores = {}
        weights_log = []

        for i, sig in enumerate(signal_dates):
            sig = pd.Timestamp(sig)
            tr_start = sig - pd.DateOffset(months=WINDOW_MONTHS)

            # 训练窗口内的调仓期：signal_date in [tr_start, sig)
            train_cal = cal[
                (cal["signal_date"] >= tr_start) & (cal["signal_date"] < sig)
            ]
            if len(train_cal) < MIN_PERIODS:
                print(
                    f"  [{i + 1:>2}/{len(signal_dates)}] {sig.date()}: "
                    f"训练调仓期不足 ({len(train_cal)}), skip"
                )
                continue

            # 拼接训练样本：每个调仓期一个截面
            train_parts = []
            for _, crow in train_cal.iterrows():
                csig = crow["signal_date"]
                ctd = crow["trade_date"]
                if ctd not in ret_by_trade_date:
                    continue
                ret_s = ret_by_trade_date[ctd]
                cross = fp[fp["date"] == csig][["date", "symbol"] + factor_cols].copy()
                if cross.empty:
                    continue
                cross["ret_horizon"] = cross["symbol"].map(ret_s)
                cross = cross.dropna(subset=["ret_horizon"])
                if not cross.empty:
                    train_parts.append(cross)

            if not train_parts:
                print(
                    f"  [{i + 1:>2}/{len(signal_dates)}] {sig.date()}: "
                    f"训练样本为空, skip"
                )
                continue

            train = pd.concat(train_parts, ignore_index=True)
            if len(train) < MIN_ROWS:
                print(
                    f"  [{i + 1:>2}/{len(signal_dates)}] {sig.date()}: "
                    f"训练样本不足 ({len(train)}), skip"
                )
                continue

            train_std = cs_standardize(
                train[["date"] + factor_cols].copy(), factor_cols
            )
            X_train = train_std[factor_cols].fillna(0.0).values
            y_train = train["ret_horizon"].values

            y_mu = float(np.nanmean(y_train))
            y_sd = float(np.nanstd(y_train))
            if y_sd == 0 or np.isnan(y_sd):
                y_sd = 1.0
            y_train_std = (y_train - y_mu) / y_sd

            lasso = Lasso(alpha=ALPHA, max_iter=5000, fit_intercept=True)
            lasso.fit(X_train, y_train_std)

            today = fp[fp["date"] == sig][["date", "symbol"] + factor_cols].copy()
            if today.empty:
                print(
                    f"  [{i + 1:>2}/{len(signal_dates)}] {sig.date()}: "
                    f"当日无数据, skip"
                )
                continue

            today_std = cs_standardize(today, factor_cols)
            X_today = today_std[factor_cols].fillna(0.0).values
            today_scores = lasso.predict(X_today)

            scores[sig] = pd.Series(today_scores, index=today["symbol"].values)

            coef_s = pd.Series(lasso.coef_, index=factor_cols)
            coef_s["intercept"] = lasso.intercept_
            coef_s["n_train"] = len(train)
            coef_s["n_periods"] = len(train_cal)
            coef_s.name = sig
            weights_log.append(coef_s)

            nz = int(np.sum(lasso.coef_ != 0))
            print(
                f"  [{i + 1:>2}/{len(signal_dates)}] {sig.date()}: "
                f"train={len(train):>7d}  periods={len(train_cal):>2d}  "
                f"nz={nz}/8  coef={np.round(lasso.coef_, 4).tolist()}"
            )

        if not scores:
            print(f"  [warn] set={set_name} 无输出")
            continue

        score_df = pd.DataFrame(scores).T
        score_df.index.name = "signal_date"
        out_score = os.path.join(
            PROC, f"composite_scores_lasso_horizon_{set_name}.parquet"
        )
        score_df.to_parquet(out_score)
        print(f"\n  → {out_score}")
        print(f"    shape = {score_df.shape}")

        weight_df = pd.DataFrame(weights_log).T
        out_w = os.path.join(PROC, f"composite_weights_lasso_horizon_{set_name}.csv")
        weight_df.to_csv(out_w)
        print(f"  → {out_w}")


if __name__ == "__main__":
    main()
