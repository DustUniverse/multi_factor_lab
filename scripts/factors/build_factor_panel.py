"""合并出 18 因子面板。

输入：
    data/processed/factor_panel_11f.parquet          11 因子（价量 7 + 技术 4）
    data/processed/financial_panel_pit.parquet   4 财务字段（PIT 对齐）
    data/raw/financial/daily_basic_*.parquet     PE/PB/换手率

输出：
    data/processed/factor_panel.parquet       18 因子

运行：
    python scripts/factors/build_factor_panel_v2.py
"""

from pathlib import Path

import pandas as pd

from mfalpha.data.pit_align import to_symbol
from mfalpha.factors.valuation import bp, ep_ttm

# ---------- 路径 ----------
ROOT = Path(__file__).resolve().parents[2]
PANEL_V1 = ROOT / "data" / "processed" / "factor_panel_11f.parquet"
FIN_PIT = ROOT / "data" / "processed" / "financial_panel_pit.parquet"
BASIC_DIR = ROOT / "data" / "raw" / "financial"
OUT_FILE = ROOT / "data" / "processed" / "factor_panel.parquet"

# ---------- 1. 读 11 因子面板 ----------
print("读 11 因子面板...")
panel = pd.read_parquet(PANEL_V1)
print(f"  {panel.shape}")
panel["date"] = pd.to_datetime(panel["date"])

# ---------- 2. 读 PIT 财务面板 ----------
print("读 PIT 财务面板...")
fin_pit = pd.read_parquet(FIN_PIT)
print(f"  {fin_pit.shape}")
fin_pit["date"] = pd.to_datetime(fin_pit["date"])

# ---------- 3. 读 daily_basic 并计算估值因子 ----------
print("读 daily_basic...")
fs = sorted(BASIC_DIR.glob("daily_basic_*.parquet"))
basic = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
print(f"  原始 {len(basic):,} 行")

basic["symbol"] = basic["ts_code"].map(to_symbol)
basic["date"] = pd.to_datetime(basic["trade_date"], format="%Y%m%d")
basic["ep_ttm"] = ep_ttm(basic["pe_ttm"])
basic["bp"] = bp(basic["pb"])
basic["turnover"] = pd.to_numeric(basic["turnover_rate"], errors="coerce")
basic = basic[["symbol", "date", "ep_ttm", "bp", "turnover"]]
print(f"  计算估值因子后 {basic.shape}")

# ---------- 4. 三方合并 ----------
print("合并...")
merged = panel.merge(fin_pit, on=["symbol", "date"], how="left")
merged = merged.merge(basic, on=["symbol", "date"], how="left")
print(f"  合并后 {merged.shape}")

# ---------- 5. 保存 ----------
merged.to_parquet(OUT_FILE, index=False)
print(f"[保存] {OUT_FILE.name}")

# ---------- 6. 验证 ----------
print("\n===== 验证 =====")
print(f"总行数：{len(merged):,}（应为 5,088,372）")
print(f"股票数：{merged['symbol'].nunique()}")
print(f"日期范围：{merged['date'].min().date()} ~ {merged['date'].max().date()}")

factor_cols = [
    "momentum_20",
    "reversal_20",
    "volatility_20",
    "corr_pv_20",
    "volume_ratio",
    "amplitude_20",
    "amihud_20",
    "rsi_14",
    "bias_20",
    "boll_dev_20",
    "macd_dev",
    "roe",
    "netprofit_yoy",
    "or_yoy",
    "debt_to_assets",
    "ep_ttm",
    "bp",
    "turnover",
]
print(f"因子数：{len(factor_cols)}（应为 18）")
print(f"缺失的因子列：{[c for c in factor_cols if c not in merged.columns]}")

print("\n各因子缺失率(%):")
missing = (merged[factor_cols].isna().mean() * 100).round(2)
print(missing.sort_values(ascending=False).to_string())

# ---------- 7. 抽样验证：000001 在 2024-09-30 ----------
print("\n抽样：000001 在 2024-09-30")
sample = merged[(merged["symbol"] == "000001") & (merged["date"] == "2024-09-30")]
if len(sample) > 0:
    s = sample.iloc[0]
    print(f"  ep_ttm   = {s['ep_ttm']:.6f}  (应 = 1/5.0471 ≈ 0.1981)")
    print(f"  bp       = {s['bp']:.6f}  (应 = 1/0.5752 ≈ 1.7385)")
    print(f"  turnover = {s['turnover']:.4f}")
    print(f"  roe      = {s['roe']:.4f}")
