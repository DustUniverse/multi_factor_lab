"""把 fina_indicator 按 PIT（公告日）对齐到日频面板。

输出：
    data/processed/financial_panel_pit.parquet

字段：
    symbol, date, roe, netprofit_yoy, or_yoy, debt_to_assets

运行：
    python scripts/factors/build_financial_panel.py
"""

from pathlib import Path

import pandas as pd

from mfalpha.data.pit_align import align_financials_to_daily

# ---------- 路径 ----------
ROOT = Path(__file__).resolve().parents[2]
FACTOR_PANEL = ROOT / "data" / "processed" / "factor_panel.parquet"
FIN_DIR = ROOT / "data" / "raw" / "financial"
OUT_FILE = ROOT / "data" / "processed" / "financial_panel_pit.parquet"

# ---------- 要带过来的财务字段 ----------
FIN_COLS = ["roe", "netprofit_yoy", "or_yoy", "debt_to_assets"]

# ---------- 读日频面板（只取 symbol、date）----------
print("读日频面板...")
daily = pd.read_parquet(FACTOR_PANEL, columns=["symbol", "date"])
print(f"  {len(daily):,} 行，{daily['symbol'].nunique()} 只股票")

# ---------- 读财务数据 ----------
print("读财务数据...")
fs = sorted(FIN_DIR.glob("fina_indicator_part_*.parquet"))
fin = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
print(f"  {len(fin):,} 行")

# ---------- PIT 对齐 ----------
print("PIT 对齐（merge_asof）...")
result = align_financials_to_daily(daily, fin, FIN_COLS)
print(f"  对齐后 {len(result):,} 行")

# ---------- 保存 ----------
result.to_parquet(OUT_FILE, index=False)
print(f"[保存] {OUT_FILE.name}")

# ---------- 抽样验证：000001 平安银行 ----------
print("\n抽样验证：000001 在关键日期的财务字段")
sample = result[result["symbol"] == "000001"].sort_values("date").set_index("date")

check_dates = [
    "2019-09-30",  # 面板起始日
    "2020-03-31",  # 2019Q4 年报公告前
    "2020-04-30",  # 2019Q4 年报公告后，2020Q1 季报公告前
    "2024-04-25",  # 2024Q1 季报公告后
    "2024-09-30",  # 面板截止日
]
for d in check_dates:
    d_ts = pd.Timestamp(d)
    if d_ts in sample.index:
        row = sample.loc[d_ts]
        print(
            f"  {d}:  roe={row['roe']:>8.2f}  "
            f"netprofit_yoy={row['netprofit_yoy']:>8.2f}  "
            f"debt={row['debt_to_assets']:>7.2f}"
        )

# ---------- 缺失率汇总 ----------
print("\n各字段缺失率(%):")
print((result[FIN_COLS].isna().mean() * 100).round(2))
