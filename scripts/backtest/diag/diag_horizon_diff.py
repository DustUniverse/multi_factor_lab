"""临时诊断：对比自研引擎与 Backtrader 每期收益差异。"""

import pandas as pd

SELF_FILE = "data/processed/composite_bt_lasso_horizon_all8.csv"
BT_FILE = "data/processed/bt_vs_self_lasso_horizon_all8.csv"

self_df = pd.read_csv(SELF_FILE, parse_dates=["trade_date", "next_trade_date"])
self_df = self_df.sort_values("trade_date").reset_index(drop=True)

bt_df = pd.read_csv(BT_FILE, parse_dates=["trade_date"])
bt_df = bt_df.sort_values("trade_date").reset_index(drop=True)
bt_nav = dict(zip(bt_df["trade_date"], bt_df["nav_bt"]))

rows = []
for _, r in self_df.iterrows():
    td = r["trade_date"]
    ntd = r["next_trade_date"]
    if td in bt_nav and ntd in bt_nav:
        bt_ret = bt_nav[ntd] / bt_nav[td] - 1.0
        rows.append(
            {
                "trade_date": td.date(),
                "self_ret": r["net_ret"],
                "bt_ret": bt_ret,
                "diff": r["net_ret"] - bt_ret,
                "n_holding": r["n_holding"],
            }
        )

df = pd.DataFrame(rows)
print(df.to_string(index=False))

self_cum = (1 + df["self_ret"]).prod()
bt_cum = (1 + df["bt_ret"]).prod()
print()
print(f"自研累计: {self_cum:.4f}")
print(f"BT 累计:  {bt_cum:.4f}")
print(f"平均差异: {df['diff'].mean():.4%}")
print(f"差异标准差: {df['diff'].std():.4%}")

print()
print("差异最大的 5 期（自研高于 BT）:")
print(
    df.nlargest(5, "diff")[["trade_date", "self_ret", "bt_ret", "diff"]].to_string(
        index=False
    )
)

print()
print("差异最小的 5 期（BT 高于自研）:")
print(
    df.nsmallest(5, "diff")[["trade_date", "self_ret", "bt_ret", "diff"]].to_string(
        index=False
    )
)
