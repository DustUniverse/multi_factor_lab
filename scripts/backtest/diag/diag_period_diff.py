"""逐期对比：自研 gross_ret vs BT 零成本 period_ret，并关联持仓收益离散度。"""

from pathlib import Path

import pandas as pd

PROC = Path(r"C:\Users\16075\code\multi_factor_lab\data\processed")

bt = (
    pd.read_csv(
        PROC / "bt_vs_self_lasso_horizon_all8_nocost_10x.csv",
        parse_dates=["trade_date", "align_date"],
    )
    .sort_values("align_date")
    .reset_index(drop=True)
)
bt["bt_period_ret"] = bt["nav_bt"].pct_change()

self_df = (
    pd.read_csv(
        PROC / "composite_bt_lasso_horizon_all8.csv",
        parse_dates=["trade_date", "next_trade_date"],
    )
    .sort_values("trade_date")
    .reset_index(drop=True)
)
self_df["align_date"] = self_df["next_trade_date"]

merged = (
    pd.merge(
        self_df[["align_date", "gross_ret", "net_ret", "turnover", "n_holding"]],
        bt[["align_date", "bt_period_ret", "nav_bt"]],
        on="align_date",
        how="inner",
    )
    .dropna(subset=["bt_period_ret"])
    .reset_index(drop=True)
)
merged["diff"] = merged["gross_ret"] - merged["bt_period_ret"]

# 每期持仓股票的 open-to-open 收益离散度
prices = pd.read_parquet(
    PROC / "daily_panel_tencent_clean.parquet", columns=["symbol", "date", "open"]
)
prices["symbol"] = prices["symbol"].astype(str).str.zfill(6)
prices["date"] = pd.to_datetime(prices["date"])
px = {d: g.set_index("symbol")["open"] for d, g in prices.groupby("date")}

h = pd.read_csv(
    PROC / "composite_holdings_lasso_horizon_all8.csv",
    parse_dates=["trade_date"],
    dtype={"symbol": str},
)
h["symbol"] = h["symbol"].str.zfill(6)
hold = {d: g["symbol"].tolist() for d, g in h.groupby("trade_date")}
dates = sorted(hold.keys())

disp = {}
for i in range(len(dates) - 1):
    t, nt = dates[i], dates[i + 1]
    syms = hold[t]
    if t not in px or nt not in px:
        continue
    rets = (px[nt].reindex(syms) / px[t].reindex(syms) - 1).dropna()
    if len(rets) > 1:
        disp[t] = rets.std()

merged["dispersion"] = merged["align_date"].map(
    {pd.Timestamp(k): v for k, v in disp.items()}
)

print(f"期数: {len(merged)}")
print(f"gross 平均:  {merged['gross_ret'].mean():+.4%}")
print(f"BT(0) 平均:  {merged['bt_period_ret'].mean():+.4%}")
print(f"差异平均:    {merged['diff'].mean():+.4%}")
print(f"差异标准差:  {merged['diff'].std():.4%}")
print(f"累计 gross:  {(1 + merged['gross_ret']).prod():.4f}")
print(f"累计 BT(0):  {(1 + merged['bt_period_ret']).prod():.4f}")
gross_prod = (1 + merged["gross_ret"]).prod()
bt_prod = (1 + merged["bt_period_ret"]).prod()
print(f"累计比值:    {gross_prod / bt_prod:.4f}")

print(f"\n差异 vs turnover    相关系数: {merged['diff'].corr(merged['turnover']):.4f}")
print(f"差异 vs dispersion  相关系数: {merged['diff'].corr(merged['dispersion']):.4f}")

print("\n最大 10 个 |差异| 期:")
top = merged.reindex(merged["diff"].abs().sort_values(ascending=False).index).head(10)
print(
    top[
        ["align_date", "gross_ret", "bt_period_ret", "diff", "turnover", "dispersion"]
    ].to_string(index=False)
)

merged["year"] = merged["align_date"].dt.year
print("\n按年汇总:")
print(
    merged.groupby("year")
    .agg(
        n=("diff", "count"),
        diff_sum=("diff", "sum"),
        diff_mean=("diff", "mean"),
        disp_mean=("dispersion", "mean"),
    )
    .to_string()
)
