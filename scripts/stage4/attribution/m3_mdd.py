"""M3d: MDD 区间归因（日频）。

1. 从日频 nav 识别所有回撤区间（peak -> trough），按深度排序；
2. 取 Top 3 回撤区间，用持仓 + 日频个股收益做行业/个股归因；
3. 贡献 = 区间内逐日 w_{i,t} * r_{i,t} 的算术和（非复利分解，报告注明）。

数据源与 M3a 同源：bt_nav_lasso_horizon_all8_daily.parquet + holdings + panel。
"""

import os

import numpy as np
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

NAV_FILE = os.path.join(PROC, "bt_nav_lasso_horizon_all8_daily.parquet")
HOLDINGS_FILE = os.path.join(PROC, "composite_holdings_lasso_horizon_all8.csv")
BT_FILE = os.path.join(PROC, "composite_bt_lasso_horizon_all8.csv")
PANEL_FILE = os.path.join(PROC, "daily_panel_tencent_clean.parquet")
IND_FILE = os.path.join(PROC, "industry_map.parquet")
NAV_REF_FILE = os.path.join(PROC, "bt_nav_ic_no_vol.parquet")

OUT_DD = os.path.join(PROC, "m3_mdd_periods.csv")
OUT_IND = os.path.join(PROC, "m3_mdd_industry.csv")
OUT_STOCK = os.path.join(PROC, "m3_mdd_stock.csv")

TOP_N_DD = 3
TOP_N_STOCK = 10


def load_holdings():
    h = pd.read_csv(HOLDINGS_FILE, parse_dates=["signal_date", "trade_date"])
    h["symbol"] = h["symbol"].astype(str).str.zfill(6)
    h = h.sort_values(["trade_date", "rank"])
    periods = h.groupby("trade_date")["symbol"].apply(list).sort_index().to_dict()
    return periods


def load_bt():
    return (
        pd.read_csv(
            BT_FILE, parse_dates=["signal_date", "trade_date", "next_trade_date"]
        )
        .sort_values("trade_date")
        .reset_index(drop=True)
    )


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
    sub = ind_df[ind_df["symbol"] == symbol]
    sub = sub[sub["in_date"] <= date]
    if sub.empty:
        return "未知"
    row = sub.sort_values("in_date").iloc[-1]
    if pd.notna(row["out_date"]) and row["out_date"] <= date:
        return "未知"
    return row["l1_name"]


def drift_weights(r):
    T, N = r.shape
    w = np.full((T, N), 1.0 / N)
    for t in range(1, T):
        w[t] = w[t - 1] * (1 + r[t - 1])
        s = w[t].sum()
        if s > 0:
            w[t] /= s
    return w


def find_drawdowns(nav):
    """返回 [(peak_date, trough_date, dd_depth, recovery_date or None, dur_days)]。

    回撤区间：nav 从峰值跌到谷底。recovery 为 nav 重回峰值的日期。
    """
    nav = nav.dropna()
    cummax = nav.cummax()
    dd = nav / cummax - 1.0
    # 用 drawdown 序列切分：dd<0 的连续段
    in_dd = dd < -1e-12
    periods = []
    start = None
    for d, flag in in_dd.items():
        if flag and start is None:
            start = d
        elif not flag and start is not None:
            seg = dd.loc[start:d]
            seg = seg.iloc[:-1]  # 最后一天已恢复
            if len(seg) > 0:
                trough = seg.idxmin()
                peak = nav.loc[:trough].idxmax()
                depth = float(seg.min())
                periods.append((peak, trough, depth, d))
            start = None
    # 末尾未恢复段
    if start is not None:
        seg = dd.loc[start:]
        trough = seg.idxmin()
        peak = nav.loc[:trough].idxmax()
        depth = float(seg.min())
        periods.append((peak, trough, depth, None))

    df = pd.DataFrame(periods, columns=["peak", "trough", "depth", "recovery"])
    df["dur_days"] = (df["trough"] - df["peak"]).dt.days
    df["rec_days"] = (df["recovery"] - df["trough"]).dt.days
    return df.sort_values("depth").reset_index(drop=True)


