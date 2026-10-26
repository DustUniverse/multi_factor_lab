"""M4 最终版：重建日频净值（engine 口径 + 仓位缩放）。

相对 m3_rebuild_daily_nav.py 的改动：
1. 持仓：composite_holdings_lasso_horizon_all8.csv → m4_final_holdings.csv
2. 期收益：composite_bt_lasso_horizon_all8.csv → m4_final_periods.csv
3. 输出：bt_nav_lasso_horizon_all8_daily.parquet → bt_nav_m4_final_daily.parquet
4. 对账：m3_daily_nav_check.csv → m4_daily_nav_check.csv
5. 仓位：每期期初股票权重 = pos/n，现金权重 = 1-pos，现金日收益 0
6. 对账口径：period_ret_daily vs pos × gross_ret（M3 是 gross_ret）

数学保证（现金日收益 0 时精确成立）：
    组合净值 N_t = pos × 等权组合净值 + (1-pos)
    期内收益 = pos × gross_ret

产出：
- data/processed/bt_nav_m4_final_daily.parquet（nav + daily_ret，gross 口径）
- data/processed/m4_daily_nav_check.csv（51 期对账表）
"""

import os

import numpy as np
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

HOLDINGS_FILE = os.path.join(PROC, "m4_final_holdings.csv")
BT_FILE = os.path.join(PROC, "m4_final_periods.csv")
PANEL_FILE = os.path.join(PROC, "daily_panel_tencent_clean.parquet")
NAV_REF_FILE = os.path.join(PROC, "bt_nav_ic_no_vol.parquet")
POS_FILE = os.path.join(PROC, "m4_position_series.parquet")
OUT_FILE = os.path.join(PROC, "bt_nav_m4_final_daily.parquet")
CHECK_FILE = os.path.join(PROC, "m4_daily_nav_check.csv")


def load_holdings():
    """读 M4 最终版持仓（无 signal_date），返回 (df, {trade_date: [symbol]})。"""
    h = pd.read_csv(HOLDINGS_FILE, parse_dates=["trade_date"])
    h["symbol"] = h["symbol"].astype(str).str.zfill(6)
    h = h.sort_values(["trade_date", "rank"])
    periods = h.groupby("trade_date")["symbol"].apply(list).sort_index().to_dict()
    return h, periods


