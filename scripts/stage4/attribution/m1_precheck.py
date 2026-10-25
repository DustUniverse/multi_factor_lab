"""M1 前置：Brinson 数据对齐验证。

只做三件事，不涉及个股收益：
1. 取 2023-01-03 一期的 50 只持仓，PIT 匹配申万一级行业；
2. HS300 权重 asof 到 2023-01-03，算基准行业权重；
3. 打印 daily_panel 结构，为个股收益对账做准备。

运行：
    python scripts/stage4/attribution/m1_precheck.py
"""

from pathlib import Path

import pandas as pd

PROCESSED = Path("data/processed")
TGT = "2023-01-03"  # 选 2023 年第一期，与 brinson_lasso_all8_2023.csv 对账

# ---------- 1. 持仓 ----------
holdings = pd.read_csv(
    PROCESSED / "composite_holdings_lasso_horizon_all8.csv", dtype={"symbol": str}
)
holdings["symbol"] = holdings["symbol"].str.zfill(6)
print("holdings 期数:", holdings["trade_date"].nunique())
print("每期持仓数 describe:\n", holdings.groupby("trade_date").size().describe())

h = holdings[holdings["trade_date"] == TGT].copy()
print(f"\n[{TGT}] 持仓 {len(h)} 只，前 10:", h["symbol"].tolist()[:10])

# ---------- 2. PIT 行业匹配 ----------
ind = pd.read_parquet(PROCESSED / "industry_map.parquet")
ind["in_date"] = pd.to_datetime(ind["in_date"])
ind["out_date"] = pd.to_datetime(ind["out_date"])

sb = pd.read_parquet(PROCESSED / "stock_basic.parquet")
sym2ts = sb.set_index("symbol")["ts_code"].to_dict()
h["ts_code"] = h["symbol"].map(sym2ts)
print("ts_code 缺失:", int(h["ts_code"].isna().sum()))

tgt_ts = pd.Timestamp(TGT)
ind_t = ind[
    (ind["in_date"] <= tgt_ts) & (ind["out_date"].isna() | (tgt_ts < ind["out_date"]))
]
print("PIT 行业快照行数:", len(ind_t))

m = h.merge(ind_t[["ts_code", "l1_name"]], on="ts_code", how="left")
print("行业缺失:", int(m["l1_name"].isna().sum()))
print("组合行业分布:\n", m["l1_name"].value_counts())

# ---------- 3. HS300 权重 asof ----------
w = pd.read_parquet(PROCESSED / "hs300_weight.parquet")
w["trade_date"] = pd.to_datetime(w["trade_date"])
w = w[w["trade_date"] <= tgt_ts]
snap_date = w["trade_date"].max()
last_w = w[w["trade_date"] == snap_date].copy()
last_w["weight"] = last_w["weight"] / 100.0  # 百分比 -> 小数
print(
    f"\n基准权重快照日: {snap_date.date()}, 成分数: {len(last_w)}, "
    f"sum={last_w['weight'].sum():.4f}"
)

b = last_w.merge(
    ind_t[["ts_code", "l1_name"]], left_on="con_code", right_on="ts_code", how="left"
)
print("基准行业缺失:", int(b["l1_name"].isna().sum()))
bench_ind_w = b.groupby("l1_name")["weight"].sum().sort_values(ascending=False)
print("基准行业权重 Top10:\n", bench_ind_w.head(10))

# ---------- 4. daily_panel 结构 ----------
print("\n=== daily_panel 结构 ===")
for f in ["daily_panel_tencent_clean.parquet", "daily_panel.parquet"]:
    p = PROCESSED / f
    if p.exists():
        df = pd.read_parquet(p)
        print(f"{f}: shape={df.shape}")
        print("columns:", list(df.columns))
        print(df.head(2).to_string())
        break
