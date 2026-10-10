"""M4 Step3 验证：对比中性化前后的因子分布与 IC。

用法（项目根目录、激活 .venv 后）：
    python scripts/probe/check_neutralization.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

NEU_PATH = _ROOT / "data" / "processed" / "factor_panel_neutralized.parquet"
FP_PATH = _ROOT / "data" / "processed" / "factor_panel.parquet"
PRICE_PATH = _ROOT / "data" / "processed" / "daily_panel_tencent_clean.parquet"

PERIOD = 20


def main() -> None:
    print("[验证] 中性化前后对比")

    print("  1) 读中性化面板 ...")
    neu = pd.read_parquet(NEU_PATH)
    print(f"     shape = {neu.shape}")
    print(f"     列名  = {list(neu.columns)}")

    # smoke 阶段只跑了 turnover，列名就是 'turnover'
    factor = neu.columns[0]
    print(f"     待验证因子 = {factor}")

    print("  2) 读原始 factor_panel 的同一因子 ...")
    orig = pd.read_parquet(FP_PATH, columns=["date", "symbol", factor])
    orig = orig.set_index(["date", "symbol"])

    # 重命名避免列名冲突
    neu_col = neu[factor].rename(f"{factor}_neu")

    print("  3) 按 (date, symbol) 对齐 ...")
    df = pd.concat([orig, neu_col], axis=1, join="inner")
    print(f"     对齐后行数 = {len(df)}")

    print("\n  4) 分布对比：")
    print(
        f"     原始 {factor:12s}: mean={df[factor].mean():+.6f}  "
        f"std={df[factor].std():.6f}"
    )
    print(
        f"     中性化 {factor:10s}: mean={df[f'{factor}_neu'].mean():+.8f}  "
        f"std={df[f'{factor}_neu'].std():.6f}"
    )

    # 中性化残差理论上 mean ≈ 0（每天都是 OLS 残差）
    # 全局 mean 因样本不同而不完全为 0，但应该非常接近
    neu_mean = df[f"{factor}_neu"].mean()
    if abs(neu_mean) < 1e-4:
        print(f"     [OK] 中性化后 mean≈0（{neu_mean:.2e}），符合 OLS 残差性质")
    else:
        print(f"     [WARN] 中性化后 mean={neu_mean:.6f} 偏大，检查回归逻辑")

    std_ratio = df[f"{factor}_neu"].std() / df[factor].std()
    print(f"     标准差比值（中性化/原始）= {std_ratio:.4f}")
    if std_ratio < 1.0:
        print("     [OK] 中性化后方差变小（市值/行业贡献被剔除）")
    else:
        print("     [WARN] 中性化后方差不减，检查回归逻辑")

    print("\n  5) 计算原始 / 中性化 IC（20 日）...")
    px = pd.read_parquet(PRICE_PATH, columns=["date", "symbol", "close"])
    prices = px.pivot(index="date", columns="symbol", values="close")
    fwd = prices.shift(-PERIOD) / prices - 1.0

    df_reset = df.reset_index()
    ic_orig, ic_neu = [], []
    for dt, g in df_reset.groupby("date"):
        if dt not in fwd.index:
            continue
        r = fwd.loc[dt].reindex(g["symbol"]).values
        o = g[factor].values
        n = g[f"{factor}_neu"].values
        valid_o = np.isfinite(o) & np.isfinite(r)
        valid_n = np.isfinite(n) & np.isfinite(r)
        if valid_o.sum() > 30:
            ic_orig.append(spearmanr(o[valid_o], r[valid_o])[0])
        if valid_n.sum() > 30:
            ic_neu.append(spearmanr(n[valid_n], r[valid_n])[0])

    ic_orig = np.array(ic_orig)
    ic_neu = np.array(ic_neu)
    print(
        f"     原始   IC: mean={np.nanmean(ic_orig):+.4f}  "
        f"IR={np.nanmean(ic_orig) / np.nanstd(ic_orig):+.4f}  "
        f"n={len(ic_orig)}"
    )
    print(
        f"     中性化 IC: mean={np.nanmean(ic_neu):+.4f}  "
        f"IR={np.nanmean(ic_neu) / np.nanstd(ic_neu):+.4f}  "
        f"n={len(ic_neu)}"
    )

    ic_retention = abs(np.nanmean(ic_neu)) / abs(np.nanmean(ic_orig)) * 100
    print(f"     IC 保留率 = {ic_retention:.1f}%")
    if ic_retention > 70:
        print("     [OK] 中性化后 IC 保留 >70%，该因子大部分 alpha 独立于市值/行业")
    elif ic_retention > 40:
        print("     [OK-ish] 保留 40~70%，仍有独立 alpha，但部分来自市值/行业暴露")
    else:
        print("     [WARN] 保留 <40%，该因子 alpha 主要来自市值/行业暴露")

    print("\n[验证] 完成。")


if __name__ == "__main__":
    main()
