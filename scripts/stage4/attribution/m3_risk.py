"""M3: 风险归因 — 波动分解（行业/个股 MCTR）。

方法：
- 组合日收益 R_t（来自 m3_rebuild_daily_nav 产出）
- 个股日收益 r_i,t（open-to-open，与 engine 同源）
- MCTR_i = w_bar_i * Cov(r_i, R) / sigma_R，sum(MCTR_i) = sigma_R
- 行业 MCTR：先按申万一级 PIT 聚合行业收益，再套同一公式
- 输出年化波动与 MCTR 占比，保存 CSV
"""

import os

import numpy as np
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)  # 规避 pandas 2.x FutureWarning

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

NAV_FILE = os.path.join(PROC, "bt_nav_lasso_horizon_all8_daily.parquet")
HOLDINGS_FILE = os.path.join(PROC, "composite_holdings_lasso_horizon_all8.csv")
BT_FILE = os.path.join(PROC, "composite_bt_lasso_horizon_all8.csv")
PANEL_FILE = os.path.join(PROC, "daily_panel_tencent_clean.parquet")
IND_FILE = os.path.join(PROC, "industry_map.parquet")
NAV_REF_FILE = os.path.join(PROC, "bt_nav_ic_no_vol.parquet")

OUT_IND = os.path.join(PROC, "m3_mctr_industry.csv")
OUT_STOCK = os.path.join(PROC, "m3_mctr_stock_top.csv")


def load_holdings():
    h = pd.read_csv(HOLDINGS_FILE, parse_dates=["signal_date", "trade_date"])
    h["symbol"] = h["symbol"].astype(str).str.zfill(6)
    h = h.sort_values(["trade_date", "rank"])
    periods = h.groupby("trade_date")["symbol"].apply(list).sort_index().to_dict()
    return h, periods


