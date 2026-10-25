"""M3: 重建 lasso_horizon_all8 日频净值（engine 口径）。

engine 口径（与阶段三基线一致）：
- 每期 holdings 50 只等权买入持有，open-to-open。
- 停牌日 open 视为不可用，用之前最后可用 open ffill。
- 组合日收益 = Σ w_i,t * r_i,t（漂移权重），期初 w_i0 = 1/50。
- 期收益 = rets.mean() = 期初等权买入持有区间收益（M1 已验证 = gross_ret）。

产出：
- data/processed/bt_nav_lasso_horizon_all8_daily.parquet：日频 nav + daily_ret
- data/processed/m3_daily_nav_check.csv：51 期对账表

对账：
- 期内日频累乘 vs composite_bt 的 gross_ret，要求 max abs diff ≈ 0。
"""

import os

import numpy as np
import pandas as pd

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

HOLDINGS_FILE = os.path.join(PROC, "composite_holdings_lasso_horizon_all8.csv")
BT_FILE = os.path.join(PROC, "composite_bt_lasso_horizon_all8.csv")
PANEL_FILE = os.path.join(PROC, "daily_panel_tencent_clean.parquet")
NAV_REF_FILE = os.path.join(PROC, "bt_nav_ic_no_vol.parquet")  # 交易日历参考
OUT_FILE = os.path.join(PROC, "bt_nav_lasso_horizon_all8_daily.parquet")
CHECK_FILE = os.path.join(PROC, "m3_daily_nav_check.csv")


def load_holdings():
    """读持仓，返回 (holdings_df, {trade_date: [symbol, ...]})。"""
    h = pd.read_csv(HOLDINGS_FILE, parse_dates=["signal_date", "trade_date"])
    h["symbol"] = h["symbol"].astype(str).str.zfill(6)
    h = h.sort_values(["trade_date", "rank"])
    periods = h.groupby("trade_date")["symbol"].apply(list).sort_index().to_dict()
    return h, periods


def load_bt():
    """读 composite_bt 期收益，按 trade_date 排序。"""
    bt = (
        pd.read_csv(
            BT_FILE, parse_dates=["signal_date", "trade_date", "next_trade_date"]
        )
        .sort_values("trade_date")
        .reset_index(drop=True)
    )
    return bt


def load_prices(symbols):
    """读 daily panel，过滤到持仓股票，symbol 统一 6 位字符串。"""
    panel = pd.read_parquet(PANEL_FILE)
    if "date" in panel.columns and "trade_date" not in panel.columns:
        panel = panel.rename(columns={"date": "trade_date"})
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel["symbol"] = panel["symbol"].astype(str).str.zfill(6)
    panel = panel[panel["symbol"].isin(set(symbols))].copy()
    return panel


def build_open_matrix(panel, symbols, full_idx):
    """构造 symbols × full_idx 的 open 矩阵：停牌日设 NaN，再 ffill。"""
    open_mat = pd.DataFrame(index=full_idx, columns=symbols, dtype=float)
    susp_mat = pd.DataFrame(False, index=full_idx, columns=symbols)
    for sym, g in panel.groupby("symbol", sort=False):
        g = g.sort_values("trade_date").set_index("trade_date")
        open_mat[sym] = g["open"].reindex(full_idx)
        susp_mat[sym] = g["is_suspended"].reindex(full_idx).fillna(False).astype(bool)
    # 停牌日 open 设 NaN，再用之前最后可用 open ffill
    open_mat = open_mat.where(~susp_mat)
    open_mat = open_mat.ffill()
    return open_mat


