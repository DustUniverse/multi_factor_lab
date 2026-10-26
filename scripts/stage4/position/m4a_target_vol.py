"""M4a: 波动率目标仓位管理。

口径：
- 日频净值 bt_nav_lasso_horizon_all8_daily.parquet（M3 重建，engine 口径）
- 滚动 60 日年化波动 vol60（min_periods=60），窗口右端点 <= signal_date（无前视）
- 目标波动 TARGET_VOL=20%，pos_t = min(1.0, TARGET_VOL / vol60_t)
- vol60 为 NaN 的期（前 11 期，日频净值不足 60 日）pos=1.0（满仓，等同基线）
- 对齐到 trade_date，输出 position_series

产出：
- data/processed/m4a_position_series.parquet（index=trade_date, value=pos）
- 打印 pos 分布与关键期
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

NAV_FILE = os.path.join(PROC, "bt_nav_lasso_horizon_all8_daily.parquet")
CAL_FILE = os.path.join(PROC, "rebalance_calendar.csv")
OUT_FILE = os.path.join(PROC, "m4a_position_series.parquet")

TARGET_VOL = 0.30
FLOOR = 0.50  # 新增
WINDOW = 60
MIN_PERIODS = 60
ANN = 252


def main() -> None:
    print("[M4a] 波动率目标仓位计算 ...")
    nav = pd.read_parquet(NAV_FILE)
    nav.index = pd.to_datetime(nav.index)
    ret = nav["daily_ret"]
    vol = ret.rolling(WINDOW, min_periods=MIN_PERIODS).std() * np.sqrt(ANN)
    print(f"  日频净值: {len(nav)} 天, {nav.index[0].date()} -> {nav.index[-1].date()}")
    print(f"  vol60 首个有效: {vol.first_valid_index()} = {vol.dropna().iloc[0]:.4f}")

    cal = pd.read_csv(CAL_FILE, parse_dates=["signal_date", "trade_date"])
    # 无前视：每个 signal_date 取 <= 它的最后一个 vol 值
    vol_sig = vol.reindex(cal["signal_date"], method="ffill")
    vol_sig.index = cal.index
    pos = np.minimum(1.0, TARGET_VOL / vol_sig).fillna(1.0)
    pos = pos.clip(lower=FLOOR)  # 新增这行
    print(f"  vol60 有效期数: {vol_sig.notna().sum()} / {len(cal)}")

    ps = pd.Series(pos.values, index=pd.to_datetime(cal["trade_date"]), name="pos")
    ps.index.name = "trade_date"

    print("\n  pos 分布:")
    print(ps.describe().to_string())
    print(f"\n  满仓期数 (pos>=0.999): {(ps >= 0.999).sum()} / {len(ps)}")
    print(f"  压仓期数 (pos<0.999):  {(ps < 0.999).sum()}")
    print(f"  最小 pos: {ps.min():.4f} @ {ps.idxmin().date()}")
    print(f"  最大 pos: {ps.max():.4f}")

    p24 = ps[ps.index >= "2024-01-01"]
    print("\n  2024 年 pos 最低 5 期:")
    print(p24.nsmallest(5).to_string())

    for d in ["2024-05-06", "2024-06-03", "2024-07-01"]:
        if pd.Timestamp(d) in ps.index:
            print(f"  {d} pos = {ps.loc[pd.Timestamp(d)]:.4f}")

    ps.to_frame().to_parquet(OUT_FILE)
    print(f"\n  保存: {OUT_FILE}")


if __name__ == "__main__":
    main()
