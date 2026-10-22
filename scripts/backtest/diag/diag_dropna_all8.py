"""诊断：自研每期因 next open 缺失被 dropna 掉的股票数。"""

from pathlib import Path

import pandas as pd

PROC = Path(r"C:\Users\16075\code\multi_factor_lab\data\processed")

prices = pd.read_parquet(
    PROC / "daily_panel_tencent_clean.parquet", columns=["symbol", "date", "open"]
)
prices["symbol"] = prices["symbol"].astype(str).str.zfill(6)
prices["date"] = pd.to_datetime(prices["date"])
px = {d: g.set_index("symbol")["open"] for d, g in prices.groupby("date")}

h = pd.read_csv(
    PROC / "composite_holdings_lasso_all8.csv",
    parse_dates=["trade_date"],
    dtype={"symbol": str},
)
h["symbol"] = h["symbol"].str.zfill(6)
hold = {d: g["symbol"].tolist() for d, g in h.groupby("trade_date")}
dates = sorted(hold.keys())

total_missing = 0
n_periods = 0
for i in range(len(dates) - 1):
    t, nt = dates[i], dates[i + 1]
    syms = hold[t]
    if nt not in px:
        print(f"{t.date()} -> {nt.date()}: next date 无价格面板")
        continue
    n_periods += 1
    opn = px[nt].reindex(syms)
    miss = int(opn.isna().sum())
    total_missing += miss
    if miss > 0:
        missing_syms = opn[opn.isna()].index.tolist()
        print(f"{t.date()} -> {nt.date()}: 缺 {miss}/{len(syms)}  {missing_syms}")

print(f"\n有效对比期数: {n_periods}")
print(f"累计缺价股票次数: {total_missing}")
print(f"平均每期缺: {total_missing / max(n_periods, 1):.2f} 只")
