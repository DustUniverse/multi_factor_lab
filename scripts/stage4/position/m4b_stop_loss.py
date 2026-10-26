"""M4b: 回撤止损仓位（与 M4a 合成）。

信号源：满仓基线日频净值 bt_nav_lasso_horizon_all8_daily.parquet
        （保守：实际执行仓位更低，真实回撤更浅，止损偏早触发）
回撤：dd_t = nav_t / cummax(nav)_t - 1
采样：每个调仓日 signal_date 取当日（或之前最后交易日）dd
规则（hysteresis，从深到浅）：
    dd > -5%:           pos = 1.0（完全恢复）
    -10% < dd <= -5%:   维持上期（滞回区，防震荡）
    -15% < dd <= -10%:  pos = 0.7
    -20% < dd <= -15%:  pos = 0.4
    dd <= -20%:         pos = 0.0（清仓）
合成：pos_final = min(pos_m4a, pos_m4b)

产出：
- data/processed/m4b_position_series.parquet（index=trade_date, value=pos_final）
- data/processed/m4b_pos_m4b_only.parquet（仅 M4b，供诊断）
"""

from __future__ import annotations

import os

import pandas as pd

ROOT = r"C:\Users\16075\code\multi_factor_lab"
PROC = os.path.join(ROOT, "data", "processed")

NAV_FILE = os.path.join(PROC, "bt_nav_lasso_horizon_all8_daily.parquet")
CAL_FILE = os.path.join(PROC, "rebalance_calendar.csv")
M4A_FILE = os.path.join(PROC, "m4a_position_series.parquet")
OUT_FILE = os.path.join(PROC, "m4b_position_series.parquet")
OUT_M4B_ONLY = os.path.join(PROC, "m4b_pos_m4b_only.parquet")


def compute_pos_m4b(dd_sig: pd.Series) -> pd.Series:
    """按 hysteresis 规则把 dd 序列转成 pos_m4b。"""
    pos = []
    prev = 1.0
    for d in dd_sig.values:
        if pd.isna(d):
            p = 1.0
        elif d > -0.05:
            p = 1.0
        elif d > -0.10:
            p = prev  # 滞回区：维持上期
        elif d > -0.15:
            p = 0.7
        elif d > -0.20:
            p = 0.4
        else:
            p = 0.0
        pos.append(p)
        prev = p
    return pd.Series(pos, index=dd_sig.index)


def main() -> None:
    print("[M4b] 回撤止损仓位计算 ...")
    nav = pd.read_parquet(NAV_FILE)
    nav.index = pd.to_datetime(nav.index)
    nav_s = nav["nav"]
    dd = nav_s / nav_s.cummax() - 1.0
    print(f"  日频净值: {len(nav_s)} 天, dd 最低 {dd.min():.4f} @ {dd.idxmin().date()}")

    cal = pd.read_csv(CAL_FILE, parse_dates=["signal_date", "trade_date"])
    dd_sig = dd.reindex(cal["signal_date"], method="ffill")
    dd_sig.index = pd.to_datetime(cal["trade_date"])

    pos_m4b = compute_pos_m4b(dd_sig)
    pos_m4b.name = "pos_m4b"

    print("\n  pos_m4b 分布:")
    print(pos_m4b.describe().to_string())
    print(f"  触发止损期数 (pos_m4b<0.999): {(pos_m4b < 0.999).sum()} / {len(pos_m4b)}")
    print(f"  清仓期数 (pos_m4b==0): {(pos_m4b == 0).sum()}")

    print("\n  2024 年逐期 dd / pos_m4b:")
    for dt in pos_m4b.index[pos_m4b.index >= "2024-01-01"]:
        print(
            f"    {dt.date()}  dd={dd_sig.loc[dt]:+.4f}  pos_m4b={pos_m4b.loc[dt]:.2f}"
        )

    m4a = pd.read_parquet(M4A_FILE)["pos"]
    m4a.index = pd.to_datetime(m4a.index)
    pos_final = pd.concat([m4a, pos_m4b], axis=1).min(axis=1)
    pos_final.name = "pos"
    pos_final.index.name = "trade_date"

    print("\n  pos_final 分布:")
    print(pos_final.describe().to_string())
    n_m4b_dom = (pos_m4b < m4a.reindex(pos_m4b.index)).sum()
    print(f"  M4b 主导期数 (pos_m4b < m4a): {n_m4b_dom} / {len(pos_final)}")

    pos_final.to_frame().to_parquet(OUT_FILE)
    pos_m4b.to_frame().to_parquet(OUT_M4B_ONLY)
    print(f"\n  保存: {OUT_FILE}")
    print(f"  保存: {OUT_M4B_ONLY}")


if __name__ == "__main__":
    main()