def main():
    print("[M3] 重建 lasso_horizon_all8 日频净值（engine 口径）...")

    h, periods = load_holdings()
    bt = load_bt()
    symbols = sorted(set(h["symbol"].unique()))
    print(f"  持仓期数: {len(periods)}，唯一股票: {len(symbols)}")
    print(f"  BT 期数: {len(bt)}")

    panel = load_prices(symbols)
    print(f"  panel 行数（过滤后）: {len(panel)}")

    # 交易日历：用 bt_nav_ic_no_vol 的 index，保证与阶段三一致
    nav_ref = pd.read_parquet(NAV_REF_FILE)
    full_idx = pd.DatetimeIndex(nav_ref.index).sort_values()
    print(
        f"  交易日历: {full_idx.min().date()} -> {full_idx.max().date()}，"
        f"{len(full_idx)} 天"
    )

    open_mat = build_open_matrix(panel, symbols, full_idx)
    nan_ratio = open_mat.isna().mean().mean()
    print(f"  open 矩阵: {open_mat.shape}，NaN 比例: {nan_ratio:.4f}")

    # 逐期计算日频收益
    daily_rets = []  # [(date, ret), ...]
    period_check = (
        []
    )  # [(trade_date, next_trade_date, period_ret_daily, gross_ret), ...]

    periods_list = sorted(periods.items())  # [(trade_date, [symbols]), ...]
    for k in range(len(bt)):
        row = bt.iloc[k]
        td = row["trade_date"]
        ntd = row["next_trade_date"]
        gross = row["gross_ret"]

        # 校验 holdings 第 k 期与 bt 第 k 期 trade_date 对齐
        if periods_list[k][0] != td:
            print(
                f"  [warn] 第 {k} 期 trade_date 不一致: "
                f"holdings {periods_list[k][0]} vs bt {td}"
            )

        hold_syms = periods_list[k][1]

        # 期内交易日: [td, ntd) 在 full_idx 中的位置
        try:
            idx_start = full_idx.get_loc(td)
            idx_end = full_idx.get_loc(ntd)
        except KeyError as e:
            print(f"  [error] 第 {k} 期日期不在交易日历中: {e}")
            continue

        dates_for_ret = full_idx[idx_start:idx_end]  # 日收益日期 t
        next_dates = full_idx[idx_start + 1 : idx_end + 1]  # t+1
        if len(dates_for_ret) == 0:
            print(f"  [warn] 第 {k} 期无交易日: {td} -> {ntd}")
            continue

        # 取 open（(T, N) 矩阵）
        o_t = open_mat.loc[dates_for_ret, hold_syms].values
        o_next = open_mat.loc[next_dates, hold_syms].values

        # 个股日收益 open-to-open
        r = o_next / o_t - 1.0
        # NaN/Inf 设 0（停牌已 ffill，理论上不应有 NaN；保险）
        r = np.nan_to_num(r, nan=0.0, posinf=0.0, neginf=0.0)

        # 漂移权重累乘
        n = len(hold_syms)
        w = np.full(n, 1.0 / n)  # 期初等权
        port_rets = []
        for t in range(len(dates_for_ret)):
            rt = r[t]
            R = float(np.sum(w * rt))
            port_rets.append((dates_for_ret[t], R))
            # 权重漂移：w_i,t+1 = w_i,t * (1+r_i,t) / (1+R_t)
            w = w * (1 + rt) / (1 + R)

        period_ret_daily = float(np.prod([1 + x[1] for x in port_rets]) - 1)
        daily_rets.extend(port_rets)
        period_check.append((td, ntd, period_ret_daily, gross))

    # 拼接日频收益与 nav
    dr = pd.DataFrame(daily_rets, columns=["date", "ret"]).set_index("date")
    dr = dr.sort_index()
    dr = dr[~dr.index.duplicated(keep="first")]
    nav = (1 + dr["ret"]).cumprod()
    nav_df = pd.DataFrame({"nav": nav, "daily_ret": dr["ret"]})

    # 对账
    check = pd.DataFrame(
        period_check,
        columns=["trade_date", "next_trade_date", "period_ret_daily", "gross_ret"],
    )
    check["diff"] = check["period_ret_daily"] - check["gross_ret"]
    max_abs = check["diff"].abs().max()

    print("\n  === 对账（期内日频累乘 vs gross_ret）===")
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

    # 保存
    nav_df.to_parquet(OUT_FILE)
    check.to_csv(CHECK_FILE, index=False)
    print(f"\n  日频净值保存: {OUT_FILE}")
    print(
        f"  nav 行数: {len(nav_df)}，"
        f"区间: {nav_df.index.min().date()} -> {nav_df.index.max().date()}"
    )
    print(f"  期末 nav: {nav_df['nav'].iloc[-1]:.4f}")
    print(f"  gross 累乘: {(1 + bt['gross_ret']).prod():.4f}")
    print(f"  对账表保存: {CHECK_FILE}")


if __name__ == "__main__":
    main()