def period_contrib(peak, trough, periods_h, bt, open_mat, full_idx, ind_df):
    """回撤区间内的行业/个股贡献：Σ_t w_{i,t} * r_{i,t}（算术和）。"""
    # 覆盖 [peak, trough] 的持仓期
    rows = []
    bt_dates = bt["trade_date"].tolist()
    for k, td in enumerate(bt_dates):
        ntd = bt.iloc[k]["next_trade_date"]
        if ntd <= peak or td >= trough:
            continue
        try:
            i0, i1 = full_idx.get_loc(td), full_idx.get_loc(ntd)
        except KeyError:
            continue
        if td not in periods_h:
            continue
        hold = periods_h[td]
        dates = full_idx[i0:i1]
        next_dates = full_idx[i0 + 1 : i1 + 1]
        # 只保留落在回撤区间内的交易日
        mask = (dates >= peak) & (dates <= trough)
        if not mask.any():
            continue
        dates = dates[mask]
        next_dates = next_dates[mask]
        o_t = open_mat.loc[dates, hold].values
        o_n = open_mat.loc[next_dates, hold].values
        r = np.nan_to_num(o_n / o_t - 1.0, nan=0.0, posinf=0.0, neginf=0.0)
        w = drift_weights(r)
        inds = [industry_asof(ind_df, sym, td) for sym in hold]
        for t in range(len(dates)):
            for j, sym in enumerate(hold):
                rows.append((dates[t], sym, inds[j], float(w[t, j]), float(r[t, j])))
    df = pd.DataFrame(rows, columns=["date", "symbol", "industry", "w", "r"])
    df["contrib"] = df["w"] * df["r"]
    return df


def main():
    print("[M3d] MDD 区间归因（日频）...")

    nav_df = pd.read_parquet(NAV_FILE)
    nav = nav_df["nav"]
    full_idx = pd.DatetimeIndex(nav.index).sort_values()
    nav = nav.loc[full_idx]

    dd_df = find_drawdowns(nav)
    print(f"  识别回撤区间: {len(dd_df)} 个")
    print("\n  === 全期 Top 5 回撤 ===")
    show = dd_df.head(5).copy()
    show["depth"] = (show["depth"] * 100).round(2)
    show["dur_days"] = show["dur_days"].astype(int)
    show["rec_days"] = show["rec_days"].astype("Int64")
    print(show.to_string(index=False))

    # 数据准备
    periods = load_holdings()
    bt = load_bt()
    symbols = sorted({s for v in periods.values() for s in v})
    panel = load_prices(symbols)
    open_mat = build_open_matrix(panel, symbols, full_idx)
    ind_df = load_industry()

    top = dd_df.head(TOP_N_DD).reset_index(drop=True)
    ind_out, stock_out = [], []
    for idx, row in top.iterrows():
        peak, trough, depth = row["peak"], row["trough"], row["depth"]
        print(
            f"\n  === Top {idx + 1} 回撤: {peak.date()} -> {trough.date()}，"
            f"深度 {depth:.2%} ==="
        )
        df = period_contrib(peak, trough, periods, bt, open_mat, full_idx, ind_df)
        if df.empty:
            print("    [warn] 区间内无持仓数据")
            continue
        # 区间累计
        ind_agg = (
            df.groupby("industry")["contrib"].sum().sort_values().to_frame("contrib")
        )
        stk_agg = (
            df.groupby("symbol")["contrib"].sum().sort_values().to_frame("contrib")
        )
        total = df["contrib"].sum()
        print(f"    区间日贡献算术和: {total:.2%}")
        print("    行业拖累 Top 5（贡献最负）:")
        for ind, v in ind_agg.head(5).itertuples():
            print(f"      {ind:6s} {v:+.2%}")
        print("    个股拖累 Top 5:")
        for sym, v in stk_agg.head(5).itertuples():
            print(f"      {sym} {v:+.2%}")

        for ind, v in ind_agg.itertuples():
            ind_out.append(
                {
                    "rank": idx + 1,
                    "peak": peak,
                    "trough": trough,
                    "depth": depth,
                    "industry": ind,
                    "contrib": v,
                }
            )
        for sym, v in stk_agg.head(TOP_N_STOCK).itertuples():
            stock_out.append(
                {
                    "rank": idx + 1,
                    "peak": peak,
                    "trough": trough,
                    "depth": depth,
                    "symbol": sym,
                    "contrib": v,
                }
            )

    dd_df.to_csv(OUT_DD, index=False)
    pd.DataFrame(ind_out).to_csv(OUT_IND, index=False)
    pd.DataFrame(stock_out).to_csv(OUT_STOCK, index=False)
    print(f"\n  回撤区间保存: {OUT_DD}")
    print(f"  行业归因保存: {OUT_IND}")
    print(f"  个股归因保存: {OUT_STOCK}")


if __name__ == "__main__":
    main()