def load_bt():
    bt = (
        pd.read_csv(
            BT_FILE, parse_dates=["signal_date", "trade_date", "next_trade_date"]
        )
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    return bt


def load_prices(symbols):
    panel = pd.read_parquet(PANEL_FILE)
    if "date" in panel.columns and "trade_date" not in panel.columns:
        panel = panel.rename(columns={"date": "trade_date"})
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel["symbol"] = panel["symbol"].astype(str).str.zfill(6)
    panel = panel[panel["symbol"].isin(set(symbols))].copy()
    return panel


def build_open_matrix(panel, symbols, full_idx):
    open_mat = pd.DataFrame(index=full_idx, columns=symbols, dtype=float)
    susp_mat = pd.DataFrame(False, index=full_idx, columns=symbols)
    for sym, g in panel.groupby("symbol", sort=False):
        g = g.sort_values("trade_date").set_index("trade_date")
        open_mat[sym] = g["open"].reindex(full_idx)
        s = g["is_suspended"].reindex(full_idx)
        susp_mat[sym] = s.astype("boolean").fillna(False).astype(bool)
    open_mat = open_mat.where(~susp_mat).ffill()
    return open_mat


def load_industry():
    ind = pd.read_parquet(IND_FILE)
    ind["symbol"] = ind["ts_code"].astype(str).str[:6]
    ind["in_date"] = pd.to_datetime(ind["in_date"])
    ind["out_date"] = pd.to_datetime(ind["out_date"])
    return ind


def industry_asof(ind_df, symbol, date):
    """PIT：in_date <= date 且 (out_date is NaT or out_date > date) 的 l1_name。"""
    sub = ind_df[ind_df["symbol"] == symbol]
    sub = sub[sub["in_date"] <= date]
    if sub.empty:
        return "未知"
    row = sub.sort_values("in_date").iloc[-1]
    if pd.notna(row["out_date"]) and row["out_date"] <= date:
        return "未知"
    return row["l1_name"]


def drift_weights(r):
    """r: T×N，从等权 1/N 开始漂移，返回 T×N 权重。"""
    T, N = r.shape
    w = np.full((T, N), 1.0 / N)
    for t in range(1, T):
        w[t] = w[t - 1] * (1 + r[t - 1])
        s = w[t].sum()
        if s > 0:
            w[t] /= s
    return w


def build_long_table(periods, bt, open_mat, full_idx, ind_df):
    """构造 (date, symbol, w, r) 长表，并附 industry。"""
    records = []
    periods_list = sorted(periods.items())
    for k in range(len(bt)):
        row = bt.iloc[k]
        td, ntd = row["trade_date"], row["next_trade_date"]
        try:
            i0, i1 = full_idx.get_loc(td), full_idx.get_loc(ntd)
        except KeyError:
            continue
        hold = periods_list[k][1]
        dates = full_idx[i0:i1]
        next_dates = full_idx[i0 + 1 : i1 + 1]
        if len(dates) == 0:
            continue
        o_t = open_mat.loc[dates, hold].values
        o_n = open_mat.loc[next_dates, hold].values
        r = np.nan_to_num(o_n / o_t - 1.0, nan=0.0, posinf=0.0, neginf=0.0)
        w = drift_weights(r)
        # 行业映射（每期只用 trade_date 做 asof）
        inds = [industry_asof(ind_df, sym, td) for sym in hold]
        for t in range(len(dates)):
            d = dates[t]
            for j, sym in enumerate(hold):
                records.append((d, sym, inds[j], w[t, j], r[t, j]))
    df = pd.DataFrame(records, columns=["date", "symbol", "industry", "w", "r"])
    return df


def mctr_from_long(df, R, group_col):
    """按 group_col 聚合加权收益贡献，返回 (mctr_df, sigma_daily)。

    精确分解：
        contrib_g,t = Σ_{i∈g} w_i,t * r_i,t
        R_t = Σ_g contrib_g,t  (严格成立)
        MCTR_g = Cov(contrib_g, R) / sigma_R
        Σ_g MCTR_g = sigma_R  (精确)
    """
    df = df.copy()
    df["contrib"] = df["w"] * df["r"]

    # 按 (date, group) 聚合 contrib
    pivot = df.groupby(["date", group_col])["contrib"].sum().unstack(fill_value=0.0)
    # 与 R 对齐
    common_idx = pivot.index.intersection(R.index)
    pivot = pivot.loc[common_idx]
    R_aligned = R.loc[common_idx]

    sigma = R_aligned.std()

    # 验证 Σ contrib = R
    r_check = pivot.sum(axis=1)
    max_diff = float((r_check - R_aligned).abs().max())
    print(f"  [check] Σ contrib vs R  max abs diff = {max_diff:.6e}")

    # MCTR = Cov(contrib_g, R) / sigma
    mctr_daily = pivot.apply(lambda col: col.cov(R_aligned)) / sigma

    # 参考统计：w_bar 和 n_obs（仅解读用，不参与公式）
    stats = df.groupby(group_col).agg(
        w_bar=("w", "mean"),
        n_obs=("w", "size"),
    )

    out = pd.DataFrame(
        {
            "w_bar": stats["w_bar"],
            "n_obs": stats["n_obs"],
            "mctr_daily": mctr_daily,
        }
    )
    out["mctr_ann"] = out["mctr_daily"] * np.sqrt(243)
    out["mctr_pct"] = out["mctr_daily"] / sigma
    out = out.sort_values("mctr_daily", ascending=False)
    return out, sigma


def main():
    print("[M3] 波动分解（行业/个股 MCTR）...")

    nav_df = pd.read_parquet(NAV_FILE)
    R = nav_df["daily_ret"]
    nav_ref = pd.read_parquet(NAV_REF_FILE)
    full_idx = pd.DatetimeIndex(nav_ref.index).sort_values()  # 用参考日历，含 bt 末期

    h, periods = load_holdings()
    bt = load_bt()
    symbols = sorted(set(h["symbol"].unique()))
    print(f"  持仓期数: {len(periods)}，BT 期数: {len(bt)}，唯一股票: {len(symbols)}")

    panel = load_prices(symbols)
    open_mat = build_open_matrix(panel, symbols, full_idx)
    print(
        f"  open 矩阵: {open_mat.shape}，NaN 比例: {open_mat.isna().mean().mean():.4f}"
    )

    ind_df = load_industry()
    print(f"  industry_map: {len(ind_df)} 行")

    print("  构造长表（date, symbol, industry, w, r）...")
    long_df = build_long_table(periods, bt, open_mat, full_idx, ind_df)
    d_min = long_df["date"].min().date()
    d_max = long_df["date"].max().date()
    print(f"  长表行数: {len(long_df)}，日期范围: {d_min} -> {d_max}")

    # 行业 MCTR（sigma 来自对齐后序列）
    ind_mctr, sigma = mctr_from_long(long_df, R, "industry")
    sigma_ann = sigma * np.sqrt(243)
    print(f"\n  组合日频波动（对齐后）: {sigma:.6f}，年化: {sigma_ann:.2%}")
    print("\n  === 行业 MCTR（年化，%）===")
    print(
        ind_mctr[["w_bar", "mctr_ann", "mctr_pct"]]
        .assign(
            w_bar=lambda x: (x["w_bar"] * 100).round(2),
            mctr_ann=lambda x: (x["mctr_ann"] * 100).round(3),
            mctr_pct=lambda x: (x["mctr_pct"] * 100).round(2),
        )
        .to_string()
    )
    print(
        f"  Σ MCTR_ann = {ind_mctr['mctr_ann'].sum():.4%}（应 ≈ 年化波动 {sigma_ann:.4%}）"
    )
    sum_ann = ind_mctr["mctr_ann"].sum()
    if abs(sum_ann - sigma_ann) / sigma_ann < 1e-6:
        print("  [ok] 行业 MCTR 分解精确（Σ = σ_ann）")
    else:
        print(f"  [warn] 行业 MCTR 分解不精确: Σ {sum_ann:.4%} vs σ {sigma_ann:.4%}")

    # 个股 MCTR（Top 20）
    stock_mctr, _ = mctr_from_long(long_df, R, "symbol")
    stock_mctr = stock_mctr.sort_values("mctr_ann", ascending=False)
    print("\n  === 个股 MCTR Top 20（年化，%）===")
    print(
        stock_mctr.head(20)[["w_bar", "mctr_ann", "mctr_pct", "n_obs"]]
        .assign(
            w_bar=lambda x: (x["w_bar"] * 100).round(2),
            mctr_ann=lambda x: (x["mctr_ann"] * 100).round(3),
            mctr_pct=lambda x: (x["mctr_pct"] * 100).round(2),
        )
        .to_string()
    )
    print(
        f"  Σ MCTR_ann（全部 {len(stock_mctr)} 只）= {stock_mctr['mctr_ann'].sum():.4%}"
    )

    # 保存
    ind_mctr.to_csv(OUT_IND)
    stock_mctr.to_csv(OUT_STOCK)
    print(f"\n  行业 MCTR 保存: {OUT_IND}")
    print(f"  个股 MCTR 保存: {OUT_STOCK}")


if __name__ == "__main__":
    main()
