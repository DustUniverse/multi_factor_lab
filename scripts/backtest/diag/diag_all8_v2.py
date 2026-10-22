"""诊断 lasso_all8 v2 对账逐期差异。"""

from pathlib import Path

import pandas as pd

PROC = Path(r"C:\Users\16075\code\multi_factor_lab\data\processed")
df = (
    pd.read_csv(
        PROC / "bt_vs_self_lasso_all8_v2.csv",
        parse_dates=["trade_date", "align_date"],
    )
    .sort_values("align_date")
    .reset_index(drop=True)
)

df["gross_diff"] = df["gross_ret"] - df["gross_ret_bt"]
df["net_diff"] = df["net_ret"] - df["net_ret_bt"]

cols = [
    "align_date",
    "gross_ret",
    "gross_ret_bt",
    "gross_diff",
    "net_diff",
    "turnover",
    "turnover_bt",
]
print("=== gross_diff 最大的 10 期（自研 > BT） ===")
print(
    df.sort_values("gross_diff", ascending=False).head(10)[cols].to_string(index=False)
)
print("\n=== gross_diff 最小的 10 期（BT > 自研） ===")
print(df.sort_values("gross_diff").head(10)[cols].to_string(index=False))
print("\n=== gross_diff 描述 ===")
print(df["gross_diff"].describe())
print("\n=== net_diff 描述 ===")
print(df["net_diff"].describe())
print("\n=== 按年汇总 ===")
df["year"] = df["align_date"].dt.year
print(
    df.groupby("year")
    .agg(
        n=("gross_diff", "count"),
        gross_sum=("gross_diff", "sum"),
        net_sum=("net_diff", "sum"),
    )
    .to_string()
)
