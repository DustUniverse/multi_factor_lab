"""
M2a-Lasso: 用滚动 12 个月窗口训练 Lasso 回归，输出两组综合分数：
  - composite_scores_lasso_all8.parquet
  - composite_scores_lasso_no_vol.parquet

与线性组合成严格对齐：
  - 滚动 12 个月训练窗口，最少 120 交易日
  - 逐日横截面 MAD 去极值 + z-score
  - 标签 = t+1 日收益
  - 输出格式与 composite_scores_ic_no_vol.parquet 完全一致
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
MIN_DATES = 120  # 训练集最少交易日数
MIN_ROWS = 20000  # 训练集最少样本行数
ALPHA = 1e-4  # Lasso 正则强度（针对标准化 y）


# ============================================================
# 逐日横截面 MAD 去极值 + z-score
# ============================================================
def cs_standardize(df, factor_cols):
    """
    df 必须含列：date, 以及 factor_cols。
    返回同 index 的新 df，其中 factor_cols 列已横截面标准化。
    """
    out = df.copy()
    for c in factor_cols:
        # 每日 median
        med = df.groupby("date")[c].transform("median")
        # 每日 MAD = median(|x - med|)
        abs_dev = (df[c] - med).abs()
        mad = abs_dev.groupby(df["date"]).transform("median")
        k = 1.4826  # 让 MAD 与标准差可比
        lo = med - 3 * k * mad
        hi = med + 3 * k * mad
        x = df[c].clip(lo, hi)
        # 每日 z-score
        m = x.groupby(df["date"]).transform("mean")
        s = x.groupby(df["date"]).transform("std").replace(0, 1)
        out[c] = (x - m) / s
    return out


# ============================================================
# 主流程
# ============================================================
def main():
    # ---------- 加载因子面板 ----------
    print("[Lasso] 加载因子面板 ...")
    fp = pd.read_parquet(FACTOR_FILE).reset_index()
    fp["symbol"] = fp["symbol"].astype(str).str.zfill(6)
    fp["date"] = pd.to_datetime(fp["date"])
    print(f"  shape: {fp.shape}")

    # ---------- 加载价格，算 t+1 日收益 ----------
    print("[Lasso] 加载价格，计算 t+1 日收益 ...")
    panel = pd.read_parquet(PRICE_FILE)
    # 兼容列名：date → trade_date
    if "date" in panel.columns and "trade_date" not in panel.columns:
        panel = panel.rename(columns={"date": "trade_date"})
    panel["symbol"] = panel["symbol"].astype(str).str.zfill(6)
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel = panel.sort_values(["symbol", "trade_date"])
    panel["ret_next"] = panel.groupby("symbol")["close"].transform(
        lambda s: s.shift(-1) / s - 1.0
    )
    ret_df = panel[["trade_date", "symbol", "ret_next"]].rename(
        columns={"trade_date": "date"}
    )
    print(f"  收益样本: {len(ret_df):,}")

    # ---------- 合并因子 + 标签 ----------
    print("[Lasso] 合并 ...")
    df = fp.merge(ret_df, on=["date", "symbol"], how="left")
    print(f"  合并后: {df.shape}")

    # ---------- 调仓日历（直接读线性组输出，天然对齐） ----------
    print("[Lasso] 加载调仓日历（从线性组对齐）...")
    linear_file = os.path.join(PROC, "composite_scores_ic_no_vol.parquet")
    linear_index = pd.read_parquet(linear_file).index
    signal_dates = sorted(pd.to_datetime(linear_index).normalize())
    print(f"  调仓日数: {len(signal_dates)}（对齐线性组）")
    all_dates_arr = np.array(sorted(df["date"].unique()))

    # ---------- 逐个 set 合成 ----------
    for set_name, factor_cols in [("all8", ALL8), ("no_vol", NO_VOL)]:
        print(f"\n{'=' * 60}")
        print(f"[Lasso] set = {set_name}")
        print("=" * 60)

        scores = {}
        weights_log = []

        for i, sig in enumerate(signal_dates):
            sig = pd.Timestamp(sig)

            # 训练窗口：[sig-12m, sig) 的所有交易日
            tr_start = sig - pd.DateOffset(months=WINDOW_MONTHS)
            mask = (all_dates_arr >= np.datetime64(tr_start)) & (
                all_dates_arr < np.datetime64(sig)
            )
            tr_dates = all_dates_arr[mask]

            if len(tr_dates) < MIN_DATES:
                print(
                    f"  [{i + 1:>2}/{len(signal_dates)}] {sig.date()}: "
                    f"训练日期不足 ({len(tr_dates)}), skip"
                )
                continue

            train = df[df["date"].isin(tr_dates)].dropna(
                subset=factor_cols + ["ret_next"]
            )
            if len(train) < MIN_ROWS:
                print(
                    f"  [{i + 1:>2}/{len(signal_dates)}] {sig.date()}: "
                    f"训练样本不足 ({len(train)}), skip"
                )
                continue

            # 横截面标准化
            train_std = cs_standardize(
                train[["date"] + factor_cols].copy(), factor_cols
            )
            X_train = train_std[factor_cols].fillna(0.0).values
            y_train = train["ret_next"].values

            # y 标准化（避免 alpha 相对原始收益过强）
            y_mu = float(np.nanmean(y_train))
            y_sd = float(np.nanstd(y_train))
            if y_sd == 0 or np.isnan(y_sd):
                y_sd = 1.0
            y_train_std = (y_train - y_mu) / y_sd

            # 训练 Lasso
            lasso = Lasso(alpha=ALPHA, max_iter=5000, fit_intercept=True)
            lasso.fit(X_train, y_train_std)

            # 当日预测
            today = df[df["date"] == sig][["date", "symbol"] + factor_cols].copy()
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
            coef_s["n_dates"] = len(tr_dates)
            coef_s.name = sig
            weights_log.append(coef_s)

            nz = int(np.sum(lasso.coef_ != 0))
            print(
                f"  [{i + 1:>2}/{len(signal_dates)}] {sig.date()}: "
                f"train={len(train):>7d}  dates={len(tr_dates):>3d}  "
                f"nz={nz}/8  coef={np.round(lasso.coef_, 4).tolist()}"
            )

        if not scores:
            print(f"  [warn] set={set_name} 无输出")
            continue

        # ---------- 保存 ----------
        score_df = pd.DataFrame(scores).T
        score_df.index.name = "signal_date"
        out_score = os.path.join(PROC, f"composite_scores_lasso_{set_name}.parquet")
        score_df.to_parquet(out_score)
        print(f"\n  → {out_score}")
        print(f"    shape = {score_df.shape}, 列数（股票数） = {len(score_df.columns)}")

        weight_df = pd.DataFrame(weights_log).T
        out_w = os.path.join(PROC, f"composite_weights_lasso_{set_name}.csv")
        weight_df.to_csv(out_w)
        print(f"  → {out_w}")


if __name__ == "__main__":
    main()
