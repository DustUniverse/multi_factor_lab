"""诊断 2024-04-01 期持仓收益，重点看 300641 的价格序列。"""

from pathlib import Path

import numpy as np
import pandas as pd

PROC = Path(r"C:\Users\16075\code\multi_factor_lab\data\processed")
T = pd.Timestamp("2024-04-01")
NT = pd.Timestamp("2024-05-06")

h = pd.read_csv(
    PROC / "composite_holdings_lasso_all8.csv",
    parse_dates=["trade_date"],
    dtype={"symbol": str},
)
h["symbol"] = h["symbol"].str.zfill(6)
syms = h[h["trade_date"] == T]["symbol"].tolist()
print(f"{T.date()} 期持仓数: {len(syms)}，含 300641: {'300641' in syms}")

p = pd.read_parquet(
    PROC / "daily_panel_tencent_clean.parquet",
    columns=["symbol", "date", "open", "close", "is_suspended", "is_limit_up"],
)
p["symbol"] = p["symbol"].astype(str).str.zfill(6)
p["date"] = pd.to_datetime(p["date"])

px_t = p[p["date"] == T].set_index("symbol")
px_nt = p[p["date"] == NT].set_index("symbol")

rows = []
for s in syms:
    o0 = px_t["open"].get(s, np.nan)
    o1 = px_nt["open"].get(s, np.nan)
    ret = o1 / o0 - 1 if pd.notna(o0) and pd.notna(o1) and o0 > 0 else np.nan
    rows.append({"symbol": s, "open_t": o0, "open_nt": o1, "ret": ret})

df = pd.DataFrame(rows)
print(f"\n缺 open_t: {df['open_t'].isna().sum()}")
print(f"缺 open_nt: {df['open_nt'].isna().sum()}")
print(f"自研均值（dropna）: {df['ret'].mean():.4%}")
print(f"全量均值（NaN 按 0）: {df['ret'].fillna(0).mean():.4%}")

print("\n缺 open_nt 的股票（自研会 dropna 掉）:")
print(df[df["open_nt"].isna()].to_string(index=False))

print("\n收益最高 10 只:")
print(df.sort_values("ret", ascending=False).head(10).to_string(index=False))

print("\n=== 300641 在 2024-03-01 ~ 2024-06-30 的价格序列 ===")
sub = p[
    (p["symbol"] == "300641")
    & (p["date"] >= "2024-03-01")
    & (p["date"] <= "2024-06-30")
].sort_values("date")
print(sub.to_string(index=False))
