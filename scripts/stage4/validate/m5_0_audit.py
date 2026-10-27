"""M5.0 数据体检：核对 M5.1 增量分析所需的 6 组 periods 与日频净值。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROC = Path("data/processed")

GROUPS = {
    "baseline": "composite_bt_lasso_horizon_all8.csv",
    "m4a_only": "m4a_bt_periods.csv",
    "m4b_only": "m4b_bt_periods_M4b_only.csv",
    "m4a_m4b": "m4_bt_periods.csv",
    "m4c_only": "m4c_bt_periods.csv",
    "full": "m4_final_periods.csv",
}

DAILY = {
    "baseline_daily": "bt_nav_lasso_horizon_all8_daily.parquet",
    "full_daily": "bt_nav_m4_final_daily.parquet",
}

POS = {
    "m4a_position": "m4a_position_series.parquet",
    "m4b_only_position": "m4b_pos_m4b_only.parquet",
    "m4a_m4b_position": "m4_position_series.parquet",
}


def audit_periods() -> None:
    print("=" * 70)
    print("[1] periods CSV 结构")
    print("=" * 70)
    for name, fname in GROUPS.items():
        p = PROC / fname
        if not p.exists():
            print(f"  {name:<10} MISSING: {fname}")
            continue
        df = pd.read_csv(p)
        date_col = "trade_date" if "trade_date" in df.columns else df.columns[0]
        print(f"\n  {name:<10} {fname}")
        print(f"    rows={len(df)}")
        print(f"    cols={list(df.columns)}")
        print(
            f"    {date_col} range: "
            f"{df[date_col].iloc[0]} ~ {df[date_col].iloc[-1]}"
        )


def audit_daily() -> None:
    print("\n" + "=" * 70)
    print("[2] 日频净值 parquet 结构")
    print("=" * 70)
    for name, fname in DAILY.items():
        p = PROC / fname
        if not p.exists():
            print(f"  {name:<16} MISSING: {fname}")
            continue
        df = pd.read_parquet(p)
        print(f"\n  {name:<16} {fname}")
        print(f"    rows={len(df)}")
        print(f"    cols={list(df.columns)}")
        print(f"    index: {df.index[0]} ~ {df.index[-1]}")


def audit_position() -> None:
    print("\n" + "=" * 70)
    print("[3] position_series 分布")
    print("=" * 70)
    for name, fname in POS.items():
        p = PROC / fname
        if not p.exists():
            print(f"  {name:<20} MISSING: {fname}")
            continue
        df = pd.read_parquet(p)
        col = "pos" if "pos" in df.columns else df.columns[0]
        v = df[col]
        print(f"\n  {name:<20} {fname}")
        print(
            f"    n={len(v)}  min={v.min():.4f}  "
            f"max={v.max():.4f}  mean={v.mean():.4f}"
        )
        print(f"    压仓期数 (<0.999): {(v < 0.999).sum()} / {len(v)}")


def main() -> None:
    audit_periods()
    audit_daily()
    audit_position()
    print("\n[完成] 数据体检结束。")


if __name__ == "__main__":
    main()