def load_bt():
    """读 M4 最终版期收益，按 trade_date 排序。"""
    bt = (
        pd.read_csv(
            BT_FILE, parse_dates=["signal_date", "trade_date", "next_trade_date"]
        )
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    return bt


def load_pos() -> pd.Series:
    ps = pd.read_parquet(POS_FILE)["pos"]
    ps.index = pd.to_datetime(ps.index)
    return ps


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
        susp_mat[sym] = g["is_suspended"].reindex(full_idx).fillna(False).astype(bool)
    open_mat = open_mat.where(~susp_mat)
    open_mat = open_mat.ffill()
    return open_mat


def main():
    print("[M4日频] 重建 M4 最终版日频净值（engine 口径 + 仓位缩放）...")

    h, periods = load_holdings()
    bt = load_bt()
    pos_s = load_pos()
    symbols = sorted(set(h["symbol"].unique()))
    print(f"  持仓期数: {len(periods)}，唯一股票: {len(symbols)}")
    print(f"  BT 期数: {len(bt)}")
    print(f"  仓位序列: {len(pos_s)} 期，mean={pos_s.mean():.4f}")

    panel = load_prices(symbols)
    print(f"  panel 行数（过滤后）: {len(panel)}")

    nav_ref = pd.read_parquet(NAV_REF_FILE)
    full_idx = pd.DatetimeIndex(nav_ref.index).sort_values()
    print(
        f"  交易日历: {full_idx.min().date()} -> {full_idx.max().date()}，"
        f"{len(full_idx)} 天"
    )

    open_mat = build_open_matrix(panel, symbols, full_idx)
    nan_ratio = open_mat.isna().mean().mean()
    print(f"  open 矩阵: {open_mat.shape}，NaN 比例: {nan_ratio:.4f}")

    daily_rets = []  # [(date, ret), ...]
    period_check = []  # [(td, ntd, period_ret_daily, gross_ret, pos, pos_gross)]

    for k in range(len(bt)):
        row = bt.iloc[k]
        td = row["trade_date"]
        ntd = row["next_trade_date"]
        gross = row["gross_ret"]

        # 用 trade_date 直接取持仓，避免索引对齐问题
        hold_syms = periods.get(td)
        if hold_syms is None:
            print(f"  [warn] 第 {k} 期 trade_date={td.date()} 无持仓，skip")
            continue

        # 期初仓位（缺失用 1.0）
        pos_t = float(pos_s.get(td, 1.0))

        try:
            idx_start = full_idx.get_loc(td)
            idx_end = full_idx.get_loc(ntd)
        except KeyError as e:
            print(f"  [error] 第 {k} 期日期不在交易日历中: {e}")
            continue

        dates_for_ret = full_idx[idx_start:idx_end]
        next_dates = full_idx[idx_start + 1 : idx_end + 1]
        if len(dates_for_ret) == 0:
            print(f"  [warn] 第 {k} 期无交易日: {td.date()} -> {ntd.date()}")
            continue

        o_t = open_mat.loc[dates_for_ret, hold_syms].values
        o_next = open_mat.loc[next_dates, hold_syms].values

        r = o_next / o_t - 1.0
        r = np.nan_to_num(r, nan=0.0, posinf=0.0, neginf=0.0)

        # 期初：股票部分权重 pos/n，现金权重 1-pos
        n = len(hold_syms)
        w = np.full(n, pos_t / n)
        cash = 1.0 - pos_t

        port_rets = []
        for t in range(len(dates_for_ret)):
            rt = r[t]
            R = float(np.sum(w * rt))  # 现金日收益 0
            port_rets.append((dates_for_ret[t], R))
            # 股票权重漂移
            w = w * (1 + rt) / (1 + R)
            # 现金权重漂移
            cash = cash / (1 + R)

        period_ret_daily = float(np.prod([1 + x[1] for x in port_rets]) - 1)
        daily_rets.extend(port_rets)
        period_check.append((td, ntd, period_ret_daily, gross, pos_t, pos_t * gross))

    dr = pd.DataFrame(daily_rets, columns=["date", "ret"]).set_index("date")
    dr = dr.sort_index()
    dr = dr[~dr.index.duplicated(keep="first")]
    nav = (1 + dr["ret"]).cumprod()
    nav_df = pd.DataFrame({"nav": nav, "daily_ret": dr["ret"]})

    # 对账：日频累乘 vs pos × gross_ret
    check = pd.DataFrame(
        period_check,
        columns=[
            "trade_date",
            "next_trade_date",
            "period_ret_daily",
            "gross_ret",
            "pos",
            "pos_gross",
        ],
    )
    check["diff"] = check["period_ret_daily"] - check["pos_gross"]
    max_abs = check["diff"].abs().max()

    print("\n  === 对账（期内日频累乘 vs pos × gross_ret）===")
    print(f"  期数: {len(check)}")
    print(f"  max abs diff = {max_abs:.6e}")
    print(
        f"  平均 diff = {check['diff'].mean():+.6e}，"
        f"标准差 = {check['diff'].std():.6e}"
    )
    if max_abs > 1e-6:
        print("  [warn] 对账未通过，检查停牌/权重逻辑")
        print(
            check.reindex(check["diff"].abs().sort_values(ascending=False).index)
            .head(5)
            .to_string(index=False)
        )
    else:
        print("  [ok] 对账通过（diff ≈ 0）")

    nav_df.to_parquet(OUT_FILE)
    check.to_csv(CHECK_FILE, index=False)
    print(f"\n  日频净值保存: {OUT_FILE}")
    print(
        f"  nav 行数: {len(nav_df)}，"
        f"区间: {nav_df.index.min().date()} -> {nav_df.index.max().date()}"
    )
    print(f"  期末 nav: {nav_df['nav'].iloc[-1]:.4f}")
    print(f"  pos × gross 累乘: {(1 + check['pos_gross']).prod():.4f}")
    print(f"  对账表保存: {CHECK_FILE}")


if __name__ == "__main__":
    main()
