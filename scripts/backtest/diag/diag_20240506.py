"""拆解 2024-05-06 这一期每只持仓股的 open-to-open 收益。"""

from pathlib import Path

import numpy as np
import pandas as pd

PROC = Path(r"C:\Users\16075\code\multi_factor_lab\data\processed")
T = pd.Timestamp("2024-05-06")

h = pd.read_csv(
    PROC / "composite_holdings_lasso_all8.csv",
    parse_dates=["trade_date"],
    dtype={"symbol": str},
)
h["symbol"] = h["symbol"].str.zfill(6)
dates = sorted(h["trade_date"].unique())
i = dates.index(T)
NT = dates[i + 1]
print(f"本期 {T.date()} -> 下一期 {NT.date()}")

syms = h[h["trade_date"] == T]["symbol"].tolist()
print(f"持仓数: {len(syms)}")

p = pd.read_parquet(
    PROC / "daily_panel_tencent_clean.parquet",
    columns=["symbol", "date", "open", "is_suspended", "is_limit_up"],
)
p["symbol"] = p["symbol"].astype(str).str.zfill(6)
p["date"] = pd.to_datetime(p["date"])
px_t = p[p["date"] == T].set_index("symbol")
px_nt = p[p["date"] == NT].set_index("symbol")

rows = []
for s in syms:
    o0 = px_t["open"].get(s, np.nan)
    o1 = px_nt["open"].get(s, np.nan)
    sus0 = px_t["is_suspended"].get(s, np.nan)
    sus1 = px_nt["is_suspended"].get(s, np.nan)
    ret = o1 / o0 - 1 if pd.notna(o0) and pd.notna(o1) and o0 > 0 else np.nan
    rows.append(
        {
            "symbol": s,
            "open_t": o0,
            "open_nt": o1,
            "ret": ret,
            "sus_t": sus0,
            "sus_nt": sus1,
        }
    )

df = pd.DataFrame(rows)
print(f"\n缺 open_t: {df['open_t'].isna().sum()}")
print(f"缺 open_nt: {df['open_nt'].isna().sum()}")
print(f"收益 NaN:  {df['ret'].isna().sum()}")
print(f"\n自研均值（dropna）:       {df['ret'].mean():.4%}")
print(f"全量均值（NaN 按 0）:     {df['ret'].fillna(0).mean():.4%}")

print("\n缺 open_nt 的股票（自研会 dropna 掉）:")
print(df[df["open_nt"].isna()].to_string(index=False))

print("\n收益最高 10 只:")
print(df.sort_values("ret", ascending=False).head(10).to_string(index=False))

print("\n收益最低 10 只:")
print(df.sort_values("ret").head(10).to_string(index=False))
