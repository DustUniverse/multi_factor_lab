"""诊断：自研 periods 的 gross vs net 年化，量化成本拖累。"""

from pathlib import Path

import pandas as pd

PROC = Path(r"C:\Users\16075\code\multi_factor_lab\data\processed")
df = (
    pd.read_csv(
        PROC / "composite_bt_lasso_horizon_all8.csv",
        parse_dates=["trade_date", "next_trade_date"],
    )
    .sort_values("trade_date")
    .reset_index(drop=True)
)

gross_nav = (1 + df["gross_ret"]).cumprod()
net_nav = (1 + df["net_ret"]).cumprod()
n = len(df)
years = n / 12.0

print(f"期数: {n}")
print(
    f"gross 终值: {gross_nav.iloc[-1]:.4f}   "
    f"年化: {gross_nav.iloc[-1] ** (1 / years) - 1:+.2%}"
)
print(
    f"net   终值: {net_nav.iloc[-1]:.4f}   "
    f"年化: {net_nav.iloc[-1] ** (1 / years) - 1:+.2%}"
)
print(f"平均 turnover: {df['turnover'].mean():.4f}")
print(f"平均 cost:     {df['cost'].mean():.4%}")
print(f"累计 gross: {gross_nav.iloc[-1]:.4f}  累计 net: {net_nav.iloc[-1]:.4f}")
print(f"成本累计拖累: {gross_nav.iloc[-1] / net_nav.iloc[-1] - 1:.2%}")

print("\n不同仓位比例下的 gross 累计（对比 BT v2 零成本 6.7060）：")
for w in [0.94, 0.95, 0.96, 0.97, 0.98, 0.99, 1.00]:
    nav_w = (1 + df["gross_ret"] * w).cumprod()
    print(f"  仓位 {w:.2f}: 累计 {nav_w.iloc[-1]:.4f}")
