"""M4 Step3：因子市值/行业中性化。

对每个因子、每个交易日 t，做横截面 OLS：
    factor_i = α + β · log_mktcap_i + Σ γ_k · industry_k + ε_i
取残差 ε 作为中性化后的因子值。

输入：
    data/processed/factor_panel.parquet
    data/processed/mktcap_panel.parquet
    data/processed/stock_basic.parquet
输出：
    data/processed/factor_panel_neutralized.parquet
        MultiIndex (date, symbol) × 12 因子列

用法（项目根目录、激活 .venv 后）：
    python scripts/validation/neutralize_factors.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
_ROOT = _THIS.parents[2]
sys.path.insert(0, str(_ROOT))

FACTORS = [
    "turnover",
    "amplitude_20",
    "volatility_20",
    "amihud_20",
    "bp",
    "corr_pv_20",
    "reversal_20",
    "momentum_20",
    "rsi_14",
    "bias_20",
    "ep_ttm",
    "boll_dev_20",
]
MIN_STOCKS_PER_DAY = 100
SMOKE = False  # 先只跑 turnover，验证通过后改 False 跑全部 12 个

FACTOR_PANEL = _ROOT / "data" / "processed" / "factor_panel.parquet"
MKTCAP_PANEL = _ROOT / "data" / "processed" / "mktcap_panel.parquet"
STOCK_BASIC = _ROOT / "data" / "processed" / "stock_basic.parquet"
OUT_PATH = _ROOT / "data" / "processed" / "factor_panel_neutralized.parquet"


def main() -> None:
    factors = ["turnover"] if SMOKE else FACTORS
    print(f"[M4 Step3] 中性化因子：{factors}")

    print("  1) 读 stock_basic 行业映射 ...")
    sb = pd.read_parquet(STOCK_BASIC, columns=["symbol", "industry"])
    sb = sb[sb["industry"].notna()]
    industry_map = sb.set_index("symbol")["industry"]
    print(f"     股票数：{len(industry_map)}，行业数：{industry_map.nunique()}")

    # 预构造行业哑变量矩阵（drop_first 避免与截距完全共线）
    ind_dummies = pd.get_dummies(industry_map, drop_first=True).astype(np.float32)
    print(f"     行业哑变量矩阵 shape：{ind_dummies.shape}")

    print("  2) 读 mktcap_panel ...")
    mktcap = pd.read_parquet(MKTCAP_PANEL)
    print(f"     shape：{mktcap.shape}")

    print("  3) 读 factor_panel ...")
    fp = pd.read_parquet(FACTOR_PANEL, columns=["date", "symbol"] + factors)
    print(f"     shape：{fp.shape}")
    fp = fp.set_index(["date", "symbol"])

    print("  4) 逐日横截面回归 ...")
    dates = mktcap.index
    all_symbols = mktcap.columns
    result = {
        f: pd.DataFrame(index=dates, columns=all_symbols, dtype=np.float32)
        for f in factors
    }
    n_ok, n_skip = 0, 0
    grouped = fp.groupby(level=0)

    for i, (dt, df_day) in enumerate(grouped, 1):
        if dt not in mktcap.index:
            n_skip += 1
            continue
        mkt_day = mktcap.loc[dt].dropna()
        mkt_day = mkt_day[mkt_day.index.isin(industry_map.index)]
        if len(mkt_day) < MIN_STOCKS_PER_DAY:
            n_skip += 1
            continue

        df_day = df_day.droplevel(0)  # 去掉 date level，剩 symbol 索引

        # 对齐：因子和市值都有的股票
        common = mkt_day.index.intersection(df_day.index)
        if len(common) < MIN_STOCKS_PER_DAY:
            n_skip += 1
            continue

        mkt_v = mkt_day.loc[common].values
        ind_v = ind_dummies.reindex(common).fillna(0).values
        X_base = np.column_stack(
            [np.ones(len(common), dtype=np.float32), mkt_v, ind_v]
        ).astype(np.float32)

        for factor in factors:
            y = df_day.loc[common, factor].values.astype(np.float32)
            valid = np.isfinite(y)
            if valid.sum() < MIN_STOCKS_PER_DAY:
                continue
            X = X_base[valid]
            y_v = y[valid]
            # lstsq 对秩亏矩阵稳健（返回最小范数解）
            beta, _, _, _ = np.linalg.lstsq(X, y_v, rcond=None)
            resid = y_v - X @ beta
            syms_valid = common[valid]
            result[factor].loc[dt, syms_valid] = resid

        n_ok += 1
        if i % 200 == 0:
            print(f"     已处理 {i} 天（有效 {n_ok}，跳过 {n_skip}）")

    print(f"  处理完毕：有效 {n_ok} 天，跳过 {n_skip} 天")

    print("  5) 组装 MultiIndex 面板 ...")
    stacked = {f: result[f].stack() for f in factors}
    panel = pd.concat(stacked, axis=1)
    panel.index.names = ["date", "symbol"]
    print(f"     shape：{panel.shape}")

    print("  6) 保存 ...")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT_PATH)
    print(f"     已保存：{OUT_PATH}")

    print("\n[M4 Step3] 完成。")


if __name__ == "__main__":
    main()
