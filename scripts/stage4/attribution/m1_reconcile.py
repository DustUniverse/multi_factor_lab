"""M1 对账：复现 engine 的 50 只等权 open-to-open 组合收益。

与 composite_bt_lasso_horizon_all8.csv 的 gross_ret 逐期对比，
max abs diff < 1e-6 才算口径一致，之后才能写 Brinson。

运行：
    python scripts/stage4/attribution/m1_reconcile.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED = Path("data/processed")

# ---------- 读数据 ----------
holdings = pd.read_csv(
    PROCESSED / "composite_holdings_lasso_horizon_all8.csv", dtype={"symbol": str}
)
holdings["symbol"] = holdings["symbol"].str.zfill(6)
holdings["trade_date"] = pd.to_datetime(holdings["trade_date"])

bt = pd.read_csv(PROCESSED / "composite_bt_lasso_horizon_all8.csv")
bt["trade_date"] = pd.to_datetime(bt["trade_date"])
bt["next_trade_date"] = pd.to_datetime(bt["next_trade_date"])

prices = pd.read_parquet(
    PROCESSED / "daily_panel_tencent_clean.parquet", columns=["symbol", "date", "open"]
)
prices["symbol"] = prices["symbol"].astype(str).str.zfill(6)
prices["date"] = pd.to_datetime(prices["date"])

prices_by_date = {d: g.set_index("symbol") for d, g in prices.groupby("date")}
print(f"价格面板: {prices.shape}, 交易日数: {len(prices_by_date)}")

# ---------- 逐期复现 ----------
records = []
for _, row in bt.iterrows():
    trade = row["trade_date"]
    next_trade = row["next_trade_date"]
    gross_bt = row["gross_ret"]

    h = holdings[holdings["trade_date"] == trade]["symbol"].tolist()
    trade_prices = prices_by_date.get(trade)
    next_prices = prices_by_date.get(next_trade)
    if len(h) == 0 or trade_prices is None or next_prices is None:
        records.append(
            {"trade_date": trade, "gross_bt": gross_bt, "gross_calc": np.nan, "n": 0}
        )
        continue

    open_t = trade_prices.reindex(h)["open"]
    open_next = next_prices.reindex(h)["open"]

    # 停牌/缺价：用 next_trade 之前最后一个可用 open 填充（与 engine 一致）
    missing = open_next[open_next.isna()].index
    if len(missing) > 0:
        last_avail = (
            prices[prices["symbol"].isin(missing) & (prices["date"] <= next_trade)]
            .sort_values("date")
            .groupby("symbol")["open"]
            .last()
        )
        open_next = open_next.fillna(last_avail)

    rets = (open_next / open_t - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
    gross_calc = float(rets.mean()) if len(rets) > 0 else np.nan

    records.append(
        {
            "trade_date": trade,
            "gross_bt": gross_bt,
            "gross_calc": gross_calc,
            "n": len(rets),
        }
    )

res = pd.DataFrame(records)
res["diff"] = res["gross_calc"] - res["gross_bt"]

print("\n逐期结果（前 5 期）:")
print(res.head().to_string())
print("\ndiff describe:")
print(res["diff"].describe())
print(f"\nmax abs diff: {res['diff'].abs().max():.2e}")
bad = res[res["diff"].abs() > 1e-6]
print(f"diff > 1e-6 的期数: {len(bad)}")
if len(bad) > 0:
    print(bad.sort_values("diff", key=abs, ascending=False).head(10).to_string())

# 保存对账结果，供报告引用
res.to_csv(PROCESSED / "m1_reconcile_lasso_horizon_all8.csv", index=False)
print(f"\n[OK] 已写入 {PROCESSED / 'm1_reconcile_lasso_horizon_all8.csv'}")
