"""M4b 定稿：温和线性止损 + 与 M4a 合成。

规则：pos_m4b = clip(1 - |dd_sig| / 0.15, 0.7, 1.0)
      dd_sig = 满仓基线日频净值在 signal_date 的回撤
合成：pos_final = min(pos_m4a, pos_m4b)
"""

from __future__ import annotations

import os

import pandas as pd

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

NAV_FILE = os.path.join(PROC, "bt_nav_lasso_horizon_all8_daily.parquet")
CAL_FILE = os.path.join(PROC, "rebalance_calendar.csv")
M4A_FILE = os.path.join(PROC, "m4a_position_series.parquet")
OUT_FILE = os.path.join(PROC, "m4_position_series.parquet")  # M4a×M4b 合成

D = 0.15
MIN_POS = 0.70


def main() -> None:
    print(f"[M4b] 温和线性止损 D={D}, min_pos={MIN_POS} ...")
    nav = pd.read_parquet(NAV_FILE)
    nav.index = pd.to_datetime(nav.index)
    dd = nav["nav"] / nav["nav"].cummax() - 1.0

    cal = pd.read_csv(CAL_FILE, parse_dates=["signal_date", "trade_date"])
    dd_sig = dd.reindex(cal["signal_date"], method="ffill")
    dd_sig.index = pd.to_datetime(cal["trade_date"])

    pos_m4b = (1.0 - dd_sig.abs() / D).clip(lower=MIN_POS, upper=1.0).fillna(1.0)
    pos_m4b.name = "pos_m4b"

    m4a = pd.read_parquet(M4A_FILE)["pos"]
    m4a.index = pd.to_datetime(m4a.index)
    pos_final = pd.concat([m4a, pos_m4b], axis=1).min(axis=1)
    pos_final.name = "pos"
    pos_final.index.name = "trade_date"

    print("\n  pos_m4b 分布:")
    print(pos_m4b.describe().to_string())
    print(f"  压仓期数 (pos_m4b<0.999): {(pos_m4b < 0.999).sum()} / {len(pos_m4b)}")
    print("\n  pos_final 分布:")
    print(pos_final.describe().to_string())

    print("\n  2024 年逐期 dd / pos_m4b / pos_m4a / pos_final:")
    mask = pos_final.index >= "2024-01-01"
    for dt in pos_final.index[mask]:
        print(
            f"    {dt.date()}  dd={dd_sig.loc[dt]:+.4f}  "
            f"m4b={pos_m4b.loc[dt]:.2f}  m4a={m4a.loc[dt]:.2f}  "
            f"final={pos_final.loc[dt]:.2f}"
        )

    pos_final.to_frame().to_parquet(OUT_FILE)
    print(f"\n  保存: {OUT_FILE}")


if __name__ == "__main__":
    main()
